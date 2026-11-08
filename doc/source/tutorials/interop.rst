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

Use ``read_nmrpipe_2d_storage`` for a single NMRPipe 2D file, including a
converted FID before Fourier transformation, an intermediate with one
transformed axis or a spectrum with complex data. The result reports the
domains and quadrature in file order. A complex trace is returned as complex
samples. If the row axis is also complex, the two branches remain in
successive rows. An extraction can begin on either branch or contain an
incomplete pair. Use the layout, header and any known extraction details
to reconstruct physical dimensions separately. The
:ref:`NMRPipe storage reference <interop-nmrpipe-2d-storage>` shows how to
inspect that layout.

Use ``read_jeol_2d_storage`` for supported tiled float64 JDF layouts.
The result retains each section in file order, along with the tile sizes,
header, parameters and original bytes of any explicit axis lists. In the
reference HSQC and HMBC files these lists record the non-uniform indirect
sampling times. See the :ref:`JEOL storage reference <interop-jeol-2d-storage>`
for the result layout.

The existing readers for qualified profiles provide stronger guarantees,
such as calibrated axes or a particular trace organization. Choose those
entry points when the input satisfies the corresponding profile.

What interop can read
---------------------

**Agilent/Varian, Bruker and JEOL 2D acquisitions can be read.** The storage readers
return the decoded traces and metadata needed to reconstruct the acquisition.
For example, the rows of an Agilent 2D storage result are traces in file order.
They are still available even when no interop normalizer is provided for that
2D acquisition.

.. list-table::
   :header-rows: 1
   :widths: 26 74

   * - Input
     - Available readers
   * - Agilent / Varian raw
     - Storage: FID traces from 1D and 2D acquisitions.
       Qualified: complex 1D FID and descriptive 2D States traces.
   * - Bruker raw
     - Storage: scalar SER traces in file order, regardless of ``FnMODE``.
       Qualified: 1D FID and descriptive 2D QF or States-TPPI SER.
   * - Bruker processed
     - Storage: available 2D planes at their stored scale.
       Qualified: 1D components or complete int32 2D with four planes.
   * - NMRPipe
     - Storage: real or complex 2D traces in time, frequency or mixed domains.
       Qualified: complete real or complex 1D spectrum or complete real 2D
       frequency plane.
   * - JEOL JDF
     - Storage: scalar sections of standard tiled float64 2D JDF files.
       Qualified: complex float64 1D FIDs with a time axis in seconds.
   * - SIMPSON
     - Qualified: complex 1D FIDs in native TEXT and BINARY form.
   * - JCAMP-DX
     - Qualified: real 1D NMR spectra with regular XYDATA in Hz or ppm
       complex 1D FIDs in regular NTUPLES form, and complete real 2D NTUPLES planes.
   * - nmrML
     - Explicit 1D raw or processed profile. Real processed 2D planes with
       documented shape, storage order and indirect calibration. Raw 2D
       contiguous complex traces with explicit direct count convention.

The storage readers require the binary layouts described above.

When a normalizer is available
------------------------------

A normalizer accepts the result of its corresponding qualified reader and
validates a layout or calibration for a consumer.

* Agilent/Varian and Bruker raw: qualified 1D FIDs.
* JEOL: complex 1D FIDs and qualified 2D raw time-domain acquisitions.
  The 2D normalizer preserves the sampled indirect times and keeps
  the stored quadrature branches separate for listed-axis NUS data.
* Bruker processed: complete calibrated 1D spectra and qualified four-plane
  2D spectra.
* NMRPipe: complete real or complex 1D spectra and complete 2D frequency
  grids. Complete grids in NMRPipe States or pure TPPI layout require
  confirmation of the original time grid for time or mixed domains. See
  :func:`~nmrglue.interop.normalize_nmrpipe_2d`.
* SIMPSON: complex 1D FIDs with a time grid derived from the sweep width.
* JCAMP-DX: real 1D XYDATA spectra, complex 1D NTUPLES FIDs and real 2D NTUPLES planes.
  FID normalization preserves the time grid and records the requested conjugation.
* nmrML: explicit 1D raw and processed profiles and real processed 2D planes
  described by :func:`~nmrglue.interop.read_nmrml_2d`. Uniform raw 2D
  echo/anti-echo with confirmed adjacent pairs and an explicit indirect dwell
  time is covered by :func:`~nmrglue.interop.normalize_nmrml_raw_2d`.

See the :doc:`API reference <../reference/interop>` for function names, detailed
limits and the separate raw NMRPipe export.
