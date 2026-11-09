.. _nmrglue_tutorial:

Tutorials
=========

Follow the order in which an NMR dataset becomes a result: read and identify
the axes, inspect the data, prepare and process the acquisition, then measure
the spectrum. Import the package as ``nmrglue``. The
:doc:`Getting started notebook <../getting-started/index>` supplies a small
FID to try before starting on experimental archives.

Each chapter explains a decision and introduces worked examples at the
point where you need them. The individual examples contain the data links,
complete commands, and results. Use the simplest case first, then choose
the example that matches your format, dimensionality, or acquisition mode.

1. Read the dataset and establish its axes
-----------------------------------------

Read a file and identify the direct dimension, the domain, and the stored
quadrature. Use the universal dictionary to describe the axes across formats.
Choose the reader interface once you know which metadata your workflow needs.

.. toctree::
    :maxdepth: 2

    reading
    universal-dictionaries
    unit-conversion
    interop
    manipulating-data

2. Inspect the signal and spectrum
----------------------------------

Plot a trace or a contour map before choosing which regions to process or
measure. Move from points to calibrated coordinates when you need to
interpret chemical shifts. The worked examples include experimental plots.

.. toctree::
    :maxdepth: 2

    plotting
    ../how-to/plotting
    ../how-to/interactive

3. Prepare and exchange data
----------------------------

Save a copy when you need to preserve a processing stage. Convert only if
the next tool requires another format, and verify the written file by
reading it back. Before processing a series, decide which traces belong
together.

.. toctree::
    :maxdepth: 2

    writing-data
    converting-formats
    low-memory
    ../how-to/conversion
    ../how-to/acquisition

4. Process the acquisition
--------------------------

Start with a single FID, then follow the dimensional order and quadrature
of a multidimensional acquisition. Compare the intermediate checkpoints
when adapting a recipe to another experiment.

.. toctree::
    :maxdepth: 2

    processing
    ../how-to/processing

5. Measure and validate the result
---------------------------------

Use the processed spectrum to locate peaks, integrate regions, or fit a
series. Compare the result with a simulation when you need to isolate
the effect of an analysis choice.

.. toctree::
    :maxdepth: 2

    ../how-to/quantification
    ../how-to/simulation
    additional-resources

.. toctree::
    :hidden:

    ../how-to/index
    ../jbnmr_examples/index
