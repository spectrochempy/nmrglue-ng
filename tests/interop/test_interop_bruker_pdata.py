"""Tests for the additive :mod:`nmrglue.interop` Bruker processed 1D profile.

These tests are self-contained: they synthesize a minimal Bruker ``pdata/1``
directory (a text ``procs`` file plus raw component binaries) under pytest's
``tmp_path``.  The normative rule under test is::

    f[i] = OFFSET * SF - i * (SW_p / N)

with ``N = data.shape[0]``; the first point is exactly ``OFFSET * SF`` Hz and
the direction is strictly decreasing.
"""

import dataclasses
import os
import subprocess
import sys

import numpy as np
import pytest
from numpy.testing import assert_array_equal

import nmrglue as ng
from nmrglue.fileio import fileiobase
from nmrglue.interop import Diagnostic

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))

_DTYPES = {
    ("int32", False): "<i4",
    ("int32", True): ">i4",
    ("float64", False): "<f8",
    ("float64", True): ">f8",
}

_HEAVY_MODULES = ("spectrochempy", "pint", "csdmpy")


def _fmt(value):
    if isinstance(value, bool):
        return "yes" if value else "no"
    if isinstance(value, str):
        return value
    if isinstance(value, int):
        return str(value)
    return repr(float(value))


def _write_pdata(
    root,
    component_values=None,
    *,
    dtype="int32",
    big=False,
    si=None,
    nc_proc=-1,
    offset=10.0,
    sf=400.0,
    sw_p=4000.0,
    procs_extra=None,
    omit=(),
):
    """Create a minimal Bruker processed directory and return its path."""
    if component_values is None:
        component_values = {"1r": [100, 200, 300, 400]}

    pdata = os.path.join(str(root), "pdata", "1")
    os.makedirs(pdata, exist_ok=True)

    n = len(next(iter(component_values.values())))
    if si is None:
        si = n

    dt = _DTYPES[(dtype, big)]
    for name, values in component_values.items():
        array = np.asarray(values, dtype=np.dtype(dt))
        with open(os.path.join(pdata, name), "wb") as handle:
            handle.write(array.tobytes())

    entries = {
        "SI": si,
        "XDIM": si,
        "DTYPP": 2 if dtype == "float64" else 0,
        "BYTORDP": 1 if big else 0,
        "NC_proc": nc_proc,
        "OFFSET": offset,
        "SF": sf,
        "SW_p": sw_p,
    }
    if procs_extra:
        entries.update(procs_extra)
    for key in omit:
        entries.pop(key, None)

    lines = ["##TITLE= synthetic"]
    lines += ["##$%s= %s" % (key, _fmt(value)) for key, value in entries.items()]
    lines += ["##$AXNUC= <1H>", "##END="]
    with open(os.path.join(pdata, "procs"), "w") as handle:
        handle.write("\n".join(lines) + "\n")

    return pdata


def _expected_axis(n, offset, sf, sw_p):
    return offset * sf - np.arange(n, dtype=np.float64) * (sw_p / n)


