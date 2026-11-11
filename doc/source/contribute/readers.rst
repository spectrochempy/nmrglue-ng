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
