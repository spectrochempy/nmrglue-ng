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

Normalized frequency-axis descriptor (experimental)
---------------------------------------------------

The optional ``NormalizedAcquisition.acquisition['frequency_axis']`` mapping
separates format interpretation from consumer processing. Schema
``normalized-frequency-axis-v1`` declares:

* ``bin_sign``: either -1 or +1, relative to the negative-exponent centered DFT;
* ``reference_frequency_mhz``: positive chemical-zero frequency, or ``None``;
* ``reference_enabled``: ``False`` disables reference application, ``True``
  permits it, and ``None`` means the source has no explicit enable flag;
* ``offsets_hz``: a mapping of opaque candidate labels to finite offsets.

For a selected offset ``c`` and width ``SW``, the physical frequency at bin
``i`` of a complete N-point DFT is
``c + bin_sign * (i - N//2) * SW/N``. Divide by the chemical-zero frequency in
MHz to obtain ppm. Consumers must select a candidate explicitly and must not
infer a convention from origin, profile name or raw vendor metadata.

The Agilent normalization profile declares sign -1. It exposes ``rfl-rfp`` as
``SW/2-rfl+rfp`` and ``sfrq-reffrq`` as ``(sfrq-reffrq)*1e6`` when evidence is
available. It uses ``reffrq`` for the chemical-zero frequency and permits the
explicit ``refpos=0`` flag; disabled or ambiguous flags disable referencing.
Missing flags remain unknown. This describes candidate evidence, not a choice
of experimentally correct chemical standard. The historical carbon acquisition
has conflicting candidates (0 versus 281.6 Hz), which remain separate.
The convention follows the VnmrJ reference equations and NMRPipe var2pipe sign
behavior qualified in the consumer's two-file numerical comparison. No FFT,
conjugation, scaling or reference is applied by normalization; the raw
``ReadResult`` remains unchanged. Existing normalized fields remain compatible.

The reference formulas are documented in the `VNMR Getting Started manual
<https://www2.chem.wisc.edu/~cic/nmr/Guides/Varian_VNMR_manuals/VNMR_Getting_Started--VNMR_6_1C_01-999160-00_rev_A0800--0199916000a.pdf>`_
and the `VnmrJ parameter reference
<https://imserc.northwestern.edu/downloads/nmr-vj_cpr.pdf>`_ (reffrq, rfl, rfp).

Arrayed ``rfl``, ``rfp``, ``reffrq`` or ``sfrq`` cannot establish a scalar
reference candidate. Multiple ``sw`` values are rejected by the normalized 1D
profile because they cannot establish one calibrated time grid. The raw reader
API remains unchanged.

Normalized Bruker complex 1D FIDs (experimental)
------------------------------------------------

``normalize_bruker_fid`` accepts an uncorrected ``read_bruker_fid`` result
with complex QSIM or DQD encoding::

   raw = ng.interop.read_bruker_fid("/path/to/acquisition")
   normalized = ng.interop.normalize_bruker_fid(raw, remove_digital_filter=True)

The reader is kept unchanged. Normalization trims zero storage padding to the
complex acquisition size ``TD/2`` before optional filter removal. It rejects
nonzero samples beyond TD, missing or inconsistent time calibration, real/QSEQ
input and prefiltered input. Prefiltered input may already contain padding in
its correction; read it again with the default uncorrected reader instead.

Digital-filter removal is opt-in and uses the existing time-domain correction
with a truncated integer group delay. A positive scalar GRPDLY takes priority;
otherwise DSPFVS/DECIM must identify a known table entry. Unknown delays and
corrections leaving fewer than two points are rejected. No firmware clamping is
introduced by this profile. The trace records the original delay, its source,
parameters, truncation and number of removed points. The existing head/tail
folding behavior of the correction remains part of this explicitly chosen
recipe; this is not a claim of equivalence to an arbitrary vendor recipe.

The output conjugates the corrected or uncorrected acquired samples. This
explicit quadrature normalization aligns the centered negative-exponent DFT
with the standard NMR frequency orientation; samples are not RG/NS scaled.
The operation record preserves storage/acquired/output sizes, trimmed padding,
conjugation and filter state. Raw metadata remains available unchanged.

The numeric frequency-axis descriptor uses sign -1, BF1 (MHz) as the
acquisition chemical-zero frequency and O1 (Hz) as the explicitly selected
``acquisition`` candidate offset. Missing BF1/O1 does not invent a reference.
This is an acquisition reference, not a replay of processed-data SF/OFFSET or
proof of a calibrated chemical standard. The relation
``SFO1 [MHz] = BF1 [MHz] + O1 [Hz] / 10^6`` follows the
`Bruker Avance frequency guide
<https://2210pc.chem.uic.edu/nmr/downloads/bruker/en-US/html/Avance%20Beginners%20Guide/en-US/371498891.html>`_.

Two local real acquisitions qualify QSIM/DQD, opposite int32 byte orders,
zero storage padding and both explicit/table group-delay paths. The consumer
compares unfiltered conversion, FFT and ppm axes with NMRPipe13. Filter removal
is separately tested against integer time-domain shift and head/tail folding;
bitwise agreement with NMRPipe's own digital-filter recipe is not claimed.
No SpectroChemPy dependency is added to this producer.

.. autofunction:: nmrglue.interop.normalize_bruker_fid
