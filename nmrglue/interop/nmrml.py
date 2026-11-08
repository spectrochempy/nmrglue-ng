"""Explicit nmrML profiles without vendor dispatch."""

from __future__ import annotations

import base64
import hashlib
from numbers import Real
import os
import operator
from urllib.parse import urlsplit
import zlib

import numpy as np

from ..fileio import nmrml
from .result import Axis, Component, NormalizedAcquisition, ReadResult, Reference


def _positive(value, name):
    if isinstance(value, (bool, np.bool_)) or not isinstance(value, Real):
        raise ValueError(name + ' must be a positive finite scalar')
    value = float(value)
    if not np.isfinite(value) or value <= 0:
        raise ValueError(name + ' must be a positive finite scalar')
    return value


def _number(value, name):
    try:
        result = float(value)
    except (TypeError, ValueError, OverflowError) as exc:
        raise ValueError('nmrML requires numeric ' + name) from exc
    if not np.isfinite(result):
        raise ValueError('nmrML requires finite ' + name)
    return result


def _vocabulary(document, reference, family, description):
    entries = (document.get('cvList') or {}).get('cv') or []
    entries = entries if isinstance(entries, list) else [entries]
    matches = [entry for entry in entries if entry.get('@id') == reference]
    if len(matches) != 1:
        raise ValueError('nmrML ' + description + ' requires one declared CV reference')
    uri = urlsplit(matches[0].get('@URI', ''))
    path = uri.path.rstrip('/')
    if family == 'NMR':
        valid = uri.netloc.lower() == 'nmrml.org' and (path == '/cv' or path.startswith('/cv/'))
    else:
        generic_obo = path == '/obo' and matches[0].get('@fullName', '').strip().lower() == 'unit ontology'
        valid = (uri.netloc.lower() == 'purl.obolibrary.org' and (generic_obo or path == '/obo/uo.owl')) or (
            uri.netloc.lower() == 'unit-ontology.googlecode.com' and path == '/svn/trunk/uo.owl'
        )
    if uri.scheme not in ('http', 'https') or uri.query or uri.fragment or not valid:
        raise ValueError('nmrML ' + description + ' has an unknown CV vocabulary')


def _unit(document, value, allowed):
    aliases = {'hz': 'Hz', 'hertz': 'Hz', 'ppm': 'ppm', 'parts per million': 'ppm'}
    name = value.get('@unitName', '').strip().lower()
    unit = aliases.get(name)
    if unit not in allowed:
        raise ValueError('nmrML requires explicit compatible unit names')
    accession = value.get('@unitAccession')
    expected = {'Hz': 'UO:0000106', 'ppm': 'UO:0000169'}[unit]
    if accession is not None:
        for uri in ('http://purl.obolibrary.org/obo/', 'https://purl.obolibrary.org/obo/'):
            if accession.startswith(uri):
                accession = accession[len(uri):]
                break
        accession = accession.replace('UO_', 'UO:', 1)
        if accession != expected:
            raise ValueError('nmrML unit name and unit accession contradict each other')
    reference = value.get('@unitCvRef')
    if reference is not None:
        _vocabulary(document, reference, 'UO', 'unit')
    return unit


def _uniform_sampling(document, sampling):
    accession = sampling.get('@accession')
    if accession not in ('NMR:1000349', 'NMR_1000349', '1000349'):
        raise ValueError('nmrML time profile requires declared uniform sampling')
    name = sampling.get('@name', '').strip().lower()
    if name != 'uniform sampling':
        raise ValueError('nmrML sampling label contradicts its uniform accession')
    _vocabulary(document, sampling.get('@cvRef'), 'NMR', 'sampling')


