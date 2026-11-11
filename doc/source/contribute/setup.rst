Set up a development environment
================================

Fork `nmrglue-ng on GitHub <https://github.com/spectrochempy/nmrglue-ng>`_
if you plan to submit a pull request. Clone your fork and create a virtual
environment with Python 3.10 or newer.

.. code-block:: console

   git clone https://github.com/YOUR-USERNAME/nmrglue-ng.git
   cd nmrglue-ng
   python -m venv .venv

Activate it with ``source .venv/bin/activate`` on macOS or Linux, or
``.venv\Scripts\Activate.ps1`` in Windows PowerShell. Then choose the
extra for your task.

.. code-block:: console

   python -m pip install -e ".[test]"
   python -c "import nmrglue as ng; print(ng.__file__); print(ng.__version__)"

For documentation, use ``python -m pip install -e ".[docs]"``. To run
both the tests and the documentation build, use
``python -m pip install -e ".[test,docs]"``. The package path printed
above should point to your checkout.

If you use uv, the equivalent setup is ``uv sync --extra test`` or
``uv sync --extra docs``. Repeat ``--extra`` to install both. Use
``uv run --no-sync`` for commands in the environment you just prepared.

Project layout
--------------

- ``nmrglue/`` contains file I/O, processing, analysis, and utility modules.
- ``tests/`` contains tests and versioned fixtures.
- ``examples/`` contains example scripts and their supporting files.
- ``doc/source/`` contains the Sphinx documentation and MyST-NB notebooks.
- ``data/`` is the optional local test corpus.
