"""Self-contained tests for raw States-TPPI NMRPipe export."""

import dataclasses

import numpy as np
import pytest

import nmrglue as ng


def _result(data=None):
    if data is None:
        data = (
            np.arange(4 * 6, dtype=np.float64).reshape(4, 6)
            + 1j * np.arange(100, 124, dtype=np.float64).reshape(4, 6)
        ).astype(np.complex128)
    sw = (2000.0, 10000.0)
    axes = tuple(
        ng.interop.Axis(
            values=np.arange(data.shape[0] // 2, dtype=float) / sw[0]
            if index == 0
            else np.arange(data.shape[1], dtype=float) / sw[1],
            unit="s",
            label=("15N", "1H")[index],
            domain="time",
            direction="increasing",
        )
        for index in range(2)
    )
    components = (
        ng.interop.Component("RR", data[0::2].real),
        ng.interop.Component("RI", data[0::2].imag),
        ng.interop.Component("IR", data[1::2].real),
        ng.interop.Component("II", data[1::2].imag),
    )
    return ng.interop.ReadResult(
        data=data,
        axes=axes,
        metadata={"vendor": "Bruker"},
        components=components,
        applied_corrections={
            "normalization": "none",
            "states_tppi_alternation": "declared_not_applied",
        },
        diagnostics=(),
        format="bruker-ser-states-tppi-2d",
        source="synthetic-states-tppi",
        domains=("time", "time"),
        encoding=("STATES-TPPI", "DQD"),
        dimensions={
            "physical_shape": (data.shape[0] // 2, data.shape[1]),
            "canonical_shape": (data.shape[0] // 2, data.shape[1]),
            "storage_shape": tuple(data.shape),
            "returned_shape": tuple(data.shape),
            "axis_order": ("F1", "F2"),
            "trace_order": "F1-major, F2-contiguous",
            "tppi_alternation": "declared_not_applied",
            "TD": (data.shape[0] - 1, data.shape[1] * 2),
            "TDeff": (None, None),
        },
        acquisition={
            "axes": (
                {
                    "SW_hz": sw[0],
                    "observation_frequency_mhz": 100.0,
                    "carrier_hz": 500.0,
                },
                {
                    "SW_hz": sw[1],
                    "observation_frequency_mhz": 400.0,
                    "carrier_hz": 1200.0,
                },
            )
        },
    )


def test_states_tppi_roundtrip_and_header(tmp_path):
    result = _result()
    filename = tmp_path / "states-tppi.fid"

    header = ng.interop.write_readresult_nmrpipe(result, filename, overwrite=True)
    saved_header, saved_data = ng.pipe.read(str(filename))

    np.testing.assert_array_equal(saved_data, result.data.astype(np.complex64))
    assert saved_data.dtype == np.complex64
    assert saved_data.shape == (4, 6)
    assert saved_header["FDDIMCOUNT"] == 2.0
    assert saved_header["FDF1QUADFLAG"] == 0.0
    assert saved_header["FDF2QUADFLAG"] == 0.0
    assert saved_header["FDF1AQSIGN"] == 16.0
    assert saved_header["FD2DPHASE"] == 2.0
    assert saved_header["FDF1TDSIZE"] == 2.0
    assert saved_header["FDF2TDSIZE"] == 6.0
    assert saved_header["FDSPECNUM"] == 4.0
    assert header["FDTITLE"] == "ReadResult States-TPPI 2D"


@pytest.mark.parametrize("kind", ["component", "alternation", "encoding"])
def test_states_tppi_export_rejects_inconsistent_contract(tmp_path, kind):
    result = _result()
    if kind == "component":
        components = list(result.components)
        components[0] = ng.interop.Component("RR", components[0].data + 1)
        result = dataclasses.replace(result, components=tuple(components))
    elif kind == "alternation":
        dimensions = dict(result.dimensions)
        dimensions["tppi_alternation"] = "applied"
        result = dataclasses.replace(result, dimensions=dimensions)
    else:
        result = dataclasses.replace(result, encoding=("QF", "DQD"))

    with pytest.raises(ValueError):
        ng.interop.write_readresult_nmrpipe(
            result, tmp_path / "invalid.fid", overwrite=True
        )


def test_states_tppi_export_rejects_unrepresentable_tdeff(tmp_path):
    result = _result()
    dimensions = dict(result.dimensions)
    dimensions["TDeff"] = (2, 6)
    result = dataclasses.replace(result, dimensions=dimensions)

    with pytest.raises(ValueError, match="TDeff"):
        ng.interop.write_readresult_nmrpipe(
            result, tmp_path / "invalid-tdeff.fid", overwrite=True
        )


def test_states_tppi_export_rejects_indirect_td_beyond_storage(tmp_path):
    result = _result()
    dimensions = dict(result.dimensions)
    dimensions["TD"] = (result.data.shape[0] + 1, result.data.shape[1] * 2)
    result = dataclasses.replace(result, dimensions=dimensions)

    with pytest.raises(ValueError, match="exceeds stored"):
        ng.interop.write_readresult_nmrpipe(
            result, tmp_path / "invalid-td.fid", overwrite=True
        )
