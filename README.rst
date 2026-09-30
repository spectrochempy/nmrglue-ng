==========
nmrglue-ng
==========

**An independent continuation of nmrglue for processing and working with NMR data in Python.**

``nmrglue-ng`` is an independent fork of `nmrglue <https://github.com/jjhelmus/nmrglue>`_, originally developed by Jonathan J. Helmus and contributors.

The project aims to preserve the simplicity, scientific capabilities, and established API of nmrglue while providing ongoing maintenance, reproducible testing, up-to-date documentation, and a predictable contribution and release process.

.. important::

   ``nmrglue-ng`` is an independent project. It is not the official nmrglue distribution and is not maintained or endorsed by the maintainers of the original project.

Why nmrglue-ng?
===============

nmrglue has provided the NMR community with a lightweight and powerful Python toolkit for reading, writing, converting, processing, and analysing NMR data for more than a decade.

Its broad support for NMR formats and its NumPy-oriented API make it particularly valuable for scientific scripting and interoperability.

``nmrglue-ng`` builds on that work rather than replacing it.

The main goals of this fork are:

* preserve compatibility with the established nmrglue API wherever practical;
* maintain and test existing NMR file-format support;
* fix confirmed bugs and scientific inconsistencies;
* provide reproducible test datasets for critical I/O operations;
* maintain compatibility with current Python, NumPy, and SciPy releases;
* keep packaging and continuous integration up to date;
* maintain and continuously build the documentation;
* establish a clear process for reviewing contributions as the project grows;
* document important scientific and API decisions.

Large API redesigns are explicitly **not** an initial objective.

Compatibility
=============

Backward compatibility with existing nmrglue code is a primary goal.

Existing code should, whenever possible, continue to work unchanged::

    import nmrglue as ng

    dic, data = ng.bruker.read("experiment")

The distribution name and Python import name are intentionally distinct::

    distribution: nmrglue-ng
    import:       nmrglue

Compatibility cannot be guaranteed indefinitely when correcting scientifically incorrect behaviour. Such changes will be documented, tested, and introduced through an explicit compatibility policy.

Scientific scope
================

The project retains nmrglue's established scope, including:

* reading and writing NMR data;
* vendor and interchange file formats;
* conversion between formats;
* spectral processing;
* unit and axis conversion;
* peak picking and fitting;
* low-memory access to large datasets.

Scientific correctness and preservation of acquisition and processing metadata are considered part of the public behaviour of the library, not implementation details.

Development priorities
======================

The initial development effort focuses on maintenance rather than redesign.

Reliability
-----------

* reproducible test fixtures for supported NMR formats;
* read/write and conversion round-trip tests;
* regression tests for confirmed bugs;
* validation of spectral axes and metadata.

Scientific consistency
----------------------

Particular attention is being given to the relationships between:

* observation frequency;
* reference frequency;
* carrier frequency and offset;
* spectral width;
* point, Hz, and ppm coordinates;
* quadrature and complex-data conventions.

Infrastructure
--------------

* modern Python packaging;
* current Python/NumPy/SciPy compatibility;
* Linux, macOS, and Windows CI;
* automated documentation builds;
* reproducible releases.

File formats
------------

Existing format support will be preserved and progressively strengthened with real and synthetic reference datasets.

Changes to parsers are expected to include regression tests demonstrating the corresponding format convention.

Relationship with upstream nmrglue
==================================

``nmrglue-ng`` retains the complete Git history of nmrglue and acknowledges the original authors and all contributors whose work forms the basis of this project.

Where practical, fixes developed here that are applicable to the original nmrglue project may also be proposed upstream through pull requests or reported as issues in the original repository. This may include bug fixes, regression tests, documentation improvements, compatibility updates, and clarifications of scientific or format-specific behaviour.

Before opening an upstream contribution, the proposed change will be reviewed for relevance to the original project, compatibility with its maintenance policy, and consistency with its existing API and scope. Changes that are specific to ``nmrglue-ng``, or that depend on its independent development direction, will remain in this project.

Likewise, useful upstream developments may be incorporated into ``nmrglue-ng`` with their original authorship and attribution preserved.

The intention is not to obscure or replace the history of nmrglue, but to continue building on it transparently and, where appropriate, to contribute improvements back to the original project.

Contributions
=============

Contributions are welcome, particularly:

* reproducible bug reports;
* regression tests;
* small NMR datasets that can legally be redistributed for testing;
* fixes for file-format readers and writers;
* documentation improvements;
* scientific validation against vendor software or documented format specifications;
* performance improvements accompanied by correctness tests and benchmarks.

Changes affecting scientific conventions or public API semantics may require a short design discussion before implementation.

As the project develops, contribution and maintenance practices may evolve to make it easier for additional maintainers to participate.

Installation
============

``nmrglue-ng`` is currently under development.

Installation and release instructions will be added once the first independent release is prepared.

Citation and attribution
========================

nmrglue-ng is derived from **nmrglue**, created by Jonathan J. Helmus and contributors.

Users should continue to acknowledge the original nmrglue work where appropriate:

    Jonathan J. Helmus and Christopher P. Jaroniec,

    *Nmrglue: an open source Python package for the analysis of multidimensional NMR data*,

    Journal of Biomolecular NMR (2013).

A citation specific to ``nmrglue-ng`` will be provided if and when an appropriate archival release or publication becomes available.

License
=======

``nmrglue-ng`` is distributed under the BSD 3-Clause License inherited from nmrglue.

The original copyright notices and contributor history are preserved.

See ``LICENSE.txt`` for details.

----

**nmrglue-ng is an independent continuation of nmrglue.**

Its objective is deliberately conservative: preserve a useful and established NMR toolkit while making its maintenance, testing, documentation, and evolution sustainable.
