.. _varian_module:

nmrglue.varian
==============

.. automodule:: nmrglue.fileio.varian

Use ``ng.varian.read()`` and ``write()`` on an Agilent/Varian
acquisition directory containing the binary ``fid`` and text
``procpar`` files. The same functions are available under
``ng.agilent``. These functions handle acquisition data.

The reader infers the array shape and, for 3D and 4D data, the mapping
from stored traces to indirect dimensions. Supply ``shape`` or
``torder`` when this metadata does not describe your acquisition.
Set ``as_2d=True`` to read the stored traces as rows. If reordering
fails, the reader warns and returns the flat trace matrix. Verify
the layout before assigning indirect axes.

Use ``read_lowmem()`` to slice acquisitions with one trace per block
and ``write_lowmem()`` to write data trace by trace. Use the regular
reader for FIDs with multiple traces per block.

User Information
----------------

User Functions
^^^^^^^^^^^^^^

.. autosummary::
    :toctree: generated/

    read
    write
    write_lowmem
    read_lowmem
    read_fid
    write_fid
    read_fid_lowmem
    write_fid_lowmem
    read_fid_ntraces
    read_procpar
    write_procpar
    guess_udic
    create_dic


Developer Information
---------------------

.. _agilent-varian-file-format-information:

See :ref:`developer-varian-format-notes` for storage and parser details.

Developer Functions
^^^^^^^^^^^^^^^^^^^

These functions are typically not used directly by users.  Developers who
want fine control over Agilent/Varian files will be interested in these
functions.

.. autosummary::
    :toctree: generated/

    create_data
    create_pdic_param
    find_torder
    torder2i2t
    torder2t2i
    reorder_data
    order_data
    get_nblocks
    get_block
    get_nblocks_ntraces
    get_block_ntraces
    get_trace
    get_fileheader
    get_blockheader
    skip_blockheader
    get_hyperheader
    put_block
    put_trace
    put_fileheader
    put_blockheader
    put_hyperheader
    hyperheader2dic
    repack_hyperheader
    dic2hyperheader
    make_blockheader
    blockheader2dic
    repack_blockheader
    dic2blockheader
    fileheader2dic
    repack_fileheader
    dic2fileheader
    find_shape
    find_cdtype
    find_dtype
    uninterleave_data
    interleave_data
    get_parameter


Developer Classes
^^^^^^^^^^^^^^^^^

.. autosummary::
    :toctree: generated/

    fid_nd
