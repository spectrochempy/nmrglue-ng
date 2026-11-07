"""Read and normalize the schema-validated real nmrML reference plane."""

from base64 import b64encode
from dataclasses import replace
import hashlib
import os
from pathlib import Path
from struct import pack
import xml.etree.ElementTree as ET

import numpy as np
import pytest

from nmrglue import interop

pytestmark = pytest.mark.optional_dependency
pytest.importorskip('xmltodict')
REFERENCE = Path(__file__).parents[1] / 'fixtures' / 'nmrml' / 'synthetic-2d-real.nmrML'
OPTIONS = dict(shape=(3, 4), indirect_axis=(-100, 100, 'Hz'),
               storage_order='x-fastest', axis_endpoint='last-point')


def test_reference_plane():
    stored = interop.read_nmrml_2d(REFERENCE, **OPTIONS)
    result = interop.normalize_nmrml_2d(stored)
    np.testing.assert_array_equal(
        result.data, [[1, -2, 4, 8], [16, -32, 64, 128], [3, 5, -7, 11]],
    )
    assert result.data.dtype == np.dtype('<f4')
    assert result.dimensions == ('F1', 'F2')
    assert result.domains == ('frequency', 'frequency')
    assert result.branch_order == ('real',)
    assert result.channel_axis is None
    assert tuple(axis.unit for axis in result.axes) == ('Hz', 'ppm')
    np.testing.assert_array_equal(result.axes[0].values, [-100, 0, 100])
    np.testing.assert_array_equal(result.axes[1].values, [9, 7, 5, 3])
    with pytest.raises(ValueError, match='disagrees with its source'):
        interop.normalize_nmrml_2d(replace(stored, data=stored.data + 1))


def test_explicit_storage_order_and_endpoint():
    stored = interop.read_nmrml_2d(
        REFERENCE, **{**OPTIONS, 'storage_order': 'y-fastest', 'axis_endpoint': 'outer-edge'},
    )
    np.testing.assert_array_equal(stored.data[0], [1, 8, 64, 5])
    np.testing.assert_allclose(stored.axes[0].values, [-100, -100 / 3, 100 / 3])
    np.testing.assert_array_equal(stored.axes[1].values, [9, 7.5, 6, 4.5])


@pytest.mark.parametrize(
    'old,new,message',
    [
        ('numberOfDataPoints="12"', 'numberOfDataPoints="13"', 'numberOfDataPoints'),
        ('byteFormat="float32"', 'byteFormat="complex64"', 'real float32 or float64'),
        ('<higherDimensionProcessingParameterSet/>',
         '<higherDimensionProcessingParameterSet/><higherDimensionProcessingParameterSet/>',
         'with two dimensions'),
    ],
)
def test_rejects_unsupported_spectrum(tmp_path, old, new, message):
    text = REFERENCE.read_text()
    assert old in text
    path = tmp_path / 'spectrum.nmrML'
    path.write_text(text.replace(old, new))
    with pytest.raises(ValueError, match=message):
        interop.read_nmrml_2d(path, **OPTIONS)


def test_rejects_inconsistent_shape():
    with pytest.raises(ValueError, match='supplied 2D shape'):
        interop.read_nmrml_2d(REFERENCE, **{**OPTIONS, 'shape': (3, 5)})


def test_reference_matches_pinned_schema():
    etree = pytest.importorskip('lxml.etree')
    parser = etree.XMLParser(resolve_entities=False, no_network=True)
    schema = etree.XMLSchema(etree.parse(str(REFERENCE.with_name('nmrML.xsd')), parser))
    schema.assertValid(etree.parse(str(REFERENCE), parser))


