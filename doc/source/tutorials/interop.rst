Choose a reader, a universal dictionary or interop
==================================================

The same NMR file can be useful at three levels. Choose the level that matches
what the next step needs.

.. list-table::
   :header-rows: 1
   :widths: 24 38 38

   * - Interface
     - What it gives you
     - When to use it
   * - Format reader
     - The decoded array and a format-specific metadata dictionary.
     - Inspect vendor parameters, use low-memory access, or follow an existing
       processing or conversion workflow.
   * - Universal dictionary (``udic``)
     - Common dimension descriptors such as size, width, observation frequency,
       carrier, domain and encoding.
     - Describe axes, convert point coordinates or configure a supported format
       conversion from a reader's dictionary and array.
   * - ``nmrglue.interop``
     - A named result with samples, axes, components, metadata, corrections and
       diagnostics. Selected profiles also offer a validated layout.
     - Hand a supported acquisition or spectrum to another library that needs
       explicit storage conventions and evidence about what the reader did.

An axis description alone cannot say which file supplied a component, whether
storage scaling has already been applied, or how stored traces relate to the
physical axes. Interop keeps that information with the data so consumers can
decide how to handle it. The universal dictionary remains useful alongside it
for code that expects dimension descriptors. Build the dictionary from the
original reader metadata and the corresponding array, before reshaping or
stacking components for another consumer.

From a file to a validated result
---------------------------------

Use the :download:`small NMRPipe spectrum
<../../../tests/fixtures/fileio/data/nmrpipe_1d_freq.fid>` from the repository's
test fixtures. Download it into the working directory. Its header identifies
it as a frequency-domain spectrum even though its name ends in ``.fid``.

.. code-block:: python

    import numpy as np
    import nmrglue as ng

    filename = "nmrpipe_1d_freq.fid"
    header, samples = ng.pipe.read(filename)
    udic = ng.pipe.guess_udic(header, samples)
    print(udic[0]["size"], udic[0]["sw"])

    raw = ng.interop.read_nmrpipe_1d(filename)
    spectrum = ng.interop.normalize_nmrpipe_1d(raw)

    axis = spectrum.axes[0]
    print(spectrum.dimensions, axis.unit, axis.values[-1])
    print(spectrum.provenance, raw.applied_corrections)
    np.testing.assert_array_equal(spectrum.data, samples)

The reader returns a :class:`~nmrglue.interop.ReadResult`. In this profile, the
normalizer checks its layout and calibration and returns a
:class:`~nmrglue.interop.NormalizedAcquisition`. Both preserve the stored
samples. The axis uses the header's last-point frequency in Hz. Here,
*normalize* means validating the representation for a consumer. Other
profiles can also apply documented operations, such as trimming padding or
combining stored components. Check the profile and its operation records
before processing the result.

If your workflow starts with interop, this NMRPipe profile also exposes the
original header and a compatible array. You can build the same dictionary
without reading the file again::

    udic = ng.pipe.guess_udic(raw.metadata, raw.data)

Use the format-specific ``guess_udic`` with the metadata and array it expects.
For example, a normalized array with a leading component axis is no longer
the same representation as the array returned by the format reader.

Keep the original storage layout
--------------------------------

Use ``read_bruker_pdata_2d_storage`` to read the named planes that are present.
It restores the rows and columns from the disk tiles at their stored scale.
For an extracted strip, it uses the stored size (``STSI``) without assigning
a physical grid. For example, a directory containing only ``2rr`` yields one
component.

.. code-block:: python

    import nmrglue as ng

    stored = ng.interop.read_bruker_pdata_2d_storage("experiment/pdata/1")
    for plane in stored.components:
        print(plane.name, plane.data.shape)

The processing parameters remain available for a later calibration step.

Use ``read_bruker_ser_storage`` or ``read_agilent_fid_storage`` for acquisition
traces in file order. Each row contains scalar words, including Bruker trace
padding when present. Read the Bruker acquisition status or the Agilent
``procpar`` and binary headers from ``result.metadata``. These can describe the
complex packing and the relationship between successive traces. When present,
the Bruker schedule and pulse program are retained as ``nuslist_raw`` and
``pulseprogram_raw``. The Bruker entry point supports 1024-byte-aligned traces.
The Agilent entry point supports one or two headers per binary block.
Apply the recorded conventions when constructing physical dimensions and
pairing branches. The storage result labels its axes by array position and
leaves their physical domains unknown.

The existing readers for qualified profiles provide stronger guarantees,
such as calibrated axes or a particular trace organization. Choose those
entry points when the input satisfies the corresponding profile.

Supported entry points
----------------------

.. list-table::
   :header-rows: 1
   :widths: 22 43 35

   * - Input
     - Reader profile
     - Normalizer
   * - Agilent / Varian raw
     - Complex 1D FID or descriptive 2D States traces
     - 1D FID
   * - Bruker raw
     - 1D FID or descriptive 2D QF and States-TPPI SER
     - Qualified complex 1D FID
   * - Bruker processed
     - 1D components or complete int32 2D with four stored planes
     - Complete calibrated 1D or qualified four-plane 2D
   * - NMRPipe processed
     - Complete real or complex 1D spectrum or complete real 2D plane
     - Corresponding 1D or real 2D profile
   * - nmrML
     - Explicit 1D raw or processed profile
     - Corresponding explicit 1D profile

See the :doc:`API reference <../reference/interop>` for function names, detailed
limits and the separate raw NMRPipe export. Each normalizer accepts the result
of its corresponding profile. The presence of a reader does not imply a
normalizer or an export for that profile.
