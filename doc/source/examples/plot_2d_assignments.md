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

(plot_2d_assignments)=
# Plot 2D peak assignments

This notebook overlays integration boxes and assignment labels on a 2D NMRPipe
contour plot.

**{nb-download}`Download notebook (.ipynb) <plot_2d_assignments.ipynb>`** ·
**{download}`Download example data <../_data/historical_examples/example_process_pipe_2d.zip>`** ·
**{download}`Download limits.in <../../../examples/plotting/plot_2d/limits.in>`**

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
work_dir = TemporaryDirectory(prefix="nmrglue-plot-2d-assignments-")
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

example_dir = work_path / "processing"
data_path = example_dir / "nmrpipe_2d/test.fid"
limits_path = None
for candidate in [Path.cwd(), *Path.cwd().parents]:
    fixture = candidate / "examples/plotting/plot_2d/limits.in"
    if fixture.is_file():
        limits_path = fixture
        break
if limits_path is None:
    limits_path = work_path / "limits.in"
    limits_path.write_text(
        """#Peak   X0      Y0      X1      Y1
T49     1992    1334    2003    1316
T11     1996    1302    2008    1284
G14     2032    1314    2044    1293
E15     2077    1025    2087    1004
W43     2008    952     2019    933
"""
    )
```

Draw the full point-space contour plot and overlay each integration box with its
assignment label.

```{code-cell} ipython3
levels = 30000 * 1.20 ** np.arange(20)

# Process the direct dimension, then the indirect dimension after transposition.
dic, time_data = ng.pipe.read(str(data_path))
dic, direct = ng.pipe_proc.sp(dic, time_data, off=0.35, end=0.98, pow=1, c=1.0)
dic, direct = ng.pipe_proc.zf(dic, direct, auto=True)
dic, direct = ng.pipe_proc.ft(dic, direct, auto=True)
dic, direct = ng.pipe_proc.ps(dic, direct, p0=-29.0, p1=0.0)
dic, direct = ng.pipe_proc.di(dic, direct)
dic, indirect = ng.pipe_proc.tp(dic, direct)
dic, indirect = ng.pipe_proc.sp(dic, indirect, off=0.35, end=0.9, pow=1, c=0.5)
dic, indirect = ng.pipe_proc.zf(dic, indirect, size=2048)
dic, indirect = ng.pipe_proc.ft(dic, indirect, auto=True)
dic, indirect = ng.pipe_proc.ps(dic, indirect, p0=0.0, p1=0.0)
dic, indirect = ng.pipe_proc.di(dic, indirect)
_, data = ng.pipe_proc.tp(dic, indirect)
peak_list = np.genfromtxt(limits_path, dtype=None, encoding=None)

fig, ax = plt.subplots()
ax.contour(data, levels, cmap=matplotlib.cm.Blues_r,
           extent=(0, data.shape[1] - 1, 0, data.shape[0] - 1))
for name, x0, y0, x1, y1 in peak_list:
    # Normalize reversed limits before drawing each box.
    if x0 > x1:
        x0, x1 = x1, x0
    if y0 > y1:
        y0, y1 = y1, y0
    ax.plot([x0, x1, x1, x0, x0], [y0, y0, y1, y1, y0], "k")
    ax.text(x1 + 1, y0, name, size=6, color="r")

ax.set_xlim(1900, 2200)
_ = ax.set_ylim(750, 1400)
```

```{code-cell} ipython3
:tags: [hide-cell]

plt.close(fig)
work_dir.cleanup()
```
