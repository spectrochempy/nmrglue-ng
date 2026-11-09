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
values as the Sparky input. To display the converted spectrum, use the
:doc:`2D plotting example <s4_2d_plotting>` and set the input filename to
``data.ft2``. Adjust the contour levels to suit this spectrum.
