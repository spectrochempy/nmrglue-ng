"""Self-contained tests for the additive Bruker raw 1D ReadResult profile."""

from __future__ import annotations

import numpy as np
import pytest

import nmrglue as ng


def _raw_dictionary():
    return {
        "acqus": {
            "TD": 8,
            "SW_h": 1000.0,
            "SFO1": 400.0,
            "O1": 1200.0,
            "AQ_mod": 1,
            "RG": 40.3,
            "NS": 16,
            "DECIM": 80,
            "DSPFVS": 21,
            "GRPDLY": 76.0,
            "NUC1": "<1H>",
        }
    }


def _raw_data():
    return np.asarray([1 + 2j, 3 + 4j, 5 + 6j, 7 + 8j], dtype=np.complex128)


def test_bruker_raw_result_exposes_complex_acquisition(monkeypatch, tmp_path):
    monkeypatch.setattr(
        ng.bruker, "read", lambda *args, **kwargs: (_raw_dictionary(), _raw_data())
    )

    result = ng.interop.read_bruker_fid(str(tmp_path))

    assert result.format == "bruker-fid"
    assert result.data.dtype == np.complex128
    assert result.data.shape == (4,)
    assert result.components[0].name == "complex"
    assert result.domains == ("time",)
    assert result.encoding == ("QSIM",)
    assert result.dimensions == {
        "TD": 8,
        "TDeff": None,
        "returned_points": 4,
        "returned_raw_points": 8,
        "complex_points": 4,
    }
    assert result.acquisition["RG"] == 40.3
    assert result.acquisition["NS"] == 16
    assert result.acquisition["carrier_hz"] == 1200.0
    assert result.acquisition["dwell_time_s"] == pytest.approx(0.001)
    assert result.acquisition["observation_frequency_mhz"] == 400.0
    np.testing.assert_array_equal(result.axes[0].values, np.arange(4) / 1000.0)
    assert result.axes[0].unit == "s"
    assert result.applied_corrections["normalization"] == "none"
    assert result.data.flags.writeable is False


def test_bruker_raw_real_acquisition_modes_are_preserved(monkeypatch, tmp_path):
    dic = _raw_dictionary()
    dic["acqus"]["AQ_mod"] = 0
    real = np.arange(4.0)
    monkeypatch.setattr(ng.bruker, "read", lambda *args, **kwargs: (dic, real))

    result = ng.interop.read_bruker_fid(str(tmp_path))

    assert result.encoding == ("QF",)
    assert result.components[0].name == "real"
    assert not np.iscomplexobj(result.data)
    assert result.dimensions["TDeff"] is None
    assert result.dimensions["returned_raw_points"] == 4


def test_bruker_raw_filter_is_applied_once_and_recorded(monkeypatch, tmp_path):
    calls = []

    def remove_filter(dic, data, truncate=True):
        calls.append((dic, data.copy(), truncate))
        return data[:2] * 2

    monkeypatch.setattr(
        ng.bruker, "read", lambda *args, **kwargs: (_raw_dictionary(), _raw_data())
    )
    monkeypatch.setattr(ng.bruker, "remove_digital_filter", remove_filter)

    result = ng.interop.read_bruker_fid(str(tmp_path), remove_digital_filter=True)

    assert len(calls) == 1
    assert result.data.shape == (2,)
    np.testing.assert_array_equal(result.data, _raw_data()[:2] * 2)
    assert result.dimensions["TDeff"] is None
    assert result.dimensions["returned_raw_points"] == 4
    assert result.applied_corrections["digital_filter"]["applied"] is True
    assert result.applied_corrections["normalization"] == "none"


def test_bruker_raw_does_not_apply_rg_or_ns(monkeypatch, tmp_path):
    monkeypatch.setattr(
        ng.bruker, "read", lambda *args, **kwargs: (_raw_dictionary(), _raw_data())
    )

    result = ng.interop.read_bruker_fid(str(tmp_path))

    np.testing.assert_array_equal(result.data, _raw_data())
    assert result.acquisition["RG"] == 40.3
    assert result.acquisition["NS"] == 16


def test_bruker_raw_missing_acquisition_metadata_is_diagnostic(monkeypatch, tmp_path):
    dic = _raw_dictionary()
    del dic["acqus"]["SW_h"]
    monkeypatch.setattr(ng.bruker, "read", lambda *args, **kwargs: (dic, _raw_data()))

    result = ng.interop.read_bruker_fid(str(tmp_path))

    assert result.axes[0].values is None
    diagnostic = next(
        d for d in result.diagnostics if d.code == "acquisition.missing-parameter"
    )
    assert dict(diagnostic.context) == {"missing": ("SW_h",)}


def test_bruker_raw_none_acquisition_parameter_is_diagnostic(monkeypatch, tmp_path):
    dic = _raw_dictionary()
    dic["acqus"]["SW_h"] = None
    monkeypatch.setattr(ng.bruker, "read", lambda *args, **kwargs: (dic, _raw_data()))

    result = ng.interop.read_bruker_fid(str(tmp_path))

    assert result.axes[0].values is None
    diagnostic = next(
        d for d in result.diagnostics if d.code == "acquisition.missing-parameter"
    )
    assert dict(diagnostic.context) == {"missing": ("SW_h",)}


def test_bruker_raw_invalid_spectral_width_raises(monkeypatch, tmp_path):
    dic = _raw_dictionary()
    dic["acqus"]["SW_h"] = 0.0
    monkeypatch.setattr(ng.bruker, "read", lambda *args, **kwargs: (dic, _raw_data()))

    with pytest.raises(ValueError, match="SW_h"):
        ng.interop.read_bruker_fid(str(tmp_path))


@pytest.mark.parametrize("td", [float("nan"), float("inf"), 7.5, 0, -8])
def test_bruker_raw_invalid_td_raises(monkeypatch, tmp_path, td):
    dic = _raw_dictionary()
    dic["acqus"]["TD"] = td
    monkeypatch.setattr(ng.bruker, "read", lambda *args, **kwargs: (dic, _raw_data()))

    with pytest.raises(ValueError, match="TD"):
        ng.interop.read_bruker_fid(str(tmp_path))
