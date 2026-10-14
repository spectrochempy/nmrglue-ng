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

# Coadd 1D NMRPipe files

This how-to averages a set of matching 1D NMRPipe FID files into one output
file. The example generates a small deterministic input set so the workflow can
run anywhere without downloading the historical archive.

**{nb-download}`Download notebook (.ipynb) <coadd_1d_pipe.ipynb>`** ·
**{download}`Download historical script <../../../examples/coadd/coadd_1d_pipe/coadd_1d.py>`**

```{code-cell} ipython3
:tags: [hide-cell]

from pathlib import Path
from tempfile import TemporaryDirectory

import nmrglue as ng
import numpy as np


work_dir = TemporaryDirectory(prefix="nmrglue-coadd-1d-")
work_path = Path(work_dir.name)

udic = {"ndim": 1}
udic[0] = {
    "size": 128,
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

points = np.arange(udic[0]["size"], dtype=np.float32)
base = np.exp(-points / 35.0) * np.exp(1j * 0.22 * points)
for index, scale in enumerate([0.95, 1.00, 1.05], start=1):
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

The coadd is the arithmetic mean of all matching FIDs. Start with zeros that
match the first file, then add each file divided by the number of inputs.

```{code-cell} ipython3
coadd_dic, first_data = ng.pipe.read(str(input_paths[0]))
coadd_data = np.zeros_like(first_data)

for path in input_paths:
    _, data = ng.pipe.read(str(path))
    coadd_data += data / len(input_paths)

print(f"Coadded shape: {coadd_data.shape}")
print(f"First three points: {coadd_data[:3]}")
```

## Write and read back the result

```{code-cell} ipython3
output_path = work_path / "coadded.fid"
ng.pipe.write(str(output_path), coadd_dic, coadd_data, overwrite=True)
_, roundtrip = ng.pipe.read(str(output_path))

print(f"Wrote: {output_path.name}")
print(f"Round-trip data match: {ng.misc.isdatasimilar(coadd_data, roundtrip)}")
```

```{code-cell} ipython3
:tags: [hide-cell]

work_dir.cleanup()
```

The same pattern applies to measured files: build the sorted file list, read the
first file to get the header and shape, accumulate the average, and write the
coadded NMRPipe file.
