"""Self-contained tests for the additive Agilent raw 1D profile."""

import dataclasses
import hashlib
import os
import struct
from pathlib import Path

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


@pytest.mark.parametrize(
    "nt, ct, headers, completed, status",
    [
        ([160], [160], [{"ctcount": 160, "scale": 0}], 160, "consistent"),
        ([160], [80], [{"ctcount": 80, "scale": 0}], 80, "consistent"),
        ([160], [80], [{"ctcount": 80, "scale": 2}], 80, "consistent"),
        ([160], [0], [{"ctcount": 80, "scale": 0}], None, "conflicting"),
        ([160], None, [{"ctcount": 80, "scale": 0}], 80, "block-only"),
        ([160], [80], None, None, "unavailable"),
        ([160], [0], [{"ctcount": 0, "scale": 0}], 0, "consistent"),
        (
            [1000000000], [2147483647], [{"ctcount": 2147483647}],
            2147483647, "consistent",
        ),
        (None, None, None, None, "unavailable"),
        ([160], [80], [{"ctcount": 80}, {"ctcount": 80}], None, "ambiguous"),
    ],
)
@pytest.mark.parametrize("read_blockhead", [False, True])
def test_agilent_scan_counts_keep_requested_and_completed_distinct(
    monkeypatch, tmp_path, nt, ct, headers, completed, status, read_blockhead
):
    dic, data = _dic_data()
    for key, values in (("nt", nt), ("ct", ct)):
        if values is not None:
            dic["procpar"][key] = {"values": [str(value) for value in values]}
    if headers is not None:
        dic["blockheader"] = headers
    calls = []

    def read(*args, **kwargs):
        calls.append(kwargs)
        return dic, data.copy()

    monkeypatch.setattr(ng.varian, "read", read)
    raw = ng.interop.read_agilent_fid(tmp_path, read_blockhead=read_blockhead)
    normalized = ng.interop.normalize_agilent_fid(raw)
    for result in (raw, normalized):
        counts = result.acquisition["scan_counts"]
        assert counts["requested"] == (int(nt[0]) if nt else None)
        assert counts["procpar_completed"] == (int(ct[0]) if ct else None)
        assert counts["block_completed"] == tuple(
            item["ctcount"] for item in (headers or ())
        )
        assert counts["block_scales"] == tuple(
            item.get("scale") for item in (headers or ())
        )
        assert counts["completed"] == completed
        assert counts["status"] == status
        assert counts["source"] == (
            "fid.blockheader.ctcount" if completed is not None else None
        )
        assert result.acquisition["NS"] == 4
        assert result.acquisition["NE"] == 2
        assert result.acquisition["normalization"] == "none"
        assert result.metadata["procpar"] == dic["procpar"]
        assert ("blockheader" in result.metadata) == (
            read_blockhead and headers is not None
        )
        np.testing.assert_array_equal(result.data, data)
    assert calls[0]["read_blockhead"] is True
    assert ("blockheader" in dic) == (headers is not None)


@pytest.mark.parametrize("key", ["nt", "ct", "ctcount"])
@pytest.mark.parametrize(
    "value",
    [
        -1,
        1.5,
        float("nan"),
        float("inf"),
        True,
        np.bool_(True),
        "bad",
        "80.000000000000001",
        "-1e-999",
        "9007199254740993",
        "1e9999999999",
    ],
)
def test_agilent_invalid_scan_counts_do_not_invent_normalization(
    monkeypatch, tmp_path, key, value
):
    dic, data = _dic_data()
    dic["procpar"].update({"nt": {"values": [160]}, "ct": {"values": [80]}})
    dic["blockheader"] = [{"ctcount": 80, "scale": 2}]
    if key == "ctcount":
        dic["blockheader"][0][key] = value
    else:
        dic["procpar"][key] = {"values": [value]}
    monkeypatch.setattr(ng.varian, "read", lambda *args, **kwargs: (dic, data.copy()))
    result = ng.interop.read_agilent_fid(tmp_path)
    counts = result.acquisition["scan_counts"]
    assert counts["status"] == "invalid"
    assert counts["completed"] is None
    assert counts["source"] is None
    assert counts["invalid"]
    assert result.acquisition["normalization"] == "none"
    np.testing.assert_array_equal(result.data, data)