def test_raw_echo_antiecho_trace_pairs(tmp_path):
    tree = ET.parse(REFERENCE)
    ns = '{http://nmrml.org/schema}'
    params = tree.find('.//' + ns + 'acquisitionMultiD/' + ns + 'acquisitionParameterSet')
    params.find(ns + 'indirectDimensionParameterSet').set('numberOfDataPoints', '4')
    direct = params.find(ns + 'directDimensionParameterSet')
    direct.set('numberOfDataPoints', '8')
    direct.find(ns + 'sweepWidth').set('value', '4000')
    scheme = params.find(ns + 'encodingScheme')
    scheme.set('accession', 'NMR:1400057')
    scheme.set('name', 'echo anti-echo coherence selection')
    fid = tree.find('.//' + ns + 'fidData')
    fid.text = b64encode(pack('<32d', *range(32))).decode('ascii')
    fid.set('encodedLength', str(len(fid.text)))
    path = tmp_path / 'fid.nmrML'
    tree.write(path)
    stored = interop.read_nmrml_raw_2d(path, direct_point_count='scalar')
    expected = (np.arange(0, 32, 2) + 1j * np.arange(1, 32, 2)).reshape(4, 4)
    np.testing.assert_array_equal(stored.data, expected)
    with pytest.raises(ValueError, match='confirm_adjacent_pairs'):
        interop.normalize_nmrml_raw_2d(stored, indirect_dwell_s=0.001)
    with pytest.raises(ValueError, match='original payload and geometry'):
        interop.read_nmrml_raw_2d(path, direct_point_count='scalar',
                                 official_hsqc_compatibility=True)
    result = interop.normalize_nmrml_raw_2d(stored, indirect_dwell_s=0.001,
                                             confirm_adjacent_pairs=True)
    assert result.dimensions == ('channels', 'F1', 'F2')
    assert result.branch_order == ('first', 'second')
    np.testing.assert_array_equal(result.data, [expected[[0, 2]], expected[[1, 3]]])
    np.testing.assert_allclose(result.axes[0].values, [0, 0.001])
    np.testing.assert_allclose(result.axes[1].values, [0, 0.00025, 0.0005, 0.00075])


@pytest.mark.dataset
def test_official_hsqc_matches_bmrb_ser():
    xml = os.environ.get('NMRML_HSQC_XML')
    ser = os.environ.get('NMRML_HSQC_SER')
    if not xml or not ser:
        pytest.skip('set NMRML_HSQC_XML and NMRML_HSQC_SER to the external reference files')
    assert hashlib.sha256(Path(xml).read_bytes()).hexdigest() == (
        '3231a4769029f362863fb57c7adaaaf6aae304a65c503839b57e5ec02b320f82'
    )
    raw = Path(ser).read_bytes()
    assert hashlib.sha1(raw).hexdigest() == 'a979ed42e5a28066a476557d713c76ce081541da'
    words = np.frombuffer(raw, dtype='>i4').reshape(256, 4096)
    expected = words[:, ::2] + 1j * words[:, 1::2]
    with pytest.raises(ValueError, match='encoded text'):
        interop.read_nmrml_raw_2d(xml, direct_point_count='scalar')
    stored = interop.read_nmrml_raw_2d(
        xml, direct_point_count='scalar', official_hsqc_compatibility=True,
    )
    np.testing.assert_array_equal(stored.data, expected)
    # The pulse program has two d0 delays and increments d0 once per pair.
    carbon_dwell = 2 * 6.63e-05
    result = interop.normalize_nmrml_raw_2d(
        stored, indirect_dwell_s=carbon_dwell, confirm_adjacent_pairs=True,
    )
    assert result.data.shape == (2, 128, 2048)
    np.testing.assert_array_equal(result.data[0], expected[::2])
    np.testing.assert_array_equal(result.data[1], expected[1::2])
    np.testing.assert_allclose(result.axes[0].values, np.arange(128) * carbon_dwell)
    np.testing.assert_allclose(result.axes[0].values, np.arange(128) / 7541.47812971342)
    np.testing.assert_allclose(result.axes[1].values, np.arange(2048) / 7002.80112044818)
