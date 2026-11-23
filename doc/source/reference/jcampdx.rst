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

For a multidimensional NTUPLES spectrum or FID, pass ``show_all_data=True`` to
``read()`` to retrieve all one-dimensional pages. The default returns
only the first array for each available component. ``guess_udic()``
describes only the direct dimension. For ``nD NMR FID`` data, it marks this
dimension as time-domain and computes the spectral width from the time
endpoints and the number of samples in a page. The returned pages preserve
storage order; decoding does not establish indirect quadrature, reshape
hypercomplex components, apply digital-filter corrections or reference
chemical shifts. Writing JCAMP-DX is unsupported.

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
