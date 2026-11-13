.. include:: ../../../examples/jbnmr_examples/s7-s9_s3e_processing/README.rst

The data used in this example is available for
`download. <https://storage.googleapis.com/google-code-archive-downloads/v2/code.google.com/nmrglue/jbnmr_s7-s9_s3e_processing.zip>`_ [5.42 MiB]

Extract the archive and run the three current scripts linked below, in
listing order, from the extracted directory containing the input data.

Listing S7

[:download:`separate_s3e.py <../../../examples/jbnmr_examples/s7-s9_s3e_processing/separate_s3e.py>`]

.. literalinclude:: ../../../examples/jbnmr_examples/s7-s9_s3e_processing/separate_s3e.py

Listing S8

[:download:`convert.py <../../../examples/jbnmr_examples/s7-s9_s3e_processing/convert.py>`]

.. literalinclude:: ../../../examples/jbnmr_examples/s7-s9_s3e_processing/convert.py

Listing S9

[:download:`xy_s3e.py <../../../examples/jbnmr_examples/s7-s9_s3e_processing/xy_s3e.py>`]

.. literalinclude:: ../../../examples/jbnmr_examples/s7-s9_s3e_processing/xy_s3e.py

Verified result
---------------

The two intermediate NMRPipe FIDs, ``test_sum.fid`` and ``test_dif.fid``,
each contain a ``complex64`` array of shape ``(256, 1500)``. The combined
processed spectrum, ``test.ft2``, reads back as a real ``float32`` array of
shape ``(2048, 8192)``. To display it, use the
:ref:`full-spectrum contour recipe <plot-verified-nmrpipe-spectrum>` with
``test.ft2``.
