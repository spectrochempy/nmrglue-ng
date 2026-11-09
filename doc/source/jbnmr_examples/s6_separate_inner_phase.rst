.. include:: ../../../examples/jbnmr_examples/s6_separate_inner_phase/README.rst

The data used in this example is available for
`download. <https://storage.googleapis.com/google-code-archive-downloads/v2/code.google.com/nmrglue/jbnmr_s6_seperate_inner_phase.zip>`_ [12.42 MB]

Extract the archive and run the current script linked below from the
extracted directory containing the input data.

Listing S6

[:download:`separate.py <../../../examples/jbnmr_examples/s6_separate_inner_phase/separate.py>`]

.. literalinclude:: ../../../examples/jbnmr_examples/s6_separate_inner_phase/separate.py

Verified result
---------------

Reading the original acquisition as a flat trace matrix yields shape
``(1360, 1250)``. The script writes ten Agilent/Varian FID directories,
from ``nredor_2.fid`` to ``nredor_36.fid``. Reading each with
``ng.varian.read(path, as_2d=True)`` yields a ``complex64`` array of shape
``(136, 1250)`` with both indirect quadrature traces in acquisition order.
