"""Self-contained tests for the descriptive Agilent 2D States profile."""

import hashlib
from dataclasses import replace

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
    del procpar["seqcon"]
    del procpar["sfrq2"]
    procpar["dfrq2"] = _parameter([0])
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
    assert normalized.axes[0].reference is None
    assert normalized.acquisition["observation_frequencies_mhz"] == (None, 125.0)
    if legacy:
        assert normalized.acquisition["legacy_presentation"]["observation_frequencies_mhz"] == (0, 125.0)
        assert normalized.axes[0].values is None
        assert normalized.axes[1].label == "H1"
        assert normalized.applied_operations[-1]["divisor"] == divisor
    else:
        np.testing.assert_allclose(normalized.axes[0].values, [0, 0.00018])
        assert normalized.axes[1].label == "C13"
        assert len(normalized.applied_operations) == 1
    assert normalized.quadrature_mode == "states-stored-2d"
    assert normalized.encoding == ("states", "complex")


def test_states_quadrature_selection_keeps_storage(tmp_path, monkeypatch):
    from nmrglue.interop import varian as adapter
    from nmrglue.interop.storage import _trace_result

    dic, _ = _states_fixture()
    procpar = dic["procpar"]
    del procpar["seqcon"]
    procpar["seqfil"] = _parameter(["NOESY"])
    procpar["d2"] = _parameter([0])
    scalar = np.arange(24, dtype=np.float32).reshape(4, 6)
    result = _trace_result(
        tmp_path / "fid", scalar,
        dict(dic, nblocks=4, S_SPEC=0, S_HYPERCOMPLEX=0, S_DATA=1, S_COMPLEX=1),
        "agilent-fid-storage", blocks=4, traces_per_block=1,
    )
    baseline = ng.interop.normalize(result, legacy_presentation=True)
    unknown = ng.interop.normalize(result, legacy_presentation=True, quadrature="auto")
    assert unknown.acquisition["quadrature_selection"]["mode"] is None
    np.testing.assert_array_equal(unknown.data, baseline.data)

    manual = ng.interop.normalize(result, legacy_presentation=True, quadrature="states")
    assert manual.acquisition["quadrature_selection"]["source"] == "manual"
    assert manual.acquisition["states_fft_input_transform"] == "conjugate-and-negate-second-branch"
    np.testing.assert_array_equal(manual.data, baseline.data)
    np.testing.assert_allclose(manual.axes[0].values, [0, 0.00018])

    source = tmp_path / "NOESY.c"
    source.write_bytes(b"test pulse source")
    fingerprint = hashlib.sha256(source.read_bytes()).hexdigest()
    monkeypatch.setattr(adapter, "_STATES_PROGRAMS", {
        ("NOESY", fingerprint): ("states-tppi", "reference"),
    })
    automatic = ng.interop.normalize(result, quadrature="auto")
    assert automatic.acquisition["quadrature_selection"] == {
        "mode": "states-tppi", "source": "pulse-program", "sequence": "NOESY",
        "sha256": fingerprint, "reference": "reference",
    }
    for key, values in (
        ("d2", [0.001]), ("d2", [0, 0.125]),
        ("seqfil", ["NOESY", "different"]), ("sampling", ["sparse"]),
    ):
        modified = replace(result, metadata={
            **result.metadata, "procpar": {**procpar, key: _parameter(values)},
        })
        unresolved = ng.interop.normalize(
            modified, quadrature="auto", pulse_program_source=source,
        )
        assert unresolved.acquisition["quadrature_selection"]["mode"] is None
        np.testing.assert_array_equal(unresolved.data, baseline.data)
        if key == "sampling":
            with pytest.raises(ValueError, match="complete calibrated"):
                ng.interop.normalize(modified, quadrature="states")
    source.write_bytes(b"local variant with the same name")
    unmatched = ng.interop.normalize(result, quadrature="auto")
    assert unmatched.acquisition["quadrature_selection"]["mode"] is None
    source.write_bytes(bytes(256 * 1024 + 1))
    oversized = ng.interop.normalize(result, quadrature="auto")
    assert oversized.acquisition["quadrature_selection"]["mode"] is None
    with pytest.raises(FileNotFoundError):
        ng.interop.normalize(result, quadrature="auto", pulse_program_source=tmp_path / "missing.c")
    for flag in ("S_DATA", "S_COMPLEX"):
        unsupported = replace(result, metadata={**result.metadata, flag: 0})
        with pytest.raises(ValueError, match="raw complex storage"):
            ng.interop.normalize(unsupported, quadrature="states")


@pytest.mark.parametrize(
    "key, value",
    [("phase", [2, 1]), ("array", ["phase,pw"]), ("ni2", [2]), ("seqcon", ["nnnnn"])],
)
def test_states_storage_preflight_rejects_unsupported_array(monkeypatch, tmp_path, key, value):
    dic, _ = _states_fixture()
    del dic["procpar"]["seqcon"]
    dic["procpar"][key] = _parameter(value)
    monkeypatch.setattr(ng.varian, "read_procpar", lambda _: dic["procpar"])
    with pytest.raises(ValueError, match="States storage requires"):
        ng.interop.read_agilent_fid_storage(tmp_path, states_only=True)


