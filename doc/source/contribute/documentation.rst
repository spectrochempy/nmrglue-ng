Build and edit the documentation
================================

From the repository root, install the documentation extra in your
:doc:`development environment <setup>`.

.. code-block:: console

   python -m pip install -e ".[docs]"

Preview a prose change
----------------------

For a quick HTML preview, skip API generation and notebook execution.
This command works from the repository root with the active Python
environment.

.. code-block:: console

   python -m sphinx -b html -t fastdocs -D nb_execution_mode=off -W doc/source doc/build/preview

Open ``doc/build/preview/index.html``. The preview omits the API reference
and suppresses some warnings for references to omitted pages.

Check the Read the Docs build
-----------------------------

On a system with Make and a POSIX shell, run the same target as Read the
Docs. The explicit Sphinx command uses the active interpreter.

.. code-block:: console

   READTHEDOCS=True make -C doc html-rtd SPHINXBUILD="python -m sphinx" SPHINXOPTS="-W"

Open ``doc/build/html/index.html``. This target generates the API
reference and executes eligible notebooks, using cached results where
available. The Read the Docs configuration excludes three large 3D
notebooks from execution. Other notebooks may need network access to
fetch their example data.

If you use uv, install the docs extra as described in :doc:`setup` and
prefix the Sphinx preview command with ``uv run --no-sync``. For the Make
command, set ``SPHINXBUILD="uv run --no-sync python -m sphinx"``.

Edit a page or example
----------------------

Use reStructuredText for reference pages and MyST-NB for executable
tutorials. Give readers the input files, the commands to run, and a result
they can check. Keep setup cells short and make downloaded examples
runnable outside the source checkout. Record data provenance in
:doc:`../about/data-credits`.

Build and read the affected pages. Follow new links, try download links,
and check code blocks, figures, and navigation. Preserve existing page
paths and anchors when moving material. Use the complete build to check
API references and notebook execution before submitting changes that
affect them.
