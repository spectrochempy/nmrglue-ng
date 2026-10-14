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

# Low-memory reading and writing

The usual `read()` function loads an entire spectrum into memory. For large 3D
and 4D datasets, `read_lowmem()` instead returns an array-like object that
loads requested slices on demand. Slices are NumPy arrays; the low-memory object
itself does not support assignment.

This example uses a small synthetic 3D NMRPipe fixture to demonstrate the
interface. A larger dataset benefits more from low-memory access.

**{nb-download}`Download notebook (.ipynb) <low-memory.ipynb>`** ·
{download}`Download 3D NMRPipe example data <../../../tests/fixtures/fileio/data/nmrpipe_3d_time.fid>`

The hidden setup cell locates the downloaded file or the repository fixture.
Reveal it to inspect the path handling.

```{code-cell} ipython3
:tags: [hide-cell]

from pathlib import Path
from tempfile import TemporaryDirectory

import numpy as np
import nmrglue as ng


filename = "nmrpipe_3d_time.fid"
data_path = Path(filename)
if not data_path.is_file():
    for candidate in [Path.cwd(), *Path.cwd().parents]:
        fixture = candidate / "tests/fixtures/fileio/data" / filename
        if fixture.is_file():
            data_path = fixture
            break
if not data_path.is_file():
    raise FileNotFoundError(f"Download {filename} into {Path.cwd()}")
```

## Read slices on demand

`read_lowmem()` returns metadata and an object with the shape and dtype of the
stored data. Selecting a plane or trace loads only that slice as a NumPy array.

```{code-cell} ipython3
dic, low_data = ng.pipe.read_lowmem(str(data_path))

plane = low_data[0]
trace = low_data[0, 0, :]
print(f"Low-memory object: {type(low_data).__name__}")
print(f"Shape: {low_data.shape}; dtype: {low_data.dtype}")
print(f"Selected plane: {type(plane).__name__}, shape {plane.shape}")
print(f"Selected trace: {type(trace).__name__}, shape {trace.shape}")
```

The object can also be transposed without loading the complete dataset. The
result remains a low-memory object with a different axis order.

```{code-cell} ipython3
transposed = low_data.transpose()
print(f"Transposed object: {type(transposed).__name__}")
print(f"Transposed shape: {transposed.shape}")
print(f"One transposed trace: {transposed[0, 0, :].shape}")
```

Since slices are ordinary NumPy arrays, copy a trace before editing it. Such an
edit changes only the selected copy, not the file-backed low-memory object.

```{code-cell} ipython3
trace_copy = low_data[0, 0, :].copy()
trace_copy[0] = 0.0
print(f"Edited trace copy: {trace_copy}")
print(f"Original file-backed trace: {low_data[0, 0, :]}")
```

## Write trace by trace

`write_lowmem()` writes the array-like object without first loading the whole
dataset. This round trip uses a temporary directory so it leaves no generated
file beside the notebook.

```{code-cell} ipython3
with TemporaryDirectory() as output_dir:
    output_path = Path(output_dir) / "copy.ft3"
    ng.pipe.write_lowmem(str(output_path), dic, low_data)
    _, copied_data = ng.pipe.read_lowmem(str(output_path))
    same_trace = np.array_equal(low_data[0, 0, :], copied_data[0, 0, :])

    print(f"Written shape: {copied_data.shape}")
    print(f"First trace matches: {same_trace}")
```

For 3D NMRPipe processing plane by plane, see the `iter3D` examples in the
[How-to guides](../how-to/index). The [Processing tutorial](processing.md)
compares array-only processing with NMRPipe operations that also update header
metadata.
