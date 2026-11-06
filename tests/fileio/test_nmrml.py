"""Autonomous nmrML binary/metadata round trips and schema validation."""

import base64
from copy import deepcopy
from pathlib import Path
import struct
import zlib

import numpy as np
import pytest

from nmrglue.fileio import nmrml

pytestmark = pytest.mark.optional_dependency
xmltodict = pytest.importorskip('xmltodict')
SCHEMA = Path(__file__).parents[1] / 'fixtures' / 'nmrml' / 'nmrML.xsd'


def document(size=8, processed=True):
    """Synthetic metadata ordered according to the pinned official XSD."""
    cv = {'@cvRef': 'NMR', '@accession': 'NMR:1000349', '@name': 'uniform sampling'}
    def value(number, unit):
        return {'@value': str(number), '@unitName': unit}
    direct = {
        '@decoupled': 'false', '@numberOfDataPoints': str(2 * size),
        'acquisitionNucleus': {'@cvRef': 'CHEBI', '@accession': 'CHEBI_49637', '@name': 'hydrogen atom'},
        'effectiveExcitationField': value(400, 'megaHertz'),
        'sweepWidth': value(2000, 'hertz'), 'pulseWidth': value(10, 'microsecond'),
        'irradiationFrequency': value(400, 'megaHertz'),
        'irradiationFrequencyOffset': value(0, 'hertz'), 'samplingStrategy': cv,
    }
    encoded = base64.b64encode(np.arange(size, dtype='<c16').tobytes()).decode()
    binary = {'@compressed': 'false', '@byteFormat': 'complex128',
              '@encodedLength': str(len(encoded)), '#text': encoded}
    result = {
        '@xmlns': nmrml.NAMESPACE, '@version': '1.0.rc1',
        'cvList': {'cv': {'@id': 'NMR', '@fullName': 'NMR CV',
                         '@URI': 'https://nmrml.org/cv', '@version': '1'}},
        'fileDescription': {'fileContent': {'cvParam': {'@cvRef': 'NMR', '@accession': 'NMR:1400165', '@name': '1D NMR acquisition parameter set'}}},
        'instrumentConfigurationList': {'instrumentConfiguration': {'@id': 'instrument'}},
        'acquisition': {'acquisition1D': {'acquisitionParameterSet': {
            '@numberOfSteadyStateScans': '0', '@numberOfScans': '1',
            'sampleContainer': {'@cvRef': 'NMR', '@accession': 'NMR:1400132', '@name': 'NMR Sample tube'}, 'sampleAcquisitionTemperature': value(298, 'kelvin'),
            'spinningRate': value(0, 'hertz'), 'relaxationDelay': value(1, 'second'),
            'pulseSequence': {}, 'DirectDimensionParameterSet': direct}, 'fidData': binary}},
    }
    result['cvList']['cv'] = [result['cvList']['cv'], {'@id': 'CHEBI', '@fullName': 'Chemical Entities of Biological Interest', '@URI': 'http://purl.obolibrary.org/obo/chebi.owl', '@version': '1'}]
    if processed:
        result['spectrumList'] = {'spectrum1D': {
            '@id': 'spectrum', '@numberOfDataPoints': str(size),
            'spectrumDataArray': deepcopy(binary),
            'xAxis': {'@unitName': 'parts per million', '@startValue': '10', '@endValue': '-2'},
        }}
    return result


