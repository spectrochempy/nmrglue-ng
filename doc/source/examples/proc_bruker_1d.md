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

# Process 1D Bruker data

This how-to reads a 1D Bruker FID, removes the digital-filter delay, performs
basic Fourier processing, and compares the result with the processed Bruker
reference data when available.

**{nb-download}`Download notebook (.ipynb) <proc_bruker_1d.ipynb>`**

This executable guide uses the bundled CC0 sucrose Bruker fixture so the
documentation can run without external downloads.

```{code-cell} ipython3
:tags: [hide-cell]

from pathlib import Path

import nmrglue as ng


exp_dir = Path("bruker_pdata/exp1")
if not (exp_dir / "fid").is_file():
    for candidate in [Path.cwd(), *Path.cwd().parents]:
        fixture = candidate / "tests/fixtures/fileio/data/bruker_pdata/exp1"
        if (fixture / "fid").is_file():
            exp_dir = fixture
            break
if not (exp_dir / "fid").is_file():
    raise FileNotFoundError("Run this notebook from the repository checkout.")
```

## Read the Bruker FID and processed reference

```{code-cell} ipython3
bruker_dic, fid = ng.bruker.read(str(exp_dir), read_pulseprogram=False)
proc_dic, reference = ng.bruker.read_pdata(str(exp_dir / "pdata" / "1"))

print(f"FID points: {fid.size}")
print(f"Processed reference shape: {reference.shape}")
```

## Remove the digital-filter delay

Modern Bruker FIDs include a digital-filter group delay. Remove it before the
Fourier transform so the beginning of the FID is aligned for offline processing.

```{code-cell} ipython3
filtered = ng.bruker.remove_digital_filter(bruker_dic, fid)

print(f"Points after correction: {filtered.size}")
```

## Fourier transform and phase the spectrum

This uses basic processing operations adapted to the fixture size and processing
parameters.

```{code-cell} ipython3
procs = proc_dic["procs"]
zero_filled = ng.proc_base.zf_size(filtered, int(procs["SI"]))
frequency_domain = ng.proc_base.fft_positive(zero_filled)
phased = ng.proc_base.ps(frequency_domain, p0=-procs["PHC0"], p1=-procs["PHC1"])
spectrum = phased.real

print(f"Zero-filled points: {zero_filled.size}")
print(f"Spectrum points: {spectrum.size}")
print(f"Reference points: {reference.size}")
```

## Build a ppm axis from Bruker metadata

The raw FID processing changes array values but does not rewrite Bruker
processing metadata. Use the processed reference dictionary to construct a
matching universal dictionary and ppm scale.

```{code-cell} ipython3
udic = ng.bruker.guess_udic(proc_dic, reference)
udic[0]["size"] = spectrum.size
ppm_axis = ng.fileiobase.uc_from_udic(udic).ppm_scale()

print(f"ppm range: {ppm_axis[0]:.3f} to {ppm_axis[-1]:.3f}")
print(f"Largest absolute intensity: {abs(spectrum).max():.3g}")
```

See also `nmrglue.fileio.bruker`, `nmrglue.process.proc_base`, and
`nmrglue.fileio.fileiobase` in the API reference.
