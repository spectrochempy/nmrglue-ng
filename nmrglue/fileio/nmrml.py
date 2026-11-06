"""Read and write one-dimensional `nmrML <https://nmrml.org/>`_ arrays.

XML metadata are retained, not inferred from the data or repaired from vendor
names. XML conversion requires optional xmltodict; XSD validation additionally
requires optional lxml and a caller-supplied schema.
"""

import base64
import binascii
from copy import deepcopy
import operator
from pathlib import Path
import zlib
from warnings import warn

import numpy as np

NAMESPACE = 'http://nmrml.org/schema'
BYTE_FORMAT_TO_DTYPE = {
    'float32': '<f4',
    'float64': '<f8',
    'complex64': '<c8',
    'complex128': '<c16',
}


def _read_document(filename):
    import xmltodict

    with open(filename, 'rb') as stream:
        document = xmltodict.parse(stream.read(), disable_entities=True)
    if len(document) != 1:
        raise ValueError('nmrML requires one document root')
    root, metadata = next(iter(document.items()))
    if root == 'nmrML':
        if metadata.get('@xmlns', NAMESPACE) != NAMESPACE:
            raise ValueError('nmrML requires its schema namespace')
        return metadata
    prefix, separator, name = root.partition(':')
    if not separator or name != 'nmrML' or metadata.get('@xmlns:' + prefix) != NAMESPACE:
        raise ValueError('nmrML requires its schema namespace')

    def unprefix(value):
        if isinstance(value, list):
            return [unprefix(item) for item in value]
        if not isinstance(value, dict):
            return value
        result = {}
        for key, item in value.items():
            key = key[len(prefix) + 1:] if key.startswith(prefix + ':') else key
            if key == '@xmlns:' + prefix:
                key = '@xmlns'
            if key in result:
                raise ValueError('nmrML has ambiguous namespace keys')
            result[key] = unprefix(item)
        return result

    return unprefix(metadata)


def _select_array(metadata, read_processed, spectrum_index=None):
    if read_processed:
        spectra = metadata.get('spectrumList') or {}
        if 'spectrumMultiD' in spectra:
            raise ValueError('nmrML profile supports only 1D spectra')
        selected = spectra.get('spectrum1D')
        choices = selected if isinstance(selected, list) else [selected]
        if not selected:
            raise ValueError('nmrML has no processed 1D spectrum')
        if spectrum_index is None:
            if len(choices) != 1:
                raise ValueError('select spectrum_index for multiple nmrML spectra')
            index = 0
        else:
            if isinstance(spectrum_index, (bool, np.bool_)):
                raise ValueError('spectrum_index must be a nonnegative integer')
            index = operator.index(spectrum_index)
            if index < 0 or index >= len(choices):
                raise ValueError('spectrum_index is outside the nmrML spectrum list')
        return choices[index], 'spectrumDataArray'
    if spectrum_index is not None:
        raise ValueError('spectrum_index applies only to processed spectra')
    acquisition = metadata.get('acquisition') or {}
    selected = acquisition.get('acquisition1D')
    if 'acquisitionMultiD' in acquisition or not isinstance(selected, dict):
        raise ValueError('nmrML profile requires one acquisition1D')
    return selected, 'fidData'


def _boolean(value):
    if isinstance(value, str):
        value = value.lower()
    if value in ('true', '1', True):
        return True
    if value in ('false', '0', False):
        return False
    raise ValueError('nmrML compressed must be an XML boolean')


def _get_nmrml_data(fid_dict, data_dtype=None, *, strict=False):
    """Decode little-endian scalar or interleaved-complex binary samples."""
    byte_format = fid_dict['@byteFormat'].lower()
    compressed = _boolean(fid_dict['@compressed'])
    encoded_length = int(fid_dict['@encodedLength'])
    base64_text = ''.join(fid_dict.get('#text', '').split())
    if len(base64_text) != encoded_length:
        message = ('Size of encoded text (%i) does not match stated length (%i)'
                   % (len(base64_text), encoded_length))
        if strict:
            raise ValueError(message)
        warn(message)
    try:
        payload = base64.b64decode(base64_text, validate=True)
    except (binascii.Error, ValueError) as exc:
        raise ValueError('nmrML contains invalid base64 data') from exc
    if compressed:
        try:
            decoder = zlib.decompressobj()
            payload = decoder.decompress(payload) + decoder.flush()
            if not decoder.eof or decoder.unused_data or decoder.unconsumed_tail:
                raise ValueError('nmrML requires one complete zlib stream')
        except zlib.error as exc:
            raise ValueError('nmrML contains invalid zlib data') from exc
    dtype = np.dtype(BYTE_FORMAT_TO_DTYPE[byte_format] if data_dtype is None else data_dtype)
    if dtype.kind not in 'fc' or dtype.itemsize not in (4, 8, 16):
        raise ValueError('nmrML data_dtype must describe floating or complex samples')
    if not payload or len(payload) % dtype.itemsize:
        raise ValueError('nmrML payload does not contain complete samples')
    return np.frombuffer(payload, dtype=dtype)


