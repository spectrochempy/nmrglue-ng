Interop profile conventions
===========================

See the :ref:`interop-profile-table` to select a reader and normalizer.
The sections below describe the layouts, calibrations and limitations
needed to interpret the results.

.. _interop-bruker-agilent-storage:

Bruker and Agilent storage layouts
----------------------------------

The storage readers label axes by array position. Their results leave the
physical axes uncalibrated and retain the parameters needed for reconstruction.

* **Bruker SER** returns scalar words in trace order, including padding
  to the 1024-byte-aligned trace stride. When present, ``nuslist`` and
  ``pulseprogram`` are retained as bytes in ``metadata["nuslist_raw"]``
  and ``metadata["pulseprogram_raw"]``.
* **Agilent/Varian FID** returns scalar words in block and trace order.
  It supports one or two headers per binary block and retains the block
  headers and any available ``procpar`` metadata.
* **Bruker 2D pdata** returns the available named planes at their stored
  scale, with disk tiles restored to rows and columns. Extracted strips
  use ``STSI`` for the stored size when present.

Agilent/Varian raw States 2D
----------------------------

.. code-block:: python

    import nmrglue as ng

    stored = ng.interop.read_agilent_fid_storage("acquisition.fid", states_only=True)
    states = ng.interop.normalize(stored)
    first, second = states.data
    print(states.branch_order, states.axes[0].values)

The States normalizer requires one raw trace per block, a single arrayed
``phase=[1, 2]``, and exactly ``2*ni`` blocks. Imaging layouts with
``seqcon`` use a different topology. It decodes interleaved
real/imaginary words and pairs even and odd traces into
``(branch, F1, F2)``. It retains the complex samples in acquisition order.
The two branches are labelled by position. Phase, sign and indirect Fourier
processing are separate operations.

Physical time axes use ``sw1`` (F1) and ``sw`` (F2) when available.
Physical observation frequencies come from ``sfrq2`` and ``sfrq``.
An unavailable transmitter frequency leaves the corresponding reference
unknown while the calibrated time grid remains usable.
``legacy_presentation=True`` preserves the historical public display
widths (``sw2``, ``sw``) and applies the explicit ``NS*NE`` divisor
recorded in the operations. This option retains the physical width and
observed-nucleus evidence in the acquisition metadata.

For a confirmed acquisition, use ``normalize(stored, quadrature="states")``
or ``quadrature="states-tppi"``. The normalized object preserves the stored
branches and uses physical time axes. Its ``quadrature_selection`` acquisition
entry records the mode and whether it came from the caller or a program
source. The NMRPipe FFT input convention is recorded separately. It
conjugates both branches and negates the second branch during processing.

With ``quadrature="auto"``, the normalizer checks an explicit
``pulse_program_source`` or a known ``<seqfil>.c`` beside the FID. The
catalogue matches the sequence name and source SHA-256. It currently
recognizes the audited OpenVnmrJ `NOESY source
<https://github.com/OpenVnmrJ/OpenVnmrJ/blob/0f6b0a4664def0cdf2ee9eb37cb2df7369f38ca3/src/psglib/NOESY.c>`_
as States-TPPI for a complete uniform grid starting with ``d2=0``.
Use the exact source associated with the acquisition. A missing or
unrecognized source leaves the selection undetermined.

Agilent/Varian raw TPPI 2D
--------------------------

The scalar storage reader can check this profile before reading samples
with ``read_agilent_fid_storage("acquisition.fid", tppi_only=True)``.
``normalize()`` selects the TPPI normalizer for ``phase=[3]``. A
qualified input has no additional arrayed parameter and exactly one raw
trace per block and per F1 increment (``arraydim=ni``, ``ni>=2``).
This profile requires uniform sampling and excludes a ``sampling.sch``
schedule.

