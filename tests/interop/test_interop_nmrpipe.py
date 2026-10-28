"""Self-contained tests for the experimental ReadResult NMRPipe export."""

import numpy as np
import pytest

import nmrglue as ng


def _result(data, *, encoding, source="synthetic-bruker-fid"):
    sw = 2000.0
    axis = ng.interop.Axis(
        values=np.arange(data.size, dtype=float) / sw,
        unit="s",
        label="<1H>",
        domain="time",
        direction="increasing",
    )
    return ng.interop.ReadResult(
        data=data,
        axes=(axis,),
        metadata={"vendor": "Bruker"},
        components=(
            ng.interop.Component(
                name="complex" if np.iscomplexobj(data) else "real", data=data
            ),
        ),
        applied_corrections={
            "digital_filter": {"applied": False},
            "normalization": "none",
        },
        diagnostics=(),
        format="bruker-fid",
        source=source,
        domains=("time",),
        encoding=(encoding,),
        dimensions={"TD": int(data.size * (2 if np.iscomplexobj(data) else 1))},
        acquisition={
            "spectral_width_hz": sw,
            "observation_frequency_mhz": 400.0,
            "carrier_hz": 1200.0,
            "RG": 40.3,
            "NS": 16,
        },
    )


def test_complex_readresult_nmrpipe_roundtrip_and_header(tmp_path):
    data = (np.arange(8, dtype=np.float64) + 1j * np.arange(8, 16)).astype(
        np.complex128
    )
    result = _result(data, encoding="QSIM")
    before = result.data.copy()
    filename = tmp_path / "complex.fid"

    header = ng.interop.write_readresult_nmrpipe(result, filename, overwrite=True)
    saved_header, saved_data = ng.pipe.read(str(filename))

    np.testing.assert_array_equal(saved_data, data.astype(np.complex64))
    assert saved_data.dtype == np.complex64
    assert saved_header["FDF2QUADFLAG"] == 0.0
    assert saved_header["FDF2TDSIZE"] == 8.0
    assert saved_header["FDF2SW"] == 2000.0
    assert saved_header["FDF2OBS"] == 400.0
    assert saved_header["FDF2CAR"] == pytest.approx(3.0)
    assert header["FDCOMMENT"].startswith("source=synthetic-bruker-fid;")
    np.testing.assert_array_equal(result.data, before)


def test_real_readresult_nmrpipe_roundtrip_declares_real_quadrature(tmp_path):
    data = np.linspace(-2.0, 3.0, 8, dtype=np.float64)
    result = _result(data, encoding="QF")
    filename = tmp_path / "real.fid"

    ng.interop.write_readresult_nmrpipe(result, filename, overwrite=True)
    header, saved_data = ng.pipe.read(str(filename))

    np.testing.assert_array_equal(saved_data, data.astype(np.float32))
    assert saved_data.dtype == np.float32
    assert header["FDF2QUADFLAG"] == 1.0
    assert header["FDF2TDSIZE"] == 8.0


def _with_result(result, *, axis=None, acquisition=None):
    return ng.interop.ReadResult(
        data=result.data,
        axes=(axis,) if axis is not None else result.axes,
        metadata=result.metadata,
        components=result.components,
        applied_corrections=result.applied_corrections,
        diagnostics=result.diagnostics,
        format=result.format,
        source=result.source,
        domains=result.domains,
        encoding=result.encoding,
        dimensions=result.dimensions,
        acquisition=acquisition if acquisition is not None else result.acquisition,
    )


@pytest.mark.parametrize("kind", ["missing-carrier", "bad-axis"])
def test_nmrpipe_export_rejects_incomplete_or_inconsistent_result(tmp_path, kind):
    result = _result(np.ones(8, dtype=np.complex64), encoding="QSIM")
    if kind == "missing-carrier":
        acquisition = dict(result.acquisition)
        del acquisition["carrier_hz"]
        result = _with_result(result, acquisition=acquisition)
    else:
        bad_axis = ng.interop.Axis(
            values=np.arange(8, dtype=float) / 2000.0,
            unit="ppm",
            label="<1H>",
            domain="time",
            direction="increasing",
        )
        result = _with_result(result, axis=bad_axis)
    with pytest.raises(ValueError):
        ng.interop.write_readresult_nmrpipe(
            result, tmp_path / "invalid.fid", overwrite=True
        )


@pytest.mark.parametrize(
    ("data", "domains", "encoding", "match"),
    [
        (np.empty(0, dtype=np.complex64), ("time",), ("QSIM",), "at least one"),
        (np.ones(8, dtype=np.complex64), ("frequency",), ("QSIM",), "domains"),
        (np.ones(8, dtype=np.complex64), ("time",), ("QSIM", "extra"), "encoding"),
        (np.array([np.finfo(np.float64).max] * 8), ("time",), ("QF",), "finite"),
    ],
)
def test_nmrpipe_export_rejects_unrepresentable_profiles(
    tmp_path, data, domains, encoding, match
):
    result = _result(data, encoding=encoding[0])
    result = ng.interop.ReadResult(
        data=result.data,
        axes=result.axes,
        metadata=result.metadata,
        components=result.components,
        applied_corrections=result.applied_corrections,
        diagnostics=result.diagnostics,
        format=result.format,
        source=result.source,
        domains=domains,
        encoding=encoding,
        dimensions=result.dimensions,
        acquisition=result.acquisition,
    )
    with pytest.raises(ValueError, match=match):
        ng.interop.write_readresult_nmrpipe(
            result, tmp_path / "invalid-profile.fid", overwrite=True
        )
