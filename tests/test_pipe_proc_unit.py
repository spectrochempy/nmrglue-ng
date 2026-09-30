import numpy as np
import pytest

import nmrglue as ng


FUNCTIONS = {
    1: ng.proc_base.zd_triangle,
    2: ng.proc_base.zd_sinebell,
    3: ng.proc_base.zd_gaussian,
}


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
