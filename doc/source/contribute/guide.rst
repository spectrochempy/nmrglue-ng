Contributor Guide
=================

This page summarizes the current ``nmrglue-ng`` contributor workflow. The
authoritative details are maintained in the repository-level `CONTRIBUTING.md
<https://github.com/spectrochempy/nmrglue-ng/blob/master/CONTRIBUTING.md>`_.

Key points
----------

- Install from a source checkout when testing unreleased changes.
- Keep changes small, focused, and reviewable.
- Preserve the public import name, ``nmrglue``, and the distribution identity,
  ``nmrglue-ng``.
- Add or update tests for behavior changes.
- Keep external data, optional dependencies, and external software requirements
  explicit.
- Update the changelog for user- or developer-visible changes.

Project layout
--------------

The main source tree is organized around the public ``nmrglue`` import:

- ``nmrglue/`` contains file I/O, processing, analysis, and utility modules.
- ``tests/`` contains the pytest suite, versioned fixtures, and infrastructure
  checks.
- ``examples/`` contains runnable example scripts and supporting files.
- ``doc/`` contains this Sphinx documentation, including executable MyST-NB
  notebooks.
- ``maintainer/`` contains roadmap, release, and test-data policy material used
  by maintainers.

Two local-only directories are common during development and are ignored by Git:

- ``data/`` for the optional external test corpus.
- ``sandbox/`` for temporary experiments that are not ready for review.

Development install
-------------------

Clone the repository and create the development environment:

.. code-block:: console

    git clone https://github.com/spectrochempy/nmrglue-ng.git
    cd nmrglue-ng
    uv sync --extra test

Run commands through that environment, for example:

.. code-block:: console

    uv run python -c "import nmrglue as ng; print(ng.__version__)"
    uv run pytest -m "not dataset and not external_software"

Optional dependencies and external NMR programs are not required for ordinary
use. Tests or examples that need external data or software must say so
explicitly.

Testing
-------

Use the smallest test scope that proves the change, then widen only when the
change needs it. The standard self-contained test profile is:

.. code-block:: console

    uv run pytest -m "not dataset and not external_software"

Focused file or module tests are preferred while developing, for example:

.. code-block:: console

    uv run pytest tests/fileio/test_pipe.py
    uv run pytest tests/analysis/test_peakpick.py

Dataset-dependent tests are marked ``dataset`` and require the optional local
``data/`` corpus. External-software tests are marked ``external_software`` and
require tools such as NMRPipe. A skipped external test is not evidence that the
external behavior passed; report the skip and the reason.

Documentation builds
--------------------

Documentation dependencies are installed through the project extras. The local
fast documentation build used by maintainers is:

.. code-block:: console

    cd doc
    READTHEDOCS=True make html-fast SPHINXOPTS="-W"

Before opening a pull request, also run the repository checks described in
``CONTRIBUTING.md``.

Data and provenance
-------------------

Prefer the smallest fixture that demonstrates the behavior. Do not commit large
datasets when a small synthetic or public fixture is sufficient. Any new data
used in tests or documentation should have clear provenance, redistribution
status, and checksums when applicable.

Tests must never write into the canonical external corpus. Copy data to a
temporary directory before modifying it.

Pull requests
-------------

Keep pull requests focused and reviewable. A good pull request usually includes:

- A short explanation of the problem and the change.
- Tests or documentation updates appropriate to the change.
- Exact validation commands that were run.
- A changelog entry for user- or developer-visible changes.
- Clear notes about any dataset, optional dependency, or external software that
  was required or intentionally not run.

For bug fixes, include a reproducer when possible. For file-format or scientific
behavior changes, include a regression test and cite the relevant format,
vendor, reference software, or scientific basis for the expected behavior.
