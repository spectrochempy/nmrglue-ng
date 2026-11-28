import numpy as np
import pytest

from nmrglue.fileio import fileiobase, rnmrtk


def test_make_uc_from_created_dictionary():
    udic = fileiobase.create_blank_udic(1)
    udic[0].update(size=8, complex=False, sw=8000., obs=400., car=1800.,
                   time=False, freq=True)
    dic = rnmrtk.create_dic(udic)
    data = np.zeros(8)

    uc = rnmrtk.make_uc(dic, data)

    np.testing.assert_allclose(uc.ppm_scale(), 14.5 - 2.5 * np.arange(8))
    assert uc.hz(4) == pytest.approx(1800.)
    assert rnmrtk.guess_udic(dic, data)[0]['car'] == pytest.approx(1800.)


@pytest.mark.parametrize("dim", [0, 1, -1, -2])
@pytest.mark.parametrize("complex_direct", [False, True])
def test_make_uc_uses_permuted_dictionary_axis(dim, complex_direct):
    dic = dict(ndim=2, layout=[(6, 8), ['F2', 'F1']],
               nptype=['C' if complex_direct else 'R', 'R'],
               sf=[400., 100.], ppm=[4.5, 50.], sw=[8000., 6000.])
    data = np.zeros((6, 8), dtype=complex if complex_direct else float)
    axis = dim % 2

    uc = rnmrtk.make_uc(dic, data, dim)

    expected = (80. - 10. * np.arange(6) if axis == 0
                else 14.5 - 2.5 * np.arange(8))
    np.testing.assert_allclose(uc.ppm_scale(), expected, rtol=0, atol=1e-12)
    np.testing.assert_allclose(uc.hz_scale(), expected * [100., 400.][axis])