The normalized matrix has shape ``(F1, F2)``, one complex F2 FID for
each F1 increment, in file order. The normalizer retains the TPPI
encoding and the acquired signs. Physical and compatibility time axes
follow the same conventions as the States profile above. For TPPI,
``1/sw1`` describes the stored F1 time step. The effective Fourier
bandwidth belongs to the processing convention. An undeclared F1
transmitter nucleus remains unknown, while the compatibility
presentation retains the historical decoupler label.

Agilent/Varian flat FID series
------------------------------

Use ``read_agilent_fid_storage(directory, series_only=True)`` to check
a flat series with explicit acquired-data and complex flags before
decoding samples. ``normalize()`` returns one
complex FID per row, in block and trace order, and records the binary
block and trace counts. The leading axis is a trace index. The direct
axis uses the acquired dwell time when available. No indirect time
calibration or interpretation of receiver channels is inferred.
The historical public presentation is opt-in.

JCAMP-DX real 1D spectra
------------------------

:func:`~nmrglue.interop.read_jcampdx_1d` reads a single real
``NMR SPECTRUM`` block in regular ``XYDATA`` form, including a spectrum
nested in a ``LINK`` block. The existing JCAMP-DX decoder applies
``YFACTOR`` to the intensities. The result records that factor and
retains the spectrum metadata.

.. code-block:: python

    import nmrglue as ng

    read = ng.interop.read_jcampdx_1d("epicatechin_1h.jdx")
    spectrum = ng.interop.normalize_jcampdx_1d(read)
    print(spectrum.axes[0].values[[0, -1]])  # approximately 4996.51, -998.69 Hz

The frequency axis runs from ``FIRSTX`` through ``LASTX`` over
``NPOINTS`` samples, in the declared Hz or ppm unit. Both endpoints are
sample coordinates. ``XFACTOR`` applies to abscissae encoded in the
table, and ``DELTAX`` records nominal spacing. The profile derives its
regular grid from the declared endpoints and checks the table’s line
anchors and DIF checkpoints. When present, ``.OBSERVE
FREQUENCY`` is recorded in MHz as metadata. The axis retains the
file's unit and direction. Normalization validates the description and
preserves the decoded intensities on the F2 axis.

This profile covers regular real 1D spectra. For a complex 1D FID in
NTUPLES form, see the profile below.

.. seealso::

   `JCAMP-DX for NMR <https://iupac.org/wp-content/uploads/2021/08/JCAMP-DX_NMR_1993.pdf>`_
   and the `epicatechin reference dataset <https://doi.org/10.57992/nmrxiv.p33>`_.

JCAMP-DX complex 1D FIDs
------------------------

:func:`~nmrglue.interop.read_jcampdx_fid` reads one ``NMR FID`` block
with regular NTUPLES tables for R and I. The decoder applies each
component's own ``FACTOR`` and the result preserves R + iI. When
provided, page labels identify the two component pages as N=1 and N=2.
Each page has one table within the NTUPLES block. The X column is in seconds. The first and last sample times come from
``FIRST`` and ``LAST``, and the sample count comes from ``VAR_DIM``.
The reader uses the X factor to check the line anchors in both tables.
The normalized dwell time is the endpoint span divided by the number
of intervals.

.. code-block:: python

    import nmrglue as ng

    read = ng.interop.read_jcampdx_fid("TESTFID.DX")
    fid = ng.interop.normalize_jcampdx_fid(read, conjugation="none")
    print(fid.axes[0].values)
    print(fid.acquisition["dwell_time_s"])

Select ``conjugation="conjugate"`` when the downstream convention
requires the opposite imaginary sign. The caller's choice is
recorded in the normalization operations.

JCAMP-DX real 2D spectra
------------------------

:func:`~nmrglue.interop.read_jcampdx_2d` reads a complete real NTUPLES
plane with one F2 PROFILE table per F1 PAGE and an explicit common F2
grid. It uses the existing decoder and applies the Y factor once.

.. code-block:: python

    import nmrglue as ng

    read = ng.interop.read_jcampdx_2d("betapinene_cosy_400mhz.jdx")
    spectrum = ng.interop.normalize_jcampdx_2d(read)
    print(spectrum.data.shape)  # (128, 3278) in (F1, F2) order

