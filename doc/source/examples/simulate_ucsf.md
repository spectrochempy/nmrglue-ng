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

# Simulate a UCSF (Sparky) file

This how-to uses `nmrglue.analysis.linesh.sim_NDregion` to simulate a small
2D HSQC-like spectrum from peak positions in ppm, then writes the result as a
UCSF/Sparky file.

**{nb-download}`Download notebook (.ipynb) <simulate_ucsf.ipynb>`** ·
**{download}`Download historical script <../../../examples/simulation/simulate_ucsf/make_ucsf.py>`** ·
**{download}`Download peak list <../../../examples/simulation/simulate_ucsf/peaks.txt>`**

```{code-cell} ipython3
:tags: [hide-cell]

from pathlib import Path
from tempfile import TemporaryDirectory

import matplotlib.pyplot as plt
import nmrglue as ng
import numpy as np


work_dir = TemporaryDirectory(prefix="nmrglue-simulate-ucsf-")
work_path = Path(work_dir.name)
peak_text = """#15N     1H
112.7    7.45
117.8    8.57
123.0    9.02
"""
peak_path = work_path / "peaks.txt"
peak_path.write_text(peak_text)
```

## Define the target spectrum

Start with a universal dictionary describing a real, frequency-domain 2D
spectrum. `sparky.create_dic()` converts it to the UCSF/Sparky header dictionary
used for writing.

```{code-cell} ipython3
udic = {
    "ndim": 2,
    0: {
        "car": 7329.0,
        "complex": False,
        "encoding": "states",
        "freq": True,
        "label": "15N",
        "obs": 60.8,
        "size": 512,
        "sw": 1523.43,
        "time": False,
    },
    1: {
        "car": 5403.570418865944,
        "complex": False,
        "encoding": "direct",
        "freq": True,
        "label": "1H",
        "obs": 600.0,
        "size": 1024,
        "sw": 3606.5,
        "time": False,
    },
}

dic = ng.sparky.create_dic(udic)
print(f"Target shape: {(udic[0]['size'], udic[1]['size'])}")
```

## Convert peak positions from ppm to points

The peak list stores one `15N` and one `1H` position per row. Unit converters
from the Sparky dictionary translate ppm positions to array indices for the line
shape simulator.

```{code-cell} ipython3
peak_list = np.genfromtxt(peak_path, dtype=float, names=True)

uc_15n = ng.sparky.make_uc(dic, None, 0)
uc_1h = ng.sparky.make_uc(dic, None, 1)

lw_15n = 5.0
lw_1h = 5.0
params = []
for ppm_15n, ppm_1h in peak_list:
    pts_15n = uc_15n.f(ppm_15n, "ppm")
    pts_1h = uc_1h.f(ppm_1h, "ppm")
    params.append([(pts_15n, lw_15n), (pts_1h, lw_1h)])

print(f"Peaks: {len(params)}")
print(f"First peak points: {params[0]}")
```

## Simulate the spectrum

```{code-cell} ipython3
shape = (udic[0]["size"], udic[1]["size"])
lineshapes = ("g", "g")
amps = [100.0] * len(params)
data = ng.linesh.sim_NDregion(shape, lineshapes, params, amps).astype(np.float32)

print(f"Simulated shape: {data.shape}")
print(f"Intensity range: {data.min():.3f} to {data.max():.3f}")
```

## Plot a quick contour check

```{code-cell} ipython3
levels = data.max() * np.geomspace(0.08, 1.0, 8)
extent = (uc_1h.ppm_limits()[0], uc_1h.ppm_limits()[1], uc_15n.ppm_limits()[0], uc_15n.ppm_limits()[1])

fig, ax = plt.subplots(figsize=(6, 4), constrained_layout=True)
ax.contour(data, levels=levels, extent=extent, cmap="Blues_r", linewidths=0.8)
ax.set_xlabel("1H (ppm)")
ax.set_ylabel("15N (ppm)")
ax.set_title("Simulated UCSF spectrum")
ax.invert_xaxis()
ax.invert_yaxis()
_ = fig
```

## Write and read back the UCSF file

```{code-cell} ipython3
output_path = work_path / "test.ucsf"
ng.sparky.write(str(output_path), dic, data, overwrite=True)
roundtrip_dic, roundtrip = ng.sparky.read(str(output_path))

print(f"Wrote: {output_path.name}")
print(f"Round-trip shape: {roundtrip.shape}")
print(f"Round-trip data match: {ng.misc.isdatasimilar(data, roundtrip)}")
```

```{code-cell} ipython3
:tags: [hide-cell]

plt.close(fig)
work_dir.cleanup()
```

The same workflow can use measured peak positions: read a peak table, convert
ppm to points with unit converters, simulate the desired line shapes, and write
the array with the Sparky/UCSF dictionary.
