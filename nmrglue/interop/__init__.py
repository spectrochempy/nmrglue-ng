"""Optional, additive interoperability layer for nmrglue-ng readers.

``nmrglue.interop`` exposes a neutral :class:`ReadResult` built from existing
readers.  It is additive: the historical ``(dic, data)`` APIs are unchanged,
and no SpectroChemPy, NDDataset, Pint, or CSDM dependency is imported.

The supported profiles include Bruker/TopSpin processed 1D data and raw 1D/2D
acquisitions::

    import nmrglue as ng

    result = ng.interop.read_bruker_pdata(".../pdata/1", scale_data=True)
    dic, data = ng.bruker.read_pdata(".../pdata/1", scale_data=True)

    result = ng.interop.read_bruker_ser(".../1/ser")
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from .bruker import read_bruker_fid, read_bruker_pdata, read_bruker_ser
from .dispatch import read
from .bruker_ser import (
    normalize_bruker_ser_echo_antiecho, normalize_bruker_ser_qf,
    normalize_bruker_ser_states_tppi,
)
from .bruker_pdata_2d import (
    normalize_bruker_pdata_2d,
    read_bruker_pdata_2d,
    read_bruker_pdata_2d_storage,
)
from .jcampdx import (
    normalize_jcampdx_1d, normalize_jcampdx_fid, read_jcampdx_1d, read_jcampdx_fid,
    normalize_jcampdx_2d, read_jcampdx_2d,
)
from .jeol import normalize_jeol_2d, normalize_jeol_fid, read_jeol_2d_storage, read_jeol_fid
from .simpson import (
    normalize_simpson_fid, normalize_simpson_fid_2d, normalize_simpson_spectrum,
    normalize_simpson_spectrum_2d,
    read_simpson_fid, read_simpson_fid_2d, read_simpson_spectrum, read_simpson_spectrum_2d,
)
from .storage import read_agilent_fid_storage, read_bruker_ser_storage
from .nmrpipe import write_readresult_nmrpipe
from .nmrml import (
    normalize_nmrml_1d, normalize_nmrml_2d, normalize_nmrml_raw_2d,
    read_nmrml_1d, read_nmrml_2d, read_nmrml_raw_2d,
)
from .nmrpipe_read import (
    normalize_nmrpipe_1d, normalize_nmrpipe_2d, read_nmrpipe_1d, read_nmrpipe_2d,
    read_nmrpipe_2d_storage,
)
from .normalize import normalize_agilent_fid, normalize_bruker_fid, normalize_bruker_pdata
from .varian import read_agilent_fid, read_agilent_states_2d
from .result import (
    DIAGNOSTIC_CONTEXT_SCHEMA,
    Axis,
    Component,
    Diagnostic,
    NormalizedAcquisition,
    ReadResult,
    Reference,
)

_NORMALIZERS: dict[str, Callable[..., NormalizedAcquisition]] = {
    "agilent-fid": normalize_agilent_fid,
    "bruker-fid": normalize_bruker_fid,
    "bruker-ser-qf-2d": normalize_bruker_ser_qf,
    "bruker-pdata": normalize_bruker_pdata,
    "bruker-pdata-2d": normalize_bruker_pdata_2d,
    "jcampdx-fid-1d": normalize_jcampdx_fid,
    "jcampdx-spectrum-1d": normalize_jcampdx_1d,
    "jcampdx-spectrum-2d": normalize_jcampdx_2d,
    "jeol-fid-1d": normalize_jeol_fid,
    "jeol-2d-storage": normalize_jeol_2d,
    "nmrml-1d": normalize_nmrml_1d,
    "nmrml-2d-spectrum": normalize_nmrml_2d,
    "nmrml-raw-2d": normalize_nmrml_raw_2d,
    "nmrpipe-1d": normalize_nmrpipe_1d,
    "nmrpipe-2d": normalize_nmrpipe_2d,
    "nmrpipe-2d-storage": normalize_nmrpipe_2d,
    "simpson-fid-1d": normalize_simpson_fid,
    "simpson-fid-2d": normalize_simpson_fid_2d,
    "simpson-spectrum-1d": normalize_simpson_spectrum,
    "simpson-spectrum-2d": normalize_simpson_spectrum_2d,
}


def normalize(result: ReadResult, **options: Any) -> NormalizedAcquisition:
    """Normalize a read result using the profile recorded by its reader.

    Options are passed directly to the selected normalizer. Supply any
    confirmations required by that profile, such as a time-grid confirmation.

    Raises
    ------
    TypeError
        If result is not a ReadResult, or the options do not match the profile.
    ValueError
        If no normalizer is registered for the profile or the result fails
        the selected normalizer's validation.
    """
    if not isinstance(result, ReadResult):
        raise TypeError("normalize() expects a ReadResult")
    normalizer = _NORMALIZERS.get(result.format)
    if normalizer is None:
        raise ValueError(f"No interop normalizer for profile {result.format!r}")
    return normalizer(result, **options)


__all__ = [
    "Axis",
    "Component",
    "DIAGNOSTIC_CONTEXT_SCHEMA",
    "Diagnostic",
    "NormalizedAcquisition",
    "ReadResult",
    "Reference",
    "normalize",
    "read",
    "read_bruker_pdata",
    "read_bruker_pdata_2d",
    "read_bruker_pdata_2d_storage",
    "read_bruker_ser_storage",
    "read_agilent_fid_storage",
    "normalize_bruker_pdata_2d",
    "read_bruker_fid",
    "read_jeol_fid",
    "read_simpson_fid",
    "read_simpson_fid_2d",
    "normalize_simpson_fid_2d",
    "read_simpson_spectrum",
    "read_simpson_spectrum_2d",
    "normalize_simpson_spectrum_2d",
    "normalize_simpson_spectrum",
    "normalize_simpson_fid",
    "read_jcampdx_1d",
    "read_jcampdx_2d",
    "normalize_jcampdx_2d",
    "read_jcampdx_fid",
    "normalize_jcampdx_fid",
    "normalize_jcampdx_1d",
    "read_jeol_2d_storage",
    "normalize_jeol_fid",
    "normalize_jeol_2d",
    "read_bruker_ser",
    "read_agilent_fid",
    "read_agilent_states_2d",
    "normalize_agilent_fid",
    "normalize_bruker_fid",
    "normalize_bruker_ser_echo_antiecho",
    "normalize_bruker_ser_qf",
    "normalize_bruker_ser_states_tppi",
    "normalize_bruker_pdata",
    "write_readresult_nmrpipe",
    "read_nmrml_1d",
    "normalize_nmrml_1d",
    "read_nmrml_2d",
    "normalize_nmrml_2d",
    "read_nmrml_raw_2d",
    "normalize_nmrml_raw_2d",
    "read_nmrpipe_1d",
    "normalize_nmrpipe_1d",
    "read_nmrpipe_2d",
    "read_nmrpipe_2d_storage",
    "normalize_nmrpipe_2d",
]
