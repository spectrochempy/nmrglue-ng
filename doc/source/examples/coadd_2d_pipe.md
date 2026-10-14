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

# Coadd 2D NMRPipe files

This how-to averages a series of 2D NMRPipe FID files. The notebook creates a
small synthetic input set and writes the coadded result as `coadded.fid`.

**{nb-download}`Download notebook (.ipynb) <coadd_2d_pipe.ipynb>`** ·
**{download}`Download historical script <../../../examples/coadd/coadd_2d_pipe/coadd_2d.py>`**

```{code-cell} ipython3
:tags: [hide-cell]

from pathlib import Path
from tempfile import TemporaryDirectory

import nmrglue as ng
import numpy as np


work_dir = TemporaryDirectory(prefix="nmrglue-coadd-2d-")
work_path = Path(work_dir.name)

udic = {"ndim": 2}
udic[0] = {
    "size": 16,
    "complex": True,
    "encoding": "states",
    "sw": 1800.0,
    "obs": 125.0,
    "car": 56.0 * 125.0,
    "label": "C13",
    "time": True,
    "freq": False,
}
udic[1] = {
    "size": 64,
    "complex": True,
    "encoding": "direct",
    "sw": 4000.0,
    "obs": 500.0,
    "car": 4.7 * 500.0,
    "label": "H1",
    "time": True,
    "freq": False,
}
pipe_dic = ng.pipe.create_dic(udic)

indirect, direct = np.indices((udic[0]["size"], udic[1]["size"]), dtype=np.float32)
base = np.exp(-direct / 24.0 - indirect / 8.0) * np.exp(1j * (0.22 * direct + 0.35 * indirect))
for index, scale in enumerate([0.90, 1.00, 1.10], start=1):
    data = (scale * base).astype(np.complex64)
    ng.pipe.write(str(work_path / f"test{index:03d}.fid"), pipe_dic, data)
```

## Find the files to average

```{code-cell} ipython3
input_paths = sorted(work_path.glob("test*.fid"))

print(f"Files found: {len(input_paths)}")
print("First file:", input_paths[0].name)
```

## Read and coadd

```{code-cell} ipython3
coadd_dic, first_data = ng.pipe.read(str(input_paths[0]))
coadd_data = np.zeros_like(first_data)

for path in input_paths:
    _, data = ng.pipe.read(str(path))
    coadd_data += data / len(input_paths)

print(f"Coadded shape: {coadd_data.shape}")
print(f"Coadded dtype: {coadd_data.dtype}")
```

## Write and read back the result

```{code-cell} ipython3
output_path = work_path / "coadded.fid"
ng.pipe.write(str(output_path), coadd_dic, coadd_data, overwrite=True)
_, roundtrip = ng.pipe.read(str(output_path))

print(f"Wrote: {output_path.name}")
print(f"Round-trip shape: {roundtrip.shape}")
print(f"Round-trip data match: {ng.misc.isdatasimilar(coadd_data, roundtrip)}")
```

```{code-cell} ipython3
:tags: [hide-cell]

work_dir.cleanup()
```

Use the same approach for measured 2D files: keep the input files on the same
grid, sort them deterministically, average their arrays, and write the result
with the header from the first file.
