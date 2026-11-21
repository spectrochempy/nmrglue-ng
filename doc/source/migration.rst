Coming from nmrglue?
====================

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

When comparing results with an older environment, record both package
versions. Use the checks below for workflows you rely on, and consult the
:doc:`release notes <whats-new>` for all changes between those versions.

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
