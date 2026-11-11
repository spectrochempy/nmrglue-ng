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

The reader supports JCAMP-DX NMR data. Multidimensional NTUPLES spectra
can be read as a series of pages. ``guess_udic()`` describes only the
direct dimension. Writing JCAMP-DX is unsupported.

See :doc:`../contribute/readers` for format specifications and validation
guidance.