@pytest.mark.parametrize("nt", [[], [0], [160, 320], [1000000001]])
def test_agilent_missing_or_arrayed_requested_count_is_not_scalarized(
    monkeypatch, tmp_path, nt
):
    dic, data = _dic_data()
    dic["procpar"]["nt"] = {"values": nt}
    dic["blockheader"] = [{"ctcount": 80, "scale": 0}]
    monkeypatch.setattr(ng.varian, "read", lambda *args, **kwargs: (dic, data.copy()))
    result = ng.interop.read_agilent_fid(tmp_path)
    counts = result.acquisition["scan_counts"]
    assert counts["requested"] is None
    assert counts["status"] == "invalid"
    assert counts["completed"] is None
    assert counts["invalid"] == ("procpar.nt",)
    np.testing.assert_array_equal(result.data, data)


@pytest.mark.dataset
@pytest.mark.parametrize(
    "environment, count, hashes",
    [
        (
            "NMRGLUE_AGILENT_HOP_DATA",
            160,
            (
                "ffdb15ed7ec30d3e01d86a8a743958ea6e165c618f791a728956bee43a06ce81",
                "458e0230178a7642effa116ff32f005edda092f698899998300a4620096ca370",
            ),
        ),
        (
            "NMRGLUE_AGILENT_LEGACY_DATA",
            512,
            (
                "4a4ccf9b8a8c20e4dd5d151564d84585fd13a15f53cc967cbaa77c556b29e145",
                "423d25e161adc5b5ad5a504ece04667c89835f698b4ba19ddd0a2de545bd2fbb",
            ),
        ),
    ],
)
def test_agilent_real_scan_counts_and_unscaled_samples(environment, count, hashes):
    location = os.environ.get(environment)
    if not location:
        pytest.skip("set %s to the external acquisition directory" % environment)
    source = Path(location)
    for name, expected in zip(("fid", "procpar"), hashes):
        assert hashlib.sha256((source / name).read_bytes()).hexdigest() == expected
    payload = (source / "fid").read_bytes()
    blocks, traces, points, width, _, _, _, status, headers = struct.unpack(
        ">6i2hi", payload[:32]
    )
    assert blocks == traces == headers == 1 and width == 4 and status == 201
    scale, _, _, _, ctcount, _, _, _, _ = struct.unpack(">4hi4f", payload[32:60])
    assert ctcount == count and scale == 0
    values = np.frombuffer(payload, dtype=">f4", count=points, offset=60)
    expected_data = values[::2] + 1j * values[1::2]
    for retain_headers in (False, True):
        raw = ng.interop.read_agilent_fid(source, read_blockhead=retain_headers)
        normalized = ng.interop.normalize_agilent_fid(raw)
        for result in (raw, normalized):
            assert result.acquisition["scan_counts"] == {
                "requested": count,
                "procpar_completed": count,
                "block_completed": (count,),
                "block_scales": (0,),
                "completed": count,
                "source": "fid.blockheader.ctcount",
                "status": "consistent",
                "invalid": (),
            }
            assert result.acquisition["NS"] is None
            assert result.acquisition["NE"] is None
            assert result.acquisition["normalization"] == "none"
            np.testing.assert_array_equal(result.data, expected_data)
    for name, expected in zip(("fid", "procpar"), hashes):
        assert hashlib.sha256((source / name).read_bytes()).hexdigest() == expected


@pytest.mark.parametrize(
    "observed, decoupled, expected",
    [
        (["H1"], ["C13"], "H1"),
        (["C13"], ["H1"], "C13"),
        (["F19"], None, "F19"),
        (None, ["C13"], None),
        ([], ["C13"], None),
        ([""], ["C13"], None),
        (None, None, None),
    ],
)
def test_agilent_direct_nucleus_uses_observed_tn_only(
    monkeypatch, tmp_path, observed, decoupled, expected
):
    dic, data = _dic_data()
    for key, values in (("tn", observed), ("dn", decoupled)):
        if values is None:
            dic["procpar"].pop(key)
        else:
            dic["procpar"][key] = {"values": values}
    monkeypatch.setattr(ng.varian, "read", lambda *args, **kwargs: (dic, data.copy()))

    raw = ng.interop.read_agilent_fid(str(tmp_path))
    normalized = ng.interop.normalize_agilent_fid(raw)

    for result in (raw, normalized):
        assert result.acquisition["nucleus"] == expected
        assert result.axes[0].label == expected
        assert result.acquisition["observation_frequency_mhz"] == 125.0
        assert result.metadata["procpar"] == dic["procpar"]
        np.testing.assert_array_equal(result.data, data)