F1 follows the explicit page coordinates, including their written precision
and spacing. F2 is reconstructed from the common first and last sample
coordinates and the declared number of points. Each axis retains its
declared Hz or ppm unit and direction. The supported profile requires
monotonic page coordinates, unity F1 factor and a shared F2 grid.

The regression reference is the `β-pinene COSY from nmrXiv
<https://doi.org/10.57992/nmrxiv.p33>`_.

SIMPSON complex 1D FIDs
-----------------------

:func:`~nmrglue.interop.read_simpson_fid` reads a single-element complex
1D ``TYPE=FID`` block in native SIMPSON TEXT or BINARY form. The existing
decoder supplies the complex samples. The header specifies the sample
count ``NP`` and sweep width ``SW`` in Hz. Sample ``i`` is at
``i / SW`` seconds, starting at zero.

.. code-block:: python

    import nmrglue as ng

    read = ng.interop.read_simpson_fid("1d_text.fid")
    fid = ng.interop.normalize_simpson_fid(read, conjugation="none")
    print(fid.acquisition["dwell_time_s"])

Use ``conjugation="none"`` to preserve the stored sign or
``"conjugate"`` to reverse the imaginary sign explicitly. Both native encodings were checked against indexed exports
from SIMPSON 4.2.1.

SIMPSON complex 2D FIDs
-----------------------

:func:`~nmrglue.interop.read_simpson_fid_2d` reads a single-element
``TYPE=FID`` block in native TEXT or BINARY form. Samples are returned in
``(F1, F2)`` order with shape ``(NI, NP)``. Times are ``i / SW1`` on
F1 and ``j / SW`` on F2, in seconds.

.. code-block:: python

    read = ng.interop.read_simpson_fid_2d("2d.fid")
    fid = ng.interop.normalize_simpson_fid_2d(read, conjugation="none")

The normalized result reports sweep widths and dwell times in ``(F1, F2)``
order. The caller may request conjugation of the stored complex samples.
The indirect quadrature convention remains unknown. Both native encodings were checked against
the XYREIM export.

SIMPSON complex 1D spectra
--------------------------

:func:`~nmrglue.interop.read_simpson_spectrum` reads a single-element
``TYPE=SPE`` spectrum in native TEXT or BINARY form.
:func:`~nmrglue.interop.normalize_simpson_spectrum` preserves the complex
samples and their order on F2.

For zero-based sample index ``i``, the frequency is
``REF + (i / NP - 0.5) * SW`` Hz, with ``REF=0`` when absent. The axis
starts at ``REF - SW/2`` and increases in steps of ``SW/NP``. The
reference frequency ``REF`` falls on bin ``NP/2`` for even ``NP`` and
between two bins for odd spectra with at least two points.
The bin convention was verified against SIMPSON 4.2.1 XREIM exports.

SIMPSON complex 2D spectra
--------------------------

:func:`~nmrglue.interop.read_simpson_spectrum_2d` reads a single-element
``TYPE=SPE`` plane in native TEXT or BINARY form.
:func:`~nmrglue.interop.normalize_simpson_spectrum_2d` preserves the
complex samples in ``(F1, F2)`` order with shape ``(NI, NP)``.

For zero-based indices ``i`` and ``j``, the coordinates are
``REF1 + (i / NI - 0.5) * SW1`` on F1 and
``REF + (j / NP - 0.5) * SW`` on F2, in Hz. Each reference offset
defaults to zero when absent. The two axes follow the native XYREIM
bin convention, including odd point counts. The indirect quadrature
convention remains unknown.

Agilent 1D scan-count evidence
------------------------------

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

A consumer preserving the historical 1D public display can request
``normalize_agilent_fid(..., legacy_presentation=True)``. The option
applies the historical NS/NE divisor and records the conjugated-input
display FFT. The returned FID remains in canonical complex orientation.
Requested and completed counts remain acquisition evidence. The default
normalizer continues to expose unscaled samples. The reader's
``single_trace_only=True`` option rejects multi-block or multi-trace
files at the file header, before sample decoding.

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

