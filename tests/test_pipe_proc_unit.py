import numpy as np
import pytest

import nmrglue as ng


FUNCTIONS = {
    1: ng.proc_base.zd_triangle,
    2: ng.proc_base.zd_sinebell,
    3: ng.proc_base.zd_gaussian,
}


def test_save_writes_nonpipeline_header_and_preserves_data(tmp_path):
    udic = ng.fileiobase.create_blank_udic(1)
    udic[0]["size"] = 8
    udic[0]["complex"] = False
    dic = ng.pipe.create_dic(udic)
    data = np.array(
        [-3.0, -1.0, 0.5, 2.0, 4.0, 7.0, 1.5, -0.5], dtype="float32"
    )
    before = dic.copy()
    filename = tmp_path / "save.ft1"

    returned_dic, returned_data = ng.pipe_proc.save(
        dic, data, filename, overwrite=True
    )
    saved_dic, saved_data = ng.pipe.read(filename)

    assert before["FDPIPEFLAG"] == 0.0
    assert before["FDPIPECOUNT"] == 0.0
    assert saved_dic["FDPIPEFLAG"] == 0.0
    assert saved_dic["FDPIPECOUNT"] == 0.0
    assert returned_dic is dic
    assert returned_dic["FDPIPEFLAG"] == before["FDPIPEFLAG"]
    assert returned_dic["FDPIPECOUNT"] == before["FDPIPECOUNT"]
    assert returned_data is data
    assert saved_data.dtype == data.dtype
    assert saved_data.shape == data.shape
    np.testing.assert_array_equal(saved_data, data)
    np.testing.assert_array_equal(returned_data, data)


@pytest.mark.parametrize("func", FUNCTIONS)
@pytest.mark.parametrize(
    ("wide", "effective_width"),
    [
        (5.0, 5),
        (5.25, 5),
        (5.49, 5),
        (5.5, 6),
        (5.75, 6),
        (6.0, 6),
        (np.float64(5.5), 6),
    ],
)
def test_zd_uses_nmrpipe_fractional_width(wide, effective_width, func):
    data = np.ones((8, 64))
    kwargs = {"g": 2} if func == 3 else {}
    expected = FUNCTIONS[func](
        data.copy(), wide=effective_width, x0=19, slope=1, **kwargs
    )

    _, result = ng.pipe_proc.zd(
        {}, data.copy(), wide=wide, x0=20, slope=1, func=func, g=2
    )

    np.testing.assert_array_equal(result, expected)


@pytest.mark.parametrize("func", FUNCTIONS)
@pytest.mark.parametrize("wide", [np.nan, np.inf, -np.inf])
def test_zd_rejects_nonfinite_width(wide, func):
    data = np.ones((8, 64))

    with pytest.raises(ValueError, match="wide must be an integer number of points"):
        ng.pipe_proc.zd(
            {}, data, wide=wide, x0=20, slope=1, func=func, g=2
        )
