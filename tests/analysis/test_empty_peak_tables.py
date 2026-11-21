import numpy as np
import pytest

from nmrglue.analysis.peakpick import pick


@pytest.mark.parametrize('ndim', [1, 2, 3, 4])
@pytest.mark.parametrize('algorithm', ['connected', 'downward', 'thres', 'thres-fast'])
@pytest.mark.parametrize('cluster', [False, True])
@pytest.mark.parametrize('est_params', [False, True])
def test_no_peaks_returns_empty_table_with_expected_schema(ndim, algorithm, cluster, est_params):
    names = ['A', 'Z', 'Y', 'X'][-ndim:]
    dtype = [(name + '_AXIS', float) for name in names]
    if cluster:
        dtype.append(('cID', int))
    if est_params:
        dtype.extend((name + '_LW', float) for name in names)
        dtype.append(('VOL', float))
    result = pick(np.zeros((3,) * ndim), 1., algorithm=algorithm,
                  msep=(1,) * ndim, cluster=cluster, est_params=est_params)
    assert isinstance(result, np.recarray)
    assert result.shape == (0,)
    assert result.dtype == np.dtype(dtype)


def test_custom_axis_names_and_edge():
    result = pick(np.zeros((3, 4)), 1., axis_names=['F1', 'F2'], edge=(10, 20))
    assert result.dtype.names == ('F1_AXIS', 'F2_AXIS', 'cID', 'F1_LW', 'F2_LW', 'VOL')
    assert result.size == 0


@pytest.mark.parametrize('cluster', [False, True])
@pytest.mark.parametrize('est_params', [False, True])
def test_empty_list_return_contract_is_preserved(cluster, est_params):
    result = pick(np.zeros(8), 1., table=False, cluster=cluster, est_params=est_params)
    if not cluster and not est_params:
        assert result == []
    else:
        assert result == tuple([] for _ in range(1 + int(cluster) + 2 * int(est_params)))
