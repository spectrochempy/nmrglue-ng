"""Self-contained tests for the additive Agilent raw 1D profile."""

import dataclasses

import numpy as np
import pytest

import nmrglue as ng


def _procpar():
    def p(values):
        return {"values": [str(value) for value in values]}

    return {
        "np": p([8]),
        "sw": p([2000.0]),
        "sfrq": p([125.0]),
        "dfrq": p([499.0]),
        "dn": p(["H1"]),
        "tn": p(["C13"]),
        "ns": p([4]),
        "ne": p([2]),
        "rfl": p([25000.0]),
        "rfp": p([0.0]),
        "reffrq": p([125.0]),
        "tof": p([0.0]),
    }


def _dic_data():
    data = np.asarray([1 + 2j, 3 + 4j, 5 + 6j, 7 + 8j], dtype=np.complex64)
    return {"procpar": _procpar(), "nblocks": 1, "ntraces": 1, "np": 8}, data


def test_agilent_raw_result_preserves_data_and_normalized_metadata(
    monkeypatch, tmp_path
):
    dic, data = _dic_data()
    monkeypatch.setattr(ng.varian, "read", lambda *args, **kwargs: (dic, data.copy()))

    result = ng.interop.read_agilent_fid(str(tmp_path), carrier_ppm=99.0)

    assert result.format == "agilent-fid"
    assert result.data.dtype == np.complex64
    np.testing.assert_array_equal(result.data, data)
    assert result.domains == ("time",)
    assert result.encoding == ("QSIM",)
    assert result.acquisition["spectral_width_hz"] == 2000.0
    assert result.acquisition["dwell_time_s"] == pytest.approx(0.0005)
    assert result.acquisition["observation_frequency_mhz"] == 125.0
    assert result.acquisition["carrier_ppm"] == 99.0
    assert result.acquisition["carrier_hz"] == 12375.0
    assert result.acquisition["NS"] == 4.0
    assert result.acquisition["NE"] == 2.0
    assert result.acquisition["normalization"] == "none"
    assert result.metadata["procpar"] == dic["procpar"]
    assert result.data.flags.writeable is False

    normalized = ng.interop.normalize_agilent_fid(result)
    assert normalized.normalization_state == "storage-normalized"
    assert normalized.normalization_profile == "agilent-fid-1d-complex-v1"
    assert normalized.dimensions == ("F2",)
    assert normalized.physical_dimensions == ("F2",)
    assert normalized.quadrature_mode == "complex-1d"
    assert normalized.branch_order == ("complex",)
    assert normalized.data.flags.writeable is False
    np.testing.assert_array_equal(normalized.data, data)
    assert normalized.applied_operations[0]["conjugation"] == "none"
    assert normalized.provenance["format"] == "agilent-fid"


def test_agilent_normalization_preserves_unknown_axis_calibration(
    monkeypatch, tmp_path
):
    dic, data = _dic_data()
    del dic["procpar"]["sw"]
    monkeypatch.setattr(ng.varian, "read", lambda *args, **kwargs: (dic, data.copy()))

    normalized = ng.interop.normalize_agilent_fid(
        ng.interop.read_agilent_fid(str(tmp_path))
    )

    assert normalized.axes[0].values is None
    assert normalized.axes[0].domain == "time"
    assert normalized.acquisition["spectral_width_hz"] is None


def test_agilent_raw_missing_carrier_is_diagnostic_and_export_blocked(
    monkeypatch, tmp_path
):
    dic, data = _dic_data()
    monkeypatch.setattr(ng.varian, "read", lambda *args, **kwargs: (dic, data.copy()))

    result = ng.interop.read_agilent_fid(str(tmp_path))

    diagnostic = next(
        item
        for item in result.diagnostics
        if item.code == "acquisition.missing-parameter"
    )
    assert "carrier_hz/carrier_ppm" in diagnostic.context["missing"]
    with pytest.raises(ValueError, match="carrier_hz"):
        ng.interop.write_readresult_nmrpipe(result, tmp_path / "missing.fid")


def test_agilent_raw_export_uses_explicit_carrier_and_preserves_samples(
    monkeypatch, tmp_path
):
    dic, data = _dic_data()
    monkeypatch.setattr(ng.varian, "read", lambda *args, **kwargs: (dic, data.copy()))

    result = ng.interop.read_agilent_fid(str(tmp_path), carrier_hz=12375.0)
    header = ng.interop.write_readresult_nmrpipe(
        result, tmp_path / "agilent.fid", overwrite=True
    )
    saved_header, saved_data = ng.pipe.read(str(tmp_path / "agilent.fid"))

    np.testing.assert_array_equal(saved_data, data)
    assert header["FDF2CAR"] == pytest.approx(99.0)
    assert saved_header["FDF2OBS"] == 125.0
    assert saved_header["FDF2SW"] == 2000.0
    assert saved_header["FDF2QUADFLAG"] == 0.0


def test_agilent_raw_does_not_interpret_rfl_as_carrier(monkeypatch, tmp_path):
    dic, data = _dic_data()
    monkeypatch.setattr(ng.varian, "read", lambda *args, **kwargs: (dic, data.copy()))

    result = ng.interop.read_agilent_fid(str(tmp_path))

    assert result.acquisition["carrier_hz"] is None
    assert result.acquisition["original_reference"]["rfl"] == 25000.0


def test_agilent_raw_does_not_use_decoupler_frequency_as_observation(
    monkeypatch, tmp_path
):
    dic, data = _dic_data()
    del dic["procpar"]["sfrq"]
    monkeypatch.setattr(ng.varian, "read", lambda *args, **kwargs: (dic, data.copy()))

    result = ng.interop.read_agilent_fid(str(tmp_path))

    assert result.acquisition["observation_frequency_mhz"] is None
    diagnostic = next(
        item
        for item in result.diagnostics
        if item.code == "acquisition.missing-parameter"
    )
    assert "sfrq/dfrq" in diagnostic.context["missing"]


def test_agilent_raw_td_matches_procpar_np(monkeypatch, tmp_path):
    dic, data = _dic_data()
    monkeypatch.setattr(ng.varian, "read", lambda *args, **kwargs: (dic, data.copy()))

    result = ng.interop.read_agilent_fid(str(tmp_path), carrier_ppm=99.0)

    assert result.dimensions["TD"] == 8
    assert result.dimensions["TDeff"] == 4


def test_agilent_raw_long_source_uses_compact_nmrpipe_provenance(monkeypatch, tmp_path):
    dic, data = _dic_data()
    monkeypatch.setattr(ng.varian, "read", lambda *args, **kwargs: (dic, data.copy()))
    result = ng.interop.read_agilent_fid(str(tmp_path), carrier_ppm=99.0)
    result = dataclasses.replace(result, source="/" + ("very-long-source/" * 30))

    header = ng.interop.write_readresult_nmrpipe(
        result, tmp_path / "compact.fid", overwrite=True
    )

    assert len(header["FDCOMMENT"].encode()) <= 160
    assert "storage=float32" in header["FDCOMMENT"]


@pytest.mark.parametrize(
    "kwargs",
    [{"carrier_hz": float("nan")}, {"carrier_hz": 12375.0, "carrier_ppm": 98.0}],
)
def test_agilent_raw_rejects_invalid_or_inconsistent_carrier(
    monkeypatch, tmp_path, kwargs
):
    dic, data = _dic_data()
    monkeypatch.setattr(ng.varian, "read", lambda *args, **kwargs: (dic, data.copy()))

    with pytest.raises(ValueError, match="carrier"):
        ng.interop.read_agilent_fid(str(tmp_path), **kwargs)
