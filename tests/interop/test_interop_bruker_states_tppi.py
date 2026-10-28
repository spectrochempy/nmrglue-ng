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
