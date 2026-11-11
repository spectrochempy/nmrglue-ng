nmrglue.jcampdx
===============

.. automodule:: nmrglue.fileio.jcampdx

This module is imported as nmrglue.jcampdx and can be called as such.

User Information
----------------

User Functions
^^^^^^^^^^^^^^

.. autosummary::
    :toctree: generated/

    read
    guess_udic


.. _developer-information:

Format notes
------------

For a multidimensional NTUPLES spectrum, pass ``show_all_data=True`` to
``read()`` to retrieve all one-dimensional pages. The default returns
only the first array for each available component. ``guess_udic()``
describes only the direct dimension. Writing JCAMP-DX is unsupported.

See :doc:`../contribute/readers` for format specifications and validation
guidance.
