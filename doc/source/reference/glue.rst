Glue/HDF5
=========

Glue stores a NumPy spectrum or acquisition in an HDF5 dataset and its
universal dictionary in the dataset attributes. Install the optional
``h5py`` package in the same environment, then import
``glue`` from ``nmrglue.fileio``.

.. code-block:: python

   from nmrglue import pipe
   from nmrglue.fileio import glue

   header, data = pipe.read("spectrum.ft2")
   udic = pipe.guess_udic(header, data)
   glue.write("spectrum.h5", udic, data)
   restored_udic, restored = glue.read("spectrum.h5")

Reading and writing
-------------------

``write(filename, dic, data, dataset="spectrum", overwrite=False)``
creates a file with one data array. Supply a :doc:`universal dictionary
<../tutorials/universal-dictionaries>` for the stored data, with
``ndim`` and numbered axis dictionaries. To replace an existing file,
pass ``overwrite=True``. This replaces the file, including any other
datasets it contains.

``read(filename, dataset="spectrum")`` returns the stored dictionary
and loads the array into memory. ``read_lowmem()`` takes the same
arguments and returns a file-backed object that supports slice reads.
It wraps 2D and 3D arrays for NumPy-like access and returns an
``h5py.Dataset`` for 1D and higher-dimensional arrays. Keep the
backing file open while using the result.

The format expects the Glue attribute layout. An arbitrary HDF5 file
may have a different dataset layout or lack the metadata needed by
``glue.make_uc(dic, data, dim=-1)``. The unit conversion uses the
stored dictionary.
