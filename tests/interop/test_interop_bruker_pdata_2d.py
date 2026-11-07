"""Synthetic Bruker processed planes in independent tiled storage order."""

from dataclasses import replace

import numpy as np
import pytest

from nmrglue import interop


NAMES = ("2rr", "2ri", "2ir", "2ii")


def write_planes(path, *, endian="<", indirect=None, direct=None):
    for name, size, tile, sf, sw, offset, label, overrides in (
        ("proc2s", 4, 2, 100, 800, 3, "13C", indirect),
        ("procs", 6, 3, 500, 2400, 7, "1H", direct),
    ):
        parameters = dict(
            SI=size,
            XDIM=tile,
            STSI=size,
            STSR=0,
            FTSIZE=size,
            FT_mod=6,
            BYTORDP=int(endian == ">"),
            DTYPP=0,
            NC_proc=-3,
            SF=sf,
            SW_p=sw,
            OFFSET=offset,
            AXNUC=f"<{label}>",
        )
        parameters.update(overrides or {})
        body = "".join(f"##${key}= {value}\n" for key, value in parameters.items())
        (path / name).write_text("##TITLE= synthetic pdata\n" + body + "##END=\n")
    planes = []
    for index, name in enumerate(NAMES):
        plane = np.arange(-12, 12, dtype=np.int32).reshape(4, 6) + 100 * index
        tiles = [plane[y : y + 2, x : x + 3] for y in (0, 2) for x in (0, 3)]
        (path / name).write_bytes(np.stack(tiles).astype(endian + "i4").tobytes())
        planes.append(plane)
    return np.stack(planes)


@pytest.mark.parametrize("endian", ["<", ">"])
@pytest.mark.parametrize("scaled", [False, True])
def test_read_complete_planes(tmp_path, endian, scaled):
    expected = write_planes(tmp_path, endian=endian)
    result = interop.read_bruker_pdata_2d(tmp_path, scale_data=scaled)
    normalized = interop.normalize_bruker_pdata_2d(result)
    if scaled:
        expected = expected / 8
    assert normalized.data.dtype == expected.dtype
    np.testing.assert_array_equal(normalized.data, expected)
    np.testing.assert_array_equal(result.data, expected[0])
    assert tuple(c.name for c in result.components) == normalized.branch_order == NAMES
    assert normalized.dimensions == ("channels", "F1", "F2")
    assert normalized.physical_dimensions == ("F1", "F2")
    assert normalized.channel_axis == 0
    assert not normalized.data.flags.writeable
    np.testing.assert_array_equal(normalized.axes[0].values, [300, 100, -100, -300])
    np.testing.assert_array_equal(
        normalized.axes[1].values, [3500, 3100, 2700, 2300, 1900, 1500]
    )
    assert tuple(a.label for a in normalized.axes) == ("13C", "1H")
    assert tuple(a.reference.observation_frequency for a in normalized.axes) == (
        100,
        500,
    )
    assert result.applied_corrections.get("NC_proc") == (-3 if scaled else None)


@pytest.mark.parametrize(
    "indirect",
    [
        {"FT_mod": 0},
        {"FT_mod": 99},
        {"PPARMOD": 2},
        {"XDIM": 3},
        {"SI": 8},
        {"STSR": 1},
        {"FTSIZE": 8},
        {"DTYPP": 2},
        {"BYTORDP": 1},
        {"SF": 0},
    ],
)
def test_reject_inconsistent_geometry(tmp_path, indirect):
    write_planes(tmp_path, indirect=indirect)
    with pytest.raises(ValueError):
        interop.read_bruker_pdata_2d(tmp_path)


@pytest.mark.parametrize("size", [None, 4, 100])
def test_reject_missing_truncated_or_extra_plane(tmp_path, size):
    write_planes(tmp_path)
    plane = tmp_path / "2ir"
    if size is None:
        plane.unlink()
    else:
        plane.write_bytes(bytes(size))
    with pytest.raises(ValueError, match="2ir.*payload size"):
        interop.read_bruker_pdata_2d(tmp_path)


def test_normalizer_rejects_wrong_component_order(tmp_path):
    write_planes(tmp_path)
    result = interop.read_bruker_pdata_2d(tmp_path)
    with pytest.raises(ValueError, match="file-name order"):
        interop.normalize_bruker_pdata_2d(
            replace(result, components=result.components[::-1])
        )
