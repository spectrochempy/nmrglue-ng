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

(integrate_1d)=
# Integrate 1D peak regions

This notebook reads a 1D NMRPipe spectrum, integrates ppm regions from a limits
table, and overlays the integration regions on the spectrum.

**{nb-download}`Download notebook (.ipynb) <integrate_1d.ipynb>`** ·
**{download}`Download example data <../_data/historical_examples/example_integrate_1d.zip>`** ·
**{download}`Download limits.in <../../../examples/integration/integrate_1d/limits.in>`**

```{code-cell} ipython3
:tags: [hide-cell]

from pathlib import Path
from tempfile import TemporaryDirectory
from zipfile import ZipFile

import matplotlib.pyplot as plt
import nmrglue as ng
import numpy as np


archive_name = "example_integrate_1d.zip"
work_dir = TemporaryDirectory(prefix="nmrglue-integrate-1d-")
work_path = Path(work_dir.name)
archive_path = None
for candidate in [Path.cwd(), *Path.cwd().parents]:
    fixture = candidate / "doc/source/_data/historical_examples" / archive_name
    if fixture.is_file():
        archive_path = fixture
        break
if archive_path is None:
    raise FileNotFoundError(f"Download {archive_name} into doc/source/_data/historical_examples")
with ZipFile(archive_path) as archive:
    archive.extractall(work_path)

example_dir = work_path / "integrate_1d"
data_path = example_dir / "1d_data.ft"
limits_path = example_dir / "limits.in"
```

Read the spectrum and the ppm limits, then convert each ppm interval to point
indices before summing the selected data.

```{code-cell} ipython3
# Read the spectrum and the peak-region table.
dic, data = ng.pipe.read(str(data_path))
peak_list = np.genfromtxt(limits_path, dtype=None, encoding=None)

# Unit conversion maps ppm limits to array indices.
uc = ng.pipe.make_uc(dic, data)
ppm_scale = uc.ppm_scale()

fig, ax = plt.subplots(figsize=(10, 4), constrained_layout=True)
ax.plot(ppm_scale, data, "k-")

rows = []
ppm_limits = [float(limit) for _, start, end in peak_list for limit in (start, end)]
ppm_min = min(ppm_limits)
ppm_max = max(ppm_limits)
for name, start, end in peak_list:
    # Convert ppm boundaries to point indices and keep the slice increasing.
    start_pt = uc(start, "ppm")
    end_pt = uc(end, "ppm")
    if start_pt > end_pt:
        start_pt, end_pt = end_pt, start_pt

    peak = data[start_pt:end_pt + 1]
    peak_scale = ppm_scale[start_pt:end_pt + 1]

    # Overlay a simple cumulative integral for visual checking.
    ax.plot(peak_scale, peak.cumsum() / 100.0 + peak.max(), "g-")
    ax.plot(peak_scale, [0] * len(peak_scale), "r-")
    ax.text(peak_scale[0], 0.5 * peak.sum() / 100.0 + peak.max(), name, fontsize=8)
    rows.append((name, peak_scale[0], peak_scale[-1], peak.sum()))

ax.set_xlabel("13C (ppm)")
ax.set_yticklabels([])
ax.set_title("1D integration regions")
_ = ax.set_xlim(ppm_max + 2.0, ppm_min - 2.0)
```

The table below is the text output that would normally be written to
`area.out`.

```{code-cell} ipython3
print("#Name\tStart\tStop\tArea")
for name, start, stop, area in rows:
    print(f"{name}\t{start:.3f}\t{stop:.3f}\t{area:E}")
```

```{code-cell} ipython3
:tags: [hide-cell]

plt.close(fig)
work_dir.cleanup()
```
