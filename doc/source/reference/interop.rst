nmrglue.interop
===============

.. automodule:: nmrglue.interop

See :doc:`../tutorials/interop` for the relationship between readers, the
universal dictionary and interop, and for a worked example.

Import these entry points from ``nmrglue.interop``. The groups below organize
the reference by task. Existing import paths and signatures are retained.

Result types and diagnostics
^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. autosummary::
    :toctree: generated/

    ReadResult
    NormalizedAcquisition
    Axis
    Reference
    Component
    Diagnostic
    DIAGNOSTIC_CONTEXT_SCHEMA

Read stored planes and traces
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

These readers expose decoded storage and source metadata. See
:doc:`../tutorials/interop` for the distinction between storage and physical
axes.

.. autosummary::
    :toctree: generated/

    read_bruker_pdata_2d_storage
    read_bruker_ser_storage
    read_agilent_fid_storage
    read_nmrpipe_2d_storage

Read raw acquisitions
^^^^^^^^^^^^^^^^^^^^^

.. autosummary::
    :toctree: generated/

    read_agilent_fid
    read_agilent_states_2d
    read_bruker_fid
    read_bruker_ser

Read processed spectra and exchange files
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. autosummary::
    :toctree: generated/

    read_bruker_pdata
    read_bruker_pdata_2d
    read_nmrpipe_1d
    read_nmrpipe_2d
    read_nmrml_1d

Normalize a supported result
^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. autosummary::
    :toctree: generated/

    normalize_agilent_fid
    normalize_bruker_fid
    normalize_bruker_pdata
    normalize_bruker_pdata_2d
    normalize_nmrpipe_1d
    normalize_nmrpipe_2d
    normalize_nmrml_1d

Export an acquisition
^^^^^^^^^^^^^^^^^^^^^

.. autosummary::
    :toctree: generated/

    write_readresult_nmrpipe

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

:func:`~nmrglue.interop.normalize_bruker_fid`

Normalized Bruker processed 1D spectra (experimental)
-----------------------------------------------------

The processed normalizer consumes the existing descriptive reader::

   raw = ng.interop.read_bruker_pdata("/path/to/pdata/1", all_components=True)
   spectrum = ng.interop.normalize_bruker_pdata(raw)

The primary ``1r`` component remains real when it is the only component
supplied. If ``1i`` is supplied as well, the result is ``1r + 1j*1i`` with one
complex branch. Component association uses names, not tuple order. Missing
imaginary data are not fabricated; existing missing-component diagnostics are
retained. The normalized ``real-1d`` mode validates one real numeric branch.

The reader owns ``NC_proc`` storage decoding. Normalization preserves its
``scale_data`` state and exponent in the operation trace and never reapplies
scaling, RG/NS normalization, FFT, phasing or chemical referencing. Missing or
contradictory scaling evidence is rejected. ``scale_data=False`` retains the
unscaled storage values explicitly; it is not a physical amplitude calibration.

The normative supplied axis remains
``frequency_hz[i] = OFFSET*SF - i*SW_p/N``. Its processing reference is SF (MHz),
not acquisition BF1/SFO1. No new frequency sign or acquisition-reference recipe
is guessed for a processed spectrum. Calibration, primary/component shapes,
unique names and finite data are checked before normalization.

This first strict profile requires the complete SI-matched spectrum. SI must
equal N, supplied STSI must equal N, and supplied STSR must be zero. Extracted,
truncated and unknown-calibration processed grids are not qualified. These
restrictions apply to the new normalizer only; descriptive readers are unchanged.

The consumer can preserve the already-frequency-domain spectrum, convert its
coordinate between Hz and ppm through the supplied reference, and record
explicit additional processing. It must not repeat acquisition transforms.
Two real original datasets (SCP TopSpin and the public nmrML tomato example)
qualify real/complex and scaled/unscaled variants, source preservation and
SCP persistence, with separately configured NMRPipe component/grid comparisons.

:func:`~nmrglue.interop.normalize_bruker_pdata`

Normalized NMRPipe spectra (experimental)
-----------------------------------------

Read a single complete, already transformed 1D spectrum through the historical
NMRPipe reader and the neutral contract::

   raw = ng.interop.read_nmrpipe_1d("spectrum.ft1")
   spectrum = ng.interop.normalize_nmrpipe_1d(raw)

Real data remain real; complex data retain both components without conjugation.
No FFT, phase, scan/gain normalization or chemical recalibration is performed.
The frequency grid is in Hz, with ``f[i] = ORIG + (N - 1 - i) * SW / N``:
NMRPipe ORIG is the **last** point, not the first. OBS supplies the MHz reference
for ppm conversion. CAR is preserved as metadata, not used instead of ORIG.

