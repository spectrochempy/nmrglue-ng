"""Self-contained normalized Bruker complex 1D acquisition contracts."""
from dataclasses import replace

import numpy as np
import pytest
import nmrglue as ng


def _result(monkeypatch, tmp_path, *, padding=0, delay=2.5, mode=3):
    values = np.arange(32, dtype=float)
    data = np.pad(values + 1j * (values + 1), (0, padding))
    dic = {"acqus": {"TD": 64, "SW_h": 2000.0, "SFO1": 125.00025,
                     "BF1": 125.0, "O1": 250.0, "AQ_mod": mode,
                     "NS": 16, "RG": 40.3, "DECIM": 16,
                     "DSPFVS": 12, "GRPDLY": delay, "NUC1": "13C"}}
    monkeypatch.setattr(ng.bruker, "read", lambda *a, **k: (dic, data.copy()))
    return ng.interop.read_bruker_fid(tmp_path), data


@pytest.mark.parametrize("mode", [1, 3])
@pytest.mark.parametrize("padding", [0, 7])
def test_trim_and_conjugate_without_amplitude_scaling(monkeypatch, tmp_path, mode, padding):
    raw, data = _result(monkeypatch, tmp_path, padding=padding, mode=mode)
    result = ng.interop.normalize_bruker_fid(raw)
    np.testing.assert_array_equal(result.data, np.conj(data[:32]))
    np.testing.assert_array_equal(raw.data, data)
    assert not result.data.flags.writeable
    assert not np.shares_memory(raw.data, result.data)
    assert result.normalization_state == "quadrature-normalized"
    assert result.acquisition["trimmed_padding_points"] == padding
    assert result.acquisition["frequency_axis"] == {
        "schema": "normalized-frequency-axis-v1", "bin_sign": -1,
        "reference_frequency_mhz": 125.0, "reference_enabled": None,
        "offsets_hz": {"acquisition": 250.0},
    }
    np.testing.assert_allclose(result.axes[0].values, np.arange(32) / 2000)
    assert result.applied_operations[0]["conjugation"] == "applied"
    assert result.applied_operations[0]["scale"] is None
    assert raw.metadata["acqus"]["NS"] == 16
    with pytest.raises(TypeError):
        result.acquisition["frequency_axis"] = {}


def test_integer_truncated_filter_has_direct_time_domain_oracle(monkeypatch, tmp_path):
    raw, data = _result(monkeypatch, tmp_path, padding=7)
    result = ng.interop.normalize_bruker_fid(raw, remove_digital_filter=True)
    expected = np.roll(data[:32], -2)[:-4]
    np.testing.assert_allclose(result.data, np.conj(expected), atol=1e-12)
    trace = result.acquisition["digital_filter"]
    assert trace["group_delay_points"] == 2.5
    assert trace["removed_points"] == 4
    assert trace["delay_source"] == "GRPDLY"
    np.testing.assert_array_equal(raw.data, data)


def test_filter_receives_only_acquired_points_and_runs_once(monkeypatch, tmp_path):
    raw, data = _result(monkeypatch, tmp_path, padding=7)
    calls = []
    def correct(samples, decim, firmware, delay, truncate_grpdly):
        calls.append((samples.copy(), decim, firmware, delay, truncate_grpdly))
        return samples[4:]
    monkeypatch.setattr(ng.bruker, "rm_dig_filter", correct)
    result = ng.interop.normalize_bruker_fid(raw, remove_digital_filter=True)
    assert len(calls) == 1
    np.testing.assert_array_equal(calls[0][0], data[:32])
    assert calls[0][1:] == (16, 12, 2.5, True)
    np.testing.assert_array_equal(result.data, np.conj(data[4:32]))


@pytest.mark.parametrize("change", ["real", "encoding", "format", "td", "td_bool", "short", "component", "grid", "width", "prefiltered", "correction", "nonzero_padding"])
def test_invalid_contract_refuses_without_mutating_input(monkeypatch, tmp_path, change):
    raw, _ = _result(monkeypatch, tmp_path, padding=7)
    if change == "real": raw = replace(raw, data=raw.data.real)
    elif change == "encoding": raw = replace(raw, encoding=("QSEQ",))
    elif change == "format": raw = replace(raw, format="agilent-fid")
    elif change in ("td", "td_bool", "short"):
        raw = replace(raw, dimensions={**raw.dimensions, "TD": {"td": 63, "td_bool": True, "short": 100}[change]})
    elif change == "component": raw = replace(raw, components=())
    elif change == "grid": raw = replace(raw, axes=(replace(raw.axes[0], values=np.arange(raw.data.size)),))
    elif change == "width": raw = replace(raw, acquisition={**raw.acquisition, "spectral_width_hz": 1000})
    elif change == "prefiltered": raw = replace(raw, applied_corrections={**raw.applied_corrections, "digital_filter": {"applied": True}})
    elif change == "correction": raw = replace(raw, applied_corrections={**raw.applied_corrections, "normalization": "RG/NS"})
    else:
        bad = raw.data.copy(); bad[-1] = 1
        raw = replace(raw, data=bad, components=(ng.interop.Component("complex", bad),))
    before = raw.data.copy()
    with pytest.raises(ValueError): ng.interop.normalize_bruker_fid(raw)
    np.testing.assert_array_equal(raw.data, before)


