"""Self-contained tests for the raw Bruker States-TPPI ReadResult profile."""

import numpy as np
import pytest

import nmrglue as ng


def _states_dictionary():
    return {
        "acqus": {
            "TD": 8,
            "AQ_mod": 3,
            "SW_h": 1000.0,
            "SFO1": 400.0,
            "O1": 1200.0,
            "RG": 40.3,
            "NS": 16,
            "NUC1": "<1H>",
        },
        "acqu2s": {
            "TD": 4,
            "FnMODE": 5,
            "SW": 10.0,
            "SFO1": 100.0,
            "O1": 500.0,
            "NUC1": "<13C>",
        },
    }


def _states_data(rows=4):
    values = np.arange(rows * 4, dtype=np.float64).reshape(rows, 4)
    return values + 1j * (1000.0 + values)


def test_states_tppi_exposes_storage_and_canonical_components(monkeypatch, tmp_path):
    data = _states_data()
    monkeypatch.setattr(
        ng.bruker,
        "read",
        lambda *args, **kwargs: (_states_dictionary(), data.copy()),
    )

    result = ng.interop.read_bruker_ser(str(tmp_path))

    assert result.format == "bruker-ser-states-tppi-2d"
    assert result.encoding == ("STATES-TPPI", "DQD")
    assert result.data.shape == (4, 4)
    np.testing.assert_array_equal(result.data, data)
    assert tuple(component.name for component in result.components) == (
        "RR",
        "RI",
        "IR",
        "II",
    )
    np.testing.assert_array_equal(result.components[0].data, data[0::2].real)
    np.testing.assert_array_equal(result.components[1].data, data[0::2].imag)
    np.testing.assert_array_equal(result.components[2].data, data[1::2].real)
    np.testing.assert_array_equal(result.components[3].data, data[1::2].imag)
    assert result.dimensions["storage_shape"] == (4, 4)
    assert result.dimensions["canonical_shape"] == (2, 4)
    assert result.dimensions["trace_pairing"] == (
        "trace[2a]=RR+i*RI; trace[2a+1]=IR+i*II"
    )
    assert result.dimensions["tppi_alternation"] == "declared_not_applied"
    assert result.dimensions["TD"] == (4, 8)
    assert result.dimensions["TDeff"] == (None, None)
    assert result.axes[0].values.shape == (2,)
    assert result.axes[1].values.shape == (4,)
    assert result.data.flags.writeable is False
    assert all(
        component.data.flags.writeable is False for component in result.components
    )


def test_states_tppi_pairing_is_discriminating_and_not_fft(monkeypatch, tmp_path):
    data = _states_data()
    data[0] = [1 + 10j, 0, 0, 0]
    data[1] = [2 + 20j, 0, 0, 0]
    data[2] = [3 + 30j, 0, 0, 0]
    data[3] = [4 + 40j, 0, 0, 0]
    monkeypatch.setattr(
        ng.bruker,
        "read",
        lambda *args, **kwargs: (_states_dictionary(), data.copy()),
    )

    result = ng.interop.read_bruker_ser(str(tmp_path))

    np.testing.assert_array_equal(result.components[0].data[0], [1, 0, 0, 0])
    np.testing.assert_array_equal(result.components[1].data[0], [10, 0, 0, 0])
    np.testing.assert_array_equal(result.components[2].data[0], [2, 0, 0, 0])
    np.testing.assert_array_equal(result.components[3].data[0], [20, 0, 0, 0])
    assert result.applied_corrections["states_tppi_alternation"] == (
        "declared_not_applied"
    )


def test_states_tppi_filter_is_recorded_without_normalization(monkeypatch, tmp_path):
    calls = []

    def remove_filter(dic, data, truncate=True):
        calls.append((data.copy(), truncate))
        return data[:, 1:]

    monkeypatch.setattr(
        ng.bruker,
        "read",
        lambda *args, **kwargs: (_states_dictionary(), _states_data()),
    )
    monkeypatch.setattr(ng.bruker, "remove_digital_filter", remove_filter)

    result = ng.interop.read_bruker_ser(str(tmp_path), remove_digital_filter=True)

    assert len(calls) == 1
    assert calls[0][1] is True
    assert result.data.shape == (4, 3)
    assert result.components[0].data.shape == (2, 3)
    assert result.dimensions["storage_shape"] == (4, 4)
    assert result.dimensions["returned_shape"] == (4, 3)
    assert result.applied_corrections["digital_filter"]["applied"] is True
    assert result.applied_corrections["normalization"] == "none"