By default normalization trims zero storage padding to ``TD/2``. Choose
``preserve_storage=True`` to keep verified padding in the signal, including
during DC removal and digital-filter correction. This matches the point
selection in the public TopSpin FID reader. The normalizer rejects nonzero
samples beyond TD, missing or inconsistent time calibration, real/QSEQ input
and prefiltered input. Prefiltered input may already contain padding in
its correction; read it again with the default uncorrected reader instead.

``remove_dc_offset=True`` subtracts the complex mean of the selected samples
before any digital-filter correction. This also removes genuine signal at
the carrier. Digital-filter removal is opt-in and uses the existing
time-domain correction with a truncated integer group delay.
``remove_digital_filter=True`` applies an explicit positive GRPDLY even at
``DECIM=1``. Choose ``remove_digital_filter="if-decimated"`` to match the
public TopSpin reader and record the correction as skipped at ``DECIM=1``.
When filtering, a positive scalar GRPDLY takes priority over the
DSPFVS/DECIM table. Unknown delays and
corrections leaving fewer than two points are rejected. No firmware clamping is
introduced by this profile. The trace records the original delay, its source,
parameters, truncation and number of removed points. The existing head/tail
folding behavior of the correction remains part of this explicitly chosen
recipe; this is not a claim of equivalence to an arbitrary vendor recipe.

The output conjugates the corrected or uncorrected acquired samples. This
explicit quadrature normalization aligns the centered negative-exponent DFT
with the standard NMR frequency orientation. With ``normalize_scan_gain=True``,
the corrected samples are divided by NS times RG. Missing factors default
individually to one. Nonpositive or nonfinite factors are rejected.
The operation records storage, acquired and output sizes, trimmed padding,
DC removal, filter state, scan/gain divisor and conjugation. Raw metadata
remains available unchanged.

The numeric frequency-axis descriptor uses sign -1, BF1 (MHz) as the
acquisition chemical-zero frequency and O1 (Hz) as the explicitly selected
``acquisition`` candidate offset. Missing BF1/O1 does not invent a reference.
This is an acquisition reference, not a replay of processed-data SF/OFFSET or
proof of a calibrated chemical standard. The relation
``SFO1 [MHz] = BF1 [MHz] + O1 [Hz] / 10^6`` follows the
`Bruker Avance frequency guide
<https://2210pc.chem.uic.edu/nmr/downloads/bruker/en-US/html/Avance%20Beginners%20Guide/en-US/371498891.html>`_.

To reproduce the public TopSpin reader's FFT presentation, pass the selected
acquisition and processing files to ``read_bruker_fid(acqus_files=...,
procs_files=...)``. Fields in ``acqus`` and ``procs`` take precedence over
their counterparts in ``acqu`` and ``proc``. Normalize with
``preserve_storage=True``. When the selected parameters provide the required
calibration, ``acquisition["fft_display_axis"]`` describes a decreasing grid
from center plus half the width to center minus half the width, with both
endpoints included. Its center is ``(SFO1 - SF) * 10**6`` Hz, its width is
``SW * SFO1`` Hz and its ppm conversion frequency is BF1 in MHz. It is a
presentation convention separate from the physical FFT bins.
``acquisition["fft_initial_phase"]``, when present, records the zero- and
first-order phase in degrees at the first bin. For N FFT points, its
multiplier at bin i is ``exp(+1j * radians(zero_order_deg +
first_order_deg * i / N))``. Neither descriptor changes the FID.

.. rubric:: Deferred FID preparation

When the correction options are left off, the FID remains uncorrected and
``acquisition["fid_preparation"]`` describes what a consumer can apply later.
The ``fid-preparation-v1`` descriptor declares the complex convention and the
returned sample count. Check that the time grid and sample count still
describe the acquisition before using it. The separate ``dc_offset``,
``digital_filter`` and ``scan_gain`` acquisition records state which
operations have already been applied.

