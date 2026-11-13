nmrglue.tecmag
==============

.. automodule:: nmrglue.fileio.tecmag

Use ``ng.tecmag.read()`` to load a TNMR ``.tnt`` file as a metadata
dictionary and a NumPy array. The module provides reading only. Files
with multiple points along an indirect dimension emit a warning. Verify
the axis calibration and transformation flags against a TNMR reference
before interpreting multidimensional data.

User Information
----------------

User Functions
^^^^^^^^^^^^^^

.. autosummary::
    :toctree: generated/

    read
    guess_udic


Developer Information
---------------------

.. _tecmag-tnt-file-format-information:

See :ref:`developer-tecmag-format-notes` for storage and reader details.
