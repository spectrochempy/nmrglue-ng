"""Explicit nmrML 1D profiles; real files are opt-in external inputs."""

from copy import deepcopy
from dataclasses import replace
import hashlib
import os
from pathlib import Path
import struct
import xml.etree.ElementTree as ET
import zlib
import base64

import numpy as np
import pytest

import nmrglue as ng

pytestmark = pytest.mark.optional_dependency
pytest.importorskip('xmltodict')
FIXTURE = Path(__file__).parents[1] / 'fixtures' / 'nmrml' / 'synthetic.nmrML'


def spectrum(tmp_path, complex_data=True, unit='parts per million', reverse=False):
    metadata, _ = ng.nmrml.read(FIXTURE, read_processed=True, strict=True)
    spec = metadata['spectrumList']['spectrum1D']
    spec['xAxis']['@unitName'] = unit
    if reverse:
        spec['xAxis']['@startValue'], spec['xAxis']['@endValue'] = '-2', '10'
    values = np.arange(8, dtype='f8') - 3
    if complex_data:
        values = values + 1j * np.arange(8, dtype='f8')
    path = tmp_path / 'spectrum.nmrML'
    ng.nmrml.write(path, metadata, values, write_processed=True)
    return path, values


@pytest.mark.parametrize('complex_data', [False, True])
@pytest.mark.parametrize('endpoint', ['last-point', 'outer-edge'])
@pytest.mark.parametrize('reverse', [False, True])
@pytest.mark.parametrize('unit', ['hertz', 'parts per million'])
@pytest.mark.parametrize('obs', [None, 400.0])
def test_processed_explicit_geometry(tmp_path, complex_data, endpoint, reverse, unit, obs):
    path, values = spectrum(tmp_path, complex_data, unit, reverse)
    before = path.read_bytes()
    raw = ng.interop.read_nmrml_1d(path, read_processed=True, axis_endpoint=endpoint,
                                  observation_frequency_mhz=obs)
    saved = deepcopy(raw.metadata['document'])
    normalized = ng.interop.normalize_nmrml_1d(raw)
    np.testing.assert_array_equal(normalized.data, values)
    assert normalized.domains == ('frequency',)
    assert normalized.axes[0].reference.source == 'unknown'
    start, span = (-2, 12) if reverse else (10, -12)
    expected = start + np.arange(8) * span / (7 if endpoint == 'last-point' else 8)
    if unit == 'parts per million' and obs is not None:
        expected *= obs
    np.testing.assert_allclose(normalized.axes[0].values, expected, rtol=1e-15, atol=1e-12)
    assert normalized.axes[0].unit == ('ppm' if unit == 'parts per million' and obs is None else 'Hz')
    assert raw.metadata['document'] == saved
    assert path.read_bytes() == before
    with pytest.raises(ValueError):
        normalized.data[0] = 99
    with pytest.raises(ValueError):
        normalized.axes[0].values[0] = 99


@pytest.mark.parametrize('count_unit', ['complex', 'scalar'])
@pytest.mark.parametrize('sign', ['none', 'conjugate'])
def test_raw_explicit_count_sign_and_time_grid(tmp_path, count_unit, sign):
    metadata, data = ng.nmrml.read(FIXTURE, strict=True)
    params = metadata['acquisition']['acquisition1D']['acquisitionParameterSet']['DirectDimensionParameterSet']
    params['@numberOfDataPoints'] = str(data.size * (2 if count_unit == 'scalar' else 1))
    path = tmp_path / 'fid.nmrML'
    ng.nmrml.write(path, metadata, data + 1j * np.arange(8))
    raw = ng.interop.read_nmrml_1d(path, raw_point_count=count_unit)
    with pytest.raises(ValueError, match='explicit conjugation'):
        ng.interop.normalize_nmrml_1d(raw)
    normalized = ng.interop.normalize_nmrml_1d(raw, conjugation=sign)
    expected = raw.data.conj() if sign == 'conjugate' else raw.data
    np.testing.assert_array_equal(normalized.data, expected)
    np.testing.assert_array_equal(normalized.axes[0].values, np.arange(8) / 2000)
    assert normalized.axes[0].unit == 's'
    assert normalized.acquisition['spectral_width_hz'] == 2000
    assert normalized.domains == ('time',)


@pytest.mark.parametrize('options', [
    {}, {'axis_endpoint': 'guess'},
    {'axis_endpoint': 'last-point', 'observation_frequency_mhz': 0},
    {'axis_endpoint': 'last-point', 'observation_frequency_mhz': True},
    {'axis_endpoint': 'last-point', 'observation_frequency_mhz': np.nan},
])
def test_processed_refuses_missing_or_ambiguous_conventions(tmp_path, options):
    path, _ = spectrum(tmp_path)
    with pytest.raises(ValueError):
        ng.interop.read_nmrml_1d(path, read_processed=True, **options)