For the qualified ``integer-shift-fold-trim`` method, rotate the canonical
samples left by ``left_shift_points``, add the reversed last ``fold_points``
samples of that rotated array to its first points, then discard the final
``discard_points`` samples. Apply optional complex-mean subtraction before
this operation and divide by the declared scan/gain divisor afterward.
The filter status is ``not-required`` for a non-decimated acquisition or
``unavailable`` when there is insufficient evidence for this method. Missing
or unsupported correction evidence does not prevent importing the FID.

Two local real acquisitions qualify QSIM/DQD, opposite int32 byte orders,
zero storage padding and both explicit/table group-delay paths. The consumer
compares unfiltered conversion, FFT and ppm axes with NMRPipe13. Filter removal
is separately tested against integer time-domain shift and head/tail folding;
bitwise agreement with NMRPipe's own digital-filter recipe is not claimed.
No SpectroChemPy dependency is added to this producer.

:func:`~nmrglue.interop.normalize_bruker_fid`

Normalized Bruker QF SER
------------------------

Use ``normalize_bruker_ser_qf()`` or generic ``normalize()`` with an
uncorrected QF result from ``read_bruker_ser()``::

   raw = ng.interop.read_bruker_ser("/path/to/acquisition")
   normalized = ng.interop.normalize(raw)

The normalized data contain real and imaginary F2 planes, in the stored
complex convention, with shape ``(2, F1, F2)``. F1 is real and both time
axes retain their physical order and calibrated sampling. This profile
requires a complete, uniformly sampled grid and excludes prefiltered or
otherwise corrected input. By default the output samples are uncorrected.
To match the public reader's requested acquisition corrections, pass
``remove_dc_offset=True``, ``remove_digital_filter=True``, or
``normalize_scan_gain=True`` explicitly. They subtract the complex mean
of each F2 trace, remove the time-domain filter on decimated acquisitions,
and divide by NS times RG, in that order. The F2 axis is shortened when
filtering truncates the samples, and the applied operations are recorded.
A fractional decimation rate requires a positive explicit group delay.
The corrected planes retain the stored complex convention.

With explicit processing files, ``fft_presentation=True`` also describes
the historical public FFT presentation for F1 and F2. Each stage uses a
negative-exponent FFT on conjugated input and an optional initial phase.
When calibrated, the display spans inclusive decreasing endpoints about
``(SFO1 - SF) * 10**6`` Hz with width ``SW * SFO1`` Hz and BF1 for ppm.
The descriptor leaves the stored samples and physical QF FFT grid unchanged.


Normalized Bruker States-TPPI SER
---------------------------------

Pass a complete Bruker SER storage result to the explicit
``normalize_bruker_ser_states_tppi()`` profile::

   stored = ng.interop.read_bruker_ser_storage("/path/to/acquisition")
   normalized = ng.interop.normalize_bruker_ser_states_tppi(stored)

For uniform States-TPPI with direct DQD, adjacent acquired traces form the
E1 and E2 branches. The normalized planes are RR, RI, IR and II in F1/F2
order. The aligned words beyond direct TD are storage padding. The F1
coordinate counts pairs, and F2 counts acquired complex points. The
alternation remains encoded for downstream processing. Nonuniform or
incomplete acquisitions are outside this profile.

Use ``preserve_storage=True`` when reproducing the public reader's aligned
trace length. The same optional per-trace DC removal, digital filter and
scan/gain corrections as for QF apply to the selected points in that order.
If the filter shortens the trace, F2 follows its new length. Neither
corrections nor storage-length selection apply indirect alternation.
When selected processing files are supplied to the storage reader,
``fft_presentation=True`` describes the public F2 transform and the F1
States-TPPI cross-pair transform, with each axis's display calibration and
initial phase.

Normalized Bruker echo/anti-echo SER
------------------------------------

