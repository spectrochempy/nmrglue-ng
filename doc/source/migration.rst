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
* Since nmrglue-ng 1.3.1, unit conversion recovers the referenced frequency axis for even-length processed TNT
  spectra stored in descending TNMR order with valid reference metadata.
  Rebuild the axis and compare peak positions with the referenced TNMR
  spectrum. See :doc:`release notes <whats-new>` for release availability.

* Since nmrglue-ng 1.3.1, processed Bruker strips read with
  ``strip_fake=True`` retain their calibrated axis. Rebuild the axis and
  check previously reported peak positions and spectral widths.
* Since nmrglue-ng 1.3.1, compact 2D JCAMP-DX NTUPLES with signed axis
  factors and truncated F2 line anchors can be read. Re-import affected
  exports and check peak positions against the source. Re-read XYW and XYM
  tables if downstream results depend on peak widths or multiplicities.
* Since nmrglue-ng 1.3.1, interop rejects arrays with active NumPy masks.
  Check earlier results if an input mask might have been discarded. Resolve
  the missing values explicitly before passing data to interop.

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
