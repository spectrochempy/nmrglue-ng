---
jupytext:
  text_representation:
    extension: .md
    format_name: myst
kernelspec:
  display_name: Python 3
  language: python
  name: python3
---

# Getting started

In a few minutes, you will read a time-domain NMR signal, inspect its metadata,
apply a Fourier transformation, construct a chemical-shift axis, detect the
peaks, and plot the resulting spectrum.

This guide starts after **nmrglue-ng 1.0.0** has been installed. Choose one of
the {doc}`installation procedures <../install>` first, then return here with
that environment active.

The example signal is stored in the **NMRPipe** file format. NMRPipe is one of
the formats supported by nmrglue-ng; it is used here as a compact way to keep
the time-domain array and the acquisition metadata together in one
redistributable file. The same overall workflow—read, inspect, process, pick
peaks, and plot—also applies to data from other supported spectrometer and
processing formats, although the reader function and metadata may differ.

**{nb-download}`Download this page as a notebook <index.ipynb>`** ·
{download}`Download the synthetic NMRPipe data <synthetic_1d_time.fid>`

## Read the time-domain signal

Download the data file above into the same directory as your notebook or
Python script.

```{code-cell} ipython3
import matplotlib.pyplot as plt
import nmrglue as ng
import numpy as np

dic, fid = ng.pipe.read("synthetic_1d_time.fid")

print(f"Points: {fid.size}")
print(f"Data type: {fid.dtype}")
print(f"Time-domain data: {dic['FDF2FTFLAG'] == 0}")
```

`dic` contains the NMRPipe header and `fid` is a complex NumPy array.

## Inspect the acquisition metadata

```{code-cell} ipython3
udic = ng.pipe.guess_udic(dic, fid)
direct = udic[0]

print(f"Nucleus: {direct['label']}")
print(f"Spectral width: {direct['sw']:.0f} Hz")
print(f"Observation frequency: {direct['obs']:.0f} MHz")
print(f"Carrier: {direct['car'] / direct['obs']:.2f} ppm")
```

These values define the relation between array positions and physical units.
Always check them before interpreting a spectrum from an unfamiliar file. The
reader-specific header has now been translated into nmrglue-ng's universal
dictionary, which gives later steps a format-independent description of the
spectral dimension.

## Transform the FID into a spectrum

```{code-cell} ipython3
# These processing functions operate on NumPy arrays, independently of the
# format used to store the original data.
fid = ng.proc_base.zf_size(fid, size=8192)

# The Fourier transform converts time into frequency. This sign convention
# matches the complex FID supplied with the example.
spectrum = ng.proc_base.fft_positive(fid)

# This synthetic signal needs no phase correction; keep its real component.
spectrum = ng.proc_base.di(spectrum)
```

Zero filling makes the plotted line smoother but does not increase the
intrinsic spectral resolution. Real experimental data will commonly need
apodization, phase correction, and baseline correction as well. Processing is
performed here with {mod}`nmrglue.process.proc_base`, not with NMRPipe-specific
processing wrappers.

## Construct a ppm axis and find the peaks

```{code-cell} ipython3
# Describe the processed dimension, then create an axis from generic metadata.
direct.update(size=spectrum.size, complex=False, time=False, freq=True)
ppm = ng.fileiobase.uc_from_udic(udic).ppm_scale()

# Locate positive peaks above 10% of the largest intensity.
threshold = 0.10 * spectrum.max()
peak_locations = ng.peakpick.pick(
    spectrum,
    pthres=threshold,
    algorithm="downward",
    est_params=False,
    cluster=False,
    table=False,
)
peak_indices = np.array([location[0] for location in peak_locations])

print("Detected peaks:")
for index in peak_indices:
    print(f"  {ppm[index]:.3f} ppm  (intensity {spectrum[index]:.1f})")
```

The threshold is deliberately simple for this clean synthetic spectrum. On
experimental data, choose it from the noise level and verify the detected
peaks visually; there is no universal percentage that suits every spectrum.

## Plot the result

```{code-cell} ipython3
time_ms = np.arange(fid.size) / direct["sw"] * 1000

fig, (time_ax, spectrum_ax) = plt.subplots(1, 2, figsize=(10, 3.8))

time_ax.plot(time_ms, fid.real, color="#176B87", linewidth=1)
time_ax.set(
    xlim=(0, 120),
    xlabel="Time / ms",
    ylabel="Signal / a.u.",
    title="Time-domain signal (FID)",
)

spectrum_ax.plot(ppm, spectrum, color="#176B87", linewidth=1)
marker_y = spectrum[peak_indices] + 0.06 * spectrum.max()
spectrum_ax.scatter(
    ppm[peak_indices],
    marker_y,
    color="#D1495B",
    marker="v",
    zorder=3,
)
for index, y_position in zip(peak_indices, marker_y):
    spectrum_ax.annotate(
        f"{ppm[index]:.2f}",
        (ppm[index], y_position),
        xytext=(0, 7),
        textcoords="offset points",
        ha="center",
        fontsize=8,
    )
spectrum_ax.set(
    xlim=(9, -1),
    ylim=(-0.05 * spectrum.max(), 1.25 * spectrum.max()),
    xlabel="¹H chemical shift / ppm",
    ylabel="Intensity / a.u.",
    title="Transformed spectrum and detected peaks",
)

for axis in (time_ax, spectrum_ax):
    axis.spines[["top", "right"]].set_visible(False)
fig.tight_layout()
plt.show()
```

The three frequency components hidden in the FID become distinct peaks near
7.25, 3.55, and 1.25 ppm.

```{admonition} About this example data
:class: note

This is a deterministic synthetic signal for learning the workflow, not a real
sample and not evidence for a chemical assignment. It contains three damped
resonances plus weak seeded noise. The source and numerical validation are in
{download}`generate_synthetic_1d.py <generate_synthetic_1d.py>`.
```

## Where to go next

- Use {doc}`../tutorials/index` to choose a longer executable walkthrough,
  including the 2D axes and contour tutorial.
- Consult {doc}`../how-to/index` for focused recipes and migration examples.
- Look up modules and functions in the {doc}`API reference <../reference/index>`.

```{toctree}
:maxdepth: 1
:hidden:

../install
```