Use ``normalize_bruker_ser_echo_antiecho()`` with the result of
``read_bruker_ser_storage()`` for complete uniform echo/anti-echo with
direct DQD. The normalized complex planes represent the first and second
stored traces of each pair. The profile leaves their reconstruction to
the consumer. A positive explicit GRPDLY is available in the digital-filter
record in points. The optional DC, filter and gain options operate on
individual traces before pairing, as in the States-TPPI profile.

Use ``echo_antiecho_only=True`` on the storage reader to check the profile
before decoding the traces. The optional ``fft_presentation=True`` on the
normalizer declares the public branchwise FFT convention, its initial
phases and the display calibration when the required parameters are
available. This descriptor leaves the stored branches unchanged.

Bruker 2D processed channel pairs
---------------------------------

The default 2D processed normalizer retains the four named planes at the
scale declared by the reader. Pass the acquisition status files to
``read_bruker_pdata_2d(..., acqus_files=...)`` and select
``axis_reference="acquisition"`` or ``axis_reference="processing"`` on
``normalize_bruker_pdata_2d()`` to request the public spectrum convention.
It returns ``S_R = 2rr + i*2ir`` and ``S_I = 2ri + i*2ii`` after dividing
both channels by RG. The input planes already include NC_proc scaling.
The selected axis convention controls ppm calibration independently of
the acquisition frequencies retained in the result.

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

Real nmrML 2D spectra
---------------------

Use :func:`~nmrglue.interop.read_nmrml_2d` for a real, densely sampled
processed ``spectrumMultiD`` plane with exactly two dimensions.
The nmrML 1.0.rc1 schema stores the direct ``xAxis``. Supply the
processed shape, indirect axis and binary order from the exporter or
an independent reference. The processed shape can differ from the
acquisition dimensions after zero filling or extraction.

.. code-block:: python

    import nmrglue as ng

    plane = ng.interop.read_nmrml_2d(
        "synthetic-2d-real.nmrML",
        shape=(3, 4),
        indirect_axis=(-100, 100, "Hz"),
        storage_order="x-fastest",
        axis_endpoint="last-point",
    )
    spectrum = ng.interop.normalize_nmrml_2d(plane)

The result has dimensions ``(F1, F2)`` and retains the stored intensities
as float32 or float64. With ``x-fastest``, adjacent values belong to
successive F2 positions. With ``y-fastest``, they belong to successive
F1 positions. Both axes retain their original direction and Hz or ppm
units. ``last-point`` includes the stated end coordinate on each axis.
``outer-edge`` excludes it. A document with several multidimensional
spectra requires a zero-based ``spectrum_index``.

The example uses the synthetic reference in ``tests/fixtures/nmrml/``.
The official HSQC example contains an acquisition, but its processed
array is empty.

Raw nmrML 2D acquisitions
-------------------------

:func:`~nmrglue.interop.read_nmrml_raw_2d` reads contiguous complex
traces from ``acquisitionMultiD``. The indirect count is the number of
stored traces. Supply ``direct_point_count="scalar"`` if the direct count
includes both real and imaginary words, or ``"complex"`` if it counts
complex samples.

The `official HSQC example <https://nmrml.org/examples/6/>`_ has a legacy
length field and zero padding after the zlib stream. Its compatibility
option verifies the original payload by checksum. The stored 256 × 2048
array matches the corresponding BMRB ``ser`` exactly. The BMRB acquisition
parameters and pulse program give an indirect evolution increment of
132.6 µs per pair. The sequence uses two d0 delays. The indirect sweep
width in nmrML and the increment recorded in the direct acquisition
status agree at this precision.

.. code-block:: python

    import nmrglue as ng

    stored = ng.interop.read_nmrml_raw_2d(
        "bmse000400-exp06.nmrML",
        direct_point_count="scalar",
        official_hsqc_compatibility=True,
    )
    acquisition = ng.interop.normalize_nmrml_raw_2d(
        stored, indirect_dwell_s=132.6e-6,
        confirm_adjacent_pairs=True,
    )

