"""Self-contained tests for raw QF 2D ReadResult NMRPipe export."""

import dataclasses

import numpy as np
import pytest

import nmrglue as ng


def _result(data=None):
    if data is None:
        data = (
            np.arange(12, dtype=np.float64).reshape(3, 4)
            + 1j * np.arange(100, 112, dtype=np.float64).reshape(3, 4)
        ).astype(np.complex128)
    sw = (1000.0, 2000.0)
    axes = tuple(
        ng.interop.Axis(
            values=np.arange(data.shape[index], dtype=float) / sw[index],
            unit="s",
            label=("13C", "1H")[index],
            domain="time",
            direction="increasing",
        )
        for index in range(2)
    )
    return ng.interop.ReadResult(
        data=data,
        axes=axes,
        metadata={"vendor": "Bruker"},
        components=(ng.interop.Component("complex", data),),
        applied_corrections={
            "normalization": "none",
            "digital_filter": {"applied": False},
        },
        diagnostics=(),
        format="bruker-ser-qf-2d",
        source="synthetic-qf-2d",
        domains=("time", "time"),
        encoding=("QF", "DQD"),
        dimensions={
            "physical_shape": tuple(data.shape),
            "storage_shape": tuple(data.shape),
            "returned_shape": tuple(data.shape),
            "axis_order": ("F1", "F2"),
            "trace_order": "F1-major, F2-contiguous",
            "TD": (data.shape[0], data.shape[1] * 2),
            "TDeff": (None, None),
        },
        acquisition={
            "axes": (
                {
                    "SW_hz": sw[0],
                    "observation_frequency_mhz": 100.0,
                    "carrier_hz": 500.0,
                    "dwell_time_s": 1.0 / sw[0],
                },
                {
                    "SW_hz": sw[1],
                    "observation_frequency_mhz": 400.0,
                    "carrier_hz": 1200.0,
                    "dwell_time_s": 1.0 / sw[1],
                },
            ),
            "RG": 40.3,
            "NS": 16,
        },
    )


def test_qf_2d_roundtrip_and_header(tmp_path):
    result = _result()
    before = result.data.copy()
    filename = tmp_path / "qf.fid"

    header = ng.interop.write_readresult_nmrpipe(result, filename, overwrite=True)
    saved_header, saved_data = ng.pipe.read(str(filename))

    np.testing.assert_array_equal(saved_data, result.data.astype(np.complex64))
    assert saved_data.dtype == np.complex64
    assert saved_data.shape == (3, 4)
    assert saved_header["FDDIMCOUNT"] == 2.0
    assert saved_header["FDF1QUADFLAG"] == 1.0
    assert saved_header["FDF2QUADFLAG"] == 0.0
    assert saved_header["FDF1TDSIZE"] == 3.0
    assert saved_header["FDF2TDSIZE"] == 4.0
    assert saved_header["FDSIZE"] == 4.0
    assert saved_header["FDSPECNUM"] == 3.0
    assert saved_header["FDF1SW"] == 1000.0
    assert saved_header["FDF2SW"] == 2000.0
    assert saved_header["FDF1OBS"] == 100.0
    assert saved_header["FDF2OBS"] == 400.0
    assert saved_header["FDF1CAR"] == pytest.approx(5.0)
    assert saved_header["FDF2CAR"] == pytest.approx(3.0)
    assert header["FDTITLE"] == "ReadResult QF 2D"
    np.testing.assert_array_equal(result.data, before)


def test_qf_2d_export_preserves_no_rg_ns_normalization(tmp_path):
    result = _result()
    filename = tmp_path / "qf.fid"

    ng.interop.write_readresult_nmrpipe(result, filename, overwrite=True)
    _, saved_data = ng.pipe.read(str(filename))

    np.testing.assert_array_equal(saved_data, result.data.astype(np.complex64))
    assert result.applied_corrections["normalization"] == "none"
    assert result.acquisition["RG"] == 40.3
    assert result.acquisition["NS"] == 16


