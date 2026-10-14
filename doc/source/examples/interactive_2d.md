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

# Explore a 2D spectrum interactively

This how-to builds the same contour view as the historical interactive script
and shows a static preview that can run during documentation builds. Run the
downloadable script locally when you need Matplotlib pan, zoom, and GUI tools.

**{nb-download}`Download notebook (.ipynb) <interactive_2d.ipynb>`** ·
**{download}`Download script <../../../examples/interactive/interactive_2d/2d_interactive.py>`** ·
**{download}`Download example data <../_data/historical_examples/example_process_pipe_2d.zip>`**

```{code-cell} ipython3
:tags: [hide-cell]

from pathlib import Path
from tempfile import TemporaryDirectory
from urllib.request import urlretrieve
from zipfile import ZipFile
import os

import matplotlib.cm
import matplotlib.pyplot as plt
import nmrglue as ng


archive_name = "example_process_pipe_2d.zip"
archive_url = "https://storage.googleapis.com/google-code-archive-downloads/v2/code.google.com/nmrglue/" + archive_name
work_dir = TemporaryDirectory(prefix="nmrglue-interactive-2d-")
work_path = Path(work_dir.name)
archive_path = None
for candidate in [Path.cwd(), *Path.cwd().parents]:
    fixture = candidate / "doc/source/_data/historical_examples" / archive_name
    if fixture.is_file():
        archive_path = fixture
        break
if archive_path is None:
    cache_dir = os.environ.get("NMRGLUE_HISTORICAL_EXAMPLES")
    archive_path = Path(cache_dir) / archive_name if cache_dir else work_path / archive_name
if not archive_path.is_file():
    archive_path = work_path / archive_name
    urlretrieve(archive_url, archive_path)
with ZipFile(archive_path) as archive:
    archive.extractall(work_path)
data_path = work_path / "processing/nmrpipe_2d/test.fid"
```

## Read and process the 2D FID

The downloadable script expects a processed `nmrpipe_2d/test.ft2` file. This
notebook starts from the packaged FID so the preview is fully reproducible.

```{code-cell} ipython3
dic, time_data = ng.pipe.read(str(data_path))

proc_dic, direct = ng.pipe_proc.sp(dic, time_data, off=0.35, end=0.98, pow=1, c=1.0)
proc_dic, direct = ng.pipe_proc.zf(proc_dic, direct, auto=True)
proc_dic, direct = ng.pipe_proc.ft(proc_dic, direct, auto=True)
proc_dic, direct = ng.pipe_proc.ps(proc_dic, direct, p0=-29.0, p1=0.0)
proc_dic, direct = ng.pipe_proc.di(proc_dic, direct)

proc_dic, indirect = ng.pipe_proc.tp(proc_dic, direct)
proc_dic, indirect = ng.pipe_proc.sp(proc_dic, indirect, off=0.35, end=0.9, pow=1, c=0.5)
proc_dic, indirect = ng.pipe_proc.zf(proc_dic, indirect, size=2048)
proc_dic, indirect = ng.pipe_proc.ft(proc_dic, indirect, auto=True)
proc_dic, indirect = ng.pipe_proc.ps(proc_dic, indirect, p0=0.0, p1=0.0)
proc_dic, indirect = ng.pipe_proc.di(proc_dic, indirect)
proc_dic, spectrum = ng.pipe_proc.tp(proc_dic, indirect)

print(f"Processed shape: {spectrum.shape}")
```

## Build the contour plot

The ppm limits come from unit-conversion objects for each dimension. In a local
interactive session, Matplotlib handles the pan and zoom controls after
`plt.show()`.

```{code-cell} ipython3
cmap = matplotlib.cm.Blues_r
contour_start = 30000
contour_num = 20
contour_factor = 1.20
levels = [contour_start * contour_factor**x for x in range(contour_num)]

uc_13c = ng.pipe.make_uc(proc_dic, spectrum, dim=1)
ppm_13c_0, ppm_13c_1 = uc_13c.ppm_limits()
uc_15n = ng.pipe.make_uc(proc_dic, spectrum, dim=0)
ppm_15n_0, ppm_15n_1 = uc_15n.ppm_limits()

fig, ax = plt.subplots(figsize=(6, 5), constrained_layout=True)
ax.contour(spectrum, levels, cmap=cmap, extent=(ppm_13c_0, ppm_13c_1, ppm_15n_0, ppm_15n_1))
ax.set_ylabel("15N (ppm)")
ax.set_xlabel("13C (ppm)")
ax.set_title("Protein 2D NCa spectrum")
ax.set_xlim(70, 40)
ax.set_ylim(135, 100)
_ = fig
```

## Run it interactively

Download the script and run it in a directory containing a processed
`nmrpipe_2d/test.ft2` file:

```bash
python 2d_interactive.py
```

The script keeps the window open with `plt.show()` for local interactive
inspection.

```{code-cell} ipython3
:tags: [hide-cell]

plt.close(fig)
work_dir.cleanup()
```
