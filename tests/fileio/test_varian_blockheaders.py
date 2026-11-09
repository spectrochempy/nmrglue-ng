"""Tests for reading Varian blocks containing multiple traces."""

import io

import numpy as np
import pytest
from numpy.testing import assert_array_equal

from nmrglue.fileio import varian


def test_get_block_ntraces_with_blockheader():
    """Read multi-trace data when block-header details are requested."""
    blockheader = bytes(28)
    trace_data = np.array([1, 2, 3, 4], dtype=">i4").tobytes()

    dic, data = varian.get_block_ntraces(
        io.BytesIO(blockheader + trace_data),
        ntraces=2,
        pts=2,
        nbheaders=1,
        dt=np.dtype(">i4"),
        read_blockhead=True,
    )

    assert dic["scale"] == 0
    assert_array_equal(data, [[1, 2], [3, 4]])


def _write_multitrace_fid(path, ntraces=3):
    words = np.arange(16 * ntraces, dtype=">i4").reshape(2, ntraces, 8)
    words[..., 1::2] *= -3
    with path.open("wb") as stream:
        varian.put_fileheader(stream, (2, ntraces, 8, 4, 32, 28 + 32 * ntraces, 0, 21, 1))
        for index, block in enumerate(words, 1):
            varian.put_blockheader(stream, (0, 21, index, 0, 1, 0, 0, 0, 0))
            stream.write(block.tobytes())
    return words[..., ::2].reshape(-1, 4) + 1j * words[..., 1::2].reshape(-1, 4)


def test_read_recovers_multitrace_fid_with_inconsistent_procpar(tmp_path):
    expected = _write_multitrace_fid(tmp_path / "fid")
    params = {"np": ["8"], "ni": ["2"], "ni2": ["2"], "phase": ["1", "2"],
              "phase2": ["1", "2"]}
    varian.write_procpar(tmp_path / "procpar", {
        key: varian.create_pdic_param(key, values) for key, values in params.items()
    })
    with pytest.warns(UserWarning, match="returning raw 2D data"):
        header, actual = varian.read(tmp_path, torder="regular", read_blockhead=True)
    assert header["ntraces"] == 3
    assert [item["index"] for item in header["blockheader"]] == [1, 2]
    assert_array_equal(actual, expected)


@pytest.mark.parametrize("shape", [(2, 2, 4), (2, 3, 1)])
def test_multitrace_reordering_preserves_all_raw_samples_on_mismatch(tmp_path, shape):
    path = tmp_path / "fid"
    expected = _write_multitrace_fid(path)
    with pytest.warns(UserWarning, match="returning raw 2D data"):
        _, actual = varian.read_fid_ntraces(path, shape=shape, torder="regular")
    assert_array_equal(actual, expected)


def test_multitrace_reordering_retains_consistent_shape(tmp_path):
    path = tmp_path / "fid"
    raw = _write_multitrace_fid(path, ntraces=4)
    _, actual = varian.read_fid_ntraces(path, shape=(2, 4, 4), torder="regular")
    assert_array_equal(actual, raw[[0, 1, 4, 5, 2, 3, 6, 7]].reshape(2, 4, 4))


@pytest.mark.parametrize("shape, expected_shape", [(None, (1,)), ((1, 1), (1, 1))])
def test_read_fid_legacy_single_trace_shape(tmp_path, shape, expected_shape):
    path = tmp_path / "fid"
    with path.open("wb") as stream:
        varian.put_fileheader(stream, (1, 1, 2, 4, 8, 36, 0, 21, 1))
        varian.put_blockheader(stream, (0, 21, 1, 0, 1, 0, 0, 0, 0))
        stream.write(np.array([2, -3], dtype=">i4").tobytes())
    _, actual = varian.read_fid(path, shape=shape, legacy_layout=True)
    assert_array_equal(actual, np.array([2 - 3j]).reshape(expected_shape))
    _, explicit_matrix = varian.read_fid(path, shape=shape, legacy_layout=True, as_2d=True)
    assert_array_equal(explicit_matrix, [[2 - 3j]])


@pytest.mark.parametrize("shape", [(-1, 2, 4), (3, 2, -1)])
def test_multitrace_flat_shape_can_infer_an_axis(tmp_path, shape):
    path = tmp_path / "fid"
    raw = _write_multitrace_fid(path)
    _, actual = varian.read_fid_ntraces(path, shape=shape, torder="flat")
    assert_array_equal(actual, raw.reshape(3, 2, 4))
