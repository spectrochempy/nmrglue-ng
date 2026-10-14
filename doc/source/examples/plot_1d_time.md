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

(plot_1d_time)=
# Plot a 1D NMRPipe FID

This notebook reads a 1D NMRPipe time-domain file and plots the FID on a
millisecond axis.

**{nb-download}`Download notebook (.ipynb) <plot_1d_time.ipynb>`** ·
**{download}`Download example data <../_data/historical_examples/example_plot_1d.zip>`**

```{code-cell} ipython3
:tags: [hide-cell]

from pathlib import Path
from tempfile import TemporaryDirectory
from zipfile import ZipFile

import matplotlib.pyplot as plt
import nmrglue as ng


archive_name = "example_plot_1d.zip"
work_dir = TemporaryDirectory(prefix="nmrglue-plot-1d-time-")
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

data_path = work_path / "plot_1d/nmrpipe_1d/test.fid"
```

Read the time-domain data, build a time axis in milliseconds, and plot the real
component of the FID.

```{code-cell} ipython3
dic, data = ng.pipe.read(str(data_path))
uc = ng.pipe.make_uc(dic, data)

fig, ax = plt.subplots()
ax.plot(uc.ms_scale(), data.real, "k-")
ax.set_yticklabels([])
ax.set_title("Protein 1D FID")
ax.set_xlabel("Time (ms)")
# In notebooks, assigning the last return value to `_` suppresses text output.
_ = ax.set_ylim(-100000, 100000)
```

```{code-cell} ipython3
:tags: [hide-cell]

plt.close(fig)
work_dir.cleanup()
```