def test_qf_2d_export_rejects_inconsistent_raw_dimensions(tmp_path):
    result = _result()
    dimensions = dict(result.dimensions)
    dimensions["physical_shape"] = (99, 99)
    result = dataclasses.replace(result, dimensions=dimensions)

    with pytest.raises(ValueError, match="TD-derived raw shape"):
        ng.interop.write_readresult_nmrpipe(
            result, tmp_path / "invalid-shape.ft2", overwrite=True
        )


@pytest.mark.parametrize("shape", [(0, 4), (3, 0)])
def test_qf_2d_export_rejects_empty_data(tmp_path, shape):
    result = _result(np.empty(shape, dtype=np.complex128))

    with pytest.raises(ValueError, match="non-empty"):
        ng.interop.write_readresult_nmrpipe(
            result, tmp_path / "empty.ft2", overwrite=True
        )


@pytest.mark.parametrize(
    "match",
    [
        "declared",
        "axes",
    ],
)
def test_qf_2d_export_rejects_unsupported_or_incomplete_profiles(tmp_path, match):
    result = _result()
    if match == "declared":
        dimensions = dict(result.dimensions)
        del dimensions["trace_order"]
        result = ng.interop.ReadResult(
            data=result.data,
            axes=result.axes,
            metadata=result.metadata,
            components=result.components,
            applied_corrections=result.applied_corrections,
            diagnostics=result.diagnostics,
            format=result.format,
            source=result.source,
            domains=result.domains,
            encoding=result.encoding,
            dimensions=dimensions,
            acquisition=result.acquisition,
        )
    else:
        acquisition = dict(result.acquisition)
        acquisition["axes"] = (acquisition["axes"][0],)
        result = ng.interop.ReadResult(
            data=result.data,
            axes=result.axes,
            metadata=result.metadata,
            components=result.components,
            applied_corrections=result.applied_corrections,
            diagnostics=result.diagnostics,
            format=result.format,
            source=result.source,
            domains=result.domains,
            encoding=result.encoding,
            dimensions=result.dimensions,
            acquisition=acquisition,
        )
    with pytest.raises(ValueError, match=match):
        ng.interop.write_readresult_nmrpipe(
            result, tmp_path / "invalid.ft2", overwrite=True
        )


@pytest.mark.parametrize("transposed", [False, True])
def test_normalize_qf_2d_export_preserves_samples_and_dwell(tmp_path, transposed):
    result = _result()
    path = tmp_path / "qf.fid"
    header = ng.interop.write_readresult_nmrpipe(result, path)
    assert header["FD2DPHASE"] == 0
    order, encoding, branches = ("F1", "F2"), ("real", "complex"), ("rr", "ri")
    expected = result.data
    axes = result.axes
    if transposed:
        rows, cols = expected.shape
        header.update(FDTRANSPOSED=1, FDDIMORDER1=1, FDDIMORDER2=2, FDSIZE=rows, FDSPECNUM=cols)
        expected = expected.T
        packed = np.stack((expected.real, expected.imag), axis=1).reshape(2 * cols, rows)
        path.write_bytes(ng.pipe.dic2fdata(header).tobytes() + packed.astype(np.float32).tobytes())
    stored = ng.interop.read(path)
    if transposed:
        with pytest.raises(ValueError, match="non-transposed"):
            ng.interop.normalize(stored, confirm_time_grid=True)
        return
    with pytest.raises(ValueError, match="confirm_time_grid=True"):
        ng.interop.normalize(stored)
    normalized = ng.interop.normalize(stored, confirm_time_grid=True)
    assert normalized.acquisition["indirect_sampling"] == "qf"
    assert normalized.physical_dimensions == order
    assert normalized.domains == ("time", "time")
    assert normalized.encoding == encoding
    assert normalized.branch_order == branches
    np.testing.assert_array_equal(normalized.data[0], expected.real)
    np.testing.assert_array_equal(normalized.data[1], expected.imag)
    for axis, expected_axis in zip(normalized.axes, axes, strict=True):
        assert axis.unit == "s"
        np.testing.assert_array_equal(axis.values, expected_axis.values)
