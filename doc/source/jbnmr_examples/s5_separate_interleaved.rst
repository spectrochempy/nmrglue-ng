.. include:: ../../../examples/jbnmr_examples/s5_separate_interleaved/README.rst

The data used in this example is available for
`download. <https://storage.googleapis.com/google-code-archive-downloads/v2/code.google.com/nmrglue/jbnmr_s5_seperate_interleaved.zip>`_ [78.42 MB]

Extract the archive and run the current script linked below from the
extracted directory containing the input data.

Listing S5

[:download:`separate.py <../../../examples/jbnmr_examples/s5_separate_interleaved/separate.py>`]

.. literalinclude:: ../../../examples/jbnmr_examples/s5_separate_interleaved/separate.py

Verified result
---------------

The original Agilent/Varian array has shape ``(1536, 6, 1200)``. The script
writes six Agilent/Varian FID directories, from ``techo_180.fid`` to
``techo_14580.fid`` in acquisition order. Reading each with
``ng.varian.read(path, as_2d=True)`` yields a ``complex64`` array of shape
``(1536, 1200)`` matching the slice for that echo time.
