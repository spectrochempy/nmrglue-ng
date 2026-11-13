Readers and file formats
========================

The format modules live in ``nmrglue/fileio/``. Most readers return
format-specific metadata and a NumPy array. Start with the relevant
:doc:`API reference <../reference/index>` and its tests before changing
how a reader interprets a file.

Describe the file or directory the reader accepts, the returned shape
and axis order, and how it handles units and complex data. When changing
a format convention, include a small reproducer and document the
reference used to validate it. For a writer, use a read-back test where
possible. See :doc:`testing` for fixture and validation guidance.

Put details needed to use a reader in its API reference. These include
supported variants, meaningful warnings, axis conventions, and limitations.
Document binary layouts and parser decisions in format notes when they
are needed to maintain or extend a reader.

JCAMP-DX format notes
---------------------

Consult the `JCAMP-DX specifications
<https://github.com/IUPAC/JCAMP-DX>`_ for record labels, data tables,
and encoding rules. When testing a new dialect, record the exporter
and the declarations that identify it, and check both the decoded
values and the declared coordinates. See :doc:`../reference/jcampdx`
for the reader interface.

.. _developer-spinsolve-format-notes:

Spinsolve format notes
----------------------

The ``.1d`` reader interprets the first 32 bytes as eight little-endian
integer header fields. It reads the remaining values as little-endian
32-bit floats. The first third holds the coordinates and the rest
alternates real and imaginary samples. The reader returns the header
and coordinates under ``dic["spectrum"]``.

For ``.dx`` files, the reader delegates decoding to
:doc:`../reference/jcampdx` and combines its two components into a complex
array. It loads ``acqu.par`` and ``proc.par`` when present. When adding
support for another export variant, record the Spinsolve software version,
the files present, and the units and sample order of the exported axis.
See :doc:`../reference/spinsolve` for supported inputs.

.. _developer-bruker-format-notes:

Bruker format notes
-------------------

For raw ``fid`` and ``ser`` files, ``BYTORDA`` selects little endian
(``0``) or big endian (``1``), and ``DTYPA`` selects 32-bit integers
(``0``) or 64-bit floats (``2``). Processed files use ``BYTORDP`` and
``DTYPP``. When testing raw shape inference, check the direct trace
padding and word size. Include a case where the declared indirect
shape disagrees with the number of samples on disk.

Acquisition and processing parameters use the Bruker variant of
JCAMP-DX, where parameter names are prefixed with ``$``. The pulse
program parser extracts quoted variable assignments, loops, phase
operations and increments. Raw shape inference can use the parsed
loop structure.

For processed spectra, the status files ``procs``, ``proc2s`` and
their higher-dimensional counterparts hold the parameters used to
write the data. Check ``NC_proc`` for intensity scaling, ``XDIM``
for submatrix layout, ``STSI`` for processed size, and ``OFFSET``,
``SF`` and ``SW_p`` for axis calibration. The singular files
``proc`` and ``proc2`` can contain editor settings or stale values.
An explicit ``procs_files`` list can expose both families in the
returned dictionary. Include the status files in the list to retain
their metadata. See :doc:`../reference/bruker` for reading and writing
procedures.

.. _developer-varian-format-notes:

Agilent/Varian format notes
---------------------------

The binary ``fid`` contains a file header followed by blocks with their
own headers and one or more traces. Each complex trace stores interleaved
real and imaginary samples. The accompanying ``procpar`` supplies
acquisition parameters. When testing shape inference, compare its
declared dimensions with the number of stored traces and verify the
trace-to-index mapping before assigning indirect axes.

The low-memory reader uses a trace-to-block mapping and expects a
single trace per block. Exercise the full reader separately for
multi-trace blocks and for files whose declared geometry disagrees
with the data. See :doc:`../reference/varian` for the reader options.

For the binary layout and parameter definitions, see the historical
*VnmrJ / VNMR FID Data Format* note in Varian MR News (18 April 2005)
and chapter 5, “Parameters and Data,” in *VnmrJ User Programming*.

.. _developer-tecmag-format-notes:

Tecmag format notes
-------------------

The vendor describes the TNT binary format in *A1 - TNMR File Format.doc*,
distributed with TNMR. The reader was based on
`pytnt <https://github.com/chatcannon/pytnt>`_. When checking a new file
variant, compare the stored samples, axis calibration, and transformation
flags with a TNMR reference. See :doc:`../reference/tecmag` for user-facing
limits.

.. _developer-sparky-format-notes:

Sparky format notes
-------------------

The UCSF reader uses the header to determine the number of axes and
the tile geometry. Samples are stored in tiles. For a new fixture,
check both a full read and a low-memory slice that crosses a tile
boundary. The `UCSF Sparky manual
<https://www.cgl.ucsf.edu/home/sparky/manual/files.html#UCSFFormat>`_
and the Sparky source file ``ucsffile.cc`` describe the file layout.
See :doc:`../reference/sparky` for the reader and writer options.

.. _developer-nmrpipe-format-notes:

NMRPipe format notes
--------------------

The NMRPipe manual pages and the header definition in ``fdatap.h``
describe the format. The binary header occupies 512 four-byte words.
When changing shape inference, check both single-file streams and
numbered plane sets. When changing axis reconstruction, compare the
coordinates with NMRPipe for the same data, including extraction
metadata if present. See :doc:`../reference/pipe` for reader options.
