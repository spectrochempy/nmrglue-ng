"""Self-contained tests for the descriptive Agilent 2D States profile."""

import numpy as np
import pytest

import nmrglue as ng


def _parameter(values):
    return {"values": [str(value) for value in values]}


def _states_fixture(*, phase=(1, 2), ni=2, arraydim=4, np_raw=6, ntraces=1):
    procpar = {
        "np": _parameter([np_raw]),
        "ni": _parameter([ni]),
        "arraydim": _parameter([arraydim]),
        "phase": _parameter(phase),
        "sw": _parameter([50000.0]),
        "sw1": _parameter([5555.55555556]),
        "sfrq": _parameter([125.0]),
        "sfrq2": _parameter([50.0]),
        "dn": _parameter(["H1"]),
        "dn2": _parameter(["N15"]),
        "ns": _parameter([1]),
        "ne": _parameter([1]),
        "array": _parameter(["phase"]),
        "seqcon": _parameter(["s"]),
    }
    rows = arraydim if isinstance(arraydim, int) else 4
    columns = np_raw // 2 if isinstance(np_raw, int) and np_raw > 0 else 3
    data = (
        np.arange(rows * columns, dtype=np.float32).reshape(rows, columns)
        + 1j * np.arange(rows * columns, dtype=np.float32).reshape(rows, columns)
    ).astype(np.complex64)
    return {"procpar": procpar, "ntraces": ntraces, "np": np_raw}, data


def test_agilent_states_result_preserves_raw_matrix_and_storage_metadata(
    monkeypatch, tmp_path
):
    dic, data = _states_fixture()
    monkeypatch.setattr(ng.varian, "read", lambda *args, **kwargs: (dic, data.copy()))

    result = ng.interop.read_agilent_states_2d(str(tmp_path))

    assert result.format == "agilent-states-2d"
    assert result.data.shape == (4, 3)
    assert result.data.dtype == np.complex64
    np.testing.assert_array_equal(result.data, data)
    assert result.data.flags.writeable is False
    assert tuple(component.name for component in result.components) == ("complex",)
    assert result.axes[0].values is None
    assert result.axes[1].values.shape == (3,)
    assert result.dimensions["physical_shape"] == (2, 3)
    assert result.dimensions["storage_shape"] == (4, 3)
    assert result.dimensions["stored_trace_count"] == 4
    assert result.dimensions["physical_indirect_increments"] == 2
    assert result.acquisition["phase"] == (1, 2)
    assert result.acquisition["normalization"] == "none"
    assert "states_pairing" not in result.applied_corrections
    assert result.dimensions["trace_pairing"] == (
        "trace[2a]=phase=1; trace[2a+1]=phase=2"
    )


@pytest.mark.parametrize(
    "kwargs",
    [
        {"phase": (1, 3)},
        {"phase": (1,)},
        {"phase": (1.5, 2)},
        {"ni": 2.5},
        {"arraydim": 5},
        {"np_raw": 5},
        {"ntraces": 2},
    ],
)
def test_agilent_states_result_rejects_unvalidated_profiles(
    monkeypatch, tmp_path, kwargs
):
    dic, data = _states_fixture(**kwargs)
    monkeypatch.setattr(ng.varian, "read", lambda *args, **kwargs: (dic, data.copy()))

    with pytest.raises(ValueError):
        ng.interop.read_agilent_states_2d(str(tmp_path))


def test_agilent_states_result_reports_missing_axis_metadata(monkeypatch, tmp_path):
    dic, data = _states_fixture()
    del dic["procpar"]["sw1"]
    del dic["procpar"]["sfrq2"]
    dic["procpar"]["dfrq2"] = _parameter([50.0])
    monkeypatch.setattr(ng.varian, "read", lambda *args, **kwargs: (dic, data.copy()))

    result = ng.interop.read_agilent_states_2d(str(tmp_path))

    diagnostic = next(
        item
        for item in result.diagnostics
        if item.code == "acquisition.missing-parameter"
    )
    assert "sw1" in diagnostic.context["missing"]
    assert "sfrq2" in diagnostic.context["missing"]
    assert result.axes[0].values is None


@pytest.mark.parametrize("legacy", [False, True])
def test_normalize_states_scalar_storage(tmp_path, legacy):
    dic, _ = _states_fixture()
    procpar = dic["procpar"]
    procpar["tn"] = _parameter(["C13"])
    procpar["ns"] = _parameter([3])
    procpar["ne"] = _parameter([2])
    scalar = np.arange(24, dtype=np.float32).reshape(4, 6)
    scalar[:, 1::2] *= -3
    metadata = dict(dic, nblocks=4, S_SPEC=0, S_HYPERCOMPLEX=0)
    from nmrglue.interop.storage import _trace_result

    result = _trace_result(
        tmp_path / "fid", scalar, metadata, "agilent-fid-storage",
        blocks=4, traces_per_block=1,
    )
    normalized = ng.interop.normalize(result, legacy_presentation=legacy)

    expected = scalar[:, ::2] + 1j * scalar[:, 1::2]
    divisor = 6 if legacy else 1
    np.testing.assert_array_equal(normalized.data[0], expected[::2] / divisor)
    np.testing.assert_array_equal(normalized.data[1], expected[1::2] / divisor)
    np.testing.assert_array_equal(normalized.axes[1].values, [0, 20e-6, 40e-6])
    if legacy:
        assert normalized.axes[0].values is None
        assert normalized.axes[1].label == "H1"
        assert normalized.applied_operations[-1]["divisor"] == divisor
    else:
        np.testing.assert_allclose(normalized.axes[0].values, [0, 0.00018])
        assert normalized.axes[1].label == "C13"
        assert len(normalized.applied_operations) == 1
    assert normalized.quadrature_mode == "states-stored-2d"
    assert normalized.encoding == ("states", "complex")


@pytest.mark.parametrize("key, value", [("phase", [2, 1]), ("array", ["phase,pw"]), ("ni2", [2])])
def test_states_storage_preflight_rejects_unsupported_array(monkeypatch, tmp_path, key, value):
    dic, _ = _states_fixture()
    dic["procpar"][key] = _parameter(value)
    monkeypatch.setattr(ng.varian, "read_procpar", lambda _: dic["procpar"])
    with pytest.raises(ValueError, match="States storage requires"):
        ng.interop.read_agilent_fid_storage(tmp_path, states_only=True)
