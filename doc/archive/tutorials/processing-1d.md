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

# Processing a Bruker 1D FID

**{nb-download}`Download notebook (.ipynb) <processing-1d.ipynb>`** ·
[Zenodo dataset (400/700 MHz)](https://zenodo.org/records/11341174)

This tutorial starts from a real Bruker time-domain signal rather than a
processed spectrum. We use one of the commercial-honey ¹H spectra from the
[Zenodo dataset](https://doi.org/10.5281/zenodo.11341174), which contains raw
FID data, acquisition and processing parameters, and the processed `1r`
reference in the same experiment directory. The dataset is released under
[CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) (Maulidiani,
Universiti Malaysia Terengganu).

Download `400MHz.zip` from Zenodo and extract it so that the selected
experiment is available as `400MHz/H1/10/`. The code below also falls back to
the small CC0 fixture bundled with nmrglue-ng, so that the notebook remains
executable in a clean checkout.

## Read the data and its metadata

```{code-cell} ipython3
from pathlib import Path
import tempfile
import zipfile

import matplotlib.pyplot as plt
import nmrglue as ng
import numpy as np


dataset_candidates = (
    Path("400MHz/H1/10"),
    Path.home() / "GitHub/data/400MHz/H1/10",
    Path.cwd().parents[2] / "data/400MHz/H1/10",
)
exp_dir = next((path for path in dataset_candidates if (path / "fid").is_file()), None)
dataset_label = "commercial honey (400 MHz)"
if exp_dir is None:
    archive_candidates = (
        Path.home() / "GitHub/data/400MHz.zip",
        Path.cwd().parents[2] / "data/400MHz.zip",
    )
    archive = next((path for path in archive_candidates if path.is_file()), None)
    if archive is not None:
        extraction_dir = Path(tempfile.mkdtemp(prefix="nmrglue-400MHz-"))
        with zipfile.ZipFile(archive) as archive_file:
            archive_file.extractall(extraction_dir)
        exp_dir = extraction_dir / "400MHz/H1/10"
if exp_dir is None:
    exp_dir = Path.cwd().parents[2] / "tests/fixtures/fileio/data/bruker_pdata/exp1"
    dataset_label = "bundled sucrose fixture"

if not exp_dir.is_dir():
    raise FileNotFoundError(
        "Extract Zenodo's 400MHz.zip or run this notebook from the nmrglue-ng checkout."
    )

dic, fid = ng.bruker.read(str(exp_dir))
proc_dic, processed_reference = ng.bruker.read_pdata(
    str(exp_dir / "pdata" / "1")
)
acqus = dic["acqus"]
procs = proc_dic["procs"]

print(f"FID points: {fid.size} complex points")
print(f"Nucleus: {acqus['NUC1']}")
print(f"Observation frequency: {acqus['SFO1']:.3f} MHz")
print(f"Spectral width: {acqus['SW_h']:.1f} Hz")
print(f"Digital filter: DSPFVS={acqus['DSPFVS']}, DECIM={acqus['DECIM']}, GRPDLY={acqus['GRPDLY']}")
print(f"Stored phase: PHC0={procs['PHC0']:.5f}, PHC1={procs['PHC1']:.5f} degrees")
print(f"Dataset: {dataset_label}")
```

`ng.bruker.read()` returns a metadata dictionary and the complex FID. The
second call reads the processing metadata from `pdata/1`; keeping these two
objects separate makes it easy to try a different processing recipe. See the
<a href="../reference/bruker.html"><code>nmrglue.bruker</code> API</a> for the
other Bruker layouts and options supported by the reader.

## Inspect the FID

```{code-cell} ipython3
:tags: [hide-input]

time_axis = np.arange(fid.size) / acqus["SW_h"]
fig, ax = plt.subplots(figsize=(10, 3))
ax.plot(time_axis, fid.real, color="#536878", linewidth=0.7)
ax.set(
    xlabel="Acquisition time / s",
    ylabel="FID real part / a.u.",
    title=f"{dataset_label.capitalize()} — ¹H Bruker FID",
)
ax.spines[["top", "right"]].set_visible(False)
fig.tight_layout()
plt.show()
```

## Prepare the FID

```{code-cell} ipython3
# Remove the instrument's digital-filter delay.
filtered_fid = ng.bruker.remove_digital_filter(dic, fid)

# Apply a gentle exponential window before transforming.
# ``proc_base.em`` expects the line-broadening value in points.
apodized_fid = ng.proc_base.em(
    filtered_fid,
    lb=procs["LB"] / acqus["SW_h"],
)

print(f"Points after digital-filter correction: {filtered_fid.size}")
print(f"Exponential line broadening: {procs['LB']:.3f} Hz")
```

The first operation corrects an acquisition-specific delay using the Bruker
parameters. The window controls the trade-off between resolution and
signal-to-noise; try changing `LB` and re-running the cell. The functions used
here are documented in the <a href="../reference/bruker.html"><code>bruker</code>
API</a> and the <a href="../reference/proc_base.html"><code>processing</code>
API</a>.

## Fourier-transform the signal

Zero-filling changes the number of points used to display the spectrum; it
does not add experimental information. The Fourier transform converts the
time-domain FID into a complex frequency-domain spectrum.

```{code-cell} ipython3
zero_filled = ng.proc_base.zf_size(apodized_fid, int(procs["SI"]))
raw_spectrum = ng.proc_base.fft_positive(zero_filled)

print(f"Zero-filled points: {zero_filled.size}")
print(f"Spectrum points: {raw_spectrum.size}")
```

## Apply a phase correction and build the ppm axis

```{code-cell} ipython3
# Bruker processing stores PHC0/PHC1 with the opposite sign to proc_base.ps.
phased_spectrum = ng.proc_base.ps(
    raw_spectrum,
    p0=-procs["PHC0"],
    p1=-procs["PHC1"],
)
spectrum = phased_spectrum.real

# Build the ppm scale from the processed-data parameters. The stored `1r` is
# only used here to provide the size information expected by `guess_udic`.
processed_udic = ng.bruker.guess_udic(proc_dic, processed_reference)
processed_udic[0]["size"] = spectrum.size
uc = ng.fileiobase.uc_from_udic(processed_udic)
ppm_axis = uc.ppm_scale()

print(f"ppm range: {ppm_axis[0]:.3f} to {ppm_axis[-1]:.3f}")
```

The phase values come from `pdata/1/procs`. In this dataset the sign is
reversed because Bruker and `proc_base.ps()` use opposite phase conventions.
For data without recorded phase values, a later tutorial will show how to
adjust `p0` and `p1` interactively.

## Plot the spectrum

```{code-cell} ipython3
:tags: [hide-input]

fig, ax = plt.subplots(figsize=(10, 4))
ax.plot(ppm_axis, spectrum / np.max(np.abs(spectrum)), color="#176B87", linewidth=0.8)
ax.set(
    xlim=(8, -1),
    xlabel="¹H chemical shift / ppm",
    ylabel="Normalised intensity",
    title="Processed ¹H spectrum",
)
ax.spines[["top", "right"]].set_visible(False)
fig.tight_layout()
plt.show()
```

At this point `spectrum` is an ordinary NumPy array and `ppm_axis` is a matching
axis. You can pass both directly to any Matplotlib or NumPy workflow, select a
region with a boolean mask, or continue with peak picking and integration.
The detailed reader-versus-TopSpin comparison is intentionally left for a
specialized processing note.

## Where to go next

- Use the [progressive 1D workflow](nmrpipe-1d.md) for peak picking and
  explicit integration on an experimental spectrum.
- Return to {doc}`Getting started <../getting-started/index>` for the compact
  synthetic workflow.
- Consult {doc}`../how-to/index` for focused processing recipes.
