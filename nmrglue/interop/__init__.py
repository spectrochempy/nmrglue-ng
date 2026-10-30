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
from .nmrpipe import write_readresult_nmrpipe
from .normalize import normalize_agilent_fid
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
    "read_bruker_fid",
    "read_bruker_ser",
    "read_agilent_fid",
    "read_agilent_states_2d",
    "normalize_agilent_fid",
    "write_readresult_nmrpipe",
]