@pytest.mark.parametrize("parameters", [{}, {"DECIM": 16, "DSPFVS": 21}, {"DECIM": 16, "DSPFVS": 9}, {"DECIM": True, "DSPFVS": 12}, {"DECIM": 16, "DSPFVS": 12, "GRPDLY": float("nan")}, {"DECIM": 16, "DSPFVS": 12, "GRPDLY": 1000}])
def test_unknown_filter_evidence_refuses_without_preventing_uncorrected_read(monkeypatch, tmp_path, parameters):
    raw, _ = _result(monkeypatch, tmp_path)
    raw = replace(raw, applied_corrections={"normalization": "none", "digital_filter": {"applied": False, "parameters": parameters}})
    with pytest.raises(ValueError): ng.interop.normalize_bruker_fid(raw, remove_digital_filter=True)
    assert ng.interop.normalize_bruker_fid(raw).data.size == 32


def test_missing_reference_keeps_time_calibration(monkeypatch, tmp_path):
    raw, _ = _result(monkeypatch, tmp_path)
    raw = replace(raw, metadata={"acqus": {}}, acquisition={key: value for key, value in raw.acquisition.items() if key != "carrier_hz"})
    result = ng.interop.normalize_bruker_fid(raw)
    assert result.acquisition["frequency_axis"]["reference_frequency_mhz"] is None
    assert result.acquisition["frequency_axis"]["offsets_hz"] == {}


@pytest.mark.parametrize("preserve_storage", [False, True])
@pytest.mark.parametrize("filtered", [False, True])
def test_dc_filter_and_gain_order(monkeypatch, tmp_path, preserve_storage, filtered):
    raw, data = _result(monkeypatch, tmp_path, padding=7, delay=8.5)
    result = ng.interop.normalize(
        raw,
        remove_dc_offset=True,
        remove_digital_filter=filtered,
        normalize_scan_gain=True,
        preserve_storage=preserve_storage,
    )
    expected = data.copy() if preserve_storage else data[:32].copy()
    input_points = expected.size
    expected -= expected.mean()
    if filtered:
        expected = np.roll(expected, -8)
        expected[:4] += expected[:-5:-1].copy()
        expected = expected[:-10]
    divisor = 16 * 40.3
    np.testing.assert_allclose(result.data, expected.conj() / divisor, atol=1e-15)
    np.testing.assert_allclose(result.axes[0].values, np.arange(expected.size) / 2000)
    assert result.acquisition["trimmed_padding_points"] == (0 if preserve_storage else 7)
    assert result.applied_operations[0]["dc_offset"] == {
        "applied": True, "input_points": input_points,
    }
    assert result.applied_operations[0]["scan_gain"]["divisor"] == divisor
    assert result.applied_operations[0]["scale"] == 1 / divisor
    np.testing.assert_array_equal(raw.data, data)


def test_no_decimation_keeps_dc_and_gain_corrections(monkeypatch, tmp_path):
    raw, data = _result(monkeypatch, tmp_path)
    raw = replace(
        raw,
        acquisition={key: value for key, value in raw.acquisition.items() if key != "RG"},
        applied_corrections={
            "normalization": "none",
            "digital_filter": {"applied": False, "parameters": {"DECIM": 1}},
        },
    )
    result = ng.interop.normalize_bruker_fid(
        raw, remove_digital_filter="if-decimated", remove_dc_offset=True, normalize_scan_gain=True
    )
    np.testing.assert_array_equal(result.data, (data - data.mean()).conj() / 16)
    assert result.acquisition["digital_filter"] == {
        "requested": True, "applied": False, "reason": "no-decimation",
    }


@pytest.mark.parametrize("key,value", [("NS", 0), ("RG", -1), ("RG", np.inf)])
def test_invalid_scan_gain_is_rejected_when_requested(monkeypatch, tmp_path, key, value):
    raw, data = _result(monkeypatch, tmp_path)
    raw = replace(raw, acquisition={**raw.acquisition, key: value})
    with pytest.raises(ValueError, match=key):
        ng.interop.normalize_bruker_fid(raw, normalize_scan_gain=True)
    np.testing.assert_array_equal(ng.interop.normalize_bruker_fid(raw).data, data.conj())


