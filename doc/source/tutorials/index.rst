.. _nmrglue_tutorial:

Tutorials
=========

``nmrglue-ng`` is a Python package for reading, writing, converting, processing,
and analysing data from common NMR file formats. In Python, its modules are
imported as ``nmrglue``. This progressive tutorial assumes basic familiarity
with Python and introduces the package's file readers, data arrays, metadata,
unit-aware axes, format conversion, processing, and plotting APIs.

Start by reading a data file and inspecting its metadata. Next, learn how the
universal dictionary describes the axes, then visualize the spectrum. Later
guides cover array manipulation, writing and converting data, processing, and
low-memory access. Read them in order or choose a topic directly. The NMRPipe
walkthroughs provide practical examples with downloadable data.

Guide
-----

.. toctree::
    :maxdepth: 2

    reading
    universal-dictionaries
    interop
    plotting
    manipulating-data
    writing-data
    unit-conversion
    converting-formats
    processing
    low-memory
    additional-resources

Apply what you learned
----------------------

Use the workflow guides when you need to complete a specific task. The JBNMR
examples show how the same operations fit together on published experimental
datasets, from format conversion and visualization to processing and analysis.

.. toctree::
    :maxdepth: 2

    Workflow guides <../how-to/index>
    Worked examples from the JBNMR article <../jbnmr_examples/index>