def _describe(document, values, options, source):
    data = np.asarray(values)
    if (np.ma.is_masked(values) or data.ndim != 1 or data.size < 2
        or data.dtype.kind not in 'fc' or not np.isfinite(data).all()):
        raise ValueError('nmrML interop requires one finite unmasked 1D floating array')
    if document.get('@xmlns') != nmrml.NAMESPACE:
        raise ValueError('nmrML interop requires the schema namespace')
    processed = options['read_processed']
    selected, key = nmrml._select_array(document, processed, options['spectrum_index'])
    nmrml._check_count(selected, data, processed)
    decoded = nmrml._get_nmrml_data(selected[key], options['data_dtype'], strict=True)
    if decoded.dtype != data.dtype or not np.array_equal(decoded, data):
        raise ValueError('nmrML samples disagree with their encoded source')
    obs = options['observation_frequency_mhz']
    if obs is not None:
        obs = _positive(obs, 'observation_frequency_mhz')
    reference = Reference(observation_frequency=obs,
                          observation_frequency_unit='MHz' if obs is not None else None,
                          source='unknown')
    acquisition = {'normalization': 'none'}
    if obs is not None:
        acquisition['observation_frequency_mhz'] = obs
        acquisition['reference_evidence'] = 'explicit caller-supplied frequency, not inferred from acquisition'
    if processed:
        endpoint = options['axis_endpoint']
        if endpoint not in ('last-point', 'outer-edge'):
            raise ValueError('nmrML requires explicit axis_endpoint: last-point or outer-edge')
        xaxis = selected.get('xAxis') or {}
        unit = _unit(document, xaxis, ('Hz', 'ppm'))
        start = _number(xaxis.get('@startValue'), 'xAxis startValue')
        end = _number(xaxis.get('@endValue'), 'xAxis endValue')
        axis_values = np.linspace(start, end, data.size, endpoint=endpoint == 'last-point')
        if unit == 'ppm' and obs is not None:
            axis_values = axis_values * obs
            unit = 'Hz'
        domain = 'frequency'
        acquisition['axis_endpoint'] = endpoint
    else:
        if not np.iscomplexobj(data):
            raise ValueError('nmrML time profile requires complex samples')
        params = selected['acquisitionParameterSet']['DirectDimensionParameterSet']
        count_unit = options['raw_point_count']
        if count_unit not in ('complex', 'scalar'):
            raise ValueError('nmrML requires explicit raw_point_count: complex or scalar')
        expected = data.size * (2 if count_unit == 'scalar' else 1)
        if int(params['@numberOfDataPoints']) != expected:
            raise ValueError('nmrML raw point count disagrees with selected count convention')
        sampling = params.get('samplingStrategy') or {}
        _uniform_sampling(document, sampling)
        if params.get('samplingTimePoints') is not None:
            raise ValueError('nmrML explicit/nonuniform time grids are not qualified')
        sw = params.get('sweepWidth') or {}
        _unit(document, sw, ('Hz',))
        width = _positive(_number(sw.get('@value'), 'sweepWidth'), 'sweepWidth')
        axis_values = np.arange(data.size, dtype=float) / width
        unit, domain = 's', 'time'
        acquisition['spectral_width_hz'] = width
        acquisition['raw_point_count'] = count_unit
    differences = np.diff(axis_values)
    if (not np.isfinite(axis_values).all()
        or not (np.all(differences > 0) or np.all(differences < 0))):
        raise ValueError('nmrML axis must be finite and strictly monotonic')
    direction = 'increasing' if differences[0] > 0 else 'decreasing'
    mode = 'complex' if np.iscomplexobj(data) else 'real'
    return ReadResult(
        data=data, axes=(Axis(values=axis_values, unit=unit, domain=domain,
                             direction=direction, reference=reference),),
        components=(Component(name=mode, data=data),),
        metadata={'document': document, 'profile_options': options},
        applied_corrections={'normalization': 'none', 'conjugation': 'none'},
        format='nmrml-1d', source=source, domains=(domain,), encoding=(mode,),
        dimensions={'points': data.size}, acquisition=acquisition, diagnostics=(),
    )


