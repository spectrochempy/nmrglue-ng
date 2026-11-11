RS2D
====

Use ``nmrglue.rs2d.read(path)`` to load a directory containing
``data.dat`` and ``header.xml``. Pass ``datafile=`` or ``headerfile=``
to select other filenames in that directory. Install the optional
``xmltodict`` package in the same environment before reading.

.. code-block:: python

   import nmrglue as ng

   dic, data = ng.rs2d.read("experiment")
   udic = ng.rs2d.guess_udic(dic, data)

Reading and writing
-------------------

The reader returns parameters extracted from the XML header and an
in-memory NumPy array. The test corpus includes 1D and 2D FIDs and
processed spectra. The binary reader uses big-endian complex64 by
default. It selects big-endian float32 when the first item in the
header's data representation list is ``REAL``.

The header must supply the receiver count and matrix dimensions, and the
binary sample count must match the resulting shape. Singleton dimensions
are omitted. The direct dimension is last, and a receiver dimension with
more than one receiver comes first. ``guess_udic()`` describes the
spectral axes and excludes the receiver axis. Verify the widths,
references, and time or frequency domain when metadata is incomplete.

The module provides neither a writer nor a low-memory reader.

.. currentmodule:: nmrglue.fileio.rs2d

.. autosummary::
   :toctree: generated/

   read
   guess_udic
