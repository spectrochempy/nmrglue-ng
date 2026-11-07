"""Binary fixtures for scalar trace reads without acquisition interpretation."""

import struct

import numpy as np
import pytest

from nmrglue import interop


def test_bruker_ser_storage_preserves_padding_and_unknown_mode(tmp_path):
    (tmp_path / "acqus").write_text(
        "##TITLE= synthetic\n##$TD= 6\n##$BYTORDA= 1\n##$DTYPA= 0\n##$AQ_mod= 3\n##END=\n"
    )
    (tmp_path / "acqu2s").write_text(
        "##TITLE= synthetic\n##$TD= 12\n##$FnMODE= 99\n##END=\n"
    )
    (tmp_path / "nuslist").write_bytes(b"0\n5\n9\n")
    words = np.arange(3 * 256, dtype=">i4").reshape(3, 256)
    path = tmp_path / "ser"
    path.write_bytes(words.tobytes())
    result = interop.read_bruker_ser_storage(tmp_path)
    np.testing.assert_array_equal(result.data, words)
    assert result.data.dtype == words.dtype
    assert result.dimensions["declared_td"] == 6
    assert result.metadata["acqu2s"]["FnMODE"] == 99
    assert result.metadata["nuslist_raw"] == b"0\n5\n9\n"
    assert result.axes[0].values is None
    path.write_bytes(words.tobytes()[:-1])
    with pytest.raises(ValueError, match="stride"):
        interop.read_bruker_ser_storage(tmp_path)


def test_agilent_fid_storage_preserves_scalar_values_and_trace_order(tmp_path):
    words = np.arange(2**25, 2**25 + 12, dtype=">i4").reshape(4, 3)
    header = struct.pack(">6i2hi", 2, 2, 3, 4, 12, 52, 0, 5, 1)
    blocks = [
        struct.pack(">4hi4f", 0, 5, i + 1, 0, i + 2, 0, 0, 0, 0)
        + words[2 * i : 2 * i + 2].tobytes()
        for i in range(2)
    ]
    path = tmp_path / "fid"
    payload = header + b"".join(blocks)
    path.write_bytes(payload)
    result = interop.read_agilent_fid_storage(tmp_path)
    np.testing.assert_array_equal(result.data, words)
    assert result.data.dtype == words.dtype
    assert result.dimensions["traces_per_block"] == 2
    assert [block["ctcount"] for block in result.metadata["blockheader"]] == [2, 3]
    assert result.domains == ("unknown", "unknown")
    path.write_bytes(payload + b"\0")
    with pytest.raises(ValueError, match="block geometry"):
        interop.read_agilent_fid_storage(tmp_path)
