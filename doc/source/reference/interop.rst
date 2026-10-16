nmrglue.interop
===============

.. automodule:: nmrglue.interop

This module is imported as ``nmrglue.interop``.  It is an optional, additive
layer: the historical ``format.read() -> (dic, data)`` reader APIs are
unchanged, and no SpectroChemPy, NDDataset, Pint or CSDM dependency is
imported.  The first supported profile is Bruker/TopSpin processed 1D data.

User Classes
^^^^^^^^^^^^

.. autosummary::
    :toctree: generated/

    ReadResult
    Axis
    Reference
    Component
    Diagnostic

User Functions
^^^^^^^^^^^^^^

.. autosummary::
    :toctree: generated/

    read_bruker_pdata