def _check_count(selected, data, processed):
    params = selected if processed else selected.get('acquisitionParameterSet', {}).get(
        'DirectDimensionParameterSet', {})
    try:
        count = int(params['@numberOfDataPoints'])
    except (KeyError, TypeError, ValueError) as exc:
        raise ValueError('nmrML requires integer numberOfDataPoints') from exc
    counts = (data.size,) if processed or not np.iscomplexobj(data) else (data.size, 2 * data.size)
    if count not in counts:
        raise ValueError('nmrML numberOfDataPoints disagrees with decoded samples')


def read(filename, data_dtype=None, read_processed=False, *, spectrum_index=None,
         strict=False):
    """Read an acquisition or one processed spectrum as ``(metadata, data)``.

    ``read_processed`` retains the historical default False. ``data_dtype``
    overrides the stored binary type explicitly. A file with several processed
    spectra requires a zero-based ``spectrum_index``. XML namespace prefixes,
    whitespace in base64 and XML boolean spellings are accepted. By default an
    encoded-length mismatch warns as before; ``strict=True`` rejects it and
    checks declared point counts. Raw complex counts in existing documents may
    count complex samples or scalar words; neither convention is inferred for
    scientific normalization. No axis, scale, phase or vendor correction occurs.
    """
    metadata = _read_document(filename)
    selected, key = _select_array(metadata, read_processed, spectrum_index)
    data = _get_nmrml_data(selected[key], data_dtype, strict=strict)
    if strict:
        _check_count(selected, data, read_processed)
    return metadata, data


def _validate_xml(payload, schema):
    from lxml import etree

    parser = etree.XMLParser(resolve_entities=False, no_network=True)
    validator = etree.XMLSchema(etree.parse(str(schema), parser))
    document = etree.fromstring(payload, parser)
    if not validator.validate(document):
        raise ValueError('nmrML schema validation failed: ' + str(validator.error_log.last_error))


def write(filename, dic, data, overwrite=False, *, write_processed=False,
          spectrum_index=None, compressed=None, schema=None):
    """Write a 1D array into a copy of existing nmrML metadata.

    The selected array is replaced; other spectra, provenance and annotations
    are preserved. Supply a dictionary returned by :func:`read`, or a complete
    document dictionary with coherent counts and axis metadata. This is not a
    metadata generator: point counts must already match the new data. Complex
    acquisition counts may use complex samples or scalar words, as in historical
    documents. Only float32/64 and complex64/128 are supported, without precision
    reduction. Stored bytes are always little-endian, independent of input byte
    order. ``compressed=None`` preserves the selected array's compression.

    ``schema`` optionally names a local XSD, validated before any output is
    opened (requires lxml). No schema is fetched implicitly. Metadata preserved
    from an invalid legacy document remain invalid unless the caller repairs
    them explicitly. Existing files require ``overwrite=True``. The caller's
    data and dictionary are unchanged.
    """
    import xmltodict

    if np.ma.is_masked(data):
        raise ValueError('nmrML cannot store masked samples')
    values = np.asarray(data)
    formats = {np.dtype(dtype).str[1:]: name for name, dtype in BYTE_FORMAT_TO_DTYPE.items()}
    if values.ndim != 1 or values.size == 0 or values.dtype.str[1:] not in formats:
        raise ValueError('nmrML write requires nonempty 1D float32/64 or complex64/128 data')
    metadata = deepcopy(dic)
    if metadata.get('@xmlns') != NAMESPACE:
        raise ValueError('nmrML requires its schema namespace')
    selected, key = _select_array(metadata, write_processed, spectrum_index)
    _check_count(selected, values, write_processed)
    if compressed is None:
        compress = _boolean(selected[key]['@compressed'])
    elif isinstance(compressed, (bool, np.bool_)):
        compress = bool(compressed)
    else:
        raise ValueError('compressed must be boolean or None')
    byte_format = formats[values.dtype.str[1:]]
    payload = values.astype(BYTE_FORMAT_TO_DTYPE[byte_format], copy=False).tobytes()
    if compress:
        payload = zlib.compress(payload)
    encoded = base64.b64encode(payload).decode('ascii')
    selected[key] = {'@byteFormat': byte_format, '@compressed': str(compress).lower(),
                     '@encodedLength': str(len(encoded)), '#text': encoded}
    payload = xmltodict.unparse({'nmrML': metadata}, encoding='utf-8').encode('utf-8')
    if schema is not None:
        _validate_xml(payload, schema)
    with Path(filename).open('wb' if overwrite else 'xb') as stream:
        stream.write(payload)
