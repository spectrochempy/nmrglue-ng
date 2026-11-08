"""Integration tests for selecting an existing interop reader."""

import os
from pathlib import Path
import struct

import numpy as np
import pytest

from nmrglue import interop


FIXTURES = Path(__file__).parents[1] / "fixtures" / "fileio" / "data"


@pytest.mark.parametrize(
    "filename, profile, reader",
    [
        ("nmrpipe_1d_freq.fid", "nmrpipe-1d", interop.read_nmrpipe_1d),
        ("nmrpipe_2d_freq.ft2", "nmrpipe-2d-storage", interop.read_nmrpipe_2d_storage),
        ("nmrpipe_2d_time.fid", "nmrpipe-2d-storage", interop.read_nmrpipe_2d_storage),
        ("jeol/epicatechin_1h.jdf", "jeol-fid-1d", interop.read_jeol_fid),
        ("jeol/epicatechin_hsqc.jdf", "jeol-2d-storage", interop.read_jeol_2d_storage),
    ],
)
def test_detect_binary_header(filename, profile, reader):
    source = FIXTURES / filename
    result = interop.read(source)
    assert result.format == profile
    np.testing.assert_array_equal(result.data, reader(source).data)


@pytest.mark.parametrize("kind, name", [("FID", "fid"), ("SPE", "spectrum")])
@pytest.mark.parametrize("ndim", [1, 2])
def test_detect_simpson_header(tmp_path, kind, name, ndim):
    source = tmp_path / "unrelated.ft2"
    indirect = "NI=2\nSW1=1000\n" if ndim == 2 else ""
    samples = "1 -2\n3 4\n" * (2 if ndim == 2 else 1)
    source.write_text(
        f"SIMP\nNP=2\nSW=2000\n{indirect}TYPE={kind}\nDATA\n{samples}END\n"
    )
    result = interop.read(source)
    assert result.format == f"simpson-{name}-{ndim}d"
    np.testing.assert_array_equal(result.data.reshape(-1, 2)[0], [1 - 2j, 3 + 4j])


def test_bruker_processed_detection_preserves_scale():
    source = FIXTURES / "bruker_pdata" / "exp1" / "pdata" / "1"
    result = interop.read(source)
    assert result.format == "bruker-pdata"
    assert result.applied_corrections["scale_data"] is False
    assert interop.read(source, profile="bruker-pdata").applied_corrections["scale_data"]
    assert interop.read(source, scale_data=True).applied_corrections["scale_data"]


def test_ambiguous_fid_directory_requires_profile(tmp_path):
    header = struct.pack(">6i2hi", 1, 1, 2, 4, 8, 36, 0, 5, 1)
    block = struct.pack(">4hi4f2i", 0, 5, 1, 0, 1, 0, 0, 0, 0, 23, -42)
    (tmp_path / "fid").write_bytes(header + block)
    (tmp_path / "procpar").touch()
    result = interop.read(tmp_path)
    assert result.format == "agilent-fid-storage"
    (tmp_path / "acqus").touch()
    with pytest.raises(ValueError, match="Ambiguous.*agilent-fid-storage.*bruker-fid"):
        interop.read(tmp_path)
    result = interop.read(tmp_path, profile="agilent-fid-storage")
    np.testing.assert_array_equal(result.data, [[23, -42]])


def test_unrecognized_input_does_not_use_extension(tmp_path):
    source = tmp_path / "unknown.ft2"
    source.write_bytes(b"unknown")
    with pytest.raises(ValueError, match="specify profile"):
        interop.read(source)
    with pytest.raises(ValueError, match="Unknown.*nmrpipe-1d"):
        interop.read(source, profile="typo")


def test_explicit_profile_preserves_reader_error():
    source = FIXTURES / "nmrpipe_2d_time.fid"
    assert interop.read(source).format == "nmrpipe-2d-storage"
    with pytest.raises(ValueError, match="frequency|FTFLAG"):
        interop.read(source, profile="nmrpipe-2d")



@pytest.mark.skipif(not hasattr(os, "mkfifo"), reason="requires POSIX FIFOs")
def test_detection_refuses_fifo_without_opening(tmp_path, monkeypatch):
    source = tmp_path / "fifo"
    os.mkfifo(source)

    def unexpected_open(*args, **kwargs):
        pytest.fail("detection attempted to open a FIFO")

    monkeypatch.setattr(Path, "open", unexpected_open)
    with pytest.raises(ValueError, match="Cannot detect an interop profile"):
        interop.read(source)
