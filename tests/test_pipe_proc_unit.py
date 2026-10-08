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


@pytest.mark.parametrize(
    ("data", "expected"),
    [
        (
            [1.0, 2.0, 4.0, 8.0, 16.0],
            [
                1.0 - 12.242127j,
                2.0 - 5.3340144j,
                4.0 - 5.8728495j,
                8.0 - 6.950515j,
                16.0 + 5.830447j,
            ],
        ),
        (
            [1.0, 2.0, 4.0, 8.0, 16.0, 32.0],
            [
                1.0 - 25.333336j,
                2.0 - 7.333332j,
                4.0 - 14.666667j,
                8.0 - 7.6666665j,
                16.0 - 15.333332j,
                32.0 + 12.666667j,
            ],
        ),
    ],
)
@pytest.mark.parametrize(
    "dtype", ["float32", "float64", "complex64", "complex128"]
)
def test_ht_ps90_180_matches_mirror_image_reference(data, expected, dtype):
    data = np.asarray(data, dtype=dtype)
    dic = ng.pipe.create_empty_dic()

    _, result = ng.pipe_proc.ht(dic, data, mode="ps90-180")

    assert result.shape == data.shape
    assert result.dtype == np.dtype("complex64")
    np.testing.assert_allclose(result, expected, rtol=1e-6, atol=1e-6)


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


@pytest.mark.parametrize(
    ("kwargs", "expected_rows", "expected_x1", "expected_xn", "expected_axis"),
    [
        ({"y1": 2, "yn": 512}, slice(1, 512), 2.0, 512.0,
         (511.0, 255.0, 998.046875, -500.0)),
        ({"y1": 1, "yn": 128}, slice(0, 128), None, None,
         (None, 256.0, 250.0, 250.0)),
        ({"y1": 400, "yn": 700}, slice(399, 512), 400.0, 512.0,
         (113.0, -143.0, 220.703125, -500.0)),
        ({"y1": 1, "yn": 700}, slice(0, 512), None, None,
         (None, 256.0, 1000.0, -500.0)),
        ({"y1": 600, "yn": 700}, slice(511, 512), 512.0, 512.0,
         (1.0, -255.0, 1.953125, -500.0)),
        ({"y1": 1, "yn": 128, "round": 256}, slice(0, 256), None, None,
         (None, 256.0, 500.0, 0.0)),
        ({"y1": 1, "yn": 100, "pow2": True}, slice(0, 128), None, None,
         (None, 256.0, 250.0, 250.0)),
        ({"y1": 400, "yn": 500, "round": 128}, slice(384, 512), 385.0, 512.0,
         (128.0, -128.0, 250.0, -500.0)),
        ({"y1": 400, "yn": 700, "pow2": True}, slice(384, 512), 385.0, 512.0,
         (128.0, -128.0, 250.0, -500.0)),
    ],
)
def test_ext_updates_indirect_metadata_and_axis(
    tmp_path, kwargs, expected_rows, expected_x1, expected_xn, expected_axis
):
    data = np.arange(512 * 1024, dtype="float32").reshape(512, 1024)
    udic = ng.fileiobase.create_blank_udic(2)
    udic[0].update(size=512, complex=False, sw=1000.0, obs=1.0, car=0.0)
    udic[1].update(size=1024, complex=False)
    dic = ng.pipe.create_dic(udic)
    dic["FDSPECNUM"] = dic["FDSLICECOUNT"] = 512.0
    dic["FDF1FTFLAG"] = dic["FDF2FTFLAG"] = 1.0
    dic["FDF1APOD"] = 512.0
    dic["FDF1CENTER"] = 256.0
    dic["FDF1ORIG"] = -500.0

    result_dic, result = ng.pipe_proc.ext(dic, data, **kwargs)

    expected = data[expected_rows]
    np.testing.assert_array_equal(result, expected)
    assert result.shape == expected.shape
    assert result_dic["FDSPECNUM"] == result.shape[0]
    assert result_dic["FDSLICECOUNT"] == result.shape[0]
    if expected_axis[0] is not None:
        assert result_dic["FDF1APOD"] == expected_axis[0]
    assert result_dic["FDF1CENTER"] == expected_axis[1]
    assert result_dic["FDF1SW"] == expected_axis[2]
    assert result_dic["FDF1ORIG"] == expected_axis[3]
    if expected_x1 is not None:
        assert result_dic["FDF1X1"] == expected_x1
        assert result_dic["FDF1XN"] == expected_xn

    filename = tmp_path / "ext.ft2"
    ng.pipe.write(str(filename), result_dic, result, overwrite=True)
    read_dic, read_data = ng.pipe.read(filename)
    assert read_dic["FDSPECNUM"] == result.shape[0]
    assert read_data.shape == result.shape
    np.testing.assert_array_equal(read_data, result)
