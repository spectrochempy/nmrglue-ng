"""Self-contained error-path tests for the SIMPSON reader."""

import pytest

import nmrglue.fileio.simpson as simpson


def test_read_raw_binary_requires_parameters(tmp_path):
    """Reject incomplete raw-binary parameters before reading its contents."""
    raw_binary = tmp_path / "minimal.raw"
    raw_binary.write_bytes(b"\x00" * 16)

    with pytest.raises(
        ValueError,
        match="spe must be True or False for raw_bin data",
    ):
        simpson.read(raw_binary)

    with pytest.raises(
        ValueError,
        match="ndim must be 1 or 2 for raw_bin data",
    ):
        simpson.read(raw_binary, spe=False)

    with pytest.raises(
        ValueError,
        match="NP and NI must be given for raw_bin data",
    ):
        simpson.read(raw_binary, spe=False, ndim=2)

    with pytest.raises(ValueError, match="unknown ftype"):
        simpson.read(raw_binary, ftype="unsupported")