The current profile requires FDDIMCOUNT=1, direct dimension F2, no transposition,
FTFLAG=1, consistent quadrature flags, positive SW/OBS, finite samples and an
exact payload matching FDSIZE. Extracted grids (nonzero FDF2X1/FDF2XN), FIDs,
multidimensional files, streams supplied in memory, and missing or ambiguous
calibration are rejected. Historical ``ng.pipe.read`` remains available for
broader low-level reading; that availability is not normalized qualification.

NMRPipe stores float32 components. Existing rounding cannot be recovered, and
header frequencies are float32 too. Stored scaling, phase and reference choices
are preserved rather than independently validated as chemically correct.
The normalized producer does not recover original vendor parameters or digital
filter history. It is not a universal converter of native processed formats.

Validation covers synthetic little/big-endian real/complex payloads and local
real Agilent/Bruker NMRPipe reference FIDs transformed by external NMRPipe 13.0,
including real spectra obtained by its zero-phase PS/DI operation. Historical
reference provenance and the current external transformation are distinct;
no fresh native vendor-to-NMRPipe conversion is claimed. Numerical tests compare
raw output words and the documented header formula; their shared format
assumptions are not an independent proof of chemical referencing.

:func:`~nmrglue.interop.read_nmrpipe_1d`

:func:`~nmrglue.interop.normalize_nmrpipe_1d`

Explicit nmrML 1D bridge
------------------------

See :doc:`../nmrml_1d` for examples and grid conventions.

:func:`~nmrglue.interop.read_nmrml_1d`

:func:`~nmrglue.interop.normalize_nmrml_1d`

.. _interop-nmrpipe-2d-storage:

NMRPipe 2D storage
------------------

Read stored traces from a single two-dimensional NMRPipe file::

    stored = ng.interop.read_nmrpipe_2d_storage("test.fid")
    print(stored.dimensions["axis_order"], stored.domains, stored.encoding)
    print(stored.dimensions["row_layout"], stored.data.shape)

The filename extension is immaterial. The header identifies the file order
(F1, F2 or F2, F1), whether each axis is transformed and whether it stores
real or complex points. The reader accepts either byte order and checks the
exact payload size against the header. It supports the standard real and
complex quadrature flags (1 and 0).

``dimensions["stored_shape"]`` counts the scalar float32 words on disk.
``dimensions["shape"]`` describes the decoded array. For complex traces,
NMRPipe stores the real vector followed by the imaginary vector in each
row, and the historical reader combines them into a complex64 array.
When the row axis is complex, ``dimensions["row_layout"]`` reports
``interleaved-real-imaginary``. This describes the storage convention.
An extraction can begin on either branch or contain an incomplete pair,
and the header may give no indication of the starting branch. The reader
returns the rows in file order. When only the row axis is complex,
NMRPipe records the row count as complex points, so the file contains
twice as many rows as ``FDSPECNUM``.

The result has a single ``stored-traces`` component. Its axes describe
the file labels and domains without a calibrated coordinate grid.
``metadata`` retains the header, including ``FD2DPHASE`` and per-axis
acquisition sign fields, for later interpretation. The reader applies
no sign corrections, branch recombination or Fourier transformation.

See the `NMRPipe format reference
<https://spin.niddk.nih.gov/bax/software/NMRPipe/NMRPipe.html>`_ and the
format notes in NMRPipe's ``fdatap.h``.

Real NMRPipe 2D spectra (experimental)
--------------------------------------

Use the explicit reader and normalizer for a complete real frequency/frequency
plane stored as one NMRPipe file::

    plane = ng.interop.read_nmrpipe_2d("spectrum.ft2")
    spectrum = ng.interop.normalize_nmrpipe_2d(plane)

The data, axes and dimension names follow file order (F1, F2 or F2, F1).
Each decreasing frequency axis uses its own SW and last-point ORIG in Hz.
OBS provides its observation frequency in MHz. Samples retain their float32
values. The real 2D profile accepts both byte orders and both orientations.
For stored traces from mixed domains or complex planes, see
:ref:`interop-nmrpipe-2d-storage`. This interface describes the stored spectrum and
leaves interpretation and processing to the caller.

Complete Bruker processed 2D planes (experimental)
--------------------------------------------------

Read a complete int32 Bruker processed frequency/frequency dataset::

    raw = ng.interop.read_bruker_pdata_2d("experiment/pdata/1")
    spectrum = ng.interop.normalize_bruker_pdata_2d(raw)

The reader preserves the four stored planes named ``2rr``, ``2ri``,
``2ir`` and ``2ii``. The primary array is ``2rr``. The normalizer
stacks the four real planes in that order along a leading channel axis.
Each plane is indexed in F1, F2 order. Frequency grids in Hz use the
processing parameters in ``proc2s`` and ``procs``, respectively.

The default applies the storage factor ``2**NC_proc`` from ``procs``
once. Use ``scale_data=False`` to preserve stored int32 values. The
profile requires complete, unextracted grids, forward processing status
(``FT_mod=4`` or ``6``) and exact file sizes.
The file names identify storage components and leave processing choices
to the consumer.
