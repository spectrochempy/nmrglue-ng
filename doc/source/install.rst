Installation
============

Package names
-------------

Install the distribution named ``nmrglue-ng``. Import it in Python as
``nmrglue``:

.. code-block:: python

    import nmrglue as ng

The distinct distribution name identifies this independent continuation while
the unchanged import preserves compatibility with existing nmrglue scripts.
Do not install the historical ``nmrglue`` distribution when you intend to use
``nmrglue-ng``.

The distributions must not be installed together in one environment because
both provide the ``nmrglue`` Python package. Use separate environments if you
need to work with both projects.

Requirements
------------

The package supports Python 3.10 and newer. Its required runtime dependencies
are installed automatically:

=================  ===============================
Dependency         Supported version
=================  ===============================
Python             3.10 or newer
NumPy              1.21.2 or newer
SciPy              1.7.2 or newer
=================  ===============================

Matplotlib and JupyterLab are optional. Install them when you want to run the
plotting tutorials and notebooks.

Install with uv
---------------

`uv <https://docs.astral.sh/uv/>`_ is the recommended option for a new project.
It manages the environment, Python version, dependencies, and lock file
together.

``uv`` is not included with Python. If it is not already installed, follow the
`official installation instructions
<https://docs.astral.sh/uv/getting-started/installation/>`_. Confirm the
installation before continuing:

.. code-block:: console

    uv --version

In a new working directory, run:

.. code-block:: console

    uv init --bare
    uv add nmrglue-ng

Use ``uv run`` for commands that should run in this environment:

.. code-block:: console

    uv run python -c "import nmrglue as ng; print(ng.__version__)"

For the tutorials, add the optional interactive tools to the same project:

.. code-block:: console

    uv add matplotlib jupyterlab
    uv run jupyter lab

If you already have a uv project, only ``uv add nmrglue-ng`` is needed.

Install with pip
----------------

Create a virtual environment before installing with ``pip``:

.. tab-set::

   .. tab-item:: macOS and Linux

      .. code-block:: console

          python -m venv .venv
          source .venv/bin/activate
          python -m pip install --upgrade pip
          python -m pip install nmrglue-ng

   .. tab-item:: Windows PowerShell

      .. code-block:: powershell

          py -m venv .venv
          .venv\Scripts\Activate.ps1
          python -m pip install --upgrade pip
          python -m pip install nmrglue-ng

Verify which package and interpreter are active:

.. code-block:: console

    python -c "import sys, nmrglue as ng; print(sys.executable); print(ng.__version__)"

Upgrade an existing installation
--------------------------------

In a uv project, update the locked dependency with:

.. code-block:: console

    uv lock --upgrade-package nmrglue-ng
    uv sync

For a ``pip`` environment, run:

.. code-block:: console

    python -m pip install --upgrade nmrglue-ng

Install with Conda
------------------

Install the stable release from the ``spectrocat`` channel with ``conda-forge``
for dependencies:

.. code-block:: console

    mamba create -n nmrglue-ng -c spectrocat -c conda-forge nmrglue-ng
    mamba activate nmrglue-ng

The Conda recipe prevents co-installation with the historical ``nmrglue``
package. This constraint cannot protect ``pip`` environments; install only one
of the two distributions in each environment.

Install from a source checkout
------------------------------

Installing a checkout is intended for contributors and for testing unreleased
changes. Clone the repository, then create the development environment:

.. code-block:: console

    git clone https://github.com/spectrochempy/nmrglue-ng.git
    cd nmrglue-ng
    uv sync --extra test

Run commands through that environment, for example:

.. code-block:: console

    uv run python -c "import nmrglue as ng; print(ng.__version__)"
    uv run pytest

See the :doc:`contributor guide <contribute/guide>` for the current contributor
workflow and documentation-specific dependencies.

Use in Google Colab
-------------------

Install the stable PyPI release in a Colab code cell:

.. code-block:: ipython3

    %pip install nmrglue-ng==1.0.0

To use the latest development version, install directly from the repository's
``master`` branch in a Colab cell:

.. code-block:: ipython3

    %pip install "git+https://github.com/spectrochempy/nmrglue-ng.git@master"

For reproducible work, replace ``master`` with a tag or specific commit.

To test uncommitted changes from a local checkout, build a wheel locally:

.. code-block:: console

    python -m pip wheel --no-deps --wheel-dir dist .

Upload the resulting ``dist/nmrglue_ng-*.whl`` file to the Colab runtime:

.. code-block:: ipython3

    from google.colab import files
    files.upload()

Then install the uploaded wheel:

.. code-block:: ipython3

    from pathlib import Path
    wheel = next(Path("/content").glob("nmrglue_ng-*.whl"))
    %pip install {wheel}

Verify that the expected package is imported:

.. code-block:: python

    import nmrglue as ng
    print(f"nmrglue-ng version: {ng.__version__}")

To run the :doc:`getting-started/index` notebook, also upload its downloadable
synthetic NMRPipe fixture to the runtime so it is beside the notebook file.

Next step
---------

Continue to :doc:`tutorials/index` to begin the tutorial path.
