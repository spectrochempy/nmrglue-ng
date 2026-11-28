Coming from nmrglue?
====================

What changes beyond installation
--------------------------------

nmrglue-ng continues the original project and preserves its history and
attribution. Alongside maintenance and additional readers, it corrects
defects in the original I/O, processing and analysis code. Keeping the same
``import nmrglue`` does not mean every numerical result stays unchanged.

For example, fixes address JCAMP endpoint coordinates and nD FID detection,
JEOL dimension order, Bruker low-memory trace addressing and float64 values,
integration uncertainty scaling, and several NMRPipe transform conventions.
Structured interop results additionally expose axes, components, acquisition
domains and applied normalization explicitly. These profiles have bounded
coverage; decoding a format does not automatically qualify its complete
processing workflow.

Use the :doc:`release notes <whats-new>` to check availability in your installed
version. Items below marked as development changes are not claims about an
earlier release. Record your previous environment and compare the workflows
that matter to you against known data before replacing it.

Install in a separate environment
---------------------------------

Install ``nmrglue-ng`` in a new environment using the :doc:`installation guide
<install>`. Both distributions provide the same ``nmrglue`` Python package,
so use one distribution per environment.

Keep ``import nmrglue as ng`` and your existing format reader calls.
For example, ``ng.pipe.read(path)`` still returns the header dictionary and
the data array. If you want to try a complete workflow, use the downloadable
FID and notebook in :doc:`getting-started/index`.

Check results affected by fixes
-------------------------------

* Development builds with the endpoint-covariance fix return ``None`` for
  covariance when a fitted parameter reaches a bound. The transformation
  is singular at an endpoint even if its floating-point derivative is
  nonzero. Reassess earlier uncertainties for such fits: numerical and
  analytic Jacobians could yield misleadingly different covariance values.
  Lineshape parameter errors are also unavailable; fitted values and
  interior covariance calculations retain their behavior. This does not
  qualify uncertainty estimates arbitrarily close to a bound.

* Development builds with the automatic-quadrature fix preserve the real
  channel and orthogonalize and balance the imaginary channel using an
  amplitude gain. Reprocess spectra corrected with ``qart_auto`` or
  ``pipe_proc.qart(auto=True)``; earlier output could introduce imbalance
  even for ideal data. Recompute stored ``gram_schmidt`` coefficients, which
  now match ``qart``'s amplitude/leakage convention. Empty, real-only,
  nonfinite or dependent channels raise ``ValueError``. Manual ``qart``
  coefficients retain their meaning. Automatic estimation can still be
  unsuitable for signals symmetric about the spectral center.

* Development builds with the bounded analytic-Jacobian fix evaluate the
  residual and its derivatives in consistent transformed coordinates.
  Refit models that used ``leastsqbound`` with both ``bounds`` and ``Dfun``;
  earlier successful convergence codes could accompany incorrect parameters.
  Numerical-Jacobian fits and fits without bounds retain their behavior.

When comparing results with an older environment, record both package
versions. Use the checks below for workflows you rely on, and consult the
:doc:`release notes <whats-new>` for all changes between those versions.

* Development builds with the distribution-baseline pipeline fix interpret
  ``wd`` as a positive integer half-width: up to ``2*wd+1`` centered samples.
  Signal segments use both locally averaged boundaries and the final smoother
  is a clipped mean, following the non-diffusion-edited published routine.
  Earlier results used misaligned windows and different interpolation and
  smoothing; recompute affected corrections and derived integrals. Flat and
  short spectra now work. Invalid, masked or wholly signal-classified inputs
  raise ``ValueError``. Broad weak peaks can still be removed as background;
  inspect the estimated baseline before quantitative use.

* Development builds with the real-input complex-FFT fix promote real
  arrays to a complex result in ``fft``, ``ifft`` and their positive-exponent
  and normalized variants. Earlier calls discarded the imaginary component
  with a warning, so transform/inverse round trips could lose information.
  Recompute affected transforms and downstream spectra. To select only the
  real component, use ``.real`` explicitly after the transform. Complex-input
  behavior and the separately packed real transform ``rft`` are unchanged.

