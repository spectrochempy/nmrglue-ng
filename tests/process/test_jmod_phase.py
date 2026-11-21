import numpy as np
import pytest
from numpy.testing import assert_allclose

from nmrglue.fileio import fileiobase, pipe
from nmrglue.process import pipe_proc


@pytest.mark.parametrize("shape", [(12,), (2, 12)])
@pytest.mark.parametrize("options, off", [({}, 0.), ({"sin": True}, 0.),
    ({"off": 0.25}, 0.25), ({"cos": True}, 0.5), ({"hdr": True}, 0.)])
def test_jmod_complex_phase_and_partial_window(shape, options, off):
    udic = fileiobase.create_blank_udic(len(shape))
    for axis, size in enumerate(shape):
        udic[axis].update(size=size, sw=100., obs=400., car=0.,
                          complex=True, time=True, freq=False)
    dic = pipe.create_dic(udic)
    fn = "FDF" + str(int(dic["FDDIMORDER"][0]))
    dic.update({fn + "APODQ1": 0., fn + "APODQ2": 10.,
                fn + "APODQ3": 2., fn + "C1": -0.5})
    data = np.full(shape, 1. + 2.j, dtype=np.complex64)
    window = np.ones(12)
    i = np.arange(4)
    profile = np.exp(-np.pi * 2. * i / 100.) * np.sin(np.pi * (off + 10. * i / 100.))
    window[2:6] = profile
    expected = data * window
    expected[..., 0] *= 0.5
    if off == 0.:
        expected *= -1.j
    _, actual = pipe_proc.jmod(dic, data.copy(), j=10., lb=2., c=0.5,
                               start=3, size=4, one=True, **options)
    assert_allclose(actual, expected, rtol=2e-6, atol=2e-6)