def read_nmrml_1d(filename, *, read_processed=False, spectrum_index=None,
                  axis_endpoint=None, raw_point_count=None,
                  observation_frequency_mhz=None, data_dtype=None):
    """Describe one strictly decoded nmrML acquisition or processed spectrum.

    Processed xAxis requires an explicit endpoint convention: ``last-point``
    includes endValue; ``outer-edge`` excludes it. The XSD does not resolve this
    ambiguity. Hz/ppm units must be present. Acquisition frequency is never
    substituted for processing calibration: without an explicitly supplied MHz
    reference a ppm axis remains ppm, and cannot be converted to Hz here.
    Supplied MHz is recorded as caller evidence with unknown reference source,
    not certified as chemical calibration.

    Complex FIDs require ``raw_point_count='scalar'`` or ``'complex'``, declared
    uniform sampling and a positive Hz sweepWidth. Times are i/SW seconds.
    Sign, phase, gain, digital filtering and quadrature correction are not
    implicit. Supplied unit accessions/CV references and the complete uniform
    sampling term must be consistent; this is not whole-document CV validation. Unsupported/ambiguous metadata fail closed. No vendor inference,
    multidimensional data, nonuniform sampling or XY-pair layouts are qualified.
    """
    document, data = nmrml.read(filename, data_dtype=data_dtype, read_processed=read_processed,
                                 spectrum_index=spectrum_index, strict=True)
    options = {'read_processed': bool(read_processed), 'spectrum_index': spectrum_index,
               'axis_endpoint': axis_endpoint, 'raw_point_count': raw_point_count,
               'observation_frequency_mhz': observation_frequency_mhz,
               'data_dtype': None if data_dtype is None else np.dtype(data_dtype).str}
    return _describe(document, data, options, os.fspath(filename))


def normalize_nmrml_1d(result, *, conjugation=None):
    """Validate a 1D description and explicitly select raw complex sign policy.

    For FIDs ``conjugation`` must be ``'none'`` or ``'conjugate'``; this is a
    caller decision supported by external evidence, never selected by origin.
    Processed spectra accept only None/'none', preserving their samples.
    Source bytes/metadata and descriptive arrays are unchanged.
    """
    if not isinstance(result, ReadResult) or result.format != 'nmrml-1d':
        raise ValueError('normalize_nmrml_1d requires a nmrml-1d ReadResult')
    checked = _describe(result.metadata['document'], result.data,
                        result.metadata['profile_options'], result.source)
    if (result.domains != checked.domains or result.encoding != checked.encoding
        or len(result.axes) != 1 or len(result.components) != 1
        or result.components[0].name != checked.components[0].name
        or not np.array_equal(result.components[0].data, checked.data)
        or dict(result.applied_corrections) != dict(checked.applied_corrections)):
        raise ValueError('nmrML description disagrees with its source')
    axis, expected = result.axes[0], checked.axes[0]
    if (axis.unit != expected.unit or axis.domain != expected.domain
        or axis.direction != expected.direction or axis.reference != expected.reference
        or axis.values is None or not np.array_equal(axis.values, expected.values)):
        raise ValueError('nmrML axis disagrees with its source and explicit conventions')
    time_domain = checked.domains == ('time',)
    if (time_domain and conjugation not in ('none', 'conjugate')) or (
        not time_domain and conjugation not in (None, 'none')
    ):
        raise ValueError('nmrML FIDs require explicit conjugation; spectra are never conjugated')
    sign = conjugation or 'none'
    data = np.conjugate(checked.data) if sign == 'conjugate' else checked.data
    mode = checked.encoding[0]
    operation = {'name': 'normalize-nmrml-1d', 'stage': 'acquisition' if time_domain else 'processing',
                 'input_dimensions': ('storage',), 'output_dimensions': ('F2',),
                 'axis': 'F2', 'scale': None, 'conjugation': sign, 'sign': 'none',
                 'permutation': None, 'evidence': 'explicit nmrML 1D profile options'}
    return NormalizedAcquisition(
        data=data, axes=checked.axes, dimensions=('F2',), physical_dimensions=('F2',),
        domains=checked.domains, quadrature_mode=mode + '-1d', branch_order=(mode,),
        normalization_state='storage-normalized',
        normalization_profile='nmrml-' + ('time' if time_domain else 'spectrum') + '-1d-v1',
        applied_operations=(operation,), acquisition=checked.acquisition,
        provenance={'source': result.source, 'format': result.format},
        metadata=checked.metadata, encoding=checked.encoding, diagnostics=checked.diagnostics,
    )


_2D_DIMS = ('F1', 'F2')
_2D_DOMAINS = ('frequency', 'frequency')
_2D_ENCODING = ('real', 'real')