* Development builds with the JMOD sine-phase fix rotate complex data by
  -90 degrees when the effective modulation offset is zero, matching NMRPipe.
  Re-run affected JMOD processing and downstream spectra; nonzero offsets
  and the lower-level ``proc_base.jmod`` window retain their behavior.

* Development builds with the fitting-covariance fix restore
  ``leastsqbound(full_output=True)`` and lineshape ``error_flag=True`` with
  current NumPy. Covariance accounts for MINPACK pivot indexing and the bound
  transformation in external parameter units. Recompute earlier reported
  uncertainties when comparing environments. A zero transformation derivative
  at a bound leaves covariance unavailable; the fit parameters remain usable
  subject to the solver's convergence status.

* Development builds with the HT automatic-mode fix preserve the requested
  ``zf`` value outside mirror mode. ``auto=True`` no longer adds padding
  implicitly, matching NMRPipe 13. Recompute affected Hilbert transforms of
  non-power-of-two arrays; pass ``zf=True`` to request the former padding.

* Development builds with the real-input TP nohyper fix represent the new
  complex last axis as adjacent real/imaginary pairs and record its true size.
  The returned array can therefore become complex and have half as many last
  axis elements. Re-run affected transposes and exports; earlier files could
  mix quadrature components or carry an incorrect real-axis size.

* Development builds with the slow positive-threshold segment fix return one
  segment per detected peak, including an empty list when no peak is present.
  Calls with ``find_segs=True`` previously failed or returned an empty tuple;
  re-run workflows that could not complete this segmentation.

* Development builds with the integration-window fix clip converted bounds
  to the available data instead of interpreting negative indices from the
  end of the spectrum. Uncertainty counts the actual selected bins. Recompute
  integrals and uncertainties whose limits exceeded the data domain; empty
  noise windows now raise an error rather than returning NaN estimates.

* Development builds with the metadata-comparison fix reject missing keys
  regardless of dictionary argument order. Review earlier validation results
  that used ``misc.isdicsimilar`` or ``pair_similar``: metadata present only in
  the second dictionary could previously pass unnoticed. Explicitly ignored
  NMRPipe display fields remain excluded when requested.

* Development builds with the linear-baseline edge fix use the available
  samples when a node's averaging window reaches a trace boundary. Re-run
  baselines and derived integrals if earlier edge windows produced NaN values.

* Development builds with the ACME input-validation fix reject constant,
  nonfinite or insufficient spectra before optimization. Earlier calls could
  return initial phases after invalid score divisions; treat those outputs
  as unvalidated. Custom scoring functions retain their own input contract.

* Development builds with the iterative-noise fix update the median after
  every rejection step in distribution-based baseline correction. Recompute
  affected noise thresholds and downstream baselines when comparing results.
  This fix does not qualify the complete baseline interpolation algorithm.

* Development builds with the negative-threshold segmentation fix estimate
  negative peak widths and signed volumes from samples below the threshold.
  Re-run affected threshold peak picking; these paths previously selected
  empty or incorrect segments. This does not qualify the separate legacy
  slow-window iterator implementation.

* Development builds with the constant-baseline fix use the actual selected
  sample count at ``cbf(last=100)``. Recompute affected baselines and derived
  integrals if the previous residual offset mattered. Intermediate percentages
  retain their historical sample selection, including one trailing sample at
  zero percent. Empty traces and percentages outside 0--100 are rejected.
* Development builds with the Spinsolve domain fix identify ``spectrum.1d``
  and ``spectrum_processed.1d`` as frequency-domain in ``guess_udic`` when the
  dictionary comes from ``read``. Avoid applying another FFT to those spectra.
  Legacy dictionaries without the selected filename keep their previous
  time-domain default. Calibration and the stored coordinate array are unchanged.

* Development builds with the NUS validation fix reject repeated or out-of-grid
  increments, inconsistent trace counts and invalid acquisition or quadrature
  permutations. Check earlier expansions for overwritten or misplaced FIDs.
  Combine repeated acquisitions explicitly before calling ``expand_nus``.
  Narrow-integer NumPy coordinates are also expanded without scalar overflow;
  re-expand earlier grids if those coordinate dtypes were used.
