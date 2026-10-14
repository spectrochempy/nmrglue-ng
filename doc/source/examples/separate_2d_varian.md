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

# Separate arrayed 2D Agilent/Varian data

This how-to separates a 2D Agilent/Varian experiment collected with an
innermost arrayed parameter. The synthetic input has layout
`(indirect point, array value, direct point)`, matching the historical script's
`data[:, i, :]` split.

**{nb-download}`Download notebook (.ipynb) <separate_2d_varian.ipynb>`** ·
**{download}`Download historical script <../../../examples/separate/separate_2d_varian/separate.py>`**

```{code-cell} ipython3
:tags: [hide-cell]

from pathlib import Path
from tempfile import TemporaryDirectory

import nmrglue as ng
import numpy as np


work_dir = TemporaryDirectory(prefix="nmrglue-separate-2d-varian-")
work_path = Path(work_dir.name)

udic = {"ndim": 3}
udic[0] = {
    "size": 4,
    "complex": False,
    "encoding": "states",
    "sw": 1200.0,
    "obs": 125.0,
    "car": 56.0 * 125.0,
    "label": "C13",
    "time": True,
    "freq": False,
}
udic[1] = {
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
udic[2] = {
    "size": 32,
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
dic["procpar"]["array"] = ng.varian.create_pdic_param("array", ["tXmix"])
dic["procpar"]["tXmix"] = ng.varian.create_pdic_param("tXmix", ["5", "10", "15"])

indirect, array_index, direct = np.indices((4, 3, 32), dtype=np.float32)
arrayed_data = np.exp(-direct / 14.0 - indirect / 5.0) * np.exp(1j * (0.2 * direct + 0.4 * indirect))
arrayed_data *= 1.0 + 0.1 * array_index
arrayed_data = arrayed_data.astype(np.complex64)
ng.varian.write(str(work_path / "arrayed_data.dir"), dic, arrayed_data, overwrite=True)
```

## Read the arrayed experiment

```{code-cell} ipython3
dic, data = ng.varian.read(str(work_path / "arrayed_data.dir"), shape=(4, 3, 32), torder="flat")

arrayed_param = dic["procpar"]["array"]["values"][0]
arrayed_values = dic["procpar"][arrayed_param]["values"]

print(f"Arrayed parameter: {arrayed_param}")
print(f"Arrayed values: {arrayed_values}")
print(f"Input shape: {data.shape}")
```

## Write one 2D directory per array value

Each output keeps all indirect increments for one array value.

```{code-cell} ipython3
separated_dic = dict(dic)
separated_dic["nblocks"] = data.shape[0]

output_dirs = []
for index, array_value in enumerate(arrayed_values):
    output_dir = work_path / f"{arrayed_param}_{array_value}.fid"
    ng.varian.write(str(output_dir), separated_dic, data[:, index, :], overwrite=True)
    output_dirs.append(output_dir)

print("Created directories:")
for output_dir in output_dirs:
    print("-", output_dir.name)
```

## Verify one separated 2D file

```{code-cell} ipython3
_, separated = ng.varian.read(str(output_dirs[1]), shape=(4, 32), torder="flat")

print(f"Second output shape: {separated.shape}")
print(f"Matches source slice: {ng.misc.isdatasimilar(data[:, 1, :], separated)}")
```

```{code-cell} ipython3
:tags: [hide-cell]

work_dir.cleanup()
```

For measured data, use the same indexing pattern after confirming which arrayed
parameter is interleaved innermost in `procpar`.
