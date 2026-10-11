==================================
Building documentation for nmrglue
==================================

nmrglue-ng uses Sphinx for building its documentation. The documented build
uses the ``docs`` optional dependency extra from ``pyproject.toml``.

Instructions
------------

1.  Create and activate a Python environment. For example:

        python -m venv .venv
        . .venv/bin/activate

2.  Install nmrglue-ng and the documentation dependencies in editable mode from
    the repository root directory.

        python -m pip install -e '.[docs]'

3.  Run ``make html``. in this directory.

The html documentation should be stored in the build/html directory.


ReadTheDocs
-----------

Read the Docs builds are configured by ``../.readthedocs.yml``. The configured
Python version must remain compatible with ``requires-python`` in
``pyproject.toml``.
