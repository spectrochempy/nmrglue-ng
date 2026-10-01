"""Autonomous RNMRTK tests with independently generated files."""

from itertools import permutations

import nmrglue as ng
import numpy as np
from numpy.testing import assert_array_equal


def _values(shape, complex_data):
    """Return distinctive, exactly representable values for every index."""
    values = np.arange(np.prod(shape), dtype=np.float32).reshape(shape)
    if complex_data:
        return (values + 0.5 - 1j * (values + 1.25)).astype(np.complex64)
    return values * np.float32(1.25) - np.float32(7.75)


def _write_independent_fixture(
        tmp_path, name, domains, npts, nptype, *, endian="<"):
    """Build RNMRTK parameter text and IEEE-float bytes without its writer."""
    ndim = len(domains)
    raw_shape = tuple(
        npts[int(domain[1]) - 1]
        * (2 if nptype[int(domain[1]) - 1] == "C" else 1)
        for domain in domains
    )
    complex_data = nptype[-1] == "C"
    shape = raw_shape[:-1] + (
        (raw_shape[-1] // 2) if complex_data else raw_shape[-1],)
    expected = _values(shape, complex_data)
    raw = expected.view(np.float32) if complex_data else expected

    sw = [1000.0 / (2 ** i) for i in range(ndim)]
    sf = [100.0 + 25.0 * i for i in range(ndim)]
    ppm = [4.0 + 0.5 * i for i in range(ndim)]
    dom_by_number = [None] * ndim
    for domain in domains:
        dom_by_number[int(domain[1]) - 1] = domain[0]

    lines = [
        "Comment 'synthetic'",
        f"Dom {' '.join(domains)}",
        "N " + " ".join(
            f"{size} {kind}" for size, kind in zip(npts, nptype)),
        "Sw " + " ".join(str(value) for value in sw),
        "Xfirst " + " ".join("0.0" for _ in range(ndim)),
        "Xstep " + " ".join(str(1.0 / value) for value in sw),
        "Cphase " + " ".join("0.0" for _ in range(ndim)),
        "Lphase " + " ".join("0.0" for _ in range(ndim)),
        "Sf " + " ".join(str(value) for value in sf),
        "Ppm " + " ".join(str(value) for value in ppm),
        "Nacq " + " ".join(str(value) for value in npts),
        "Quad " + " ".join("States" for _ in range(ndim)),
        "Format " + (
            "Little-endian IEEE-Float" if endian == "<"
            else "Big-endian IEEE-Float"),
        "Layout " + " ".join(
            f"{domain}:{size}" for domain, size in zip(domains, raw_shape)),
    ]
    sec_path = tmp_path / f"{name}.sec"
    sec_path.write_bytes(raw.astype(f"{endian}f4").tobytes())
    sec_path.with_suffix(".par").write_text("\n".join(lines) + "\n")

    metadata = {
        "dom": dom_by_number,
        "format": f"{endian}f4",
        "layout": (list(raw_shape), list(domains)),
        "ndim": ndim,
        "npts": list(npts),
        "nptype": list(nptype),
        "ppm": ppm,
        "sf": sf,
        "sw": sw,
    }
    return sec_path, expected, metadata


def _assert_metadata(dic, expected):
    for key, value in expected.items():
        assert dic[key] == value


def _expected_bytes(data, dtype):
    values = data.view(np.float32) if np.iscomplexobj(data) else data
    return values.astype(dtype).tobytes()


def _assert_written_file(sec_path, dic, expected):
    """Check writer bytes/header independently, then use read as secondary."""
    assert sec_path.read_bytes() == _expected_bytes(expected, dic["format"])
    text = sec_path.with_suffix(".par").read_text()
    assert f"Dom {' '.join(dic['layout'][1])}\n" in text
    assert "Layout  " + " ".join(
        f"{domain}:{size}"
        for size, domain in zip(*dic["layout"])) + "\n" in text
    endian = "Little-endian" if dic["format"][0] == "<" else "Big-endian"
    assert f"Format  {endian}" in text
    read_dic, read_data = ng.rnmrtk.read(str(sec_path))
    assert read_dic == dic
    assert_array_equal(read_data, expected)


def _check_regular(tmp_path, name, domains, npts, nptype, *, endian="<"):
    sec_path, expected, metadata = _write_independent_fixture(
        tmp_path, name, domains, npts, nptype, endian=endian)
    dic, data = ng.rnmrtk.read(str(sec_path))
    _assert_metadata(dic, metadata)
    assert_array_equal(data, expected)

    written = tmp_path / f"{name}_written.sec"
    ng.rnmrtk.write(str(written), dic, data)
    _assert_written_file(written, dic, expected)
    return dic, data


def _check_lowmem(tmp_path, name, domains, npts, nptype):
    sec_path, expected, metadata = _write_independent_fixture(
        tmp_path, name, domains, npts, nptype)
    dic, data = ng.rnmrtk.read_lowmem(str(sec_path))
    _assert_metadata(dic, metadata)
    assert data.shape == expected.shape
    assert data.dtype == expected.dtype
    whole = tuple(slice(None) for _ in data.shape)
    assert_array_equal(data[whole], expected)
    slices = tuple(slice(1, None, 2) if size > 3 else slice(None)
                   for size in data.shape)
    assert_array_equal(data[slices], expected[slices])

    written = tmp_path / f"{name}_written.sec"
    ng.rnmrtk.write_lowmem(str(written), dic, data)
    _assert_written_file(written, dic, expected)
    return dic, data, expected


def test_1d_time(tmp_path):
    dic, data = _check_regular(tmp_path, "time_1d", ("T1",), (8,), ("C",))
    assert data.shape == (8,)
    assert data[3] == np.complex64(3.5 - 4.25j)
    assert dic["dom"] == ["T"]


def test_1d_freq(tmp_path):
    dic, data = _check_regular(
        tmp_path, "freq_1d", ("F1",), (8,), ("R",), endian=">")
    assert data.shape == (8,)
    assert data.dtype == np.dtype(">f4")
    assert data[3] == np.float32(-4.0)
    assert dic["dom"] == ["F"]


def test_2d_time(tmp_path):
    dic, data = _check_regular(
        tmp_path, "time_2d", ("T1", "T2"), (3, 8), ("R", "C"))
    assert data.shape == (3, 8)
    assert data[1, 2] == np.complex64(10.5 - 11.25j)
    assert dic["sw"] == [1000.0, 500.0]


def test_2d_freq(tmp_path):
    dic, data = _check_regular(
        tmp_path, "freq_2d", ("F1", "F2"), (3, 8), ("R", "R"))
    assert data.shape == (3, 8)
    assert data[2, 3] == np.float32(16.0)
    assert dic["sf"] == [100.0, 125.0]


def test_2d_time_lowmem(tmp_path):
    dic, data, expected = _check_lowmem(
        tmp_path, "time_2d_lowmem", ("T1", "T2"),
        (3, 8), ("R", "C"))
    assert_array_equal(data[1:, 2:7:2], expected[1:, 2:7:2])
    assert dic["ppm"] == [4.0, 4.5]


def test_2d_freq_lowmem(tmp_path):
    dic, data, expected = _check_lowmem(
        tmp_path, "freq_2d_lowmem", ("F1", "F2"),
        (3, 8), ("R", "R"))
    assert_array_equal(data[1:, 1:8:3], expected[1:, 1:8:3])
    assert dic["nptype"] == ["R", "R"]


def test_3d_time_lowmem(tmp_path):
    dic, data, expected = _check_lowmem(
        tmp_path, "time_3d_lowmem", ("T1", "T2", "T3"),
        (2, 3, 8), ("R", "R", "C"))
    assert data.shape == (2, 3, 8)
    assert_array_equal(data[:, 1:, 1:7:2], expected[:, 1:, 1:7:2])
    assert dic["dom"] == ["T", "T", "T"]


def test_3d_freq_lowmem(tmp_path):
    dic, data, expected = _check_lowmem(
        tmp_path, "freq_3d_lowmem", ("F1", "F2", "F3"),
        (2, 3, 8), ("R", "R", "R"))
    assert data.shape == (2, 3, 8)
    assert_array_equal(data[:, ::2, 2:8:2], expected[:, ::2, 2:8:2])
    assert dic["dom"] == ["F", "F", "F"]


def test_3d_transpose(tmp_path):
    npts = (2, 3, 4)
    for domains in permutations(("T1", "T2", "T3")):
        name = "transpose_" + "_".join(domains)
        dic, data = _check_regular(
            tmp_path, name, domains, npts, ("C", "C", "C"))
        expected_shape = tuple(
            2 * npts[int(domain[1]) - 1] for domain in domains[:-1]
        ) + (npts[int(domains[-1][1]) - 1],)
        assert data.shape == expected_shape
        assert dic["layout"][1] == list(domains)
        assert dic["npts"] == list(npts)


def test_3d_transpose_lowmem(tmp_path):
    npts = (2, 3, 4)
    for domains in permutations(("T1", "T2", "T3")):
        name = "transpose_lowmem_" + "_".join(domains)
        dic, data, expected = _check_lowmem(
            tmp_path, name, domains, npts, ("C", "C", "C"))
        assert data.shape == expected.shape
        index = tuple(min(1, size - 1) for size in expected.shape)
        assert data[index] == expected[index]
        assert dic["layout"][1] == list(domains)
        assert dic["npts"] == list(npts)