* Development builds with the Bruker integer-conversion fix scale very small
  and large signals into the documented integer range instead of losing them
  to truncation or overflow. Nonfinite inputs are rejected and the conversion
  helper no longer modifies its input. Check earlier ``write_pdata`` exports
  made with automatic scaling. This normalization sets an arbitrary intensity
  scale; it does not infer or update ``NC_proc`` for absolute calibration.

* Development builds with the nD JCAMP-DX FID recognition fix return pages
  for ``DATA TYPE=nD NMR FID`` instead of reporting no data. For these FIDs,
  ``guess_udic()`` now identifies the direct dimension as time-domain and
  computes its spectral width as ``(size - 1) / (LAST - FIRST)`` in seconds.
  Recompute direct-axis metadata previously inferred as frequency-domain.
  This does not qualify indirect quadrature or multidimensional processing.

* Since nmrglue-ng 1.0.0, axes reconstructed from descending processed
  JCAMP-DX spectra preserve the declared first and last coordinates.
* Since nmrglue-ng 1.1.1, integration noise estimates use the same bin width
  or volume as the integral. This can change uncertainty estimates.
* Since nmrglue-ng 1.2.2, ``ng.proc_lp.cadzow()`` processes each row of a 2D
  array. Earlier versions returned the input unchanged for 2D arrays.
  Re-run Cadzow if you need to compare previously processed 2D results.

* Since nmrglue-ng 1.2.3, Varian reads warn and retain the complete flat
  trace matrix when declared multidimensional geometry conflicts with the
  binary data. Check the warning before treating the leading axis as a
  calibrated indirect dimension. Use ``legacy_layout=True`` if a consumer
  expects the historical singleton-trace presentation.
* Since nmrglue-ng 1.2.3, integration uncertainty remains nonnegative
  after normalization against a signed reference integral. A zero
  reference integral raises an error. Recompute previously normalized
  uncertainties when comparing results.
* Since nmrglue-ng 1.2.3, peak-minima automatic phasing evaluates the
  samples available when a scoring window reaches a spectrum boundary.
  Re-run automatic phasing if edge peaks affected the earlier result.

* Since nmrglue-ng 1.2.4, SIMPSON XYREIM reads validate the complete
  coordinate grid. The axes follow first occurrence order, and every sample
  is placed at its coordinate pair. Use ``legacy_layout=True`` to reproduce
  the ascending axes of historical SpectroChemPy imports. Incomplete grids
  and truncated TEXT data raise an error.

* Since nmrglue-ng 1.3.0, ``autops(data, "acme")`` rejects multidimensional
  arrays. Earlier versions scored differences along the first axis while
  applying phase along the last. Recompute affected results on individual
  traces or use a custom score with an explicit multidimensional convention.
* Since nmrglue-ng 1.3.0, the universal dictionary for JEOL 2D data follows
  the array order, with indirect F1 on rows and direct F2 on columns.
  Rebuild the axes and check any peak coordinates or exports based on the
  earlier metadata order.
* In development builds with the Tecmag axis fix, unit conversion recovers
  the referenced frequency axis for even-length processed 1D TNT
  spectra stored in descending TNMR order with valid reference metadata.
  Rebuild the axis and compare peak positions with the referenced TNMR
  spectrum. See :doc:`release notes <whats-new>` for release availability.

* In development builds with the Bruker strip fix,
  ``bruker.guess_udic(..., strip_fake=True, pdata=True)`` retains the
  calibrated axis derived from processing parameters. Use ``pdata=True``
  to select those parameters when acquisition parameters are also present.
  Rebuild the axis and check previously reported peak positions and spectral
  widths.
* Development builds with the compact JCAMP-DX fix can read 2D NTUPLES
  with signed axis factors and truncated F2 line anchors. Re-import affected
  exports and check peak positions against the source. Re-read XYW and XYM
  tables if downstream results depend on peak widths or multiplicities.
* Development builds with the interop mask fix reject arrays with active
  NumPy masks.
  Check earlier results if an input mask might have been discarded. Resolve
  the missing values explicitly before passing data to interop.