def _spectrum_2d_axis(document, grid, size, endpoint, label):
    unit = _unit(document, grid, ('Hz', 'ppm'))
    start = _number(grid.get('@startValue'), label + ' startValue')
    end = _number(grid.get('@endValue'), label + ' endValue')
    values = np.linspace(start, end, size, endpoint=endpoint == 'last-point')
    differences = np.diff(values)
    if not np.isfinite(values).all() or not (
        np.all(differences > 0) or np.all(differences < 0)
    ):
        raise ValueError('nmrML axis must be finite and strictly monotonic')
    return Axis(values=values, unit=unit, label=label, domain='frequency',
                direction='increasing' if start < end else 'decreasing')


def _describe_2d(document, options, source):
    if document.get('@xmlns') != nmrml.NAMESPACE:
        raise ValueError('nmrML interop requires the schema namespace')
    spectra = document.get('spectrumList') or {}
    if not isinstance(spectra, dict) or not spectra.get('spectrumMultiD') or 'spectrum1D' in spectra:
        raise ValueError('nmrML requires a multidimensional spectrum list')
    spectrum = nmrml._select_spectrum(spectra['spectrumMultiD'], options['spectrum_index'])
    if not isinstance(spectrum, dict) or not (
        isinstance(spectrum.get('firstDimensionProcessingParameterSet'), (dict, type(None)))
        and 'firstDimensionProcessingParameterSet' in spectrum
        and 'higherDimensionProcessingParameterSet' in spectrum
        and isinstance(spectrum['higherDimensionProcessingParameterSet'], (dict, type(None)))
        and 'projected3DProcessingParamaterSet' not in spectrum
    ):
        raise ValueError('nmrML requires a non-projected spectrum with two dimensions')
    try:
        sizes = tuple(options['shape'])
        if len(sizes) != 2 or any(isinstance(size, (bool, np.bool_)) for size in sizes):
            raise ValueError
        rows, cols = map(operator.index, sizes)
        if min(rows, cols) < 2:
            raise ValueError
    except (TypeError, ValueError) as exc:
        raise ValueError('nmrML requires a two-dimensional shape with sizes >= 2') from exc

    order = options['storage_order']
    endpoint = options['axis_endpoint']
    if order not in ('x-fastest', 'y-fastest'):
        raise ValueError('nmrML requires storage_order: x-fastest or y-fastest')
    if endpoint not in ('last-point', 'outer-edge'):
        raise ValueError('nmrML requires axis_endpoint: last-point or outer-edge')
    binary = spectrum.get('spectrumDataArray')
    if not isinstance(binary, dict) or binary.get('@byteFormat', '').lower() not in ('float32', 'float64'):
        raise ValueError('nmrML 2D requires a real float32 or float64 spectrum array')
    if not {'@compressed', '@encodedLength'} <= binary.keys():
        raise ValueError('nmrML spectrum array requires compressed and encodedLength')
    flat = nmrml._get_nmrml_data(binary, strict=True)
    nmrml._check_count(spectrum, flat, True)
    if flat.size != rows * cols or not np.isfinite(flat).all():
        raise ValueError('nmrML samples must be finite and match the supplied 2D shape')
    xaxis = spectrum.get('xAxis')
    if not isinstance(xaxis, dict):
        raise ValueError('nmrML 2D requires the stored xAxis')
    y_start, y_end, y_unit = options['indirect_axis']
    if not isinstance(y_unit, str):
        raise ValueError('nmrML requires an explicit indirect axis unit')
    yaxis = {'@startValue': y_start, '@endValue': y_end, '@unitName': y_unit}
    axes = (_spectrum_2d_axis(document, yaxis, rows, endpoint, 'F1'),
            _spectrum_2d_axis(document, xaxis, cols, endpoint, 'F2'))
    data = flat.reshape((rows, cols), order='C' if order == 'x-fastest' else 'F')
    return ReadResult(
        data=data, axes=axes, components=(Component('real', data),),
        metadata={'document': document, 'profile_options': options},
        applied_corrections={}, diagnostics=(), format='nmrml-2d-spectrum',
        source=source, domains=_2D_DOMAINS, encoding=_2D_ENCODING,
        dimensions={'axis_order': _2D_DIMS, 'shape': data.shape},
        acquisition={'axis_endpoint': endpoint, 'storage_order': order,
                     'indirect_axis_source': 'caller'},
    )


