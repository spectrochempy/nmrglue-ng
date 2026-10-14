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

# Separate interleaved 2D Bruker data

This how-to separates an interleaved Bruker acquisition into one 2D directory per
array element. The synthetic input follows the historical example convention:
rows from each array element are interleaved, so output `i` is selected with
`data[i::array_size]`.

**{nb-download}`Download notebook (.ipynb) <separate_2d_bruker.ipynb>`** ·
**{download}`Download historical script <../../../examples/separate/separate_2d_bruker/separate.py>`**

```{code-cell} ipython3
:tags: [hide-cell]

from pathlib import Path
from tempfile import TemporaryDirectory

import nmrglue as ng
import numpy as np


work_dir = TemporaryDirectory(prefix="nmrglue-separate-2d-bruker-")
work_path = Path(work_dir.name)

array_size = 3
indirect_size = 4
direct_size = 32

udic = {"ndim": 2}
udic[0] = {
    "size": indirect_size,
    "complex": True,
    "encoding": "states",
    "sw": 1200.0,
    "obs": 125.0,
    "car": 56.0 * 125.0,
    "label": "C13",
    "time": True,
    "freq": False,
}
udic[1] = {
    "size": direct_size,
    "complex": True,
    "encoding": "direct",
    "sw": 4000.0,
    "obs": 500.0,
    "car": 4.7 * 500.0,
    "label": "H1",
    "time": True,
    "freq": False,
}
dic = ng.bruker.create_dic(udic)

rows, direct = np.indices((array_size * indirect_size, direct_size), dtype=np.float32)
array_index = rows % array_size
indirect = rows // array_size
interleaved_data = np.exp(-direct / 14.0 - indirect / 5.0) * np.exp(1j * (0.2 * direct + 0.4 * indirect))
interleaved_data *= 1.0 + 0.1 * array_index
interleaved_data = interleaved_data.astype(np.complex64)
ng.bruker.write(str(work_path / "arrayed_data.dir"), dic, interleaved_data, overwrite=True)
```

## Read the interleaved acquisition

Bruker data does not carry the array split in the same way as the Varian
`procpar` examples, so the user supplies the total shape and array size.

```{code-cell} ipython3
dic, data = ng.bruker.read(
    str(work_path / "arrayed_data.dir"),
    shape=(array_size * indirect_size, direct_size),
    cplex=True,
)

print(f"Array size: {array_size}")
print(f"Input shape: {data.shape}")
```

## Write one Bruker directory per array element

```{code-cell} ipython3
output_dirs = []
for index in range(array_size):
    output_dir = work_path / str(index + 1)
    ng.bruker.write(str(output_dir), dic, data[index::array_size], overwrite=True)
    output_dirs.append(output_dir)

print("Created directories:")
for output_dir in output_dirs:
    print("-", output_dir.name)
```

## Verify one separated 2D file

```{code-cell} ipython3
_, separated = ng.bruker.read(str(output_dirs[2]), shape=(indirect_size, direct_size), cplex=True)

print(f"Third output shape: {separated.shape}")
print(f"Matches source stride: {ng.misc.isdatasimilar(data[2::array_size], separated)}")
```

```{code-cell} ipython3
:tags: [hide-cell]

work_dir.cleanup()
```

For measured data, determine the true array size, the full interleaved shape,
and any acquisition files that must be copied before writing the separated
directories.
