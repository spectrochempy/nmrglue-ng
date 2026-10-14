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

(plot_2d_spectrum_pts)=
# Plot a 2D NMRPipe spectrum on point axes

This notebook draws the same style of contour plot as the ppm-axis example, but
uses raw point indices for both dimensions.

**{nb-download}`Download notebook (.ipynb) <plot_2d_spectrum_pts.ipynb>`** ·
**{download}`Download example data <../_data/historical_examples/example_process_pipe_2d.zip>`**

```{code-cell} ipython3
:tags: [hide-cell]

from pathlib import Path
from tempfile import TemporaryDirectory
from zipfile import ZipFile

import matplotlib.cm
import matplotlib.pyplot as plt
import nmrglue as ng
import numpy as np


archive_name = "example_process_pipe_2d.zip"
work_dir = TemporaryDirectory(prefix="nmrglue-plot-2d-points-")
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

data_path = work_path / "processing/nmrpipe_2d/test.fid"
```

This version uses point indices instead of ppm axes. The processing steps are
the same as in the ppm-axis example.

```{code-cell} ipython3
levels = 30000 * 1.20 ** np.arange(20)

# Process the direct dimension.
dic, time_data = ng.pipe.read(str(data_path))
dic, direct = ng.pipe_proc.sp(dic, time_data, off=0.35, end=0.98, pow=1, c=1.0)
dic, direct = ng.pipe_proc.zf(dic, direct, auto=True)
dic, direct = ng.pipe_proc.ft(dic, direct, auto=True)
dic, direct = ng.pipe_proc.ps(dic, direct, p0=-29.0, p1=0.0)
dic, direct = ng.pipe_proc.di(dic, direct)

# Process the indirect dimension after transposition.
dic, indirect = ng.pipe_proc.tp(dic, direct)
dic, indirect = ng.pipe_proc.sp(dic, indirect, off=0.35, end=0.9, pow=1, c=0.5)
dic, indirect = ng.pipe_proc.zf(dic, indirect, size=2048)
dic, indirect = ng.pipe_proc.ft(dic, indirect, auto=True)
dic, indirect = ng.pipe_proc.ps(dic, indirect, p0=0.0, p1=0.0)
dic, indirect = ng.pipe_proc.di(dic, indirect)
_, data = ng.pipe_proc.tp(dic, indirect)

fig, ax = plt.subplots()
ax.contour(data, levels, cmap=matplotlib.cm.Blues_r,
           extent=(0, data.shape[1] - 1, 0, data.shape[0] - 1))

# Labels and slices are placed directly in point coordinates.
ax.text(2006, 1322, "T49", size=8, color="r")
ax.text(2010, 1290, "T11", size=8, color="k")
ax.plot(range(data.shape[1]), data[1187, :] / 3.0e3 + 1187)
ax.plot(-data[:, 1976] / 3.0e3 + 1976, range(data.shape[0]))
ax.set_ylabel("15N (points)")
ax.set_xlabel("13C (points)")
ax.set_title("Protein 2D NCa Spectrum")
ax.set_xlim(1900, 2200)
_ = ax.set_ylim(750, 1400)
```

```{code-cell} ipython3
:tags: [hide-cell]

plt.close(fig)
work_dir.cleanup()
```
