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

# Manipulating NMR data

Readers return spectral values as NumPy arrays. Array operations change the
in-memory data; they do not change the source file on disk.

Use the same processed 2D COSY example as the preceding guides:

**{nb-download}`Download notebook (.ipynb) <manipulating-data.ipynb>`** ·
{download}`Download NMRPipe example data <../../../tests/fixtures/fileio/data/nmrpipe_2d_cosy_example.ft2>`

This hidden setup cell lets the notebook run either beside the downloaded file
or from a documentation build in the repository. Reveal it to inspect the
loading code.

```{code-cell} ipython3
:tags: [hide-cell]

from pathlib import Path

import nmrglue as ng
import numpy as np


filename = "nmrpipe_2d_cosy_example.ft2"
data_path = Path(filename)
if not data_path.is_file():
    for candidate in [Path.cwd(), *Path.cwd().parents]:
        fixture = candidate / "tests/fixtures/fileio/data" / filename
        if fixture.is_file():
            data_path = fixture
            break
if not data_path.is_file():
    raise FileNotFoundError(f"Download {filename} into {Path.cwd()}")

dic, data = ng.pipe.read(str(data_path))
```

## Inspect array values

The first array index is the indirect dimension; the second is the direct
dimension. Slices let you inspect one point, one row, one column, or a small
region without printing the full spectrum.

```{code-cell} ipython3
print(f"Array shape: {data.shape}")
print(f"Data type: {data.dtype}")
print(f"One value: {data[0, 0]}")
print(f"First five values in row 0: {data[0, :5]}")
print(f"First five values in column 0: {data[:5, 0]}")
print(f"A 3 by 5 region:\n{data[2:5, :5]}")
```

Use `.real` and `.imag` to inspect the channels of complex-valued data. The
example file is real-valued, but the operations also apply to complex NMR data.

```{code-cell} ipython3
print(f"Real channel: {data[0, :3].real}")
print(f"Imaginary channel: {data[0, :3].imag}")
```

## Summarize, reshape, and transpose

For complex-valued data, summarize the magnitude when asking for a maximum or
minimum intensity. Reshaping changes the array dimensions without changing the
sequence of stored values; transposing swaps the dimension order.

```{code-cell} ipython3
magnitude = np.abs(data)
print(f"Magnitude range: {magnitude.min():.3f} to {magnitude.max():.3f}")
print(f"Mean magnitude: {magnitude.mean():.3f}")
print(f"Standard deviation: {magnitude.std():.3f}")
print(f"Transposed shape: {data.T.shape}")
print(f"Reshaped shape: {data.reshape(1024, 1024).shape}")
```

Reshaping is useful for array computations, but it does not preserve the
original NMR dimension meanings. Keep the universal dictionary aligned with the
array shape whenever you change a spectrum's dimensions.

## Change values in memory

Copy the array before editing so that the original values remain available for
comparison. Writing edited values to a new file is covered in
[Writing NMR files](writing-data.md).

```{code-cell} ipython3
edited_data = data.copy()
edited_data[0, 0] = 100.0
edited_data[1, :3] = 0.0

print(f"Original first value: {data[0, 0]}")
print(f"Edited first value: {edited_data[0, 0]}")
print(f"Edited row segment: {edited_data[1, :3]}")
```

See the [NumPy documentation](https://numpy.org/doc/stable/) for more array
operations. {doc}`Processing data <processing>` demonstrates common NMR
operations, and [Writing NMR files](writing-data.md) shows how to save
modified data.
