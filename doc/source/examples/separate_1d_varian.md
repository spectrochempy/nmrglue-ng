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

# Separate arrayed 1D Agilent/Varian data

This how-to separates a 1D Agilent/Varian experiment collected with an
innermost arrayed parameter. The example creates a compact synthetic
`arrayed_data.dir` dataset, reads the array metadata from `procpar`, then writes
one `.fid` directory per array value.

**{nb-download}`Download notebook (.ipynb) <separate_1d_varian.ipynb>`** ·
**{download}`Download historical script <../../../examples/separate/separate_1d_varian/separate.py>`**

```{code-cell} ipython3
:tags: [hide-cell]

from pathlib import Path
from tempfile import TemporaryDirectory

import nmrglue as ng
import numpy as np


work_dir = TemporaryDirectory(prefix="nmrglue-separate-1d-varian-")
work_path = Path(work_dir.name)

udic = {"ndim": 2}
udic[0] = {
    "size": 3,
    "complex": False,
    "encoding": "states",
    "sw": 1.0,
    "obs": 1.0,
    "car": 0.0,
    "label": "array",
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
dic = ng.varian.create_dic(udic)
dic["procpar"]["array"] = ng.varian.create_pdic_param("array", ["tHX"])
dic["procpar"]["tHX"] = ng.varian.create_pdic_param("tHX", ["10", "20", "30"])

points = np.arange(udic[1]["size"], dtype=np.float32)
base = np.exp(-points / 24.0) * np.exp(1j * 0.24 * points)
arrayed_data = np.stack([(1.0 + 0.1 * index) * base for index in range(3)]).astype(np.complex64)
ng.varian.write(str(work_path / "arrayed_data.dir"), dic, arrayed_data, overwrite=True)
```

## Read the arrayed experiment

The synthetic file stores one 1D FID per array value. `shape` and `torder` are
specified here because the compact synthetic `procpar` intentionally contains
only the metadata needed for this separation example.

```{code-cell} ipython3
dic, data = ng.varian.read(str(work_path / "arrayed_data.dir"), shape=(3, 64), torder="flat")

arrayed_param = dic["procpar"]["array"]["values"][0]
arrayed_values = dic["procpar"][arrayed_param]["values"]

print(f"Arrayed parameter: {arrayed_param}")
print(f"Arrayed values: {arrayed_values}")
print(f"Input shape: {data.shape}")
```

## Write one directory per array value

Each output directory receives one FID and a copy of the Varian metadata. The
`nblocks` value is adjusted because each separated output is a single 1D FID.

```{code-cell} ipython3
separated_dic = dict(dic)
separated_dic["nblocks"] = 1

output_dirs = []
for index, array_value in enumerate(arrayed_values):
    output_dir = work_path / f"{arrayed_param}_{array_value}.fid"
    ng.varian.write(str(output_dir), separated_dic, data[index], overwrite=True)
    output_dirs.append(output_dir)

print("Created directories:")
for output_dir in output_dirs:
    print("-", output_dir.name)
```

## Verify a separated FID

```{code-cell} ipython3
_, separated = ng.varian.read(str(output_dirs[0]), shape=(64,), torder="flat")

print(f"First output shape: {separated.shape}")
print(f"Matches source row: {ng.misc.isdatasimilar(data[0], separated)}")
```

```{code-cell} ipython3
:tags: [hide-cell]

work_dir.cleanup()
```

For measured data with complete acquisition metadata, the same pattern applies:
read `arrayed_data.dir`, get the arrayed parameter name from `procpar`, and write
one output directory for each value.
