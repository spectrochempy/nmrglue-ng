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

.. _jcampdx-increasing-frequency-axes:

Increasing frequency axes
-------------------------

For processed spectra with increasing Hz or ppm coordinates,
``guess_udic()`` sets ``ascending=True`` on the dimension. In Hz,
``sw`` is the sample spacing multiplied by the number of points and
``car`` is ``FIRSTX + sw / 2`` after converting ``FIRSTX`` to Hz.
Use ``uc_from_udic()`` or ``glue.make_uc()`` to reconstruct the
coordinates in sample order.

Glue/HDF5 and the CSDM converter support increasing frequency axes.
The NMRPipe, Sparky, RNMRTK, Agilent/Varian and Bruker exporters raise
``ValueError`` for these axes.
