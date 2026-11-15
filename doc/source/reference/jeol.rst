JEOL JDF
========

Use ``nmrglue.jeol.read(path)`` to load a JEOL ``.jdf`` file. It returns
a dictionary containing the file header and acquisition or processing
parameters, followed by the data. The reader loads the file into memory.

.. code-block:: python

   import nmrglue as ng

   dic, data = ng.jeol.read("experiment.jdf")

Reading and writing
-------------------

The reader handles real and complex 1D data and the standard ``two_d``
layout. In a 2D array, the direct dimension F2 is last. When both axes
are complex and the file stores four sections, alternating rows hold
the two indirect components.
Check the acquisition mode before processing those rows as an
indirect dimension.

The reader raises ``NotImplementedError`` for ``small_two_d`` and
files with more than two dimensions. If the section count and axis types
are inconsistent, it can warn and return a list of sections. Check the
result before passing it to array-based processing or ``guess_udic()``.
The module provides neither a JDF writer nor a low-memory reader.

Uniform complex/complex acquisitions
------------------------------------

Use ``nmrglue.interop.normalize(nmrglue.interop.read(path),
conjugation="none")`` to expose the two stored section pairs on a
leading branch axis, followed by the F1 and F2 time axes in seconds.
The qualified uniform profile requires a zero-based valid window and
regular time axes consistent with the acquisition parameters.
The physical F1 quadrature mode remains undetermined.

Use ``conjugation="conjugate", legacy_presentation=True`` for the
historical signed and interleaved rows. For uniform sampling, interop
reports F1 sampling as ``regular-paired`` and repeats each F1 time
for the two rows acquired at that time.

Axis metadata
-------------

For an array result, ``guess_udic(dic, data)`` uses the JDF parameters
to describe the axes in NumPy order. Verify the sweep widths and
references before using the dictionary to build calibrated coordinates.

.. currentmodule:: nmrglue.fileio.jeol

.. autosummary::
   :toctree: generated/

   read
   guess_udic