def read_nmrml_2d(filename, *, shape, indirect_axis, storage_order,
                  axis_endpoint, spectrum_index=None):
    """Read a real 2D processed nmrML spectrum as a matrix in (F1, F2) order.

    The schema provides the F2 xAxis. Supply the matrix shape (F1, F2),
    the F1 grid as (start, end, unit), and the binary order as
    ``x-fastest`` or ``y-fastest``. Both axes use the explicitly supplied
    ``last-point`` or ``outer-edge`` endpoint convention. Axis units are Hz
    or ppm. Geometry supplied by the caller should come from a trusted
    reference for the processed spectrum.
    """
    try:
        shape = tuple(shape)
        indirect_axis = tuple(indirect_axis)
    except TypeError as exc:
        raise ValueError('nmrML requires shape and indirect_axis sequences') from exc
    if len(indirect_axis) != 3:
        raise ValueError('nmrML indirect_axis requires (start, end, unit)')
    options = {'shape': shape, 'indirect_axis': indirect_axis, 'storage_order': storage_order,
               'axis_endpoint': axis_endpoint, 'spectrum_index': spectrum_index}
    return _describe_2d(nmrml._read_document(filename), options, os.fspath(filename))


def normalize_nmrml_2d(result):
    """Validate the real 2D profile and preserve its calibrated plane."""
    if not isinstance(result, ReadResult) or result.format != 'nmrml-2d-spectrum':
        raise ValueError('normalize_nmrml_2d requires a nmrml-2d-spectrum ReadResult')
    checked = _describe_2d(result.metadata['document'], result.metadata['profile_options'],
                           result.source)
    if (
        result.data.dtype != checked.data.dtype or not np.array_equal(result.data, checked.data)
        or result.domains != checked.domains or result.encoding != checked.encoding
        or result.dimensions != checked.dimensions or result.acquisition != checked.acquisition
        or result.applied_corrections or len(result.components) != 1
        or result.components[0].name != 'real'
        or result.components[0].data.dtype != checked.data.dtype
        or not np.array_equal(result.components[0].data, checked.data)
        or len(result.axes) != 2
    ):
        raise ValueError('nmrML 2D description disagrees with its source')
    for axis, expected in zip(result.axes, checked.axes, strict=True):
        if ((axis.unit, axis.domain, axis.direction, axis.reference, axis.label)
                != (expected.unit, expected.domain, expected.direction, expected.reference,
                    expected.label)
                or not np.array_equal(axis.values, expected.values)):
            raise ValueError('nmrML 2D axis disagrees with its source and explicit conventions')
    operation = {'name': 'normalize-nmrml-spectrum-2d', 'stage': 'processing',
                 'input_dimensions': _2D_DIMS, 'output_dimensions': _2D_DIMS,
                 'axis': None, 'scale': None, 'conjugation': 'none', 'sign': 'none',
                 'permutation': None, 'evidence': 'explicit nmrML 2D profile options'}
    return NormalizedAcquisition(
        data=checked.data, axes=checked.axes, dimensions=_2D_DIMS,
        physical_dimensions=_2D_DIMS, domains=checked.domains,
        quadrature_mode='real-2d', branch_order=('real',),
        normalization_state='storage-normalized',
        normalization_profile='nmrml-spectrum-2d-real-v1',
        applied_operations=(operation,), acquisition=checked.acquisition,
        provenance={'source': result.source, 'format': result.format},
        metadata=checked.metadata, encoding=checked.encoding, diagnostics=checked.diagnostics,
    )


_HSQC_FID_SHA256 = '5e5672166dcdcb110d4838375b47b8660c18fba89d55f857a5949b13ce3e45af'
_RAW_2D_DOMAINS = ('time', 'time')


def _read_hsqc_legacy_payload(binary, shape):
    """Decode the checksum-pinned payload from the official HSQC example."""
    encoded = ''.join(binary.get('#text', '').split()).encode('ascii')
    if (
        shape != (256, 2048)
        or binary.get('@byteFormat') != 'complex128'
        or binary.get('@compressed') != 'true'
        or binary.get('@encodedLength') != '11184816'
        or hashlib.sha256(encoded).hexdigest() != _HSQC_FID_SHA256
    ):
        raise ValueError('nmrML official HSQC compatibility requires the original payload and geometry')
    compressed = base64.b64decode(encoded, validate=True)
    # The encoded text is no longer needed while zlib allocates its output.
    del encoded
    decoder = zlib.decompressobj()
    payload = decoder.decompress(compressed)
    if not decoder.eof or len(payload) != 8388608 or decoder.unused_data.strip(b'\0'):
        raise ValueError('nmrML official HSQC payload has invalid padding or size')
    return np.frombuffer(payload, dtype='<c16')


