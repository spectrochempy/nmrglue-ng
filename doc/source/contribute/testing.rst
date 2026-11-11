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
