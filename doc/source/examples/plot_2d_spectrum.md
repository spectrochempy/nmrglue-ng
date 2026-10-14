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

(plot_2d_spectrum)=
# Plot a 2D NMRPipe spectrum on ppm axes

This notebook draws a contour plot of a 2D NMRPipe spectrum, adds labels, and
overlays slices in both dimensions.

**{nb-download}`Download notebook (.ipynb) <plot_2d_spectrum.ipynb>`** ·
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
work_dir = TemporaryDirectory(prefix="nmrglue-plot-2d-ppm-")
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

Process the time-domain data, build ppm axes for both dimensions, then draw the
contours and two 1D slices on the same axes.

```{code-cell} ipython3
contour_start = 30000
contour_num = 20
contour_factor = 1.20
levels = contour_start * contour_factor ** np.arange(contour_num)

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
dic, data = ng.pipe_proc.tp(dic, indirect)

# Build ppm axes from the processed NMRPipe metadata.
uc_13c = ng.pipe.make_uc(dic, data, dim=1)
ppm_13c = uc_13c.ppm_scale()
ppm_13c_0, ppm_13c_1 = uc_13c.ppm_limits()
uc_15n = ng.pipe.make_uc(dic, data, dim=0)
ppm_15n = uc_15n.ppm_scale()
ppm_15n_0, ppm_15n_1 = uc_15n.ppm_limits()

fig, ax = plt.subplots()
ax.contour(data, levels, cmap=matplotlib.cm.Blues_r,
           extent=(ppm_13c_0, ppm_13c_1, ppm_15n_0, ppm_15n_1))
ax.text(59.25, 104.0, "T49", size=8, color="r")
ax.text(58.75, 106, "T11", size=8, color="k")
ax.plot(ppm_13c, -data[uc_15n("111.27 ppm"), :] / 4.0e4 + 111.27)
ax.plot(data[:, uc_13c("62.0 ppm")] / 2.0e4 + 62.0, ppm_15n)
ax.set_ylabel("15N (ppm)")
ax.set_xlabel("13C (ppm)")
ax.set_title("Protein 2D NCa Spectrum")
ax.set_xlim(70, 40)
_ = ax.set_ylim(135, 100)
```

```{code-cell} ipython3
:tags: [hide-cell]

plt.close(fig)
work_dir.cleanup()
```
