:orphan:

Glossary
========

This glossary defines terms used throughout the tutorials. Format-specific
parameter names and operation mappings are documented separately when an
authoritative manual and implementation evidence are available.

NMR data and dimensions
-----------------------

.. glossary::
   :sorted:

   FID
      Free induction decay: time-domain signal measured after excitation.

   direct dimension
      The dimension sampled during acquisition of one FID. In the usual NumPy
      array ordering, it is the last axis and therefore the final dimension in
      nmrglue's universal dictionary.

   indirect dimension
      A dimension incremented between FIDs. In 2D array data this is normally
      the first axis.

   quadrature
      The encoding of phase-sensitive information in real and imaginary
      components. Acquisition and indirect-dimension modes determine how the
      data are represented.

   spectrum
      Data represented in the frequency domain, commonly after Fourier
      transformation of an FID.

Axes and universal dictionary
-----------------------------

.. glossary::
   :sorted:

   universal dictionary (udic)
      A format-independent description of the data dimensions and their core
      spectral parameters. ``udic[dim]`` describes the corresponding NumPy
      axis; dimension 0 is the first array axis and the final dimension is
      normally the direct dimension.

   size
      Number of values along one array axis. In nmrglue this is taken from the
      returned data array's shape.

   spectral width (sw)
      Width of an axis in hertz in the universal dictionary. Its conversion
      from vendor parameters depends on the format, dimension, and whether the
      input represents acquired or processed data.

   observation frequency (obs)
      Nucleus observation frequency in megahertz. It converts between ppm and
      hertz: a chemical-shift difference of 1 ppm corresponds to ``obs`` Hz.

   carrier frequency (car)
      Reference position for the axis, in hertz, used together with ``sw``,
      ``obs``, and ``size`` to construct a unit-conversion axis.

   unit-conversion object
      An nmrglue object created from axis metadata that converts between array
      points, hertz, ppm, and other supported coordinate units.

Related Python array and numerical APIs include
:external+numpy:py:class:`numpy.ndarray`,
:external+numpy:py:func:`numpy.fft.fft`,
:external+scipy:py:mod:`scipy.fft`, and
:external+matplotlib:py:mod:`matplotlib.pyplot`.

Format-specific pages
---------------------

.. toctree::
   :maxdepth: 1

   topspin
