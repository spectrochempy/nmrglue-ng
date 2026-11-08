Choose a reader, a universal dictionary or interop
==================================================

.. list-table::
   :header-rows: 1
   :widths: 24 38 38

   * - Interface
     - What you get
     - When to use it
   * - Format reader
     - An array and a format-specific metadata dictionary.
     - Use an existing workflow, inspect source parameters or read with low memory.
   * - Universal dictionary (``udic``)
     - Common dimension descriptors such as size, width, carrier and domain.
     - Convert coordinates or configure a supported format conversion.
   * - ``nmrglue.interop``
     - Samples, axes, named components, metadata and diagnostics for supported profiles.
     - Pass data and explicit storage conventions to another library.

Read and normalize a spectrum
-----------------------------

Download the :download:`sample NMRPipe spectrum
<../../../tests/fixtures/fileio/data/nmrpipe_1d_freq.fid>` into your working
directory. Its header identifies it as a spectrum.

.. code-block:: python

    import nmrglue as ng

    result = ng.interop.read("nmrpipe_1d_freq.fid")
    spectrum = ng.interop.normalize(result)
    axis = spectrum.axes[0]
    print(result.format, spectrum.data.shape, axis.unit, axis.values[-1])

The reader detects the profile from the header. It returns a
:class:`~nmrglue.interop.ReadResult` with the decoded samples and source
metadata. Normalization returns a :class:`~nmrglue.interop.NormalizedAcquisition`
with a validated layout. Here it checks the axis calibration and preserves
the sample values. Other profiles may trim padding or combine quadrature
components and record the operations they applied.

Use the :ref:`interop-profile-table` to see what interop can read, when
to specify ``profile=``, and which results can be normalized. A storage
result remains usable when no normalizer is available.
