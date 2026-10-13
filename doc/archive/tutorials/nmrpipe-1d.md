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

# Progressive 1D workflow: an experimental spectrum

**{nb-download}`Download notebook (.ipynb) <nmrpipe-1d.ipynb>`** ·
{download}`Download the experimental spectrum <../../../tests/fixtures/fileio/data/jcampdx/epicatechin_1h.jdx>`

This tutorial starts from an experimental, frequency-domain **¹H spectrum** of
(-)-epicatechin. It progressively covers reading a JCAMP-DX file, inspecting
acquisition metadata, constructing a ppm axis, displaying the spectrum,
finding peaks, and integrating explicitly chosen regions.

The file is a versioned synthetic fixture in the nmrglue-ng repository's
[CENAPTNMR project P33](https://doi.org/10.57992/nmrxiv.p33) on nmrXiv. The
dataset is released under [CC0 1.0](https://creativecommons.org/publicdomain/zero/1.0/);
its acquisition metadata identifies a 399.78 MHz ¹H experiment in DMSO-d6.
The sample is real, but the analysis choices below are illustrative and are not
intended as a validated quantitative assay.

This notebook deliberately begins with a processed spectrum. To start from the
matching experimental time-domain FID instead, continue with
{doc}`Processing the matching 1D FID <processing-1d>`.

Relevant API entries: {func}`nmrglue.fileio.jcampdx.read`,
{func}`nmrglue.fileio.jcampdx.guess_udic`,
{func}`nmrglue.analysis.peakpick.pick`, and
{func}`nmrglue.analysis.integration.integrate`.

## 1. Read the JCAMP-DX spectrum

Download the data file above into the same folder as this notebook. The
checkout fallback is only used when the documentation executes from its source
tree; a downloaded notebook uses the local file directly.

```{code-cell} ipython3
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import nmrglue as ng


data_path = Path("epicatechin_1h.jdx")
if not data_path.is_file():
    data_path = (
        Path.cwd().parents[2]
        / "tests/fixtures/fileio/data/jcampdx/epicatechin_1h.jdx"
    )

dic, data = ng.jcampdx.read(str(data_path))

print(f"Points: {data.size}")
print(f"Data type: {data.dtype}")
print(f"JCAMP-DX datatype: {dic['DATATYPE'][0]}")
```

JCAMP-DX is a text-based exchange format. nmrglue returns its numerical data
as a NumPy array and keeps the format tags in `dic`. The array here is real and
already in the frequency domain.

## 2. Inspect the experimental metadata

```{code-cell} ipython3
def first_value(key, default="not recorded"):
    values = dic.get(key)
    return values[0] if values else default


for key in (
    "TITLE",
    "ORIGIN",
    "OWNER",
    ".OBSERVENUCLEUS",
    ".OBSERVEFREQUENCY",
    ".SOLVENTNAME",
    "XUNITS",
    "YUNITS",
):
    print(f"{key}: {first_value(key)}")
```

The header describes the experiment and the units of the stored ordinate and
abscissa. Keep these values with any analysis result: a peak position without
its nucleus, reference frequency, and axis units is incomplete information.

## 3. Build the chemical-shift axis

```{code-cell} ipython3
udic = ng.jcampdx.guess_udic(dic, data)
uc = ng.fileiobase.uc_from_udic(udic)
ppm_axis = uc.ppm_scale()

print(f"Nucleus: {udic[0]['label']}")
print(f"Observation frequency: {udic[0]['obs']:.3f} MHz")
print(f"Spectral width: {udic[0]['sw']:.3f} Hz")
print(f"Sampled range: {ppm_axis[0]:.3f} to {ppm_axis[-1]:.3f} ppm")
```

`guess_udic()` translates the format-specific JCAMP-DX tags into nmrglue's
universal dictionary. `uc_from_udic()` then provides conversions between array
points, Hz, ppm, and time units. The returned ppm scale is descending, so the
usual NMR orientation (high ppm on the left) is obtained by plotting it without
calling `invert_xaxis()`.

## 4. Correct the baseline

```{code-cell} ipython3
# Distribution-based baseline estimate; wd is expressed in points.
spectrum = ng.proc_bl.baseline_corrector(data, wd=50)
print(f"Raw minimum: {data.min():.4g}")
print(f"Corrected minimum: {spectrum.min():.4g}")
```

The correction estimates a slowly varying baseline from the spectrum and
subtracts it. The window is deliberately recorded here because changing it
can change weak peaks and integrals; inspect the result rather than treating a
baseline algorithm as a neutral preprocessing step.

## 5. Display the corrected spectrum

```{code-cell} ipython3
:tags: [hide-input]

fig, ax = plt.subplots(figsize=(10, 4))
ax.plot(ppm_axis, spectrum, color="#176B87", linewidth=0.7)
ax.set(
    xlim=(10.5, -0.5),
    xlabel="¹H chemical shift / ppm",
    ylabel=f"Intensity / {first_value('YUNITS', 'arbitrary units').lower()}",
    title="Experimental (-)-epicatechin ¹H spectrum",
)
ax.spines[["top", "right"]].set_visible(False)
fig.tight_layout()
plt.show()
```

At this stage the plot is an observation, not yet a quantitative result. The
baseline, solvent and reference conventions should be checked before assigning
or integrating peaks.

## 6. Pick peaks with an explicit threshold

```{code-cell} ipython3
# Five percent of the largest signal is suitable for this demonstration.
# msep is a minimum separation in array points, not in ppm.
threshold = 0.05 * spectrum.max()
locations = ng.peakpick.pick(
    spectrum,
    pthres=threshold,
    algorithm="thres",
    msep=250,
    est_params=False,
    cluster=False,
    table=False,
)
peak_indices = np.array([location[0] for location in locations], dtype=int)
peak_order = np.argsort(spectrum[peak_indices])[::-1]

print(f"Threshold: {threshold:.4g}")
print(f"Detected peaks: {peak_indices.size}")
for index in peak_indices[peak_order]:
    print(f"  {ppm_axis[index]:.3f} ppm  (intensity {spectrum[index]:.4g})")
```

Peak picking is parameter-dependent. Raising the threshold suppresses weaker
signals; increasing `msep` merges nearby candidates. Treat a picked list as a
starting point for review, not as an automatic assignment.

## 7. Integrate selected regions

Integration requires regions chosen by the analyst. Here we compare an
aromatic window with a broader aliphatic window; the limits are deliberately
visible in the code and are not claimed to represent a molecular proton count.

```{code-cell} ipython3
limits = np.array([
    [8.0, 6.0],  # aromatic region
    [5.0, 2.7],  # aliphatic region, excluding the DMSO-d6 signal near 2.5 ppm
])
areas = ng.integration.integrate(spectrum, uc, limits, unit="ppm")
relative_areas = areas / areas[0]

for (low, high), area, relative in zip(limits, areas, relative_areas):
    print(
        f"{low:.1f}–{high:.1f} ppm: area={area:.6g}, "
        f"relative-to-aromatic={relative:.3f}"
    )
```

The integral depends on the selected limits, baseline, overlap, and scaling.
For quantitative work, define a reference, estimate baseline/noise, and report
the regions and normalization used. This example demonstrates the mechanics of
`integration.integrate`, not a structure elucidation.

```{code-cell} ipython3
:tags: [hide-input]

fig, ax = plt.subplots(figsize=(10, 4))
ax.plot(ppm_axis, spectrum, color="#176B87", linewidth=0.7)
integral_ax = ax.twinx()
for (low, high), relative in zip(limits, relative_areas):
    region = (ppm_axis <= low) & (ppm_axis >= high)
    region_ppm = ppm_axis[region]
    region_spectrum = spectrum[region]
    dx = np.abs(np.diff(region_ppm))
    region_integral = np.concatenate(
        ([0.0], np.cumsum(
            (region_spectrum[:-1] + region_spectrum[1:]) * 0.5 * dx
        ))
    )
    integral_ax.plot(
        region_ppm,
        region_integral,
        color="#D1495B",
        linewidth=1.2,
        alpha=0.9,
    )
    ax.axvspan(high, low, color="#D1495B", alpha=0.14)
    ax.text(
        (low + high) / 2,
        0.96 * spectrum.max(),
        f"relative area {relative:.2f}",
        ha="center",
        va="top",
        fontsize=8,
    )
integral_ax.set_ylabel("Cumulative integral / a.u. ppm", color="#D1495B")
integral_ax.tick_params(axis="y", colors="#D1495B")
ax.set(
    xlim=(10.5, -0.5),
    xlabel="¹H chemical shift / ppm",
    ylabel=f"Intensity / {first_value('YUNITS', 'arbitrary units').lower()}",
    title="Explicit integration regions",
)
ax.spines[["top", "right"]].set_visible(False)
fig.tight_layout()
plt.show()
```

The red curves are cumulative integrals within the selected regions; each one
starts at zero at its high-ppm boundary. Their steps show where signal
contributes without plotting unrelated parts of the spectrum. They remain a
visual diagnostic here: baseline correction and a calibrated reference are
still needed before interpreting integral values quantitatively.

## Where to go next

- Continue with {doc}`Processing the matching 1D FID <processing-1d>` to read
  the original JEOL time-domain signal and Fourier-transform it.
- Return to {doc}`Getting started <../getting-started/index>` for a compact,
  format-independent synthetic example.
- Use {doc}`../tutorials/index` for the 2D axes and contour tutorial.
- Consult {doc}`../how-to/index` for focused recipes and migration examples.
- Look up the complete {doc}`API reference <../reference/index>`.