* Development builds with the JEOL 2D fixes retain both ends of the valid
  acquisition window, preserve complete indirect quadrature pairs, and read
  regular float32 storage. Uniform complex/complex acquisitions can be
  normalized as two branches with calibrated time coordinates. Re-import
  affected JDF files and check array shapes, time axes and downstream
  transforms. The legacy presentation retains its historical signs.
* Development builds with the JEOL parameter fix recover the final acquisition
  parameter when the declared block confirms an inclusive last index. Re-read
  affected JDF files before using previously missing acquisition metadata.

These versions describe when the fixes landed in nmrglue-ng. For a dated
upstream reference, see the
`nmrglue source at cd0c2c9 (8 October 2026)
<https://github.com/jjhelmus/nmrglue/tree/cd0c2c9d1cac4f1125a89dbe6ecdcd8ca194b59d>`_.

Increasing JCAMP-DX frequency axes
----------------------------------

For processed JCAMP-DX spectra with increasing Hz or ppm coordinates,
use ``uc_from_udic()`` or ``glue.make_uc()`` to reconstruct coordinates
in sample order. Check that the first and last coordinates agree with
the source before comparing peaks or exporting the spectrum.
See :ref:`jcampdx-increasing-frequency-axes` for compatible exports and
details of the axis reconstruction.

When to use interop
-------------------

Keep using format readers and the universal dictionary for existing
processing and conversion workflows. Use the optional ``nmrglue.interop``
layer when another library needs named components, axes, or explicit
storage conventions. Coverage varies by format and profile.

The first published profile, introduced in nmrglue-ng 1.1.0, reads
processed Bruker/TopSpin 1D data. The
`stable interop reference
<https://nmrglue-ng.readthedocs.io/stable/reference/interop.html>`_ describes
the API available in the latest release. The :doc:`interop guide
<tutorials/interop>` and :ref:`interop-profile-table` on this site describe
the API for this documentation version.

Raw JCAMP-DX and two-dimensional processing
-------------------------------------------

The legacy reader's ``show_all_data=True`` returns all decoded R/I pages;
``guess_udic()`` still describes only the direct dimension. This is useful
for inspecting storage, but does not establish indirect quadrature.

nmrglue-ng 1.4.0 introduced the explicit ``jcampdx-fid-2d`` interop profile
for regular ``T1,T2,R,I`` NTUPLES with one real/imaginary pair per increment.
Normalization requires both a declared non-phase-sensitive acquisition
scheme and caller confirmation ``quadrature="qf"``, plus an explicit
complex-sign choice. The output can use the SpectroChemPy NMR plugin's
existing QF processing path; no experiment-name inference is needed.

This profile retains time-domain samples and axes. It applies no digital
filter correction, FFT, phasing or chemical-shift reference.

nmrglue-ng 1.5.0 additionally normalizes declared echo/anti-echo with
simultaneous DQD acquisition. Choose ``quadrature="echo-antiecho"``, confirm
``confirm_adjacent_pairs=True`` and supply ``indirect_dwell_s`` from validated
acquisition provenance. The stored T1 row grid alone does not establish the
time between physical pairs. Normalization preserves the first and second
complex traces as two channels; reconstruction belongs to processing.
Any recorded group delay remains unapplied and can be used explicitly by
the plugin's common processor. The EPFL HSQC qualification covers four
TopSpin compression modes, native Bruker parity and signed NMRPipe planes,
with and without phase-domain digital-filter correction. This does not
establish absolute phase or chemical-shift references for every acquisition.
nmrglue-ng 1.5.0 also accepts declared ``quadrature="states"`` or
``quadrature="states-tppi"`` under the same explicit pair/dwell/DQD conditions.
They expose four stored planes (rr, ri, ir, ii). States-TPPI alternation is
recorded as declared but not applied, so processing applies it once. The
plugin's explicit ``conversion_profile`` must agree with the declared mode.
Native acquisitions exported by TopSpin in four compression modes reproduce
their native channels and common FFT results; matrix DFTs and synthetic
NMRPipe checkpoints qualify the signed components. Reading does not establish
an absolute experimental phase or chemical-shift reference.
Changing the JCAMP compression does not change that physical scope.