The normalizer accepts uniform echo/anti-echo acquisitions with confirmed
adjacent pairs and an explicit indirect dwell time. It returns complex
channels in ``(channels, F1, F2)`` order. The channel labels ``first`` and
``second`` describe stored pair order. Time coordinates are relative to
the first sample. F2 uses the declared direct sweep width. Recombination,
phase and digital filter correction belong to subsequent processing.

JEOL 1D complex FIDs
--------------------

:func:`~nmrglue.interop.read_jeol_fid` reads the two float64 storage
sections as R + iI, including padding. The qualified profile requires
a one-dimensional complex JDF with a ranged time axis in seconds and an
uncropped start.

.. code-block:: python

    import nmrglue as ng

    stored = ng.interop.read_jeol_fid("sample.jdf")
    fid = ng.interop.normalize_jeol_fid(stored, conjugation="none")

Normalization trims padding using the valid point count and checks the
time endpoints against ``x_sweep``. It requires ``x_sweep`` and ``x_freq`` in
hertz and checks ``x_freq`` against the header base frequency. It preserves
stored quadrature when
``conjugation="none"``. Select ``"conjugate"`` to match the sign convention
of the historical ``ng.jeol.read()`` reader. Digital filter parameters
remain available in the metadata for later processing. A finite carrier
offset with declared ppm units is available as ``acquisition["carrier_offset_ppm"]``.
With ``conjugation="conjugate"``, consumers can opt into
``legacy_presentation=True`` for the historical acquisition metadata and
the conjugated-input FFT convention. The legacy acquisition time, relaxation
delay and pulse width retain their decoded source units.

.. _interop-jeol-2d-storage:

JEOL 2D storage
---------------

:func:`~nmrglue.interop.read_jeol_2d_storage` reads standard tiled ``two_d``
float64 JDF files with X and Y axes. The supported header axis-type pairs,
in (X, Y) order, are ``(real, real)``, ``(complex, real)``,
``(real_complex, real_complex)`` and ``(complex, complex)``.
The array has shape
``(number_of_sections, words_per_section)``. Each row retains the file's
tile and word order, including any padding. Each component, named
``section-0``, ``section-1`` and so on, exposes the corresponding row.

.. code-block:: python

    import nmrglue as ng

    stored = ng.interop.read_jeol_2d_storage("sample_hsqc.jdf")
    print(stored.dimensions["grid_shape"])  # stored grid in (Y, X) order
    print(stored.dimensions["tile_shape"])
    print(stored.metadata["header"]["data_axis_type"][:2])

The grid and tile sizes describe each section. Tiles and the words within
each tile run with X varying fastest. ``valid_index_ranges`` records the
inclusive header offsets in X and Y. The decoded header and acquisition
parameters are available in ``metadata``. If an axis has a stored list,
``metadata["axis_lists_raw"]`` provides its original bytes by axis name.
In the reference HSQC and HMBC JDFs these bytes encode the sampled Y
times as big-endian float64 values in milliseconds, even though the
signal words are little-endian.

The storage axes index sections and words. Reconstructing physical axes,
untile operations, combining quadrature branches and interpreting a
non-uniform sampling schedule belong to a subsequent stage. The
``small_two_d`` format requires a separate storage profile.

JEOL 2D sampled-time normalization
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

:func:`~nmrglue.interop.normalize_jeol_2d` accepts two raw time-domain
layouts. The regular ``real_complex/real_complex`` layout, as found in the
reference COSY, yields one complex array in (F1, F2) order. The
``complex/complex`` layout with a listed Y axis, as found in the
reference HSQC and HMBC, yields an array in (channels, F1, F2) order.
The channels hold section pairs (0, 1) and (2, 3) in that order.

.. code-block:: python

    stored = ng.interop.read_jeol_2d_storage("sample_hsqc.jdf")
    fid = ng.interop.normalize_jeol_2d(stored, conjugation="none")
    print(fid.axes[0].values)  # acquired indirect times, in seconds
    print(fid.acquisition["nominal_shape"])  # full sampling grid