@pytest.mark.dataset
def test_agilent_real_hop_observed_nucleus():
    location = os.environ.get("NMRGLUE_AGILENT_HOP_DATA")
    if not location:
        pytest.skip("set NMRGLUE_AGILENT_HOP_DATA to the external nmrML hop FID")
    source = Path(location)
    expected_hashes = {
        "fid": "ffdb15ed7ec30d3e01d86a8a743958ea6e165c618f791a728956bee43a06ce81",
        "procpar": "458e0230178a7642effa116ff32f005edda092f698899998300a4620096ca370",
    }
    for name, expected in expected_hashes.items():
        assert hashlib.sha256((source / name).read_bytes()).hexdigest() == expected
    raw = ng.interop.read_agilent_fid(source)
    normalized = ng.interop.normalize_agilent_fid(raw)
    for result in (raw, normalized):
        assert result.metadata["procpar"]["tn"]["values"] == ["H1"]
        assert result.metadata["procpar"]["dn"]["values"] == ["C13"]
        assert result.acquisition["nucleus"] == "H1"
        assert result.axes[0].label == "H1"
    np.testing.assert_array_equal(normalized.data, raw.data)
    for name, expected in expected_hashes.items():
        assert hashlib.sha256((source / name).read_bytes()).hexdigest() == expected


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
    source_axis = result.axes[0].values
    source_axis.setflags(write=True)
    source_axis[0] = 99.0
    assert normalized.axes[0].values[0] == 0.0
    with pytest.raises(ValueError):
        normalized.axes[0].values.setflags(write=True)


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


def test_agilent_normalized_data_does_not_alias_source_buffer(monkeypatch, tmp_path):
    dic, data = _dic_data()
    monkeypatch.setattr(ng.varian, "read", lambda *args, **kwargs: (dic, data))

    normalized = ng.interop.normalize_agilent_fid(
        ng.interop.read_agilent_fid(str(tmp_path))
    )
    base = data.copy()
    normalized = dataclasses.replace(normalized, data=base)
    original = normalized.data.copy()
    base[0] = 99 + 99j

    np.testing.assert_array_equal(normalized.data, original)
    with pytest.raises(ValueError):
        normalized.data.setflags(write=True)


@pytest.mark.parametrize(
    "change",
    [
        lambda result: dataclasses.replace(result, encoding=("unknown",)),
        lambda result: dataclasses.replace(
            result, dimensions={**result.dimensions, "TDeff": 99}
        ),
        lambda result: dataclasses.replace(
            result, components=(ng.interop.Component("complex", result.data[:-1]),)
        ),
        lambda result: dataclasses.replace(
            result, applied_corrections={"normalization": "none", "conjugation": "none", "scale": 2}
        ),
        lambda result: dataclasses.replace(
            result, dimensions={**result.dimensions, "storage_shape": (99,)}
        ),
        lambda result: dataclasses.replace(
            result,
            axes=(
                ng.interop.Axis(
                    values=np.arange(1, 5, dtype=float).reshape(1, 4),
                    unit="s",
                    domain="time",
                    direction="increasing",
                ),
            ),
        ),
    ],
)
def test_agilent_normalization_rejects_inconsistent_descriptive_contract(
    monkeypatch, tmp_path, change
):
    dic, data = _dic_data()
    monkeypatch.setattr(ng.varian, "read", lambda *args, **kwargs: (dic, data.copy()))
    descriptive = change(ng.interop.read_agilent_fid(str(tmp_path)))

    with pytest.raises(ValueError):
        ng.interop.normalize_agilent_fid(descriptive)


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