@pytest.mark.parametrize('dtype', ['<f4', '>f4', '<f8', '>f8', '<c8', '>c8', '<c16', '>c16'])
@pytest.mark.parametrize('compressed', [False, True])
@pytest.mark.parametrize('processed', [False, True])
def test_roundtrip_precision_byteorder_and_dictionary_ownership(tmp_path, dtype, compressed, processed):
    values = np.arange(8, dtype='f8') - 2
    if np.dtype(dtype).kind == 'c':
        values = values + 1j * np.arange(8, dtype='f8')
    values = values.astype(dtype)
    metadata = document(processed=processed)
    if not processed and not np.iscomplexobj(values):
        metadata['acquisition']['acquisition1D']['acquisitionParameterSet']['DirectDimensionParameterSet']['@numberOfDataPoints'] = '8'
    original, original_values = deepcopy(metadata), values.copy()
    path = tmp_path / 'written.nmrML'
    nmrml.write(path, metadata, values, write_processed=processed, compressed=compressed)
    result, decoded = nmrml.read(path, read_processed=processed, strict=True)
    np.testing.assert_array_equal(decoded, values)
    assert decoded.dtype == values.dtype.newbyteorder('<')
    assert metadata == original
    np.testing.assert_array_equal(values, original_values)
    selected, key = nmrml._select_array(result, processed)
    encoded = selected[key]
    payload = base64.b64decode(encoded['#text'])
    if compressed:
        payload = zlib.decompress(payload)
    scalar = 'f' if values.real.dtype.itemsize == 4 else 'd'
    words = struct.unpack('<' + scalar * (len(payload) // values.real.dtype.itemsize), payload)
    assert words[0] == values[0].real
    if np.iscomplexobj(values):
        assert words[1] == values[0].imag
    second = tmp_path / 'second.nmrML'
    nmrml.write(second, result, decoded, write_processed=processed)
    np.testing.assert_array_equal(nmrml.read(second, read_processed=processed, strict=True)[1], values)


@pytest.mark.parametrize('processed', [False, True])
def test_writer_passes_official_schema_and_validates_before_open(tmp_path, processed):
    pytest.importorskip('lxml')
    metadata = document(processed=processed)
    path = tmp_path / 'schema.nmrML'
    values = np.arange(8).astype('complex128')
    nmrml.write(path, metadata, values, write_processed=processed, schema=SCHEMA)
    nmrml.read(path, read_processed=processed, strict=True)
    del metadata['instrumentConfigurationList']
    before = path.read_bytes()
    with pytest.raises(ValueError, match='schema validation'):
        nmrml.write(path, metadata, values, write_processed=processed, schema=SCHEMA, overwrite=True)
    assert path.read_bytes() == before


def test_processed_spectrum_selection_preserves_other_arrays(tmp_path):
    metadata = document()
    first = metadata['spectrumList']['spectrum1D']
    metadata['spectrumList']['spectrum1D'] = [first, {**deepcopy(first), '@id': 'second'}]
    path = tmp_path / 'multiple.nmrML'
    nmrml.write(path, metadata, np.arange(8, dtype='f8'), write_processed=True, spectrum_index=1)
    with pytest.raises(ValueError, match='spectrum_index'):
        nmrml.read(path, read_processed=True)
    result, values = nmrml.read(path, read_processed=True, spectrum_index=1, strict=True)
    assert result['spectrumList']['spectrum1D'][0] == first
    np.testing.assert_array_equal(values, np.arange(8))


def test_encoded_whitespace_booleans_and_invalid_payloads():
    text = base64.b64encode(struct.pack('<ff', 1, -2)).decode()
    array = {'@byteFormat': 'float32', '@compressed': '0', '@encodedLength': str(len(text)),
             '#text': ' \n'.join([text[:4], text[4:]])}
    np.testing.assert_array_equal(nmrml._get_nmrml_data(array, strict=True), [1, -2])
    for legacy_boolean in ('false', 'False', 'FALSE'):
        np.testing.assert_array_equal(
            nmrml._get_nmrml_data({**array, '@compressed': legacy_boolean}, strict=True),
            [1, -2],
        )
    array['@encodedLength'] = '1'
    with pytest.warns(UserWarning, match='Size of encoded'):
        nmrml._get_nmrml_data(array)
    with pytest.raises(ValueError, match='Size of encoded'):
        nmrml._get_nmrml_data(array, strict=True)
    for key, value in [('@compressed', 'maybe'), ('#text', '!!!!')]:
        bad = {**array, key: value, '@encodedLength': '4'}
        with pytest.raises(ValueError):
            nmrml._get_nmrml_data(bad, strict=True)


def test_writer_rejects_unsupported_shape_mask_count_and_overwrite(tmp_path):
    path = tmp_path / 'safe.nmrML'
    metadata = document()
    for values in (np.arange(8), np.zeros((2, 4)), np.zeros(7, dtype='f8'),
                   np.ma.array(np.zeros(8), mask=[True] + [False] * 7)):
        with pytest.raises(ValueError):
            nmrml.write(path, metadata, values, write_processed=True)
        assert not path.exists()
    nmrml.write(path, metadata, np.zeros(8), write_processed=True)
    before = path.read_bytes()
    with pytest.raises(FileExistsError):
        nmrml.write(path, metadata, np.ones(8), write_processed=True)
    assert path.read_bytes() == before
    nmrml.write(path, metadata, np.ones(8), write_processed=True, overwrite=True)
    np.testing.assert_array_equal(nmrml.read(path, read_processed=True)[1], np.ones(8))


def test_prefixed_namespace_roundtrip(tmp_path):
    metadata = document()
    path = tmp_path / 'namespace.nmrML'
    nmrml.write(path, metadata, np.arange(8, dtype='f8'), write_processed=True)
    import xml.etree.ElementTree as ET
    ET.register_namespace('nmr', nmrml.NAMESPACE)
    ET.parse(path).write(path, xml_declaration=True)
    parsed, values = nmrml.read(path, read_processed=True, strict=True)
    assert parsed['@xmlns'] == nmrml.NAMESPACE
    np.testing.assert_array_equal(values, np.arange(8))


def test_legacy_namespace_free_document_and_explicit_dtype_override(tmp_path):
    metadata = document()
    del metadata['@xmlns']
    path = tmp_path / 'legacy.nmrML'
    path.write_text(xmltodict.unparse({'nmrML': metadata}))
    _, decoded = nmrml.read(path, data_dtype='<f8')
    expected = np.zeros(16)
    expected[::2] = np.arange(8)
    np.testing.assert_array_equal(decoded, expected)


@pytest.mark.parametrize('suffix', [b'extra', zlib.compress(b'other')])
def test_decoder_rejects_trailing_zlib_streams(suffix):
    payload = zlib.compress(struct.pack('<dd', 1, 2)) + suffix
    encoded = base64.b64encode(payload).decode()
    metadata = {'@compressed': '1', '@byteFormat': 'float64',
                '@encodedLength': str(len(encoded)), '#text': encoded}
    with pytest.raises(ValueError, match='complete zlib'):
        nmrml._get_nmrml_data(metadata, strict=True)


@pytest.mark.parametrize('variant', ['duplicate-root-alias', 'mixed-acquisition-prefix'])
def test_schema_valid_namespace_aliases_are_resolved_by_uri(tmp_path, variant):
    etree = pytest.importorskip('lxml.etree')
    fixture = SCHEMA.parent / 'synthetic.nmrML'
    text = fixture.read_text()
    if variant == 'duplicate-root-alias':
        text = text.replace('<nmrML ', '<n:nmrML xmlns:n="' + nmrml.NAMESPACE + '" ', 1).replace('</nmrML>', '</n:nmrML>')
    else:
        text = text.replace('<acquisition>', '<m:acquisition xmlns:m="' + nmrml.NAMESPACE + '">').replace('</acquisition>', '</m:acquisition>')
    etree.XMLSchema(etree.parse(str(SCHEMA))).assertValid(etree.fromstring(text.encode()))
    path = tmp_path / 'namespaces.nmrML'
    path.write_text(text)
    metadata, data = nmrml.read(path, strict=True)
    np.testing.assert_array_equal(data, np.arange(8))
    output = tmp_path / 'copy.nmrML'
    nmrml.write(output, metadata, data, schema=SCHEMA)
    np.testing.assert_array_equal(nmrml.read(output, strict=True)[1], data)