@pytest.mark.parametrize("rows, message", [(3, "even number"), (5, "even number")])
def test_states_tppi_rejects_odd_storage_trace_count(
    monkeypatch, tmp_path, rows, message
):
    monkeypatch.setattr(
        ng.bruker,
        "read",
        lambda *args, **kwargs: (_states_dictionary(), _states_data(rows)),
    )

    with pytest.raises(ValueError, match=message):
        ng.interop.read_bruker_ser(str(tmp_path))


def test_states_tppi_rejects_non_states_encoding(monkeypatch, tmp_path):
    dic = _states_dictionary()
    dic["acqu2s"]["FnMODE"] = 3
    monkeypatch.setattr(
        ng.bruker,
        "read",
        lambda *args, **kwargs: (dic, _states_data()),
    )

    with pytest.raises(ValueError, match="FnMODE=1"):
        ng.interop.read_bruker_ser(str(tmp_path))


def test_normalize_states_tppi_storage_preserves_asymmetric_pairs_and_padding(tmp_path):
    (tmp_path / "acqus").write_text(
        "##TITLE= Synthetic direct\n"
        "##$TD= 8\n##$BYTORDA= 1\n##$DTYPA= 0\n##$AQ_mod= 3\n"
        "##$FnTYPE= 0\n##$SW_h= 2000\n##$SFO1= 125\n"
        "##$DECIM= 2.5\n##$DSPFVS= 12\n##$GRPDLY= 2.75\n"
        "##$NS= 8\n##$RG= 4\n##END=\n"
    )
    (tmp_path / "acqu2s").write_text(
        "##TITLE= Synthetic indirect\n"
        "##$TD= 4\n##$FnMODE= 5\n##$SW= 10\n##$SFO1= 100\n##END=\n"
    )
    words = np.arange(4 * 256, dtype=np.int32).reshape(4, 256)
    (tmp_path / "ser").write_bytes(words.astype(">i4").tobytes())
    (tmp_path / "pulseprogram").write_bytes(b"lo to\n")
    with pytest.warns(UserWarning, match="Error reading the pulse program"):
        stored = ng.interop.read_bruker_ser_storage(
            tmp_path, states_tppi_only=True, read_pulseprogram=True,
        )
    assert stored.metadata["pulseprogram_raw"] == b"lo to\n"
    assert "pprog" not in stored.metadata
    np.testing.assert_array_equal(stored.data, words)
    result = ng.interop.normalize_bruker_ser_states_tppi(stored)
    assert result.branch_order == ("rr", "ri", "ir", "ii")
    assert result.acquisition["tppi_alternation"] == "declared_not_applied"
    assert result.applied_operations[0]["padding_words_per_trace"] == 248
    for plane, (row, word) in zip(result.data, ((0, 0), (0, 1), (1, 0), (1, 1)), strict=True):
        np.testing.assert_array_equal(plane, words[row::2, word:8:2])
    np.testing.assert_array_equal(result.axes[0].values, np.arange(2) / 1000)
    np.testing.assert_array_equal(result.axes[1].values, np.arange(4) / 2000)

    corrected = ng.interop.normalize_bruker_ser_states_tppi(
        stored, preserve_storage=True, remove_dc_offset=True,
        remove_digital_filter=True, normalize_scan_gain=True,
    )
    traces = words[:, ::2] + 1j * words[:, 1::2]
    traces = np.roll(traces - traces.mean(axis=-1, keepdims=True), -2, axis=-1)
    traces = traces[:, :-4] / 32
    expected = np.stack((
        traces[0::2].real, traces[0::2].imag,
        traces[1::2].real, traces[1::2].imag,
    ))
    np.testing.assert_allclose(corrected.data, expected, atol=1e-12)
    np.testing.assert_array_equal(corrected.axes[1].values, np.arange(124) / 2000)
    assert corrected.applied_operations[0]["retained_padding_words_per_trace"] == 248
    assert corrected.acquisition["digital_filter"]["removed_points"] == 4
    assert corrected.acquisition["scan_gain"]["divisor"] == 32
    assert corrected.acquisition["tppi_alternation"] == "declared_not_applied"


    (tmp_path / "ser").write_bytes(words[:-1].astype(">i4").tobytes())
    with pytest.raises(ValueError, match="complete TD geometry"):
        ng.interop.normalize_bruker_ser_states_tppi(ng.interop.read_bruker_ser_storage(tmp_path))
    (tmp_path / "ser").write_bytes(words.astype(">i4").tobytes())
    (tmp_path / "nuslist").write_text("0\n1\n")
    with pytest.raises(ValueError, match="uniform States-TPPI"):
        ng.interop.normalize_bruker_ser_states_tppi(ng.interop.read_bruker_ser_storage(tmp_path))


