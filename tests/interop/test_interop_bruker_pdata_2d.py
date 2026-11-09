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


def test_storage_reads_present_planes_without_requiring_a_fourier_profile(tmp_path):
    planes = write_planes(tmp_path, endian=">", indirect={"FT_mod": 99, "SF": 0})
    (tmp_path / "2rr").unlink()
    (tmp_path / "2ir").unlink()
    stored = interop.read_bruker_pdata_2d_storage(tmp_path)
    assert stored.domains == ("unknown", "unknown")
    assert stored.metadata["proc2s"]["FT_mod"] == 99
    assert tuple(component.name for component in stored.components) == ("2ri", "2ii")
    np.testing.assert_array_equal(stored.data, planes[1])
    np.testing.assert_array_equal(stored.components[1].data, planes[3])
    with pytest.raises(ValueError):
        interop.normalize_bruker_pdata_2d(stored)


def test_storage_uses_strip_dimensions(tmp_path):
    planes = write_planes(
        tmp_path,
        indirect={"SI": 8, "STSI": 4, "STSR": 2, "FTSIZE": 8},
        direct={"SI": 12, "STSI": 6, "STSR": 3, "FTSIZE": 12},
    )
    stored = interop.read_bruker_pdata_2d_storage(tmp_path)
    assert stored.dimensions["shape"] == (4, 6)
    assert stored.metadata["proc2s"]["STSR"] == 2
    np.testing.assert_array_equal(stored.data, planes[0])
    with pytest.raises(ValueError, match="complete Fourier grid"):
        interop.read_bruker_pdata_2d(tmp_path)


def test_storage_preserves_float64_and_does_not_scale(tmp_path):
    planes = write_planes(tmp_path, indirect={"DTYPP": 2}, direct={"DTYPP": 2})
    plane = planes[0].astype(np.float64) + 0.25
    tiles = [plane[y : y + 2, x : x + 3] for y in (0, 2) for x in (0, 3)]
    (tmp_path / "2rr").write_bytes(np.stack(tiles).astype("<f8").tobytes())
    for name in NAMES[1:]:
        (tmp_path / name).unlink()
    stored = interop.read_bruker_pdata_2d_storage(tmp_path)
    assert stored.data.dtype == np.dtype("<f8")
    assert stored.applied_corrections == {}
    np.testing.assert_array_equal(stored.data, plane)


@pytest.mark.parametrize("reference", ["acquisition", "processing"])
def test_public_processed_channels(tmp_path, reference):
    path = tmp_path / "pdata" / "1"
    path.mkdir(parents=True)
    rr, ri, ir, ii = write_planes(path)
    direct = tmp_path / "acqus"
    indirect = tmp_path / "acqu2s"
    direct.write_text(
        "##TITLE= direct\n##$PARMODE= 1\n##$RG= 4\n##$NS= 32\n"
        "##$SFO1= 500.001\n##$SW= 8\n##END=\n"
    )
    indirect.write_text(
        "##TITLE= indirect\n##$SFO1= 100.002\n##$SW= 10\n##END=\n"
    )
    procs_files = ["procs", "proc2s"]
    stored = interop.read_bruker_pdata_2d(
        path, acqus_files=[direct, indirect],
        procs_files=tuple(procs_files) if reference == "processing" else procs_files,
    )
    assert procs_files == ["procs", "proc2s"]
    normalized = interop.normalize_bruker_pdata_2d(stored, axis_reference=reference)
    np.testing.assert_array_equal(
        normalized.data, np.stack((rr + 1j * ir, ri + 1j * ii)) / 32
    )
    assert normalized.branch_order == ("S_R", "S_I")
    assert normalized.acquisition["complex_axis"] == "F1"
    assert normalized.acquisition["acquisition_frequency_mhz"] == (100.002, 500.001)
    assert normalized.applied_operations[0]["scale"] == 0.25
    if reference == "processing":
        np.testing.assert_array_equal(normalized.axes[0].values, [300, 100, -100, -300])
        assert normalized.axes[0].reference.observation_frequency == 100
    else:
        np.testing.assert_allclose(
            normalized.axes[0].values[[0, -1]], [2500.01, 1499.99],
            rtol=0, atol=1e-8,
        )
        assert normalized.axes[0].reference.observation_frequency == 100.002
    np.testing.assert_array_equal(interop.normalize_bruker_pdata_2d(stored).data[0], rr / 8)
