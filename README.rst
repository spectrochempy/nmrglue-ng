==========
nmrglue-ng
==========

|CI| |PyPI| |Conda| |Docs| |License|

.. |CI| image:: https://github.com/spectrochempy/nmrglue-ng/actions/workflows/ci.yml/badge.svg?branch=master
   :alt: Test status on master
   :target: https://github.com/spectrochempy/nmrglue-ng/actions/workflows/ci.yml?query=branch%3Amaster
.. |PyPI| image:: https://img.shields.io/pypi/v/nmrglue-ng
   :alt: PyPI version
   :target: https://pypi.org/project/nmrglue-ng/
.. |Conda| image:: https://img.shields.io/conda/v/spectrocat/nmrglue-ng
   :alt: Conda version on spectrocat
   :target: https://anaconda.org/spectrocat/nmrglue-ng
.. |Docs| image:: https://readthedocs.org/projects/nmrglue-ng/badge/?version=stable
   :alt: Stable documentation build status
   :target: https://nmrglue-ng.readthedocs.io/stable/
.. |License| image:: https://img.shields.io/pypi/l/nmrglue-ng
   :alt: BSD 3-Clause License
   :target: https://github.com/spectrochempy/nmrglue-ng/blob/master/LICENSE.txt

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

For new integrations, ``nmrglue.interop`` provides structured results with
samples, axes, metadata, and diagnostics. Check the
`supported profiles <https://nmrglue-ng.readthedocs.io/stable/reference/interop.html#interop-profile-table>`_
for format coverage and limitations.

Documentation
=============

* `Getting started <https://nmrglue-ng.readthedocs.io/stable/getting-started/index.html>`_
  walks through reading, processing, and plotting a first spectrum in a
  downloadable notebook.
* `Tutorials <https://nmrglue-ng.readthedocs.io/stable/tutorials/index.html>`_
  cover reading, processing, conversion, and analysis with worked examples.
* `Coming from nmrglue? <https://nmrglue-ng.readthedocs.io/stable/migration.html>`_
  explains how to set up a separate environment and which changes can
  affect existing workflows.
* `API reference <https://nmrglue-ng.readthedocs.io/stable/reference/index.html>`_
  covers the format readers, processing, analysis, and interop interfaces.
* `Release notes <https://nmrglue-ng.readthedocs.io/stable/whats-new.html>`_
  describe changes by release. See the `development documentation
  <https://nmrglue-ng.readthedocs.io/latest/>`_ for unreleased features.

Contributing
============

Use the `Contribute section <https://nmrglue-ng.readthedocs.io/latest/contribute/index.html>`_
for issue reports, development setup, tests, documentation builds, and
pull requests.

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
