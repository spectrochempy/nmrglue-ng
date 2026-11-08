"""Reader selection for the generic interop entry point."""

from collections.abc import Callable
from pathlib import Path
import os
import stat
import struct
from typing import Any

from ..fileio import pipe
from .bruker import read_bruker_fid, read_bruker_pdata, read_bruker_ser
from .bruker_pdata_2d import _COMPONENTS, read_bruker_pdata_2d, read_bruker_pdata_2d_storage
from .jcampdx import read_jcampdx_1d, read_jcampdx_2d, read_jcampdx_fid
from .jeol import read_jeol_2d_storage, read_jeol_fid
from .nmrml import read_nmrml_1d, read_nmrml_2d, read_nmrml_raw_2d
from .nmrpipe_read import read_nmrpipe_1d, read_nmrpipe_2d, read_nmrpipe_2d_storage
from .result import ReadResult
from .simpson import (
    read_simpson_fid, read_simpson_fid_2d, read_simpson_spectrum,
    read_simpson_spectrum_2d,
)
from .storage import read_agilent_fid_storage, read_bruker_ser_storage
from .varian import read_agilent_fid, read_agilent_states_2d


_READERS: dict[str, Callable[..., ReadResult]] = {
    "agilent-fid": read_agilent_fid,
    "agilent-fid-storage": read_agilent_fid_storage,
    "agilent-states-2d": read_agilent_states_2d,
    "bruker-fid": read_bruker_fid,
    "bruker-pdata": read_bruker_pdata,
    "bruker-pdata-2d": read_bruker_pdata_2d,
    "bruker-pdata-2d-storage": read_bruker_pdata_2d_storage,
    "bruker-ser": read_bruker_ser,
    "bruker-ser-storage": read_bruker_ser_storage,
    "jcampdx-fid-1d": read_jcampdx_fid,
    "jcampdx-spectrum-1d": read_jcampdx_1d,
    "jcampdx-spectrum-2d": read_jcampdx_2d,
    "jeol-2d-storage": read_jeol_2d_storage,
    "jeol-fid-1d": read_jeol_fid,
    "nmrml-1d": read_nmrml_1d,
    "nmrml-2d-spectrum": read_nmrml_2d,
    "nmrml-raw-2d": read_nmrml_raw_2d,
    "nmrpipe-1d": read_nmrpipe_1d,
    "nmrpipe-2d": read_nmrpipe_2d,
    "nmrpipe-2d-storage": read_nmrpipe_2d_storage,
    "simpson-fid-1d": read_simpson_fid,
    "simpson-fid-2d": read_simpson_fid_2d,
    "simpson-spectrum-1d": read_simpson_spectrum,
    "simpson-spectrum-2d": read_simpson_spectrum_2d,
}


def _directory_profiles(path: Path) -> list[str]:
    files = {entry.name for entry in path.iterdir() if entry.is_file()}
    profiles = []
    if {"fid", "procpar"} <= files:
        profiles.append("agilent-fid-storage")
    if {"fid", "acqus"} <= files:
        profiles.append("bruker-fid")
    if {"ser", "acqus"} <= files:
        profiles.append("bruker-ser-storage")
    if {"1r", "procs"} <= files:
        profiles.append("bruker-pdata")
    if {"procs", "proc2s"} <= files and files.intersection(_COMPONENTS):
        profiles.append("bruker-pdata-2d-storage")
    return profiles


def _file_profile(path: Path) -> str | None:
    # Read a bounded prefix. The selected reader checks the full payload.
    with path.open("rb") as stream:
        prefix = stream.read(2048)
    if prefix.startswith(b"JEOL.NMR") and len(prefix) > 12:
        # JDF stores the dimension count as one byte at offset 12.
        return {1: "jeol-fid-1d", 2: "jeol-2d-storage"}.get(prefix[12])
    if prefix.startswith((b"SIMP\n", b"SIMP\r\n", b"SIMP\r")):
        lines = prefix.splitlines()
        if b"DATA" in lines:
            records = lines[1:lines.index(b"DATA")]
            kinds = [line[5:] for line in records if line.startswith(b"TYPE=")]
            if kinds in ([b"FID"], [b"SPE"]):
                kind = "fid" if kinds == [b"FID"] else "spectrum"
                ndim = 2 if any(line.startswith(b"NI=") for line in records) else 1
                return f"simpson-{kind}-{ndim}d"
    if len(prefix) == 2048:
        marker = int(pipe.fdata_nums["FDFLTORDER"]) * 4
        dimensions = int(pipe.fdata_nums["FDDIMCOUNT"]) * 4
        for endian in ("<", ">"):
            if prefix[:4] == bytes(4) and prefix[marker:marker + 4] == struct.pack(
                endian + "f", 2.345
            ):
                ndim, = struct.unpack_from(endian + "f", prefix, dimensions)
                return {1: "nmrpipe-1d", 2: "nmrpipe-2d-storage"}.get(ndim)
    return None


def read(
    path: str | os.PathLike[str], *, profile: str | None = None, **options: Any
) -> ReadResult:
    """Read a file or dataset directory using an existing interop reader.

    With no profile, select a reader from known headers or directory layouts.
    Prefer the storage reader when a separate qualified reader exists for the
    same input. Supply a profile to skip detection. Options are passed to the
    selected reader. Auto-detected Bruker 1D pdata defaults to stored scale.

    Raises
    ------
    ValueError
        If the profile is unknown or the source cannot be identified uniquely.
    """
    if profile is None:
        source = Path(path)
        mode = source.stat().st_mode
        if stat.S_ISDIR(mode):
            profiles = _directory_profiles(source)
            if len(profiles) > 1:
                raise ValueError(
                    f"Ambiguous interop source {source}: {', '.join(profiles)}; "
                    "specify profile= explicitly"
                )
            profile = profiles[0] if profiles else None
        elif stat.S_ISREG(mode):
            profile = _file_profile(source)
        if profile is None:
            raise ValueError(
                f"Cannot detect an interop profile for {source}; specify profile= explicitly"
            )
        if profile == "bruker-pdata":
            options.setdefault("scale_data", False)

    reader = _READERS.get(profile)
    if reader is None:
        raise ValueError(
            f"Unknown interop reader profile {profile!r}; "
            f"choose from {', '.join(_READERS)}"
        )
    return reader(path, **options)
