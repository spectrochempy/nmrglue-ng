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

# Visualizing NMR data

This page follows [Reading NMR files](reading.md) and
[Universal dictionaries](universal-dictionaries.md). It plots an experimental
1D ¹H spectrum and the same downloadable 2D NMRPipe COSY spectrum used in those
guides.

**{nb-download}`Download notebook (.ipynb) <plotting.ipynb>`** ·
{download}`Download 1D epicatechin spectrum <../../../tests/fixtures/fileio/data/jcampdx/epicatechin_1h.jdx>` ·
{download}`Download 2D COSY spectrum <../../../tests/fixtures/fileio/data/nmrpipe_2d_cosy_example.ft2>`

## Install the optional plotting library

nmrglue-ng does not install a plotting library as a runtime dependency. This
notebook uses Matplotlib; install it in the notebook environment before running
the cells:

```console
python -m pip install matplotlib
```

Or add it to a uv project with `uv add matplotlib`.

Imports are in a hidden setup cell so the sections can focus on reading and
plotting the spectra. Reveal the cell if you need to adapt the environment.

```{code-cell} ipython3
:tags: [hide-cell]

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import nmrglue as ng
```

## Plot a 1D experimental spectrum

This processed ¹H spectrum is from measured (-)-epicatechin at 400 MHz in
DMSO-d6. The downloadable fixture is released under
[CC0 1.0](https://creativecommons.org/publicdomain/zero/1.0/) and comes from
[nmrXiv project P33](https://doi.org/10.57992/nmrxiv.p33). The cell that locates
and reads the downloaded file is hidden so this page can focus on the figure.
The corresponding reading and axis-construction steps are shown in
[Reading NMR files](reading.md) and [Universal dictionaries](universal-dictionaries.md).

```{code-cell} ipython3
:tags: [hide-cell]

epicatechin_filename = "epicatechin_1h.jdx"
epicatechin_path = Path(epicatechin_filename)
if not epicatechin_path.is_file():
    for candidate in [Path.cwd(), *Path.cwd().parents]:
        fixture = candidate / "tests/fixtures/fileio/data/jcampdx" / epicatechin_filename
        if fixture.is_file():
            epicatechin_path = fixture
            break
if not epicatechin_path.is_file():
    raise FileNotFoundError(
        f"Download {epicatechin_filename} into {Path.cwd()}"
    )

epicatechin_dic, epicatechin_data = ng.jcampdx.read(str(epicatechin_path))
epicatechin_udic = ng.jcampdx.guess_udic(epicatechin_dic, epicatechin_data)
epicatechin_uc = ng.fileiobase.uc_from_udic(epicatechin_udic, dim=0)
ppm_1h_axis = epicatechin_uc.ppm_scale()
```

The processed spectrum is plotted as read, without an additional baseline
correction. The figure is for visual inspection, not quantitative analysis.

```{code-cell} ipython3
fig, ax = plt.subplots(figsize=(10, 4))
ax.plot(ppm_1h_axis, epicatechin_data, color="#176B87", linewidth=0.7)
ax.set(
    xlim=(10.5, -0.5),
    xlabel="¹H chemical shift / ppm",
    ylabel="Intensity / a.u.",
    title="Experimental (-)-epicatechin ¹H spectrum",
)
ax.spines[["top", "right"]].set_visible(False)
fig.tight_layout()
plt.show()
```

## Prepare the 2D COSY axes

The COSY setup cell is hidden to avoid repeating the file lookup and axis
construction already shown in [Universal dictionaries](universal-dictionaries.md).
Reveal it in the downloadable notebook to inspect or adapt the setup.

```{code-cell} ipython3
:tags: [hide-cell]

data_path = Path("nmrpipe_2d_cosy_example.ft2")
if not data_path.is_file():
    for candidate in [Path.cwd(), *Path.cwd().parents]:
        fixture = candidate / "tests/fixtures/fileio/data/nmrpipe_2d_cosy_example.ft2"
        if fixture.is_file():
            data_path = fixture
            break
else:
    data_path = data_path.resolve()

if not data_path.is_file():
    raise FileNotFoundError(
        f"Download nmrpipe_2d_cosy_example.ft2 into {Path.cwd()} and rerun the notebook."
    )

dic, data = ng.pipe.read(str(data_path))
udic = ng.pipe.guess_udic(dic, data)
uc_indirect = ng.fileiobase.uc_from_udic(udic, dim=0)
uc_direct = ng.fileiobase.uc_from_udic(udic, dim=1)
ppm_indirect_axis = uc_indirect.ppm_scale()
ppm_direct_axis = uc_direct.ppm_scale()
```

## Draw a 2D contour plot

In the NumPy array, rows are the indirect dimension (`dim=0`) and columns are
the direct dimension (`dim=1`). Therefore, pass the direct-dimension ppm scale
as the horizontal coordinates and the indirect-dimension ppm scale as the
vertical coordinates. Both ppm scales descend, placing high chemical shift on
the left and top as is customary for NMR spectra.

Contour levels are chosen relative to the strongest signal to make this
example's peaks visible. They are display settings, not quantitative peak
criteria.

```{code-cell} ipython3
levels = data.max() * np.array(
    [0.002, 0.004, 0.008, 0.016, 0.032, 0.064, 0.128]
)

fig, ax = plt.subplots(figsize=(7.2, 5.2))
ax.contour(
    ppm_direct_axis,
    ppm_indirect_axis,
    data,
    levels=levels,
    colors="#174f63",
    linewidths=0.65,
)
ax.set_xlim(9, 0)
ax.set_ylim(9, 0)
ax.set_xlabel("1H direct dimension / ppm")
ax.set_ylabel("1H indirect dimension / ppm")
ax.set_title("Processed 2D COSY spectrum")
fig.tight_layout()
plt.show()
```

For data with a different intensity scale or noise level, adjust the contour
levels and the displayed ppm window. The plot is intended to inspect the
spectrum, not to establish quantitative peak intensities.
