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

from .bruker import read_bruker_fid, read_bruker_pdata, read_bruker_ser
from .bruker_pdata_2d import (
    normalize_bruker_pdata_2d,
    read_bruker_pdata_2d,
    read_bruker_pdata_2d_storage,
)
from .jcampdx import normalize_jcampdx_1d, read_jcampdx_1d
from .jeol import normalize_jeol_2d, normalize_jeol_fid, read_jeol_2d_storage, read_jeol_fid
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

__all__ = [
    "Axis",
    "Component",
    "DIAGNOSTIC_CONTEXT_SCHEMA",
    "Diagnostic",
    "NormalizedAcquisition",
    "ReadResult",
    "Reference",
    "read_bruker_pdata",
    "read_bruker_pdata_2d",
    "read_bruker_pdata_2d_storage",
    "read_bruker_ser_storage",
    "read_agilent_fid_storage",
    "normalize_bruker_pdata_2d",
    "read_bruker_fid",
    "read_jeol_fid",
    "read_jcampdx_1d",
    "normalize_jcampdx_1d",
    "read_jeol_2d_storage",
    "normalize_jeol_fid",
    "normalize_jeol_2d",
    "read_bruker_ser",
    "read_agilent_fid",
    "read_agilent_states_2d",
    "normalize_agilent_fid",
    "normalize_bruker_fid",
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
