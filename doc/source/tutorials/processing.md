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

# Processing NMR data

Processing functions operate on NumPy arrays. Some operate only on the values;
format-aware functions can also update the associated header metadata. This
notebook compares both approaches and follows a 1D Bruker FID through basic
processing.

**{nb-download}`Download notebook (.ipynb) <processing.ipynb>`** ·
{download}`Download small 2D NMRPipe time-domain data <../../../tests/fixtures/fileio/data/nmrpipe_2d_time.fid>` ·
[Bruker 400 MHz example dataset (Zenodo)](https://doi.org/10.5281/zenodo.11341174)

The Bruker section uses the Zenodo commercial-honey dataset if its 400 MHz
experiment is extracted as `400MHz/H1/10/` or the `400MHz.zip` archive is
available. When neither is present, it uses the small bundled CC0 sucrose
fixture instead. The NMRPipe example is deterministic synthetic test data.
The Zenodo data are released under [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/)
by Maulidiani (Universiti Malaysia Terengganu).

The hidden setup cells locate and read the input data. Reveal them to adapt the
paths; the processing steps remain visible below.

```{code-cell} ipython3
:tags: [hide-cell]

from pathlib import Path
from tempfile import TemporaryDirectory
from zipfile import ZipFile

import numpy as np
import nmrglue as ng


def read_bruker_example(exp_dir):
    bruker_dic, fid = ng.bruker.read(
        str(exp_dir), read_pulseprogram=False
    )
    proc_dic, processed_reference = ng.bruker.read_pdata(
        str(exp_dir / "pdata" / "1")
    )
    return bruker_dic, fid, proc_dic, processed_reference


directory_candidates = (
    Path("400MHz/H1/10"),
    Path.home() / "GitHub/data/400MHz/H1/10",
    Path.cwd().parents[2] / "data/400MHz/H1/10",
)
bruker_exp = next(
    (path for path in directory_candidates if (path / "fid").is_file()),
    None,
)
dataset_label = "commercial honey (400 MHz)"

if bruker_exp is not None:
    bruker_dic, fid, proc_dic, processed_reference = read_bruker_example(bruker_exp)
else:
    archive_candidates = (
        Path("400MHz.zip"),
        Path.home() / "GitHub/data/400MHz.zip",
        Path.cwd().parents[2] / "data/400MHz.zip",
    )
    archive = next((path for path in archive_candidates if path.is_file()), None)
    if archive is not None:
        with TemporaryDirectory(prefix="nmrglue-400MHz-") as extraction_dir:
            with ZipFile(archive) as archive_file:
                archive_file.extractall(extraction_dir)
            bruker_exp = Path(extraction_dir) / "400MHz/H1/10"
            if not (bruker_exp / "fid").is_file():
                raise FileNotFoundError("The archive does not contain 400MHz/H1/10/fid")
            bruker_dic, fid, proc_dic, processed_reference = read_bruker_example(bruker_exp)
    else:
        bruker_exp = Path.cwd().parents[2] / "tests/fixtures/fileio/data/bruker_pdata/exp1"
        if not (bruker_exp / "fid").is_file():
            raise FileNotFoundError(
                "Extract Zenodo's 400MHz.zip or run this notebook from the repository."
            )
        bruker_dic, fid, proc_dic, processed_reference = read_bruker_example(bruker_exp)
        dataset_label = "bundled sucrose fixture"

acqus = bruker_dic["acqus"]
procs = proc_dic["procs"]
```

```{code-cell} ipython3
:tags: [hide-cell]

nmrpipe_filename = "nmrpipe_2d_time.fid"
nmrpipe_path = Path(nmrpipe_filename)
if not nmrpipe_path.is_file():
    for candidate in [Path.cwd(), *Path.cwd().parents]:
        fixture = candidate / "tests/fixtures/fileio/data" / nmrpipe_filename
        if fixture.is_file():
            nmrpipe_path = fixture
            break
if not nmrpipe_path.is_file():
    raise FileNotFoundError(f"Download {nmrpipe_filename} into {Path.cwd()}")

nmrpipe_dic, nmrpipe_time_data = ng.pipe.read(str(nmrpipe_path))
```

## Process a 1D Bruker FID

Begin by removing the acquisition digital-filter delay. An exponential window
can improve sensitivity at the cost of some resolution; here the line broadening
comes from the Bruker processing parameters.

```{code-cell} ipython3
print(f"Dataset: {dataset_label}")
filtered_fid = ng.bruker.remove_digital_filter(bruker_dic, fid)
apodized_fid = ng.proc_base.em(
    filtered_fid,
    lb=procs["LB"] / acqus["SW_h"],
)

print(f"Raw FID points: {fid.size}")
print(f"Points after digital-filter correction: {filtered_fid.size}")
print(f"Exponential line broadening: {procs['LB']:.3f} Hz")
```

Zero-filling sets the number of points in the transformed spectrum; it does not
add experimental resolution. `fft_positive()` transforms the apodized FID into
the frequency domain.

```{code-cell} ipython3
zero_filled = ng.proc_base.zf_size(apodized_fid, int(procs["SI"]))
raw_spectrum = ng.proc_base.fft_positive(zero_filled)

print(f"Zero-filled points: {zero_filled.size}")
print(f"Frequency-domain points: {raw_spectrum.size}")
```

The processing file records zero- and first-order phase values. For this Bruker
convention, their signs are reversed relative to `proc_base.ps()`. Check the
phase convention when working with data from another format or application.

```{code-cell} ipython3
phased_spectrum = ng.proc_base.ps(
    raw_spectrum,
    p0=-procs["PHC0"],
    p1=-procs["PHC1"],
)
spectrum = phased_spectrum.real

# Use the processed reference for axis metadata and the transformed FID for size.
processed_udic = ng.bruker.guess_udic(proc_dic, processed_reference)
processed_udic[0]["size"] = spectrum.size
ppm_axis = ng.fileiobase.uc_from_udic(processed_udic).ppm_scale()

print(f"ppm range: {ppm_axis[0]:.3f} to {ppm_axis[-1]:.3f}")
```

These `proc_base` operations change array values but do not rewrite the Bruker
metadata. The universal dictionary and unit-conversion object use the
processing reference to construct a matching chemical-shift axis.

## View the 1D processing result

Matplotlib is optional. Follow the installation instructions in
[Visualizing NMR data](plotting.md) to display the filtered FID and phased
spectrum.

The plotting code is hidden by default so the figure stays prominent. Reveal it
to inspect or adapt the display settings.

```{code-cell} ipython3
:tags: [hide-input]

import matplotlib.pyplot as plt


time_ms = np.arange(filtered_fid.size) / acqus["SW_h"] * 1e3
fid_scale = np.max(np.abs(filtered_fid))
spectrum_scale = np.max(np.abs(spectrum))
dataset_title = dataset_label[0].upper() + dataset_label[1:]

fig, (fid_ax, spectrum_ax) = plt.subplots(1, 2, figsize=(10, 3.8))
fid_ax.plot(
    time_ms,
    filtered_fid.real / fid_scale,
    color="#536878",
    linewidth=0.7,
)
fid_ax.set(
    xlim=(0, 120),
    xlabel="Acquisition time / ms",
    ylabel="Normalised signal",
    title=f"{dataset_title} — filtered ¹H FID",
)
spectrum_ax.plot(
    ppm_axis,
    spectrum / spectrum_scale,
    color="#176B87",
    linewidth=0.7,
)
spectrum_ax.set(
    xlim=(ppm_axis[0], ppm_axis[-1]),
    xlabel="¹H chemical shift / ppm",
    ylabel="Normalised intensity",
    title=f"{dataset_title} — processed ¹H spectrum",
)
for axis in (fid_ax, spectrum_ax):
    axis.spines[["top", "right"]].set_visible(False)
fig.tight_layout()
plt.show()
```

## Process NMRPipe data with array-only functions

The small NMRPipe time-domain example is 2D and synthetic. Apply an apodization
and Fourier transform directly to a copy of its array:

```{code-cell} ipython3
array_windowed = ng.proc_base.sp(
    nmrpipe_time_data.copy(),
    off=0.35,
    end=0.98,
    pow=1.0,
)
array_spectrum = ng.proc_base.fft_positive(array_windowed)

print(f"Input array shape: {nmrpipe_time_data.shape}")
print(f"Array-only result shape: {array_spectrum.shape}")
```

These functions receive only the array, so the NMRPipe header is not updated
along with the transformed data.

## Process NMRPipe data with metadata-aware functions

The `pipe_proc` functions receive both the header and data array. They update
the NMRPipe spectral parameters as processing changes the data.

```{code-cell} ipython3
processed_dic, processed_data = ng.pipe_proc.sp(
    nmrpipe_dic,
    nmrpipe_time_data.copy(),
    off=0.35,
    end=0.98,
    pow=1.0,
    c=1.0,
)
processed_dic, processed_data = ng.pipe_proc.zf(
    processed_dic, processed_data, auto=True
)
processed_dic, processed_data = ng.pipe_proc.ft(
    processed_dic, processed_data, auto=True
)
processed_dic, processed_data = ng.pipe_proc.ps(
    processed_dic, processed_data, p0=0.0, p1=0.0
)
processed_dic, processed_data = ng.pipe_proc.di(processed_dic, processed_data)
processed_dic, processed_data = ng.pipe_proc.tp(processed_dic, processed_data)

processed_udic = ng.pipe.guess_udic(processed_dic, processed_data)
print(f"Processed shape: {processed_data.shape}")
print(f"Universal-dictionary dimensions: {processed_udic['ndim']}")
for dim in range(processed_udic["ndim"]):
    axis = processed_udic[dim]
    print(f"Dimension {dim}: {axis['size']} points, frequency-domain={axis['freq']}")
```

For larger 3D or 4D datasets, a full in-memory copy may be impractical. The
[Low-memory guide](low-memory.md) introduces on-demand slicing, and the
[processing examples](../how-to/processing) show plane-by-plane `iter3D` processing.
