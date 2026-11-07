"""Check the NMRPipe 2D storage layout described in NMRPipe's fdatap.h."""

from pathlib import Path

import numpy as np
import pytest

from nmrglue import interop, pipe


@pytest.mark.parametrize(
    "rows,row_complex,trace_complex,transposed,domains",
    [
        (4, True, True, False, ("time", "time")),
        (3, True, True, False, ("time", "time")),
        (4, True, True, True, ("frequency", "frequency")),
        (4, True, False, False, ("time", "frequency")),
        (4, False, True, True, ("frequency", "time")),
        (4, False, False, False, ("frequency", "frequency")),
    ],
)
@pytest.mark.parametrize("byte_order", ["<", ">"])
def test_storage_layout(
    tmp_path, rows, row_complex, trace_complex, transposed, domains, byte_order
):
    cols = 3
    row_axis, trace_axis = (2, 1) if transposed else (1, 2)
    header = pipe.create_empty_dic()
    header.update(
        FDDIMCOUNT=2,
        FDTRANSPOSED=int(transposed),
        FDDIMORDER1=trace_axis,
        FDDIMORDER2=row_axis,
        FDQUADFLAG=int(not (row_complex or trace_complex)),
        FDSPECNUM=rows // 2 if row_complex and not trace_complex else rows,
        FDSIZE=cols,
        FD2DPHASE=2,
    )
    for axis, complex_axis, domain in zip(
        (row_axis, trace_axis), (row_complex, trace_complex), domains, strict=True
    ):
        header[f"FDF{axis}QUADFLAG"] = int(not complex_axis)
        header[f"FDF{axis}FTFLAG"] = int(domain == "frequency")

    real = np.arange(rows * cols, dtype=np.float32).reshape(rows, cols)
    imag = -real - 20
    packed = np.concatenate((real, imag), axis=1) if trace_complex else real
    path = tmp_path / "plane"
    path.write_bytes(
        pipe.dic2fdata(header).astype(byte_order + "f4").tobytes()
        + packed.astype(byte_order + "f4").tobytes()
    )

    result = interop.read_nmrpipe_2d_storage(path)
    np.testing.assert_array_equal(result.data.real, real)
    if trace_complex:
        np.testing.assert_array_equal(result.data.imag, imag)
    assert result.data.dtype == (np.complex64 if trace_complex else np.float32)
    assert result.domains == domains
    assert tuple(axis.domain for axis in result.axes) == domains
    assert all(axis.values is None for axis in result.axes)
    assert result.encoding == (
        "complex" if row_complex else "real", "complex" if trace_complex else "real"
    )
    assert result.dimensions["axis_order"] == (f"F{row_axis}", f"F{trace_axis}")
    assert result.dimensions["stored_shape"] == packed.shape
    assert result.dimensions["shape"] == real.shape
    assert result.dimensions["row_layout"] == (
        "interleaved-real-imaginary" if row_complex else "real"
    )
    assert result.dimensions["trace_layout"] == (
        "appended-real-imaginary" if trace_complex else "real"
    )
    assert result.metadata["FD2DPHASE"] == 2

    with path.open("ab") as stream:
        stream.write(b"\x00")
    with pytest.raises(ValueError, match="payload size"):
        interop.read_nmrpipe_2d_storage(path)


@pytest.mark.parametrize("suffix,shape", [("", (4, 8)), ("_tp", (16, 2))])
def test_stored_fid_matches_historical_reader(suffix, shape):
    root = Path(__file__).resolve().parents[1] / "fixtures" / "fileio" / "data"
    path = root / f"nmrpipe_2d_time{suffix}.fid"
    header, expected = pipe.read(str(path))
    result = interop.read_nmrpipe_2d_storage(path)
    assert result.domains == ("time", "time")
    assert result.encoding == ("complex", "complex")
    assert result.data.shape == shape
    assert result.metadata["FD2DPHASE"] == header["FD2DPHASE"]
    np.testing.assert_array_equal(result.data, expected)
    with pytest.raises(ValueError, match="real frequency 2D"):
        interop.read_nmrpipe_2d(path)


def test_unappend_data_preserves_components_independently():
    packed = np.array([[1.0, -0.0, np.inf, np.nan]], dtype=np.float32)
    with np.errstate(invalid="raise"):
        decoded = pipe.unappend_data(packed)

    np.testing.assert_array_equal(decoded.real, packed[..., :2])
    np.testing.assert_array_equal(decoded.imag, packed[..., 2:])
    assert np.signbit(decoded.real[0, 1])
    assert decoded.dtype == np.complex64