class TestAxis:
    def test_values_unit_direction_and_reference(self, tmp_path):
        pdata = _write_pdata(tmp_path)
        result = ng.interop.read_bruker_pdata(pdata)

        axis = result.axes[0]
        assert axis.unit == "Hz"
        assert axis.domain == "frequency"
        assert axis.direction == "decreasing"
        assert axis.label == "1H"
        assert_array_equal(axis.values, _expected_axis(4, 10.0, 400.0, 4000.0))
        assert axis.values.dtype == np.float64

        assert axis.reference.observation_frequency == 400.0
        assert axis.reference.observation_frequency_unit == "MHz"
        assert axis.reference.offset == 10.0
        assert axis.reference.offset_unit == "ppm"
        assert axis.reference.source == "processing"

    def test_first_point_is_offset_times_sf(self, tmp_path):
        pdata = _write_pdata(tmp_path, offset=12.5, sf=500.0, sw_p=2500.0)
        result = ng.interop.read_bruker_pdata(pdata)
        assert result.axes[0].values[0] == 12.5 * 500.0

    def test_matches_historical_unit_conversion(self, tmp_path):
        pdata = _write_pdata(tmp_path)
        dic, data = ng.bruker.read_pdata(pdata)
        udic = ng.bruker.guess_udic(dic, data, pdata=True)
        uc = fileiobase.uc_from_udic(udic)
        expected = np.array([uc.hz(i) for i in range(data.shape[0])])

        result = ng.interop.read_bruker_pdata(pdata)
        assert_array_equal(result.axes[0].values, expected)

    def test_axis_uses_read_length_not_si(self, tmp_path):
        pdata = _write_pdata(tmp_path, si=8)
        result = ng.interop.read_bruker_pdata(pdata)
        axis = result.axes[0]
        assert axis.values.shape == (4,)
        assert_array_equal(axis.values, _expected_axis(4, 10.0, 400.0, 4000.0))
        codes = [d.code for d in result.diagnostics]
        assert "axis.size-mismatch" in codes
        diag = next(d for d in result.diagnostics if d.code == "axis.size-mismatch")
        assert dict(diag.context) == {"SI": 8, "N": 4}

    def test_missing_parameter_yields_no_axis(self, tmp_path):
        pdata = _write_pdata(tmp_path, omit=("SW_p",))
        result = ng.interop.read_bruker_pdata(pdata)
        axis = result.axes[0]
        assert axis.values is None
        assert axis.unit is None
        assert axis.domain == "unknown"
        assert axis.direction == "unknown"
        assert axis.reference.offset == 10.0
        assert axis.reference.observation_frequency == 400.0
        diag = next(d for d in result.diagnostics if d.code == "axis.missing-parameter")
        assert dict(diag.context) == {"missing": ("SW_p",)}

    def test_reference_partial_sf_only(self, tmp_path):
        pdata = _write_pdata(tmp_path, omit=("OFFSET",))
        result = ng.interop.read_bruker_pdata(pdata)
        axis = result.axes[0]
        assert axis.values is None
        assert axis.reference.observation_frequency == 400.0
        assert axis.reference.observation_frequency_unit == "MHz"
        assert axis.reference.offset is None
        assert axis.reference.offset_unit is None

    def test_reference_partial_offset_only(self, tmp_path):
        pdata = _write_pdata(tmp_path, omit=("SF",))
        result = ng.interop.read_bruker_pdata(pdata)
        axis = result.axes[0]
        assert axis.values is None
        assert axis.reference.observation_frequency is None
        assert axis.reference.offset == 10.0
        assert axis.reference.offset_unit == "ppm"

    def test_all_parameters_absent_gives_no_reference(self, tmp_path):
        pdata = _write_pdata(tmp_path, omit=("OFFSET", "SF", "SW_p"))
        result = ng.interop.read_bruker_pdata(pdata)
        assert result.axes[0].reference is None
        diag = next(d for d in result.diagnostics if d.code == "axis.missing-parameter")
        assert dict(diag.context) == {"missing": ("OFFSET", "SF", "SW_p")}

    @pytest.mark.parametrize("bad_sw_p", [0.0, -5.0])
    def test_non_positive_sw_p_raises(self, tmp_path, bad_sw_p):
        pdata = _write_pdata(tmp_path, sw_p=bad_sw_p)
        with pytest.raises(ValueError):
            ng.interop.read_bruker_pdata(pdata)

    def test_non_finite_parameter_raises(self, tmp_path):
        pdata = _write_pdata(tmp_path, sw_p=float("inf"))
        with pytest.raises(ValueError):
            ng.interop.read_bruker_pdata(pdata)

    def test_non_numeric_parameter_raises(self, tmp_path):
        pdata = _write_pdata(tmp_path, procs_extra={"SW_p": "<nan>"})
        with pytest.raises(ValueError):
            ng.interop.read_bruker_pdata(pdata)


class TestComponents:
    def test_default_single_component(self, tmp_path):
        pdata = _write_pdata(tmp_path)
        result = ng.interop.read_bruker_pdata(pdata)
        assert [c.name for c in result.components] == ["1r"]
        assert_array_equal(result.data, result.components[0].data)
        assert not [d for d in result.diagnostics if d.code == "component.missing"]

    def test_singleton_is_wrapped_not_a_scalar(self, tmp_path):
        pdata = _write_pdata(tmp_path)
        result = ng.interop.read_bruker_pdata(pdata, all_components=True)
        assert [c.name for c in result.components] == ["1r"]
        assert result.components[0].data.shape == (4,)
        diag = next(d for d in result.diagnostics if d.code == "component.missing")
        assert dict(diag.context) == {
            "expected": ("1r", "1i"),
            "missing": ("1i",),
        }

    def test_all_components_map_by_name(self, tmp_path):
        pdata = _write_pdata(
            tmp_path, {"1r": [100, 200, 300, 400], "1i": [10, 20, 30, 40]}
        )
        result = ng.interop.read_bruker_pdata(pdata, all_components=True)
        assert [c.name for c in result.components] == ["1r", "1i"]
        by_name = {c.name: c.data for c in result.components}
        assert_array_equal(by_name["1r"], np.array([50.0, 100.0, 150.0, 200.0]))
        assert_array_equal(by_name["1i"], np.array([5.0, 10.0, 15.0, 20.0]))
        assert_array_equal(result.data, by_name["1r"])

    def test_custom_bin_files_order_preserved(self, tmp_path):
        pdata = _write_pdata(
            tmp_path, {"1r": [100, 200, 300, 400], "1i": [10, 20, 30, 40]}
        )
        result = ng.interop.read_bruker_pdata(
            pdata, all_components=True, bin_files=["1i", "1r"]
        )
        assert [c.name for c in result.components] == ["1i", "1r"]
        assert_array_equal(result.data, np.array([50.0, 100.0, 150.0, 200.0]))

    def test_all_components_false_rejects_extra_files(self, tmp_path):
        pdata = _write_pdata(
            tmp_path, {"1r": [100, 200, 300, 400], "1i": [10, 20, 30, 40]}
        )
        with pytest.raises(ValueError):
            ng.interop.read_bruker_pdata(
                pdata, all_components=False, bin_files=["1r", "1i"]
            )

    def test_all_components_false_accepts_explicit_primary(self, tmp_path):
        pdata = _write_pdata(tmp_path)
        result = ng.interop.read_bruker_pdata(
            pdata, all_components=False, bin_files=["1r"]
        )
        assert [c.name for c in result.components] == ["1r"]

    def test_primary_absent_raises(self, tmp_path):
        pdata = _write_pdata(tmp_path, {"1i": [10, 20, 30, 40]})
        with pytest.raises(ValueError):
            ng.interop.read_bruker_pdata(pdata)
        with pytest.raises(ValueError):
            ng.interop.read_bruker_pdata(
                pdata, all_components=True, bin_files=["1r", "1i"]
            )

    def test_missing_directory_raises_oserror(self, tmp_path):
        with pytest.raises(OSError):
            ng.interop.read_bruker_pdata(str(tmp_path / "does-not-exist"))

    def test_format_and_source(self, tmp_path):
        pdata = _write_pdata(tmp_path)
        result = ng.interop.read_bruker_pdata(pdata)
        assert result.format == "bruker-pdata"
        assert result.source == pdata


