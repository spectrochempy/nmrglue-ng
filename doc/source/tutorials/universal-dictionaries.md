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

# Universal dictionaries

File readers return format-specific metadata in `dic`. The
`guess_udic()` function converts that header and its data array into a common
**universal dictionary**. Compare a 1D JCAMP-DX spectrum with a 2D NMRPipe
spectrum to see how the dictionary represents one versus two dimensions.

**{nb-download}`Download notebook (.ipynb) <universal-dictionaries.ipynb>`** ·
{download}`Download 1D JCAMP-DX spectrum <../../../tests/fixtures/fileio/data/jcampdx/epicatechin_1h.jdx>` ·
{download}`Download 2D NMRPipe COSY spectrum <../../../tests/fixtures/fileio/data/nmrpipe_2d_cosy_example.ft2>`

The file-reading setup is hidden so the examples can focus on the dictionaries.
Reveal the setup cells if you want to inspect how each standalone notebook data
file is loaded.

```{code-cell} ipython3
:tags: [hide-cell]

from pathlib import Path

import nmrglue as ng


def find_data_file(filename, fixture_subdir):
    local_path = Path(filename)
    if local_path.is_file():
        return local_path.resolve()
    for candidate in [Path.cwd(), *Path.cwd().parents]:
        fixture = candidate / "tests/fixtures/fileio/data" / fixture_subdir / filename
        if fixture.is_file():
            return fixture
    raise FileNotFoundError(f"Download {filename} into {Path.cwd()}")
```

## A 1D universal dictionary

The JCAMP-DX reader returns one array dimension. Its universal dictionary has
one axis entry, `udic_1d[0]`.

```{code-cell} ipython3
:tags: [hide-cell]

jcamp_path = find_data_file("epicatechin_1h.jdx", "jcampdx")
jcamp_dic, jcamp_data = ng.jcampdx.read(str(jcamp_path))
```

```{code-cell} ipython3
udic_1d = ng.jcampdx.guess_udic(jcamp_dic, jcamp_data)
axis_1d = udic_1d[0]

print(f"Number of dimensions: {udic_1d['ndim']}")
print(f"Array shape: {jcamp_data.shape}")
print(f"Dimension 0: {axis_1d['label']}")
print(f"Size: {axis_1d['size']} points")
print(f"Spectral width: {axis_1d['sw']:.3f} Hz")
print(f"Observation frequency: {axis_1d['obs']:.3f} MHz")
```

Create a coordinate scale for this single spectral dimension:

```{code-cell} ipython3
uc_1d = ng.fileiobase.uc_from_udic(udic_1d, dim=0)
ppm_1h_axis = uc_1d.ppm_scale()
print(f"1D ppm coordinates: {len(ppm_1h_axis)}")
```

## A 2D universal dictionary

The NMRPipe COSY array has two dimensions. Its dictionary has an entry for
each NumPy axis: dimension 0 is the indirect (row) dimension and dimension 1 is
the direct (column) dimension.

```{code-cell} ipython3
:tags: [hide-cell]

pipe_path = find_data_file("nmrpipe_2d_cosy_example.ft2", "")
pipe_dic, pipe_data = ng.pipe.read(str(pipe_path))
```

```{code-cell} ipython3
udic_2d = ng.pipe.guess_udic(pipe_dic, pipe_data)
print(f"Number of dimensions: {udic_2d['ndim']}")
print(f"Array shape (indirect, direct): {pipe_data.shape}")

for dim in range(udic_2d["ndim"]):
    axis = udic_2d[dim]
    print(f"Dimension {dim} ({axis['label']}):")
    print(f"  Size: {axis['size']} points")
    print(f"  Spectral width: {axis['sw']:.3f} Hz")
    print(f"  Observation frequency: {axis['obs']:.3f} MHz")
    print(f"  Carrier: {axis['car']:.3f} Hz")
    print(f"  Frequency-domain data: {axis['freq']}")
    print(f"  Complex data: {axis['complex']}")
    print(f"  Encoding: {axis['encoding']}")
```

The principal axis fields are:

| Field | Meaning |
| --- | --- |
| `size` | Number of values along the corresponding array axis |
| `sw` | Spectral width in hertz |
| `obs` | Observation frequency in megahertz |
| `car` | Carrier/reference position in hertz |
| `label` | Nucleus or axis label |
| `complex` | Whether the dimension is represented as complex data |
| `encoding` | Indirect-dimension encoding, such as States or TPPI |
| `time`, `freq` | Whether the data are in the time or frequency domain |

The universal dictionary contains only a common subset of format metadata.
Some readers may need the user to check or supply values when a file does not
record enough information.

## Create coordinate scales for the 2D array axes

`uc_from_udic()` creates a unit-conversion object for one dictionary dimension.
Call `ppm_scale()` or `hz_scale()` to create one coordinate value per point.

```{code-cell} ipython3
uc_indirect = ng.fileiobase.uc_from_udic(udic_2d, dim=0)
uc_direct = ng.fileiobase.uc_from_udic(udic_2d, dim=1)

ppm_indirect_axis = uc_indirect.ppm_scale()
ppm_direct_axis = uc_direct.ppm_scale()

print(f"Indirect axis: {len(ppm_indirect_axis)} ppm coordinates")
print(f"Direct axis: {len(ppm_direct_axis)} ppm coordinates")
print(f"Data array shape (indirect, direct): {pipe_data.shape}")
```

The [visualization example](plotting.md) uses the direct scale horizontally and
the indirect scale vertically to draw a contour plot.
