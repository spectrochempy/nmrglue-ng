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

Agilent 1D scan-count evidence
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

``read_agilent_fid`` and ``normalize_agilent_fid`` preserve decoded sample
values. They do not divide by scan counts or apply binary scale corrections.
The normalized storage profile is not a claim of physical amplitude calibration.

``result.acquisition['scan_counts']`` exposes:

* ``requested``: the scalar positive integer ``procpar.nt``, or ``None``;
* ``procpar_completed``: the scalar nonnegative integer ``procpar.ct``, or
  ``None``;
* ``block_completed`` and ``block_scales``: values from each parsed FID block;
* ``completed``: the count from a single valid block, only when the count
  evidence is valid and no known procpar count contradicts it;
* ``source``: ``fid.blockheader.ctcount`` when ``completed`` is known;
* ``status``: ``consistent``, ``block-only``, ``conflicting``, ``invalid``,
  ``ambiguous`` or ``unavailable``;
* ``invalid``: names of count fields that cannot be interpreted safely.

Malformed, negative, fractional or array-valued counts are not scalarized.
Zero is allowed for completed transients, not for requested transients.
Text counts are validated exactly, without an intermediate float rounding.
Requested ``nt`` is limited to the documented range 1 to 1e9; completed
counts must fit the nonnegative signed 32-bit block-counter range.
A completed count is not inferred from ``nt`` or from procpar alone. Missing or
multiple block headers leave it unknown. Inconsistent ``ct`` and ``ctcount``
are retained separately; ``completed`` and ``source`` are then ``None``.
Invalid count evidence also leaves ``completed`` unknown, even if another
field is valid. These states do not prevent raw sample reading.

Block headers are parsed even with the default ``read_blockhead=False``;
that option continues to control retention of the full headers in ``metadata``.
The existing ``NS`` and ``NE`` fields retain their literal ``ns``/``ne``
meaning; they are not silently replaced by ``nt`` or ``ctcount``.

This distinction follows the Agilent `VnmrJ 3.2 Command and Parameter Reference
<https://imserc.northwestern.edu/downloads/nmr-vj_cpr.pdf>`_ (printed pages
190 and 579): ``nt`` is requested, while ``ct`` describes completed transients
and can lag acquisition until processing. The binary definition in `VnmrJ
User Programming <https://www.agilent.com/cs/library/usermanuals/public/0199937900a.pdf>`_
(printed pages 275-276) associates ``ctcount`` with the individual FID.

Two hash-verified original 1D acquisitions have matching ``nt``, ``ct`` and
``ctcount`` values of 160 and 512, with block scale zero. Aborted acquisition,
conflicting counts and nonzero scale cases are synthetic regressions, not
additional real-acquisition validation. Receiver-gain correction, nonzero
binary scale restoration and physical amplitude normalization remain unqualified.