@pytest.mark.parametrize("extra_dimension", [None, "PARMODE", "acqu3s"])
def test_normalize_echo_antiecho_storage_keeps_branch_order_and_delay(
    tmp_path, extra_dimension,
):
    (tmp_path / "acqus").write_text(
        "##TITLE= Synthetic direct\n"
        "##$TD= 16\n##$BYTORDA= 0\n##$DTYPA= 0\n##$AQ_mod= 3\n"
        "##$FnTYPE= 0\n##$SW_h= 2000\n##$SFO1= 125\n"
        "##$DECIM= 2.5\n##$DSPFVS= 12\n##$GRPDLY= 2.75\n"
        + ("##$PARMODE= 2\n" if extra_dimension == "PARMODE" else "")
        + "##END=\n"
    )
    (tmp_path / "acqu2s").write_text(
        "##TITLE= Synthetic indirect\n"
        "##$TD= 4\n##$FnMODE= 6\n##$SW= 10\n##$SFO1= 100\n##END=\n"
    )
    words = np.arange(4 * 256, dtype=np.int32).reshape(4, 256)
    (tmp_path / "ser").write_bytes(words.astype("<i4").tobytes())
    if extra_dimension == "acqu3s":
        (tmp_path / "acqu3s").write_text("##TITLE= Third axis\n##$TD= 8\n##END=\n")
    if extra_dimension is not None:
        with pytest.raises(ValueError, match="two-dimensional acquisition"):
            ng.interop.read_bruker_ser_storage(tmp_path, echo_antiecho_only=True)
        stored = ng.interop.read_bruker_ser_storage(tmp_path)
        with pytest.raises(ValueError, match="two-dimensional acquisition"):
            ng.interop.normalize_bruker_ser_echo_antiecho(stored)
        return

    stored = ng.interop.read_bruker_ser_storage(tmp_path, echo_antiecho_only=True)
    presented = ng.interop.normalize_bruker_ser_echo_antiecho(
        stored, fft_presentation=True
    )
    assert presented.acquisition["fft_presentation"]["F1"]["transform"] == (
        "echo-antiecho-branch-fft"
    )
    assert presented.acquisition["fft_presentation"]["F2"]["transform"] == (
        "conjugate-input"
    )
    with pytest.raises(ValueError, match="States-TPPI"):
        ng.interop.read_bruker_ser_storage(tmp_path, states_tppi_only=True)
    result = ng.interop.normalize_bruker_ser_echo_antiecho(stored)
    assert result.branch_order == ("first", "second")
    assert result.encoding == ("echo-antiecho", "complex")
    assert result.acquisition["reconstruction"] == "not_applied"
    assert result.acquisition["digital_filter"] == {
        "requested": False, "applied": False, "group_delay_points": 2.75,
    }
    traces = words[:, :16:2] + 1j * words[:, 1:16:2]
    np.testing.assert_array_equal(result.data, np.stack((traces[::2], traces[1::2])))
    np.testing.assert_array_equal(result.axes[0].values, np.arange(2) / 1000)
    np.testing.assert_array_equal(result.axes[1].values, np.arange(8) / 2000)
    with pytest.raises(ValueError, match="uniform States-TPPI"):
        ng.interop.normalize_bruker_ser_states_tppi(stored)