Real 2D JCAMP-DX spectra exported by TopSpin
--------------------------------------------

nmrglue-ng 1.5.0 accepts ``VAR_DIM=(ny,nx,nx)`` exports in
``jcampdx-spectrum-2d``: the dependent dimension describes one page.
Positive coordinate factors are accepted for this layout. F1 PAGE values
are physical coordinates and are not multiplied by F1 FACTOR; endpoint
agreement accounts for their written decimal precision. F2 remains the
declared FIRST/LAST grid, checked against all line anchors.

Only the exported real plane is returned. In the qualified TopSpin 4.5.0
examples, even RSPEC+ISPEC exports contain F1,F2,Y with no imaginary pages.
The real values reproduce unscaled native ``2rr`` counts. YFACTOR is applied,
but vendor ``NC_proc``, scan/gain scaling and chemical-shift references are
not inferred. Retain native 2ri/2ir/2ii separately when their information is
needed. These frequency-domain data are not raw FIDs and must not receive
another Fourier transform. Reimporting a previously rejected file is sufficient;
existing supported layouts keep their behavior.

Explicit ppm calibration of processed 2D spectra
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

nmrglue-ng 1.5.0 accepts ``axis_reference`` in ``normalize`` for
``jcampdx-spectrum-2d`` when both declared axes are in Hz. Supply both axes:

.. code-block:: python

   referenced = ng.interop.normalize(result, axis_reference={
       "F1": {"reference_frequency_mhz": 100.0, "point_index": 0,
              "ppm": 12.0, "source": "processing"},
       "F2": {"reference_frequency_mhz": 400.0, "point_index": 0,
              "ppm": 10.0, "source": "processing"},
   })

Here ``point_index`` is zero-based and identifies a known point in each
axis. The conversion is ``ppm[j] = ppm_anchor + (Hz[j] - Hz_anchor) / MHz``.
These illustrative numbers must be replaced with the experiment's references.
For a full native Bruker processed grid, use ``proc2s`` for F1 and ``procs``
for F2: ``SF`` supplies MHz and ``OFFSET`` supplies the ppm at index zero.
The resulting native grid is ``OFFSET - j * SW_p / (SF * SI)``; the bin width
uses ``SI``, not ``SI - 1``. Acquisition ``SFO1`` can differ from processing
``SF`` and is not substituted automatically.

Data values and sample order are unchanged. Reference provenance is retained
in the normalized acquisition and its operations. ``source`` defaults to
``unknown``; it can also be ``processing`` or ``acquisition``. Missing axes,
invalid or nonfinite references, and already ppm axes are rejected. Without
this option the declared coordinates are preserved. No F1 reference is
inferred from direct-dimension SHIFT REFERENCE or repeated vendor fields.
This option concerns already processed real spectra; it does not calibrate
a Fourier transform of raw 2D FIDs.

Explicit physical dwell for QF JCAMP FIDs
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

nmrglue-ng 1.5.0 optionally accepts ``indirect_dwell_s`` for QF
normalization. Supply it only from known acquisition provenance when the
declared T1 grid is not the physical evolution step. Without the option,
QF retains the declared grid. The input read result and sample values are
unchanged; normalization records both declared and caller-supplied dwell,
its source, and an unscaled time-coordinate operation. No vendor field is
selected automatically. Adjacent-pair confirmation remains invalid for QF.


Declared TPPI and QSEQ JCAMP FIDs
---------------------------------

Development builds accept ``quadrature="tppi"`` or ``"qseq"`` for declared
real-F1 JCAMP 2D FIDs with direct simultaneous QSIM or DQD acquisition. Supply
``indirect_dwell_s`` from independent acquisition provenance and choose
``conjugation`` explicitly. The exported T1 row interval does not establish
the physical TPPI/QSEQ dwell; no automatic factor-of-two correction is made.
Adjacent-pair confirmation is not accepted for these modes.