@pytest.mark.parametrize("legacy", [False, True])
def test_normalize_tppi_scalar_storage(tmp_path, legacy):
    from nmrglue.interop.storage import _trace_result

    dic, _ = _states_fixture(phase=(3,), ni=4, arraydim=4)
    procpar = dic["procpar"]
    del procpar["seqcon"]
    procpar["array"] = _parameter([""])
    procpar["ns"] = _parameter([2])
    procpar["ne"] = _parameter([3])
    words = np.arange(24, dtype=np.int32).reshape(4, 6)
    words[:, 1::2] *= -7
    metadata = dict(dic, nblocks=4, S_SPEC=0, S_HYPERCOMPLEX=0)
    result = _trace_result(
        tmp_path / "fid", words, metadata, "agilent-fid-storage",
        blocks=4, traces_per_block=1,
    )
    normalized = ng.interop.normalize(result, legacy_presentation=legacy)
    expected = words[:, ::2] + 1j * words[:, 1::2]
    np.testing.assert_array_equal(normalized.data, expected / (6 if legacy else 1))
    assert normalized.data.dtype == np.complex128
    assert normalized.dimensions == ("F1", "F2")
    assert normalized.quadrature_mode == "tppi-stored-2d"
    assert normalized.encoding == ("tppi", "complex")
    assert normalized.acquisition["nuclei"][0] is None
    assert normalized.channel_axis is None
    assert normalized.applied_operations[0]["permutation"] is None
    if legacy:
        assert normalized.axes[0].values is None
        assert normalized.axes[0].label == "N15"
        assert normalized.applied_operations[-1]["divisor"] == 6
    else:
        np.testing.assert_allclose(normalized.axes[0].values, np.arange(4) * 0.00018)
        assert normalized.axes[0].label is None


@pytest.mark.parametrize(
    "key, value",
    [("phase", [2]), ("array", ["phase"]), ("arraydim", [8]), ("ni2", [2]), ("ni2", [0]),
     ("seqcon", ["nnnnn"])],
)
def test_tppi_preflight_rejects_ambiguous_topology(monkeypatch, tmp_path, key, value):
    dic, _ = _states_fixture(phase=(3,), ni=4, arraydim=4)
    procpar = dic["procpar"]
    del procpar["seqcon"]
    procpar["array"] = _parameter([""])
    procpar[key] = _parameter(value)
    monkeypatch.setattr(ng.varian, "read_procpar", lambda _: procpar)
    with pytest.raises(ValueError, match="TPPI storage requires"):
        ng.interop.read_agilent_fid_storage(tmp_path, tppi_only=True)



def test_tppi_preflight_rejects_single_trace(monkeypatch, tmp_path):
    dic, _ = _states_fixture(phase=(3,), ni=1, arraydim=1)
    procpar = dic["procpar"]
    del procpar["seqcon"]
    procpar["array"] = _parameter([""])
    monkeypatch.setattr(ng.varian, "read_procpar", lambda _: procpar)
    with pytest.raises(ValueError, match="ni>=2"):
        ng.interop.read_agilent_fid_storage(tmp_path, tppi_only=True)



def test_tppi_preflight_rejects_sparse_sampling(monkeypatch, tmp_path):
    dic, _ = _states_fixture(phase=(3,), ni=4, arraydim=4)
    procpar = dic["procpar"]
    del procpar["seqcon"]
    procpar["array"] = _parameter([""])
    procpar["sampling"] = _parameter(["sparse"])
    monkeypatch.setattr(ng.varian, "read_procpar", lambda _: procpar)
    with pytest.raises(ValueError, match="uniform sampling"):
        ng.interop.read_agilent_fid_storage(tmp_path, tppi_only=True)
    procpar["sampling"] = _parameter(["uniform"])
    (tmp_path / "sampling.sch").touch()
    with pytest.raises(ValueError, match="uniform sampling"):
        ng.interop.read_agilent_fid_storage(tmp_path, tppi_only=True)


@pytest.mark.parametrize("legacy", [False, True])
def test_normalize_agilent_multitrace_series(tmp_path, legacy):
    from nmrglue.interop.storage import _trace_result

    words = np.arange(48, dtype=np.int32).reshape(6, 8)
    words[:, 1::2] *= -3
    procpar = {
        key: _parameter(values)
        for key, values in {
            "np": [8], "nf": [3], "arraydim": [2], "sw": [5000],
            "array": [""], "ns": [3], "ne": [2],
        }.items()
    }
    metadata = dict(procpar=procpar, nblocks=2, ntraces=3, np=8,
                    S_SPEC=0, S_HYPERCOMPLEX=0, S_DATA=1, S_COMPLEX=1)
    stored = _trace_result(
        tmp_path / "fid", words, metadata, "agilent-fid-storage",
        blocks=2, traces_per_block=3,
    )
    result = ng.interop.normalize(stored, legacy_presentation=legacy)
    expected = words[:, ::2] + 1j * words[:, 1::2]
    np.testing.assert_array_equal(result.data, expected / (6 if legacy else 1))
    assert result.dimensions == ("trace", "F2")
    assert result.domains == ("unknown", "time")
    assert result.axes[0].values is None
    assert result.axes[0].reference is None
    assert result.acquisition["blocks"] == 2
    assert result.acquisition["traces_per_block"] == 3
    np.testing.assert_allclose(result.axes[1].values, np.arange(4) / 5000)

    from dataclasses import replace

    with pytest.raises(ValueError, match="raw trace geometry"):
        ng.interop.normalize(replace(stored, metadata={**metadata, "S_COMPLEX": 0}))
