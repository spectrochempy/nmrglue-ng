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

(integrate_2d)=
# Integrate 2D peak boxes

This notebook processes a 2D NMRPipe time-domain dataset, integrates point-space
boxes from a limits table, and reports one volume per box. Use
{ref}`plot_2d_boxes` to inspect the limits graphically and
{ref}`plot_2d_assignments` to check assignment labels.

**{nb-download}`Download notebook (.ipynb) <integrate_2d.ipynb>`** ·
**{download}`Download example data <../_data/historical_examples/example_process_pipe_2d.zip>`** ·
**{download}`Download limits.in <../../../examples/integration/integrate_2d/limits.in>`**

```{code-cell} ipython3
:tags: [hide-cell]

from pathlib import Path
from tempfile import TemporaryDirectory
from zipfile import ZipFile

import matplotlib.pyplot as plt
import nmrglue as ng
import numpy as np


archive_name = "example_process_pipe_2d.zip"
work_dir = TemporaryDirectory(prefix="nmrglue-integrate-2d-")
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
limits_path = None
for candidate in [Path.cwd(), *Path.cwd().parents]:
    fixture = candidate / "examples/integration/integrate_2d/limits.in"
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

Process the 2D dataset to frequency domain, read the point-space limits, and sum
all points inside each box.

```{code-cell} ipython3
# Process the direct dimension first.
dic, time_data = ng.pipe.read(str(data_path))
dic, direct = ng.pipe_proc.sp(dic, time_data, off=0.35, end=0.98, pow=1, c=1.0)
dic, direct = ng.pipe_proc.zf(dic, direct, auto=True)
dic, direct = ng.pipe_proc.ft(dic, direct, auto=True)
dic, direct = ng.pipe_proc.ps(dic, direct, p0=-29.0, p1=0.0)
dic, direct = ng.pipe_proc.di(dic, direct)

# Transpose, process the indirect dimension, then transpose back.
dic, indirect = ng.pipe_proc.tp(dic, direct)
dic, indirect = ng.pipe_proc.sp(dic, indirect, off=0.35, end=0.9, pow=1, c=0.5)
dic, indirect = ng.pipe_proc.zf(dic, indirect, size=2048)
dic, indirect = ng.pipe_proc.ft(dic, indirect, auto=True)
dic, indirect = ng.pipe_proc.ps(dic, indirect, p0=0.0, p1=0.0)
dic, indirect = ng.pipe_proc.di(dic, indirect)
_, data = ng.pipe_proc.tp(dic, indirect)

peak_list = np.genfromtxt(limits_path, dtype=None, encoding=None)
volumes = []
boxes = []
for name, x0, y0, x1, y1 in peak_list:
    # Limits may be listed in either direction; normalize them before slicing.
    if x0 > x1:
        x0, x1 = x1, x0
    if y0 > y1:
        y0, y1 = y1, y0
    volumes.append((name, data[y0:y1 + 1, x0:x1 + 1].sum()))
    boxes.append((name, x0, y0, x1, y1))

print("# Name\tVolume")
for name, volume in volumes:
    print(f"{name}\t{volume:.3f}")
```

Plot the integrated boxes on the spectrum as a quick visual check. The axes are
in points because the limit table is defined in point coordinates.

```{code-cell} ipython3
levels = 30000 * 1.20 ** np.arange(20)
fig, ax = plt.subplots(figsize=(7, 5), constrained_layout=True)
ax.contour(data, levels, cmap="Blues_r", linewidths=0.5,
           extent=(0, data.shape[1] - 1, 0, data.shape[0] - 1))

for name, x0, y0, x1, y1 in boxes:
    ax.plot([x0, x1, x1, x0, x0], [y0, y0, y1, y1, y0], color="r", linewidth=1.5)
    ax.text(x1 + 3, y0, name, size=8, color="r")

x_values = [value for _, x0, _, x1, _ in boxes for value in (x0, x1)]
y_values = [value for _, _, y0, _, y1 in boxes for value in (y0, y1)]
ax.set_xlabel("13C (points)")
ax.set_ylabel("15N (points)")
ax.set_title("Integrated 2D boxes")
ax.set_xlim(min(x_values) - 40, max(x_values) + 40)
_ = ax.set_ylim(min(y_values) - 80, max(y_values) + 80)
```

```{code-cell} ipython3
:tags: [hide-cell]

plt.close(fig)
work_dir.cleanup()
```
