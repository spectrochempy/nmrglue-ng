.. _simpson_module:

nmrglue.simpson
===============

.. automodule:: nmrglue.fileio.simpson

This modules is imported as nmrglue.simpson and can be called as such.

User Information
----------------

Indexed XREIM files can contain fewer than four rows. For XYREIM, the
reader reconstructs the complete coordinate grid from the rows, with or
without blank separators. Axes follow first occurrence order by default.
Use ``read(path, legacy_layout=True)`` to sort both XYREIM axes in ascending
order, matching historical SpectroChemPy imports.

User Functions
^^^^^^^^^^^^^^

.. autosummary::
    :toctree: generated/

    read
    read_text
    read_xreim
    read_xyreim
    read_raw_bin_1d
    read_raw_bin_2d
    read_binary

Developer Information
---------------------

Developer Functions
^^^^^^^^^^^^^^^^^^^

These functions are typically not used directly by users.  Developers who
want fine control over SIMPSON files will be interested in these
functions.

.. autosummary::
    :toctree: generated/

    guess_ftype
    unappend_data
    chars2bytes
    bytes2float