def _raw_2d_count(params):
    try:
        count = int(params['@numberOfDataPoints'])
    except (KeyError, TypeError, ValueError) as exc:
        raise ValueError('nmrML requires integer numberOfDataPoints') from exc
    if count < 1:
        raise ValueError('nmrML raw counts must be positive')
    return count


def _describe_raw_2d(document, options, source):
    if document.get('@xmlns') != nmrml.NAMESPACE:
        raise ValueError('nmrML interop requires the schema namespace')
    acquisition = document.get('acquisition') or {}
    selected = acquisition.get('acquisitionMultiD') if isinstance(acquisition, dict) else None
    if not isinstance(selected, dict) or 'acquisition1D' in acquisition:
        raise ValueError('nmrML requires one acquisitionMultiD')
    params = selected.get('acquisitionParameterSet')
    if not isinstance(params, dict):
        raise ValueError('nmrML requires acquisitionParameterSet')
    direct = params.get('directDimensionParameterSet')
    indirect = params.get('indirectDimensionParameterSet')
    encoding = params.get('encodingScheme')
    if not all(isinstance(value, dict) for value in (direct, indirect, encoding)):
        raise ValueError('nmrML requires one direct and one indirect dimension and an encoding scheme')

    cols = _raw_2d_count(direct)
    count_unit = options['direct_point_count']
    if count_unit not in ('scalar', 'complex'):
        raise ValueError('nmrML requires direct_point_count: scalar or complex')
    if count_unit == 'scalar':
        if cols % 2:
            raise ValueError('nmrML scalar direct point count must be even')
        cols //= 2
    shape = (_raw_2d_count(indirect), cols)
    binary = selected.get('fidData')
    if (not isinstance(binary, dict) or not {'@compressed', '@encodedLength'} <= binary.keys()
        or binary.get('@byteFormat', '').lower() not in ('complex64', 'complex128')):
        raise ValueError('nmrML raw 2D requires complex64 or complex128 fidData')
    if options['official_hsqc_compatibility']:
        flat = _read_hsqc_legacy_payload(binary, shape)
    else:
        flat = nmrml._get_nmrml_data(binary, strict=True)
    if flat.size != shape[0] * shape[1] or not np.isfinite(flat).all():
        raise ValueError('nmrML raw 2D samples must be finite and match the declared counts')
    data = flat.reshape(shape)
    return ReadResult(
        data=data, axes=(Axis(label='trace'), Axis(label='sample')),
        components=(Component('stored-traces', data),),
        metadata={'document': document, 'profile_options': options},
        applied_corrections={}, diagnostics=(), format='nmrml-raw-2d',
        source=source, domains=_RAW_2D_DOMAINS, encoding=('unknown', 'complex'),
        dimensions={'axis_order': ('trace', 'sample'), 'shape': shape},
        acquisition={'direct_point_count': count_unit},
    )


def read_nmrml_raw_2d(filename, *, direct_point_count, official_hsqc_compatibility=False):
    """Decode a 2D nmrML FID stored as contiguous complex traces.

    Supply the direct count convention, scalar words or complex samples.
    The indirect count must be the number of stored traces, including
    both branches of any pair. The HSQC compatibility option accepts
    only the checksum-pinned payload of the official HSQC example.
    """
    options = {'direct_point_count': direct_point_count,
               'official_hsqc_compatibility': official_hsqc_compatibility}
    return _describe_raw_2d(nmrml._read_document(filename), options, os.fspath(filename))


