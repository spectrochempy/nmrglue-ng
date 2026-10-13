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

# The unit-conversion object

Array indices are useful for slicing, but NMR data are also described in
physical units such as ppm and Hz. A `unit_conversion` object maps between
points in one array dimension and those units. Create one object for each
dimension using the universal dictionary.

**{nb-download}`Download notebook (.ipynb) <unit-conversion.ipynb>`** ·
{download}`Download 2D NMRPipe COSY data <../../../tests/fixtures/fileio/data/nmrpipe_2d_cosy_example.ft2>`

The hidden setup cell loads the downloaded file or the repository fixture so
the notebook can run on its own. The conversion examples below remain visible.

```{code-cell} ipython3
:tags: [hide-cell]

from pathlib import Path

import nmrglue as ng


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
udic = ng.pipe.guess_udic(dic, data)
uc_indirect = ng.fileiobase.uc_from_udic(udic, dim=0)
uc_direct = ng.fileiobase.uc_from_udic(udic, dim=1)
```

## Convert units to array points

Calling a unit-conversion object returns the nearest integer point. Use `.f()`
for a fractional point when an exact conversion is useful.

```{code-cell} ipython3
indirect_point = uc_indirect("7.0 ppm")
indirect_point_exact = uc_indirect.f("7.0 ppm")
direct_point = uc_direct(2.0, "ppm")

print(f"7 ppm indirect point: {indirect_point}")
print(f"Exact indirect point: {indirect_point_exact:.3f}")
print(f"2 ppm direct point: {direct_point}")
```

The direct and indirect dimensions use separate conversion objects because each
has its own size, spectral width, observation frequency, and carrier.

## Convert points to physical units

The inverse methods convert a point into ppm, Hz, or percent of the dimension.

```{code-cell} ipython3
print(f"Indirect point {indirect_point} in ppm: {uc_indirect.ppm(indirect_point):.3f}")
print(f"Indirect point {indirect_point} in Hz: {uc_indirect.hz(indirect_point):.3f}")
print(
    f"Indirect point {indirect_point} as percent: "
    f"{uc_indirect.unit(indirect_point, 'percent'):.2f}%"
)
```

## Use physical units for slicing

Convert the desired ppm position to its nearest row index, then use ordinary
NumPy slicing. The slice returned from the NMRPipe data array is a NumPy array.

```{code-cell} ipython3
row = data[indirect_point, :]
column = data[:, direct_point]

print(f"Indirect row shape: {row.shape}")
print(f"Direct column shape: {column.shape}")
print(f"First five values in the row: {row[:5]}")
```

For `ppm_scale()` and the relationship between these coordinates and each array
dimension, see [Universal dictionaries](universal-dictionaries.md). The
[visualization tutorial](plotting.md) uses the same conversions to position a
2D contour plot.
