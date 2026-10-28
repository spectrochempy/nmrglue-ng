"""Self-contained tests for the additive Bruker raw 2D QF profile."""

import numpy as np
import pytest

import nmrglue as ng


def _ser_dictionary():
    return {
        "acqus": {
            "TD": 8,
            "AQ_mod": 3,
            "SW_h": 1000.0,
            "SFO1": 400.0,
            "O1": 1200.0,
            "RG": 40.3,
            "NS": 16,
            "DECIM": 80,
            "DSPFVS": 21,
            "GRPDLY": 76.0,
            "NUC1": "<1H>",
        },
        "acqu2s": {
            "TD": 3,
            "FnMODE": 1,
            "SW": 10.0,
            "SFO1": 100.0,
            "O1": 500.0,
            "NUC1": "<13C>",
        },
    }


def _ser_data():
    return np.arange(12, dtype=np.float64).reshape(3, 4) + 1j * np.arange(
        100, 112, dtype=np.float64
    ).reshape(3, 4)


def test_bruker_qf_ser_exposes_physical_and_storage_contract(monkeypatch, tmp_path):
    data = _ser_data()
    monkeypatch.setattr(
        ng.bruker,
        "read",
        lambda *args, **kwargs: (_ser_dictionary(), data.copy()),
    )

    result = ng.interop.read_bruker_ser(str(tmp_path))

    assert result.format == "bruker-ser-qf-2d"
    assert result.data.shape == (3, 4)
    assert result.data.dtype == np.complex128
    np.testing.assert_array_equal(result.data, data)
    assert result.domains == ("time", "time")
    assert result.encoding == ("QF", "DQD")
    assert result.components[0].name == "complex"
    assert len(result.components) == 1
    assert result.dimensions["physical_shape"] == (3, 4)
    assert result.dimensions["storage_shape"] == (3, 4)
    assert result.dimensions["axis_order"] == ("F1", "F2")
    assert result.dimensions["trace_order"] == "F1-major, F2-contiguous"
    assert result.dimensions["TD"] == (3, 8)
    assert result.dimensions["TDeff"] == (None, None)
    assert result.dimensions["returned_shape"] == (3, 4)
    assert result.acquisition["axes"][0]["SW_hz"] == pytest.approx(1000.0)
    assert result.acquisition["axes"][1]["SW_hz"] == pytest.approx(1000.0)
    assert result.acquisition["axes"][0]["carrier_hz"] == 500.0
    assert result.acquisition["axes"][1]["carrier_hz"] == 1200.0
    np.testing.assert_array_equal(
        result.axes[0].values, np.arange(3, dtype=float) / 1000.0
    )
    np.testing.assert_array_equal(
        result.axes[1].values, np.arange(4, dtype=float) / 1000.0
    )
    assert result.data.flags.writeable is False
    assert result.components[0].data.flags.writeable is False
    assert result.applied_corrections["normalization"] == "none"


def test_bruker_qf_ser_does_not_fabricate_hypercomplex_components(
    monkeypatch, tmp_path
):
    monkeypatch.setattr(
        ng.bruker,
        "read",
        lambda *args, **kwargs: (_ser_dictionary(), _ser_data()),
    )

    result = ng.interop.read_bruker_ser(str(tmp_path))

    assert tuple(component.name for component in result.components) == ("complex",)
    assert result.dimensions["component_basis"] == ("complex",)


def test_bruker_qf_ser_filter_is_explicit_and_recorded(monkeypatch, tmp_path):
    calls = []

    def remove_filter(dic, data, truncate=True):
        calls.append((dic, data.copy(), truncate))
        return data[:, 1:]

    monkeypatch.setattr(
        ng.bruker,
        "read",
        lambda *args, **kwargs: (_ser_dictionary(), _ser_data()),
    )
    monkeypatch.setattr(ng.bruker, "remove_digital_filter", remove_filter)

    result = ng.interop.read_bruker_ser(str(tmp_path), remove_digital_filter=True)

    assert len(calls) == 1
    assert calls[0][2] is True
    assert result.data.shape == (3, 3)
    assert result.dimensions["physical_shape"] == (3, 4)
    assert result.dimensions["storage_shape"] == (3, 4)
    assert result.dimensions["returned_shape"] == (3, 3)
    assert result.dimensions["TD"] == (3, 8)
    assert result.applied_corrections["digital_filter"]["applied"] is True
    assert result.applied_corrections["normalization"] == "none"


@pytest.mark.parametrize(
    "change, message",
    [
        (lambda dic: dic["acqu2s"].update(FnMODE=3), "FnMODE"),
        (lambda dic: dic["acqus"].update(SW_h=0.0), "positive"),
        (lambda dic: dic["acqus"].update(TD=7), "even"),
    ],
)
def test_bruker_qf_ser_rejects_incoherent_profiles(
    monkeypatch, tmp_path, change, message
):
    dic = _ser_dictionary()
    change(dic)
    monkeypatch.setattr(ng.bruker, "read", lambda *args, **kwargs: (dic, _ser_data()))

    with pytest.raises(ValueError, match=message):
        ng.interop.read_bruker_ser(str(tmp_path))


def test_bruker_qf_ser_requires_acquisition_metadata(monkeypatch, tmp_path):
    dic = _ser_dictionary()
    del dic["acqu2s"]["SW"]
    monkeypatch.setattr(ng.bruker, "read", lambda *args, **kwargs: (dic, _ser_data()))

    with pytest.raises(ValueError, match=r"acqu2s\.SW"):
        ng.interop.read_bruker_ser(str(tmp_path))


def test_bruker_qf_ser_rejects_qsim_direct_mode(monkeypatch, tmp_path):
    dic = _ser_dictionary()
    dic["acqus"]["AQ_mod"] = 1
    monkeypatch.setattr(ng.bruker, "read", lambda *args, **kwargs: (dic, _ser_data()))

    with pytest.raises(ValueError, match="AQ_mod=3"):
        ng.interop.read_bruker_ser(str(tmp_path))
