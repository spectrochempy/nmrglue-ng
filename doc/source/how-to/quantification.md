# Measure peaks, regions, and relaxation

Start from a phased spectrum and a known axis. Choose a measurement that
matches the question: a position, an integrated region, or a trajectory
across experiments.

## Find peaks and integrate regions

Peak picking gives positions to inspect; integration sums a specified
region. Compare the 1D and 2D integration examples and check that the
displayed regions cover the intended peaks. Keep track of the units used
for the bounds and reported areas or volumes.

```{toctree}
:maxdepth: 1

../examples/peakpick
../examples/integrate_1d
../examples/integrate_2d
```

## Fit a series of measurements

Start with the T1 example to see how a fitted curve relates to the observed
trajectory. Then work through JBNMR S12–S15, which extracts regions across
spectra, normalizes the trajectories, and fits relaxation rates. Compare
the published fit table and plots with your output.

```{toctree}
:maxdepth: 1

../examples/fitting_t1_data
../jbnmr_examples/s12-s15_relaxation_analysis
```