def test_read_fid_forwards_parameter_selection(monkeypatch, tmp_path):
    raw, data = _result(monkeypatch, tmp_path)
    calls = []

    def read(directory, **options):
        calls.append((directory, options))
        return raw.metadata, data

    monkeypatch.setattr(ng.bruker, "read", read)
    acqus_files = [tmp_path / "acqus"]
    procs_files = [tmp_path / "pdata" / "1" / "procs"]
    ng.interop.read_bruker_fid(tmp_path, acqus_files=acqus_files, procs_files=procs_files)
    assert calls[0][1]["acqus_files"] == acqus_files
    assert calls[0][1]["procs_files"] == procs_files
    assert calls[0][1]["read_procs"] is True


def test_fft_display_and_phase_are_separate_from_acquisition_reference(monkeypatch, tmp_path):
    raw, data = _result(monkeypatch, tmp_path, padding=7)
    raw = replace(raw, metadata={
        "acqus": {**raw.metadata["acqus"], "SW": 16.0},
        "proc": {"SF": 124.9, "PHC1": -12.0},
        "procs": {"SF": 125.00015, "PHC0": 42.0},
    })
    result = ng.interop.normalize_bruker_fid(raw, preserve_storage=True)
    display = result.acquisition["fft_display_axis"]
    assert display["grid"] == "inclusive-endpoints"
    assert display["direction"] == "decreasing"
    assert display["center_hz"] == pytest.approx(100)
    assert display["spectral_width_hz"] == pytest.approx(2000.004)
    assert display["reference_frequency_mhz"] == 125.0
    assert result.acquisition["frequency_axis"]["offsets_hz"]["acquisition"] == 250.0
    assert result.acquisition["fft_initial_phase"] == {
        "zero_order_deg": 42.0, "first_order_deg": -12.0, "pivot_index": 0,
    }
    np.testing.assert_array_equal(result.data, data.conj())
    default = ng.interop.normalize_bruker_fid(raw)
    assert "fft_display_axis" not in default.acquisition
    assert "fft_initial_phase" not in default.acquisition


def test_explicit_filter_preserves_delay_at_unit_decimation(monkeypatch, tmp_path):
    raw, data = _result(monkeypatch, tmp_path)
    raw = replace(raw, applied_corrections={
        "normalization": "none",
        "digital_filter": {
            "applied": False,
            "parameters": {"DECIM": 1, "DSPFVS": 12, "GRPDLY": 2.5},
        },
    })
    result = ng.interop.normalize_bruker_fid(raw, remove_digital_filter=True)
    np.testing.assert_allclose(result.data, np.roll(data, -2)[:-4].conj(), atol=1e-12)
    assert result.acquisition["digital_filter"]["removed_points"] == 4
    parameters = {**raw.applied_corrections["digital_filter"]["parameters"], "GRPDLY": np.nan}
    raw = replace(raw, applied_corrections={
        "normalization": "none",
        "digital_filter": {"applied": False, "parameters": parameters},
    })
    with pytest.raises(ValueError, match="GRPDLY"):
        ng.interop.normalize_bruker_fid(raw, remove_digital_filter=True)


def test_selected_acquisition_files_supply_missing_status_fields(monkeypatch, tmp_path):
    raw, data = _result(monkeypatch, tmp_path)
    status = dict(raw.metadata["acqus"])
    del status["RG"]
    del status["BF1"]
    del status["SFO1"]
    del status["NS"]
    del status["SW_h"]
    metadata = {
        "acqu": {
            "RG": 8, "NS": 16, "SW": 16, "BF1": 125, "SFO1": 125.00025,
            "SW_h": 2000, "TD": 32, "O1": 100,
        },
        "acqus": status,
        "procs": {"SF": 125.00015},
    }
    monkeypatch.setattr(ng.bruker, "read", lambda *args, **kwargs: (metadata, data))
    raw = ng.interop.read_bruker_fid(
        tmp_path, acqus_files=[tmp_path / "acqu", tmp_path / "acqus"]
    )
    result = ng.interop.normalize_bruker_fid(
        raw, preserve_storage=True, normalize_scan_gain=True,
    )
    np.testing.assert_array_equal(result.data, data.conj() / 128)
    assert result.acquisition["scan_gain"]["divisor"] == 128
    assert result.acquisition["frequency_axis"]["offsets_hz"]["acquisition"] == 250
    assert result.acquisition["fft_display_axis"]["center_hz"] == pytest.approx(100)
    assert result.acquisition["fft_display_axis"]["spectral_width_hz"] == pytest.approx(2000.004)