class TestDataFidelity:
    @pytest.mark.parametrize("scale_data", [True, False])
    def test_bit_identical_to_historical(self, tmp_path, scale_data):
        pdata = _write_pdata(tmp_path)
        _, history = ng.bruker.read_pdata(pdata, scale_data=scale_data)
        result = ng.interop.read_bruker_pdata(pdata, scale_data=scale_data)
        assert_array_equal(result.data, history)
        assert result.data.dtype == history.dtype

    def test_applied_corrections(self, tmp_path):
        pdata = _write_pdata(tmp_path)
        scaled = ng.interop.read_bruker_pdata(pdata, scale_data=True)
        assert scaled.applied_corrections["scale_data"] is True
        assert scaled.applied_corrections["NC_proc"] == -1

        raw = ng.interop.read_bruker_pdata(pdata, scale_data=False)
        assert raw.applied_corrections["scale_data"] is False
        assert "NC_proc" not in raw.applied_corrections


class TestImmutability:
    def test_arrays_are_read_only(self, tmp_path):
        pdata = _write_pdata(tmp_path)
        result = ng.interop.read_bruker_pdata(pdata)
        for array in (
            result.data,
            result.components[0].data,
            result.axes[0].values,
        ):
            assert array.flags.writeable is False
            with pytest.raises(ValueError):
                array[0] = 0

    def test_mappings_are_read_only_at_top_level(self, tmp_path):
        pdata = _write_pdata(tmp_path)
        result = ng.interop.read_bruker_pdata(pdata)
        with pytest.raises(TypeError):
            result.metadata["new"] = 1
        with pytest.raises(TypeError):
            result.applied_corrections["new"] = 1

    def test_dataclasses_are_frozen(self, tmp_path):
        pdata = _write_pdata(tmp_path)
        result = ng.interop.read_bruker_pdata(pdata)
        with pytest.raises(dataclasses.FrozenInstanceError):
            result.format = "other"
        with pytest.raises(dataclasses.FrozenInstanceError):
            result.axes[0].unit = "ppm"


class TestDiagnostics:
    def test_valid_schema_accepted(self):
        diag = Diagnostic(
            code="axis.size-mismatch",
            severity="warning",
            message="x",
            context={"SI": 4, "N": 4},
        )
        assert dict(diag.context) == {"SI": 4, "N": 4}

    def test_unknown_code_rejected(self):
        with pytest.raises(ValueError):
            Diagnostic(code="nope", severity="warning", message="x")

    def test_bad_severity_rejected(self):
        with pytest.raises(ValueError):
            Diagnostic(
                code="axis.size-mismatch",
                severity="error",
                message="x",
                context={"SI": 4, "N": 4},
            )

    def test_missing_context_key_rejected(self):
        with pytest.raises(ValueError):
            Diagnostic(
                code="axis.size-mismatch",
                severity="warning",
                message="x",
                context={"SI": 4},
            )

    def test_wrong_context_type_rejected(self):
        with pytest.raises(ValueError):
            Diagnostic(
                code="axis.size-mismatch",
                severity="warning",
                message="x",
                context={"SI": "a", "N": 4},
            )

    def test_tuple_required_for_named_collections(self):
        with pytest.raises(ValueError):
            Diagnostic(
                code="component.missing",
                severity="warning",
                message="x",
                context={"expected": ["1r"], "missing": ()},
            )


class TestIsolation:
    def test_heavy_dependencies_not_imported(self):
        code = (
            "import sys\n"
            "import nmrglue.interop\n"
            "leaked = [m for m in %r if m in sys.modules]\n"
            "assert not leaked, leaked\n"
            "print('ok')\n" % (_HEAVY_MODULES,)
        )
        completed = subprocess.run(
            [sys.executable, "-c", code],
            capture_output=True,
            text=True,
            cwd=REPO_ROOT,
        )
        assert completed.returncode == 0, completed.stderr
        assert completed.stdout.strip() == "ok"
