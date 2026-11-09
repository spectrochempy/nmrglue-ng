# Use synthetic data to test a workflow

A simulated signal with known peaks gives you a reference when learning
a plotting, fitting, or format-writing operation.

## Build a known signal before writing a file

Compare 1D line shapes at a fixed center and width. Combine peaks to make
a synthetic spectrum and inspect what changes with overlap. Then create a
synthetic UCSF file and read it back to test the metadata and output shape
without depending on an external acquisition.

```{toctree}
:maxdepth: 1

../examples/simulate_lineshapes_1d
../examples/simulate_ucsf
```