With ``conjugation="conjugate"``, ``legacy_presentation=True`` qualifies the
historical direct FFT for both qualified layouts. The result describes
F2 traces in ``(F1, F2)`` order, with sweep widths and carrier offsets in
the same order. For listed sampling it interleaves the section pairs,
negates the second pair and repeats each acquired F1 time for its two rows.
The nominal shape still counts physical increments. F1 quadrature remains
unqualified. The default presentation keeps the listed branches separate.

Both time axes follow the order of the stored points. The header's reversal flags
remain available in the metadata. A regular axis is calibrated with
its sweep width and checked against the header endpoints. A listed Y
axis is decoded from big-endian float64 milliseconds and checked
against the nominal grid given by ``y_sweep`` and ``y_orig_points``.
The supported listed schedules have strictly increasing grid indices.
For NUS acquisitions, the output contains only the sampled times.
Missing increments are left to a separate reconstruction step.

Choose ``conjugation="none"`` for R + iI or ``"conjugate"`` for R − iI
within each section pair. This is a direct-axis sign choice. The result
keeps the indirect channels separate and leaves their quadrature
interpretation to the consumer. The historical reader interleaves
the two channels and negates the second one for four-section files.

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

Normalize complete NMRPipe 2D grids
-----------------------------------

Use the same normalizer with a storage result to build calibrated axes
and split the stored components. For a complete frequency-domain file::

    stored = ng.interop.read_nmrpipe_2d_storage("complex.ft2")
    spectrum = ng.interop.normalize_nmrpipe_2d(stored)

For a known complete, uniformly sampled time grid stored in NMRPipe
States or pure TPPI layout, including a partially transformed file,
confirm its provenance::

    stored = ng.interop.read_nmrpipe_2d_storage("test.fid")
    acquisition = ng.interop.normalize_nmrpipe_2d(stored, confirm_time_grid=True)

Use that confirmation only when the time grid begins at the original
increment and any interleaved rows begin on the original real branch. A time-domain
extraction can retain the same size and relevant header fields while
shifting the start. Normalization checks for complete pairs, an unextracted
grid and checks each axis against ``TDSIZE`` or ``FTSIZE``. In the NMRPipe
States layout (``FD2DPHASE=2``), each time axis must be complex. This
flag describes the layout after conversion. Files
from States-TPPI or echo/antiecho acquisitions can use this layout when
the converter has arranged their samples into complex pairs. The
normalizer preserves those pairs and leaves sign alternation and
recombination to processing. Nonuniform sampling requires a separate
profile.

Pure TPPI (``FD2DPHASE=1``) stores one real sample per F1 time increment.
F1 uses ``i / (2 * SW)`` in seconds. The F2 time axis uses complex
samples at ``i / SW``. When NMRPipe transforms F1 with
`FT -real <https://spin.niddk.nih.gov/bax-apps/NMRPipe/ref/nmrpipe/ft.html>`_,
it can record the full transform size in ``FTSIZE`` while storing only
half that number of frequency points. An extraction can produce the same
header and shape. Use the storage reader for these files. The normalizer
requires the stored frequency point count to match ``FTSIZE``.

Axes follow file order in both orientations. Complex time coordinates
are ``i / SW`` in seconds and frequency coordinates decrease in steps of
``SW / N`` in Hz to the last-point ``ORIG``. Complex input produces a
leading channel axis. Channel names give the row branch followed by the
trace branch, in the order ``rr``, ``ri``, ``ir``, ``ii`` when both axes
are complex. With one complex axis only the corresponding two channels
are present. A real plane has no channel axis. These are stored components.
Acquisition sign and phase conventions remain in the header for later
processing.

Complete non-transposed raw QF files (``FD2DPHASE=0``) are supported when F1 is real and
F2 is complex. The caller must confirm the time grid. Both dwell times are
``1 / SW``. The normalized acquisition identifies this convention with
``acquisition["indirect_sampling"] == "qf"``.

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
