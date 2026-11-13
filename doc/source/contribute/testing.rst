Tests and scientific validation
===============================

Start with a test that reproduces the reported behavior. Run the affected
test module while developing, then use the self-contained profile to
check changes shared across modules.

.. code-block:: console

   python -m pytest tests/fileio/test_pipe.py
   python -m pytest -m "not dataset and not external_software"

Dataset tests use the optional local ``data/`` corpus. External-software
tests require programs such as NMRPipe. Tests that need an optional
dependency use the ``optional_dependency`` marker. In a pull request,
record the commands, results, and reasons for any skips.

Data and provenance
-------------------

Use a small synthetic fixture when it captures the behavior. For a real
dataset, record its source, redistribution terms, and checksum where
applicable. Copy data to a temporary directory before modifying it in a
test.

For changes that affect axes, units, quadrature, or sample values, derive
the expected result from the format specification or an independent
reference. State the reason for any numerical tolerance. Compare axis
values and sample order as well as array shape when those are part of
the behavior being changed.

.. _developer-linear-prediction-notes:

Linear prediction
-----------------

The notation for linear prediction coefficients and roots follows
Jeffrey C. Hoch and Alan S. Stern's *NMR Data Processing*. The
implementations prioritize simplicity, and source comments marked
``SPEED`` and ``STABILITY`` identify possible improvements. The module
does not implement reduced-order LP-SVD or LP-TLS. The HSVD root solver
is an example of a reduced-order method.

When changing a solver, compare against signals with known parameters.
For routines that apply the same operation to each row, compare the 2D
result with processing the same rows individually. See
:doc:`../reference/proc_lp` for the available functions.
