"""Read and normalize the schema-validated real nmrML reference plane."""

from dataclasses import replace
from pathlib import Path

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
