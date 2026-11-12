nmrglue.bruker
==============

.. automodule:: nmrglue.fileio.bruker

Use ``ng.bruker.read()`` on an acquisition directory containing a
``fid`` or ``ser`` file. Use ``write()`` to write raw data and
``read_lowmem()`` or ``write_lowmem()`` to work with raw data in
limited memory. Inspect shape warnings before processing indirect axes.
Use ``remove_digital_filter()`` for an approximate correction of the
direct dimension when the acquisition used a digital filter.

For processed spectra, point ``read_pdata()`` at the ``pdata/<n>``
directory. It detects standard 1D, 2D, and 3D files and applies the stored
intensity scaling by default. It returns the all-real component by
default. Set ``all_components=True`` to load the component files as a
list of arrays. Use ``guess_udic(dic, data, pdata=True)`` to use the
processed axis calibration when both acquisition and processing
metadata are available.

``write_pdata()`` writes the real part of the supplied array and can
write processing parameter files. Low-memory reading applies to raw
data only.

User Information
----------------

User Functions
^^^^^^^^^^^^^^

.. autosummary::
    :toctree: generated/

    read
    write
    read_pdata
    write_pdata
    remove_digital_filter
    read_lowmem
    write_lowmem
    read_binary
    write_binary
    read_pdata_binary
    scale_pdata
    read_binary_lowmem
    write_binary_lowmem
    read_jcamp
    write_jcamp
    read_pprog
    write_pprog
    guess_udic
    create_dic
    read_nuslist


Developer Information
---------------------

See :ref:`developer-bruker-format-notes` for storage and parser details.

Developer Functions
^^^^^^^^^^^^^^^^^^^

These functions are typically not used directly by users.  Developers who want
fine control over Bruker files may be interested in these functions.

.. autosummary::
    :toctree: generated/

    create_data
    add_axis_to_udic
    create_acqus_dic
    guess_shape
    guess_shape_and_submatrix_shape
    get_data
    put_data
    complexify_data
    uncomplexify_data
    reorder_submatrix
    rm_dig_filter
    parse_jcamp_line
    parse_jcamp_value
    write_jcamp_pair
    read_acqus_file
    read_procs_file


Developer Classes
^^^^^^^^^^^^^^^^^

.. autosummary::
    :toctree: generated/

    bruker_nd
