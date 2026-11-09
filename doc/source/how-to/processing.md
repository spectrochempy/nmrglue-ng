# Process an FID into a spectrum

The {doc}`processing lesson <../tutorials/processing>` separates
array-only operations from ones that also update format metadata. Use its
processing order as the starting point. The examples here show where the
acquisition format or indirect encoding changes that order.

## Process the directly acquired dimension

Start with the 1D NMRPipe FID. It applies a window, zero fills, transforms,
phases, and keeps the real spectrum. Inspect the spectrum before writing it
back. Then compare the Bruker workflow, which also addresses the digital
filter.

For example, the NMRPipe notebook uses the header returned by one step as
the input to the next. After apodization and zero filling, the core
frequency-domain steps are:

```python
proc_dic, spectrum = ng.pipe_proc.ft(proc_dic, spectrum, auto=True)
proc_dic, spectrum = ng.pipe_proc.ps(proc_dic, spectrum, p0=-17.7, p1=-36.0)
proc_dic, spectrum = ng.pipe_proc.di(proc_dic, spectrum)
```

The phase angles are specific to this FID. Verify the phase before
discarding the imaginary part on a new experiment.

```{toctree}
:maxdepth: 1

../examples/process_pipe_1d
../examples/proc_bruker_1d
```

## Repeat along indirect axes

Process the direct axis first, transpose, then process the indirect axis
using the correct quadrature convention. Compare the ordinary 2D and TPPI
examples before extending the workflow to a 3D stream. In the 3D case,
use `iter3D` to process one plane at a time.

```{toctree}
:maxdepth: 1

../examples/process_pipe_2d
../examples/process_pipe_2d_tppi
../examples/process_pipe_3d
```

## Combine processed branches or derive a covariance spectrum

In JBNMR S7–S9, separate the S3E sum and difference branches before
conversion, process each branch, then recombine. The reported intermediate
and final shapes give checkpoints for the pipeline. In S10, compare the
covariance result with a conventional transform; the displayed figure
helps distinguish an alternative analysis from an extra Fourier step.

```{toctree}
:maxdepth: 1

../jbnmr_examples/s7-s9_s3e_processing
../jbnmr_examples/s10_covariance_processing
```
