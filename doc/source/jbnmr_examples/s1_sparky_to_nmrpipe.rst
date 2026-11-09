.. include:: ../../../examples/jbnmr_examples/s1_sparky_to_nmrpipe/README.rst

The data used in this example is available for
`download. <https://storage.googleapis.com/google-code-archive-downloads/v2/code.google.com/nmrglue/jbnmr_s1_sparky_to_nmrpipe.zip>`_ [29.6 MB]

Listing S1

[:download:`sparky2pipe_convert.py <../../../examples/jbnmr_examples/s1_sparky_to_nmrpipe/sparky2pipe_convert.py>`]

.. literalinclude:: ../../../examples/jbnmr_examples/s1_sparky_to_nmrpipe/sparky2pipe_convert.py

Verified result
---------------

The conversion writes ``data.ft2``, a real ``float32`` array of shape
``(2048, 4096)`` in indirect, direct axis order. Reading the output back
with ``ng.pipe.read("data.ft2")`` yields the same array shape and sample
values as the Sparky input.

.. _plot-verified-nmrpipe-spectrum:

Plot the converted spectrum
---------------------------

Use both ppm axes from the NMRPipe header. Start with the full spectrum
and set the positive contour levels relative to its strongest positive
signal. This example uses Matplotlib.

.. code-block:: python

   import matplotlib.pyplot as plt
   import numpy as np
   import nmrglue as ng

   dic, spectrum = ng.pipe.read("data.ft2")
   x = ng.pipe.make_uc(dic, spectrum, dim=1).ppm_scale()
   y = ng.pipe.make_uc(dic, spectrum, dim=0).ppm_scale()
   levels = spectrum.max() * np.geomspace(0.05, 0.8, num=8)

   fig, ax = plt.subplots()
   ax.contour(x, y, spectrum, levels=levels)
   ax.set(xlim=(x.max(), x.min()), ylim=(y.max(), y.min()),
          xlabel="Direct dimension (ppm)", ylabel="Indirect dimension (ppm)")
   plt.show()