The result preserves one complex F2 trace per F1 sample in the common
``tppi-stored-2d`` contract. QSEQ applies its ``++--`` sign alternation before
processing and records both that operation and the original scheme. TPPI
samples receive only the requested conjugation. The input read result is
unchanged. No FFT, phasing, digital-filter correction or ppm reference is
implicit. Filter delay metadata remains unapplied and can be unknown.
The accepted direct-mode declarations are ``SIMULTANEOUS`` (QSIM) and
``SIMULTANEOUS (DQD)``. Missing, sequential or unknown declarations are
rejected. This extension does not relax the DQD requirement of the separate
States-family and echo/anti-echo normalizers.

Values remain in the JCAMP sample units, including its explicit NTUPLES
factors. A Bruker ``NC`` record is retained as metadata without implicitly
rescaling these samples. A comparison with native TopSpin intensities must
account for the native raw ``NC`` and processed ``NC_proc`` separately.
QSIM does not imply a zero filter delay: processing still requires an explicit
valid filter descriptor.

The QSIM path is additionally checked using a QSEQ pseudo-raw SER generated
by TopSpin 4.5.0 from a known spectrum, inverse ``iqr`` in F1 and ``iqc`` in
F2, then ``genser``. All four raw JCAMP codecs decode exactly; the companion
plugin checks four FFT planes and ppm axes against TopSpin, with the recorded
integer raw ``NC=2`` accounted for only in the reference comparison. This is
a synthetic conversion/processing reference, not an experimental QSEQ
acquisition or a digital-filter qualification. See the
`QSEQ/QSIM qualification
<https://www.spectrochempy.fr/projects/nmr/latest/reference/interop.html#qseq-qsim-generated-reference>`_.

The numerical convention is checked with synthetic matrix DFTs and controlled
TopSpin processing. Experimental TPPI decoding is additionally checked on the
CC0 `Young lab dataset
<https://github.com/the-young-lab/2025-indole-azo-sterics/tree/73af741bff1059a2a8491254a5f765644b985952>`_,
under ``Data for SI/1H and 2D NOESY NMR``: ``OMe-PAI-H cis NOESY`` and
``OMe-PAI-H trans NOESY/1``. Both declare ``acqu2s.FnMODE=3`` and direct
``acqus.AQ_mod=3``; neither is States-TPPI. Their complete SER/acqus/acqu2s
folders are public, with 256 by 1024 complex samples and ``GRPDLY=76``.

TopSpin 4.5.0 exports in FIX, PACKED, SQUEEZED and DIFF/DUP reproduce the
native complex samples exactly through ``read(..., profile="jcampdx-fid-2d")``.
Processed real 2D exports reproduce the stored TopSpin RR plane exactly through
``profile="jcampdx-spectrum-2d"``. This is stored-value parity, not automatic
``NC_proc`` or NS/RG intensity normalization. On copied acquisitions, an
uncorrected four-plane FFT is separately qualified in the `plugin workflow
<https://www.spectrochempy.fr/projects/nmr/latest/reference/interop.html#public-experimental-tppi-qualification>`_.
Its physical dwell is supplied from native TPPI metadata, not inferred by the
normalizer. The filter descriptor retains its unapplied 76-point delay.

On these two native TPPI acquisitions, explicit F2 phase compensation of the
76-point delay is additionally qualified against TopSpin 4.5.0 ``PKNL=yes``
in the `plugin filter workflow
<https://www.spectrochempy.fr/projects/nmr/latest/reference/interop.html#tppi-digital-filter-phase-compensation>`_.
It preserves F2 size and grids and records an applied correction without changing
the input. This remains a processing step: the normalizer keeps the delay
unapplied. No correction is inferred during reading.

Native indirect-QSEQ acquisitions, other filters, time-domain TPPI correction,
absolute experimental phase and full TPPI/QSEQ vendor recipes remain unqualified.
The automatic native Bruker TPPI/QSEQ processing guards are unchanged.

The acquisition-mode definitions are documented in the Bruker
`Acquisition Reference <https://nmrcore.chem.kuleuven.be/media/files/guides/bruker_manuals_4.2.0/acquisition-reference.pdf>`_
under ``FnMODE``. The Bruker
`Processing Reference <https://nmr.chem.ucsb.edu/docs/Bruker_NMR_Manuals/processing-reference_v007.pdf>`_
distinguishes the real F1 transforms used by TPPI and QSEQ.
