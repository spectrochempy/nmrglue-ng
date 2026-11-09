# Inspect spectra and annotate peaks

The {doc}`plotting lesson <../tutorials/plotting>` builds the axes and draws
the first contour plot. Here, use the same axis objects to answer three
questions in order: is the acquisition usable, where are the peaks, and which
regions should be measured?

## Start with a trace

Plot the real and imaginary parts of a FID against time to inspect decay and
phase. After Fourier transformation, use a ppm axis to compare chemical
shifts. Listing S2–S3 shows both views of experimental data, so compare the
axis labels and units before comparing intensities.

```{toctree}
:maxdepth: 1

../examples/plot_1d_time
../examples/plot_1d_freq
../jbnmr_examples/s2_s3_1d_plotting
```

## Move to two dimensions

A contour plot needs one coordinate array per data axis. Start in points if
you need to debug indexing; move to ppm once the header is calibrated.
The experimental S4 plot is a reference for the resulting display.
Keep the contour levels fixed when comparing different views of the same
spectrum.

```{toctree}
:maxdepth: 1

../examples/plot_2d_spectrum_pts
../examples/plot_2d_spectrum
../jbnmr_examples/s4_2d_plotting
```

## Mark regions and compare planes

Add assignment labels when you know peak identities. Add boxes when you need
to show exactly which region will be integrated. For a 3D experiment, extract
strips at selected positions instead of projecting away a whole dimension.
Listing S11 shows the result as a row of comparable strips.

```{toctree}
:maxdepth: 1

../examples/plot_2d_assignments
../examples/plot_2d_boxes
../jbnmr_examples/s11_strip_plots
```
