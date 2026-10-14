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

(plot_1d_freq)=
# Plot a 1D NMRPipe spectrum

This notebook reads a 1D NMRPipe frequency-domain file, plots the spectrum on a
ppm axis, and adds simple annotations.

**{nb-download}`Download notebook (.ipynb) <plot_1d_freq.ipynb>`** ·
**{download}`Download example data <../_data/historical_examples/example_plot_1d.zip>`**

```{code-cell} ipython3
:tags: [hide-cell]

from pathlib import Path
from tempfile import TemporaryDirectory
from zipfile import ZipFile

import matplotlib.pyplot as plt
import nmrglue as ng


archive_name = "example_plot_1d.zip"
work_dir = TemporaryDirectory(prefix="nmrglue-plot-1d-freq-")
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

data_path = work_path / "plot_1d/nmrpipe_1d/test.ft"
```

Read the frequency-domain spectrum, build a ppm axis, then add a few simple
Matplotlib annotations.

```{code-cell} ipython3
dic, data = ng.pipe.read(str(data_path))
uc = ng.pipe.make_uc(dic, data)

fig, ax = plt.subplots()
ax.plot(uc.ppm_scale(), data, "k-")
ax.annotate("CO region", xy=(173, 2.15e6), xycoords="data", xytext=(30, 20),
            textcoords="offset points", arrowprops=dict(arrowstyle="->"))
ax.text(59, 1.55e6, "alphatic region")
ax.annotate("", xy=(70, 1.2e6), xycoords="data", xytext=(10, 1.2e6),
            textcoords="data",
            arrowprops=dict(arrowstyle="<->", connectionstyle="bar", ec="k", shrinkA=5, shrinkB=5))
ax.set_yticklabels([])
ax.set_title("Protein 1D Spectrum")
ax.set_xlabel("13C ppm")
ax.set_xlim(200, 0)
_ = ax.set_ylim(-80000, 2500000)
```

```{code-cell} ipython3
:tags: [hide-cell]

plt.close(fig)
work_dir.cleanup()
```
