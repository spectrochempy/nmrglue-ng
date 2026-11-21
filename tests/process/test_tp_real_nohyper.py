import numpy as np
import pytest
from numpy.testing import assert_array_equal

from nmrglue.fileio import fileiobase, pipe
from nmrglue.process import pipe_proc


@pytest.mark.parametrize("indirect_complex", [False, True])
@pytest.mark.parametrize("shape", [(4, 6), (8, 3)])
@pytest.mark.parametrize("dtype", [np.float32, np.float64])
def test_real_nohyper_transpose_preserves_quadrature_and_roundtrip(tmp_path,
                                                                indirect_complex,
                                                                shape, dtype):
    udic = fileiobase.create_blank_udic(2)
    for i, size in enumerate(shape):
        udic[i].update(size=size, complex=indirect_complex if i == 0 else False,
                       time=True, freq=False, sw=100., obs=400., car=0.)
    dic = pipe.create_dic(udic)
    if indirect_complex:
        dic["FDSPECNUM"] = shape[0] / 2
    data = np.arange(np.prod(shape), dtype=dtype).reshape(shape)
    if indirect_complex:
        expected = data[::2].T + 1.j * data[1::2].T
    else:
        expected = data.T
    result_dic, actual = pipe_proc.tp(dic, data.copy(), nohyper=True)
    assert actual.shape == expected.shape
    assert_array_equal(actual, expected)
    assert result_dic["FDSIZE"] == expected.shape[-1]
    assert result_dic["FDF1QUADFLAG"] == (0. if indirect_complex else 1.)
    assert result_dic["FDDIMORDER"][:2] == [1., 2.]
    output = str(tmp_path / "transposed.fid")
    stored = actual.astype(np.complex64 if np.iscomplexobj(actual) else np.float32)
    pipe.write(output, result_dic, stored)
    read_dic, recovered = pipe.read(output)
    assert_array_equal(recovered, expected)
    assert recovered.shape == expected.shape
    assert read_dic["FDSIZE"] == expected.shape[-1]
