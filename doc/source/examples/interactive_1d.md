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

# Explore a 1D spectrum interactively

This how-to builds the same plot as the historical interactive script and shows
a static preview that can run during documentation builds. To use pan, zoom, and
other GUI controls, download and run the script in a local Python session with a
Matplotlib interactive backend.

**{nb-download}`Download notebook (.ipynb) <interactive_1d.ipynb>`** ·
**{download}`Download script <../../../examples/interactive/interactive_1d/1d_interactive.py>`** ·
**{download}`Download example data <../_data/historical_examples/example_process_pipe_1d.zip>`**

```{code-cell} ipython3
:tags: [hide-cell]

from pathlib import Path
from tempfile import TemporaryDirectory
from urllib.request import urlretrieve
from zipfile import ZipFile
import os

import matplotlib.pyplot as plt
import nmrglue as ng


archive_name = "example_process_pipe_1d.zip"
archive_url = "https://storage.googleapis.com/google-code-archive-downloads/v2/code.google.com/nmrglue/" + archive_name
work_dir = TemporaryDirectory(prefix="nmrglue-interactive-1d-")
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
data_path = work_path / "processing/nmrpipe_1d/test.fid"
```

## Read and process the FID

The historical script expects a processed NMRPipe spectrum. Here the notebook
starts from the packaged FID and applies the same compact processing chain used
elsewhere in the how-to examples.

```{code-cell} ipython3
dic, time_data = ng.pipe.read(str(data_path))

proc_dic, spectrum = ng.pipe_proc.sp(dic, time_data, off=0.35, end=0.98, pow=2, c=1.0)
proc_dic, spectrum = ng.pipe_proc.zf(proc_dic, spectrum, auto=True)
proc_dic, spectrum = ng.pipe_proc.ft(proc_dic, spectrum, auto=True)
proc_dic, spectrum = ng.pipe_proc.ps(proc_dic, spectrum, p0=-17.7, p1=-36.0)
proc_dic, spectrum = ng.pipe_proc.di(proc_dic, spectrum)

print(f"Processed shape: {spectrum.shape}")
```

## Build the interactive plot

`ng.pipe.make_uc()` creates a unit-conversion object for the ppm axis. In a
standalone script, the final step is `plt.show()`, which opens the Matplotlib
interactive window.

```{code-cell} ipython3
uc = ng.pipe.make_uc(proc_dic, spectrum)

fig, ax = plt.subplots(figsize=(8, 4), constrained_layout=True)
ax.plot(uc.ppm_scale(), spectrum, "k-", linewidth=1.0)
ax.set_yticklabels([])
ax.set_title("Protein 1D spectrum")
ax.set_xlabel("13C ppm")
ax.set_xlim(200, 0)
_ = fig
```

## Run it interactively

Download the script and run it in a directory containing a processed
`nmrpipe_1d/test.ft` file:

```bash
python 1d_interactive.py
```

The script keeps the window open with `plt.show()` so you can pan, zoom, and
inspect the spectrum with your local Matplotlib backend.

```{code-cell} ipython3
:tags: [hide-cell]

plt.close(fig)
work_dir.cleanup()
```