def normalize_nmrml_raw_2d(result, *, indirect_dwell_s, confirm_adjacent_pairs=False):
    """Normalize uniform echo/anti-echo storage into two complex channels.

    Confirm that adjacent traces belong to the same indirect increment
    and supply the time between pairs from the acquisition provenance.
    Channels preserve the first and second stored traces of each pair.
    Coordinates describe elapsed time relative to the first sample.
    """
    if not isinstance(result, ReadResult) or result.format != 'nmrml-raw-2d':
        raise ValueError('normalize_nmrml_raw_2d requires a nmrml-raw-2d ReadResult')
    if confirm_adjacent_pairs is not True:
        raise ValueError('nmrML echo/anti-echo normalization requires confirm_adjacent_pairs=True')
    dwell = _positive(indirect_dwell_s, 'indirect_dwell_s')
    document = result.metadata['document']
    checked = _describe_raw_2d(document, result.metadata['profile_options'], result.source)
    if (
        result.data.dtype != checked.data.dtype or not np.array_equal(result.data, checked.data)
        or result.domains != checked.domains or result.encoding != checked.encoding
        or result.dimensions != checked.dimensions or result.acquisition != checked.acquisition
        or result.applied_corrections or len(result.components) != 1
        or result.components[0].name != 'stored-traces'
        or result.components[0].data.dtype != checked.data.dtype
        or not np.array_equal(result.components[0].data, checked.data)
    ):
        raise ValueError('nmrML raw 2D description disagrees with its source')
    params = document['acquisition']['acquisitionMultiD']['acquisitionParameterSet']
    encoding = params['encodingScheme']
    if (encoding.get('@accession', '').replace('NMR_', 'NMR:', 1) != 'NMR:1400057'
        or ' '.join(encoding.get('@name', '').lower().split()) != 'echo anti-echo coherence selection'):
        raise ValueError('nmrML raw 2D normalization requires declared echo/anti-echo encoding')
    _vocabulary(document, encoding.get('@cvRef'), 'NMR', 'encoding')
    rows, cols = checked.data.shape
    if rows < 2 or rows % 2 or cols < 2:
        raise ValueError('nmrML echo/anti-echo requires complete trace pairs')
    widths = []
    for key in ('indirectDimensionParameterSet', 'directDimensionParameterSet'):
        dimension = params[key]
        sampling = dimension.get('samplingStrategy')
        sw = dimension.get('sweepWidth')
        if (not isinstance(sampling, dict) or not isinstance(sw, dict)
            or 'samplingTimePoints' in dimension):
            raise ValueError('nmrML raw 2D requires uniform sampling and explicit sweep widths')
        _uniform_sampling(document, sampling)
        _unit(document, sw, ('Hz',))
        widths.append(_positive(_number(sw.get('@value'), 'sweepWidth'), 'sweepWidth'))
    grids = (np.arange(rows // 2, dtype=float) * dwell, np.arange(cols, dtype=float) / widths[1])
    if any(not np.isfinite(grid).all() for grid in grids):
        raise ValueError('nmrML raw 2D requires finite time coordinates')
    axes = tuple(Axis(values=grid, unit='s', label=label, domain='time', direction='increasing')
                 for label, grid in zip(_2D_DIMS, grids, strict=True))
    dimensions = ('channels', *_2D_DIMS)
    operation = {'name': 'group-nmrml-adjacent-traces', 'stage': 'acquisition',
                 'input_dimensions': ('trace', 'sample'), 'output_dimensions': dimensions,
                 'axis': 'F1', 'scale': None, 'conjugation': 'none', 'sign': 'none',
                 'permutation': None, 'evidence': 'caller-confirmed adjacent trace pairs'}
    return NormalizedAcquisition(
        data=np.stack((checked.data[::2], checked.data[1::2])),
        axes=axes, dimensions=dimensions, physical_dimensions=_2D_DIMS, domains=_RAW_2D_DOMAINS,
        quadrature_mode='echo-antiecho-stored-2d', branch_order=('first', 'second'),
        channel_axis=0, normalization_state='storage-normalized',
        normalization_profile='nmrml-echo-antiecho-storage-2d-v1',
        applied_operations=(operation,),
        acquisition={**checked.acquisition, 'spectral_width_hz': tuple(widths),
                     'indirect_dwell_s': dwell, 'indirect_dwell_source': 'caller'},
        provenance={'source': result.source, 'format': result.format},
        metadata=checked.metadata, encoding=('echo-antiecho', 'complex'),
        diagnostics=checked.diagnostics,
    )
