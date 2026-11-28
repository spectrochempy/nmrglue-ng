from itertools import permutations

import numpy as np
import pytest

from nmrglue.fileio import rnmrtk


ORDERS = [order for ndim in (2, 3, 4) for order in permutations(range(ndim))]


def _dictionary(order, complex_data=False):
    ndim = len(order)
    npts = [3 + i for i in range(ndim)]
    domains = ['F', 'T', 'F', 'T'][:ndim]
    shape = [npts[p] * (2 if complex_data and axis != ndim - 1 else 1)
             for axis, p in enumerate(order)]
    dic = dict(ndim=ndim, npts=npts, dom=domains,
               layout=(shape, [domains[p] + str(p + 1) for p in order]),
               nptype=['C' if complex_data else 'R'] * ndim,
               sf=[400., 100., 50., 200.][:ndim],
               ppm=[4.5, 50., 20., -3.][:ndim],
               sw=[8000., 6000., 2000., 4000.][:ndim],
               quad=['states', 'states-tppi', 'tppi', 'states'][:ndim])
    return dic, tuple(shape)


@pytest.mark.parametrize("order", ORDERS)
@pytest.mark.parametrize("complex_data", [False, True])
def test_layout_selects_metadata_by_dimension_number(order, complex_data):
    dic, shape = _dictionary(order, complex_data)
    data = np.zeros(shape, dtype=np.complex64 if complex_data else np.float32)
    udic = rnmrtk.guess_udic(dic, data)

    for axis, parameter in enumerate(order):
        obs, ppm, sw = (dic[key][parameter] for key in ('sf', 'ppm', 'sw'))
        expected_ppm = ppm + sw / (2 * obs) - np.arange(shape[axis]) * sw / (shape[axis] * obs)
        for dim in (axis, axis - len(order)):
            uc = rnmrtk.make_uc(dic, data, dim)
            np.testing.assert_allclose(uc.ppm_scale(), expected_ppm, rtol=0, atol=1e-12)
            np.testing.assert_allclose(uc.hz_scale(), expected_ppm * obs, atol=1e-9)
        assert udic[axis]['obs'] == obs
        assert udic[axis]['car'] == ppm * obs
        assert udic[axis]['sw'] == sw
        assert udic[axis]['size'] == shape[axis]
        assert udic[axis]['complex'] == complex_data
        assert udic[axis]['encoding'] == dic['quad'][parameter]
        assert udic[axis]['label'] == dic['dom'][parameter] + str(parameter + 1)
        assert udic[axis]['time'] == (dic['dom'][parameter] == 'T')
        assert udic[axis]['freq'] == (dic['dom'][parameter] == 'F')


@pytest.mark.parametrize("order", ORDERS)
def test_dimension_helpers_are_zero_based_inverses(order):
    dic, _ = _dictionary(order)
    for axis, parameter in enumerate(order):
        assert rnmrtk.find_dic_dim(dic, axis) == parameter
        assert rnmrtk.find_array_dim(dic, parameter) == axis
