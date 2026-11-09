"""Self-contained tests for the additive Bruker raw 2D QF profile."""

from dataclasses import replace

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


def test_normalize_qf_ser_preserves_direct_components(monkeypatch, tmp_path):
    data = _ser_data()
    monkeypatch.setattr(ng.bruker, "read", lambda *args, **kwargs: (_ser_dictionary(), data))
    source = ng.interop.read_bruker_ser(tmp_path)
    normalized = ng.interop.normalize(source)
    assert normalized.dimensions == ("channels", "F1", "F2")
    assert normalized.encoding == ("real", "complex")
    assert normalized.branch_order == ("rr", "ri")
    assert normalized.acquisition["spectral_width_hz"] == (1000.0, 1000.0)
    np.testing.assert_array_equal(normalized.data, np.stack((data.real, data.imag)))
    np.testing.assert_array_equal(normalized.axes[0].values, np.arange(3) / 1000)
    np.testing.assert_array_equal(normalized.axes[1].values, np.arange(4) / 1000)


def test_normalize_qf_ser_refuses_nonuniform_sampling(monkeypatch, tmp_path):
    metadata = _ser_dictionary()
    metadata["acqus"]["FnTYPE"] = 2
    monkeypatch.setattr(ng.bruker, "read", lambda *args, **kwargs: (metadata, _ser_data()))
    source = ng.interop.read_bruker_ser(tmp_path)
    with pytest.raises(ValueError, match="uniform sampling"):
        ng.interop.normalize(source)


@pytest.mark.parametrize("extra_record", ["dc_offset", "digital_filter"])
def test_normalize_qf_ser_refuses_unknown_correction_evidence(monkeypatch, tmp_path, extra_record):
    monkeypatch.setattr(ng.bruker, "read", lambda *args, **kwargs: (_ser_dictionary(), _ser_data()))
    source = ng.interop.read_bruker_ser(tmp_path)
    corrections = dict(source.applied_corrections)
    if extra_record == "digital_filter":
        corrections[extra_record] = {**corrections[extra_record], "phase_applied": True}
    else:
        corrections[extra_record] = {"applied": True}
    with pytest.raises(ValueError, match="uncorrected SER"):
        ng.interop.normalize(replace(source, applied_corrections=corrections))


@pytest.mark.parametrize("invalid", ["complex", "nonfinite", "unrepresentable_width"])
def test_normalize_qf_ser_refuses_invalid_time_grid(monkeypatch, tmp_path, invalid):
    monkeypatch.setattr(ng.bruker, "read", lambda *args, **kwargs: (_ser_dictionary(), _ser_data()))
    source = ng.interop.read_bruker_ser(tmp_path)
    axis = source.axes[1]
    values = axis.values.copy()
    if invalid == "complex":
        values = values.astype(complex)
    elif invalid == "nonfinite":
        values[1:] = np.inf
    else:
        first, second = source.acquisition["axes"]
        acquisition = {**source.acquisition, "axes": (first, {**second, "SW_hz": 5e-324})}
        source = replace(source, acquisition=acquisition)
    with pytest.raises(ValueError, match="time grid"):
        ng.interop.normalize(replace(source, axes=(source.axes[0], replace(axis, values=values))))


def test_normalize_qf_ser_corrections_preserve_stored_convention(monkeypatch, tmp_path):
    metadata = _ser_dictionary()
    metadata["acqus"].update(TD=32, DECIM=2.5, GRPDLY=2.75)
    metadata["acqu"] = {"NS": 8, "RG": 99}
    del metadata["acqus"]["NS"]
    real = np.arange(48, dtype=float).reshape(3, 16)
    data = real + 1j * (real**2 - 7)
    monkeypatch.setattr(ng.bruker, "read", lambda *args, **kwargs: (metadata, data))
    raw = ng.interop.read_bruker_ser(tmp_path)
    result = ng.interop.normalize(
        raw, remove_dc_offset=True, remove_digital_filter=True, normalize_scan_gain=True,
    )
    expected = np.roll(data - data.mean(axis=-1, keepdims=True), -2, axis=-1)
    expected = expected[:, :-4] / (8 * 40.3)
    np.testing.assert_allclose(result.data, np.stack((expected.real, expected.imag)), atol=1e-13)
    np.testing.assert_array_equal(result.axes[1].values, np.arange(12) / 1000)
    np.testing.assert_array_equal(raw.data, data)
    assert result.acquisition["digital_filter"]["removed_points"] == 4
    assert result.acquisition["scan_gain"]["divisor"] == 8 * 40.3
    assert result.applied_operations[0]["dc_offset"]["applied"] is True


@pytest.mark.parametrize(("observation", "width", "sf"), [(1e-200, 1e-200, 1), (1, 1000, 1e20), (1, 256, 1e12)])
def test_qf_ser_rejects_unrepresentable_display_endpoints(monkeypatch, tmp_path, observation, width, sf):
    metadata = _ser_dictionary()
    metadata["acqus"].update(SFO1=observation, SW=width, BF1=1)
    metadata["procs"] = {"SF": sf}
    monkeypatch.setattr(ng.bruker, "read", lambda *args, **kwargs: (metadata, _ser_data()))
    source = ng.interop.read_bruker_ser(tmp_path)
    with pytest.raises(ValueError, match="display calibration"):
        ng.interop.normalize(source, fft_presentation=True)


@pytest.mark.parametrize(("mode", "sampling"), [(5, 0), (6, 0), (1, 2)])
def test_qf_ser_preflight_refuses_other_profiles_without_binary_read(monkeypatch, tmp_path, mode, sampling):
    metadata = _ser_dictionary()
    metadata["acqus"]["FnTYPE"] = sampling
    metadata["acqu2s"]["FnMODE"] = mode
    monkeypatch.setattr(ng.bruker, "read_acqus_file", lambda *args, **kwargs: metadata)
    monkeypatch.setattr(ng.bruker, "read", lambda *args, **kwargs: pytest.fail("unexpected binary read"))
    with pytest.raises(ValueError, match="uniform sampling"):
        ng.interop.read_bruker_ser(tmp_path, qf_only=True)