@pytest.mark.parametrize('change', ['units', 'bounds', 'sampling', 'count', 'nonfinite'])
def test_profiles_refuse_incoherent_metadata(tmp_path, change):
    metadata, data = ng.nmrml.read(FIXTURE, read_processed=True, strict=True)
    if change == 'nonfinite':
        data = data.copy(); data[0] = np.nan
    elif change == 'units':
        metadata['spectrumList']['spectrum1D']['xAxis']['@unitName'] = 'seconds'
    elif change == 'bounds':
        metadata['spectrumList']['spectrum1D']['xAxis']['@endValue'] = '10'
    elif change == 'sampling':
        params = metadata['acquisition']['acquisition1D']['acquisitionParameterSet']['DirectDimensionParameterSet']
        params['samplingStrategy']['@accession'] = 'NMR:unknown'
    else:
        metadata['acquisition']['acquisition1D']['acquisitionParameterSet']['DirectDimensionParameterSet']['@numberOfDataPoints'] = '8'
    path = tmp_path / 'invalid.nmrML'
    ng.nmrml.write(path, metadata, data, write_processed=True)
    kwargs = {'raw_point_count': 'scalar'} if change in ('sampling', 'count') else {
        'read_processed': True, 'axis_endpoint': 'last-point'}
    with pytest.raises(ValueError):
        ng.interop.read_nmrml_1d(path, **kwargs)


@pytest.mark.parametrize('change', ['axis', 'samples', 'domain', 'components', 'corrections'])
def test_normalizer_revalidates_description(tmp_path, change):
    path, _ = spectrum(tmp_path)
    raw = ng.interop.read_nmrml_1d(path, read_processed=True, axis_endpoint='last-point')
    if change == 'axis':
        bad = replace(raw, axes=(replace(raw.axes[0], values=np.arange(8)),))
    elif change == 'samples':
        bad = replace(raw, data=raw.data * 2)
    elif change == 'domain':
        bad = replace(raw, domains=('time',))
    elif change == 'components':
        bad = replace(raw, components=())
    else:
        bad = replace(raw, applied_corrections={})
    with pytest.raises(ValueError):
        ng.interop.normalize_nmrml_1d(bad)


def test_explicit_binary_override_is_recorded_and_revalidated(tmp_path):
    path, expected = spectrum(tmp_path)
    payload = path.read_text().replace('byteFormat="complex128"', 'byteFormat="complex64"')
    path.write_text(payload)
    with pytest.raises(ValueError, match='numberOfDataPoints'):
        ng.interop.read_nmrml_1d(path, read_processed=True, axis_endpoint='last-point')
    raw = ng.interop.read_nmrml_1d(path, read_processed=True, axis_endpoint='last-point', data_dtype='<c16')
    assert raw.metadata['profile_options']['data_dtype'] == '<c16'
    np.testing.assert_array_equal(ng.interop.normalize_nmrml_1d(raw).data, expected)


@pytest.mark.dataset
@pytest.mark.parametrize('kind', ['hop', 'bayesil'])
def test_real_public_nmrml_inputs(tmp_path, kind):
    root = os.environ.get('NMRML_QUALIFICATION_DATA')
    if not root:
        pytest.skip('set NMRML_QUALIFICATION_DATA to external official examples')
    root = Path(root)
    names = {'hop': 'hop.nmrML', 'bayesil': 'biosample_quantification.nmrML'}
    hashes = {'hop': '2f8a0b7cdc4ca8083aecb2df1ab6d81fbede5891ee2c3b562cc8dd079f8837d0',
              'bayesil': '38712b01526635b3bf2639a5b08c7e00e15c4e56d0c1174295595b9ab939c448'}
    path = root / names[kind]
    before = hashlib.sha256(path.read_bytes()).hexdigest()
    assert before == hashes[kind]
    tree = ET.parse(path)
    tag = 'fidData' if kind == 'hop' else 'spectrumDataArray'
    binary = tree.find('.//{*}' + tag)
    payload = base64.b64decode(''.join(binary.text.split()), validate=True)
    if binary.attrib['compressed'] == 'true':
        payload = zlib.decompress(payload)
    if kind == 'hop':
        with pytest.raises(ValueError, match='numberOfDataPoints'):
            ng.interop.read_nmrml_1d(path, raw_point_count='scalar')
        raw = ng.interop.read_nmrml_1d(path, raw_point_count='scalar', data_dtype='<c8')
        _, native = ng.varian.read(root / 'hop-native')
        words = struct.unpack('<' + 'f' * (len(payload) // 4), payload)
        expected = np.array(words[::2]) + 1j * np.array(words[1::2])
        np.testing.assert_array_equal(raw.data, expected)
        np.testing.assert_array_equal(raw.data, native)
        normalized = ng.interop.normalize_nmrml_1d(raw, conjugation='none')
        np.testing.assert_allclose(normalized.axes[0].values, np.arange(native.size) / 12019.2307692)
    else:
        raw = ng.interop.read_nmrml_1d(path, read_processed=True, axis_endpoint='last-point')
        words = struct.unpack('<' + 'd' * (len(payload) // 8), payload)
        expected = np.array(words[::2]) + 1j * np.array(words[1::2])
        normalized = ng.interop.normalize_nmrml_1d(raw)
        np.testing.assert_array_equal(normalized.data, expected)
        np.testing.assert_allclose(normalized.axes[0].values[[0, -1]], [10.786579189224353, -1.2185782542495236])
        assert normalized.axes[0].unit == 'ppm'
        assert normalized.axes[0].reference.observation_frequency is None
    out = tmp_path / 'roundtrip.nmrML'
    ng.nmrml.write(out, raw.metadata['document'], raw.data, write_processed=kind == 'bayesil')
    np.testing.assert_array_equal(ng.nmrml.read(out, read_processed=kind == 'bayesil', strict=True)[1], expected)
    assert hashlib.sha256(path.read_bytes()).hexdigest() == before
