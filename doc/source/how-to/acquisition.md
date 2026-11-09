# Combine replicates or separate interleaved acquisitions

Decide what each stored trace represents before processing. Average
replicate measurements of the same experiment. Keep measurements taken at
different echo times or mixing times separate.

## Coadd matched acquisitions

Start with the 1D example: check that the input shapes and axes agree, add
sample by sample, divide by the number of acquisitions if you want an
average, and verify the output after writing. The 2D example repeats this
for planes. The pseudo-3D example preserves the extra experiment index.

```{toctree}
:maxdepth: 1

../examples/coadd_1d_pipe
../examples/coadd_2d_pipe
../examples/coadd_pseudo3d_pipe
```

## Separate a series without changing trace order

First separate a 1D Agilent series. Then compare the 2D Agilent and Bruker
recipes, where separation has to preserve the indirect dimension. Use
JBNMR S5 and S6 to see why the loop order matters: S5 selects a slice for
each echo time, while S6 keeps each pair of quadrature traces together.
Their result sections give the verified sizes and output counts.

In S5, `data[:, i, :]` selects a single echo time. In S6, the input is
read as a trace matrix, and consecutive traces for the same acquisition
increment are preserved as a pair. The two operations solve the same
problem with different storage layouts: the verified outputs contain six
and ten FID directories, respectively.

```{toctree}
:maxdepth: 1

../examples/separate_1d_varian
../examples/separate_2d_varian
../examples/separate_2d_bruker
../jbnmr_examples/s5_separate_interleaved
../jbnmr_examples/s6_separate_inner_phase
```
