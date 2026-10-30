"""Validated, dependency-free normalization profiles for interop results."""

from __future__ import annotations

import os

import numpy as np

from .result import NormalizedAcquisition, ReadResult


def normalize_agilent_fid(result: ReadResult) -> NormalizedAcquisition:
    """Validate an Agilent descriptive result as a storage-normalized 1D FID.

    This profile records decoding and storage semantics only. It does not apply
    scaling, conjugation, digital-filter removal, FFT, phasing or referencing.
    """
    if not isinstance(result, ReadResult):
        raise TypeError("normalize_agilent_fid requires an interop ReadResult")
    if result.format != "agilent-fid":
        raise ValueError("normalize_agilent_fid requires format='agilent-fid'")
    data = np.asarray(result.data)
    if data.ndim != 1 or not np.iscomplexobj(data):
        raise ValueError("Agilent normalized 1D profile requires one complex FID")
    if result.domains != ("time",) or len(result.axes) != 1:
        raise ValueError("Agilent normalized 1D profile requires one time axis")
    if result.acquisition.get("normalization") != "none":
        raise ValueError("Agilent result has an unrecognized normalization state")

    operation = {
        "name": "decode-agilent-complex-fid",
        "stage": "acquisition",
        "input_dimensions": ("storage",),
        "output_dimensions": ("F2",),
        "axis": "F2",
        "scale": None,
        "conjugation": "none",
        "sign": "none",
        "permutation": None,
        "evidence": "nmrglue.interop.read_agilent_fid",
    }
    provenance = {
        "source": os.fspath(result.source),
        "format": result.format,
        "reader_encoding": result.encoding,
    }
    return NormalizedAcquisition(
        data=data,
        axes=result.axes,
        dimensions=("F2",),
        physical_dimensions=("F2",),
        domains=("time",),
        quadrature_mode="complex-1d",
        branch_order=("complex",),
        normalization_state="storage-normalized",
        normalization_profile="agilent-fid-1d-complex-v1",
        applied_operations=(operation,),
        provenance=provenance,
        acquisition=result.acquisition,
        metadata=result.metadata,
        encoding=result.encoding,
        diagnostics=result.diagnostics,
    )
