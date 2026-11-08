==========
nmrglue-ng
==========

Read, write, convert, process, and analyse NMR data in Python. nmrglue-ng is
an independent continuation of `nmrglue <https://github.com/jjhelmus/nmrglue>`_,
originally developed by Jonathan J. Helmus and contributors.

Quick start
===========

Install the ``nmrglue-ng`` distribution in a Python 3.10+ environment::

    python -m pip install nmrglue-ng

The Python import remains ``nmrglue``. For example, read an NMRPipe FID:

`Download the sample FID
<https://github.com/spectrochempy/nmrglue-ng/raw/v1.1.2/doc/source/getting-started/synthetic_1d_time.fid>`_
and save it beside your script.

.. code-block:: python

    import nmrglue as ng

    dic, data = ng.pipe.read("synthetic_1d_time.fid")

The reader returns a dictionary of NMRPipe header values and a NumPy array.
Use separate environments for the historical ``nmrglue`` distribution and
``nmrglue-ng``, since both install the same Python package.
The `installation guide <https://nmrglue-ng.readthedocs.io/stable/install.html>`_
covers uv, pip, and Conda.

What nmrglue-ng adds
====================

* **Structured results for interoperability.** The optional
  ``nmrglue.interop`` API exposes data, calibrated axes, metadata, and
  diagnostics for supported profiles. The first published profile reads
  processed Bruker/TopSpin 1D spectra. Existing format readers continue
  to return ``(dic, data)``. Interop is still in development, and coverage
  varies by format and profile. To help prioritize the remaining profiles,
  `open a GitHub issue <https://github.com/spectrochempy/nmrglue-ng/issues>`_
  describing your format, data type, and workflow.
* **Corrections to scientific workflows.** Releases include fixes for the
  endpoints of descending processed JCAMP-DX axes and for scaling noise
  estimates in 1D and multidimensional integration.
* **Runnable examples and maintained distributions.** Follow downloadable
  notebooks with reproducible example data and install releases from PyPI
  or the ``spectrocat`` Conda channel.

Documentation
=============

* `Getting started <https://nmrglue-ng.readthedocs.io/stable/getting-started/index.html>`_
  walks through reading, processing, and plotting a first spectrum.
* `API reference <https://nmrglue-ng.readthedocs.io/stable/reference/index.html>`_
  covers the format readers, processing, analysis, and interop interfaces.
* `Release notes <https://nmrglue-ng.readthedocs.io/stable/whats-new.html>`_
  describe changes by release. See the `development documentation
  <https://nmrglue-ng.readthedocs.io/latest/>`_ for unreleased features.
* `Contributor guide <https://github.com/spectrochempy/nmrglue-ng/blob/master/CONTRIBUTING.md>`_
  covers reporting issues, running tests, and contributing fixes.

Citation and license
====================

Please cite the original nmrglue paper where appropriate:

    Jonathan J. Helmus and Christopher P. Jaroniec,
    *Nmrglue: an open source Python package for the analysis of
    multidimensional NMR data*, Journal of Biomolecular NMR 55,
    355–367 (2013). doi:10.1007/s10858-013-9718-x.

nmrglue-ng retains the original Git history and is distributed under the
`BSD 3-Clause License
<https://github.com/spectrochempy/nmrglue-ng/blob/master/LICENSE.txt>`_.
