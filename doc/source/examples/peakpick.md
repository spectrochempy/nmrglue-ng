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

(peakpick)=
# Pick peaks in 1D and 2D spectra

`nmrglue.peakpick.pick` can pick peaks in multidimensional NMR datasets. The
same function call is used for 1D and 2D spectra; only plotting and annotation
change.

**{nb-download}`Download notebook (.ipynb) <peakpick.ipynb>`** ·
**{download}`Download 1D example data <../_data/historical_examples/example_integrate_1d.zip>`** ·
**{download}`Download 2D example data <../_data/historical_examples/example_process_pipe_2d.zip>`**

```{code-cell} ipython3
:tags: [hide-cell]

from pathlib import Path
from tempfile import TemporaryDirectory
from zipfile import ZipFile

import matplotlib.pyplot as plt
import nmrglue as ng
import numpy as np


work_dir = TemporaryDirectory(prefix="nmrglue-peakpick-")
work_path = Path(work_dir.name)


def extract_fixture(archive_name):
    for candidate in [Path.cwd(), *Path.cwd().parents]:
        fixture = candidate / "doc/source/_data/historical_examples" / archive_name
        if fixture.is_file():
            with ZipFile(fixture) as archive:
                archive.extractall(work_path)
            return
    raise FileNotFoundError(f"Download {archive_name} into doc/source/_data/historical_examples")


extract_fixture("example_integrate_1d.zip")
extract_fixture("example_process_pipe_2d.zip")
```

## Pick peaks in a 1D spectrum

Read the processed 1D spectrum, build a unit converter for ppm labels, then pick
all peaks above a positive threshold. The plotting code marks each detected peak
on the spectrum and draws the threshold as a dashed line.

```{code-cell} ipython3
# Read the spectrum and create the point-to-ppm converter.
dic_1d, data_1d = ng.pipe.read(str(work_path / "integrate_1d/1d_data.ft"))
uc_1d = ng.pipe.make_uc(dic_1d, data_1d)

# Pick peaks above the threshold. The downward algorithm is useful for 1D data.
threshold_1d = 1e6
peaks_1d = ng.peakpick.pick(data_1d, pthres=threshold_1d, algorithm="downward")

# Plot the spectrum, then annotate each picked peak.
fig_1d, ax_1d = plt.subplots(figsize=(8, 4), constrained_layout=True)
ax_1d.plot(uc_1d.ppm_scale(), data_1d.real)
for n, peak in enumerate(peaks_1d):
    height = data_1d[int(peak["X_AXIS"])]
    ppm = uc_1d.ppm(peak["X_AXIS"])
    ax_1d.scatter(ppm, height, marker="o", color="r", s=100, alpha=0.5)
    ax_1d.text(ppm, height + 5e5, n + 1, ha="center", va="center")

ax_1d.hlines(threshold_1d, *uc_1d.ppm_limits(), linestyle="--", color="k")
ax_1d.set_ylim(top=1.2e7)
_ = ax_1d.set_xlim(200, 0)
```

## Pick peaks in a 2D spectrum

The 2D example first processes the time-domain dataset so the peak picker sees a
frequency-domain spectrum. The picker returns peak positions in point units; the
unit converters map those positions onto the contour plot in ppm.

```{code-cell} ipython3
# Read and process the direct dimension.
dic_2d, time_data = ng.pipe.read(str(work_path / "processing/nmrpipe_2d/test.fid"))
dic_2d, direct = ng.pipe_proc.sp(dic_2d, time_data, off=0.35, end=0.98, pow=1, c=1.0)
dic_2d, direct = ng.pipe_proc.zf(dic_2d, direct, auto=True)
dic_2d, direct = ng.pipe_proc.ft(dic_2d, direct, auto=True)
dic_2d, direct = ng.pipe_proc.ps(dic_2d, direct, p0=-29.0, p1=0.0)
dic_2d, direct = ng.pipe_proc.di(dic_2d, direct)

# Transpose, process the indirect dimension, then transpose back.
dic_2d, indirect = ng.pipe_proc.tp(dic_2d, direct)
dic_2d, indirect = ng.pipe_proc.sp(dic_2d, indirect, off=0.35, end=0.9, pow=1, c=0.5)
dic_2d, indirect = ng.pipe_proc.zf(dic_2d, indirect, size=2048)
dic_2d, indirect = ng.pipe_proc.ft(dic_2d, indirect, auto=True)
dic_2d, indirect = ng.pipe_proc.ps(dic_2d, indirect, p0=0.0, p1=0.0)
dic_2d, indirect = ng.pipe_proc.di(dic_2d, indirect)
dic_2d, data_2d = ng.pipe_proc.tp(dic_2d, indirect)

# Create ppm converters for each dimension.
uc_2d = {
    "n": ng.pipe.make_uc(dic_2d, data_2d, dim=0),
    "c": ng.pipe.make_uc(dic_2d, data_2d, dim=1),
}

# Pick connected regions above the first contour level.
threshold_2d = 8.5e4
peaks_2d = ng.peakpick.pick(data_2d, pthres=threshold_2d, algorithm="thres", msep=[1, 1])
extent = [*uc_2d["c"].ppm_limits(), *uc_2d["n"].ppm_limits()]
levels = [threshold_2d * 1.4 ** i for i in range(10)]

# Draw contours and overlay the picked peak positions.
fig_2d, ax_2d = plt.subplots(figsize=(5, 4), constrained_layout=True)
ax_2d.contour(data_2d.real, levels=levels, extent=extent, cmap="bone", linewidths=0.5)
ax_2d.set_xlim(70, 40)
ax_2d.set_ylim(135, 100)
ax_2d.scatter(uc_2d["c"].ppm(peaks_2d["X_AXIS"]), uc_2d["n"].ppm(peaks_2d["Y_AXIS"]),
              marker=".", s=10, color="r")
ax_2d.set_xlabel("$^{13}$C (ppm)")
_ = ax_2d.set_ylabel("$^{15}$N (ppm)")
```

```{code-cell} ipython3
:tags: [hide-cell]

plt.close(fig_1d)
plt.close(fig_2d)
work_dir.cleanup()
```
