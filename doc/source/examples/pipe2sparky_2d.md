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

# Convert a 2D NMRPipe file to Sparky

This how-to reads a processed 2D NMRPipe spectrum, converts the data and metadata with
`nmrglue.convert.converter`, writes a Sparky UCSF file, and reads it back to
check the result.

**{nb-download}`Download notebook (.ipynb) <pipe2sparky_2d.ipynb>`** ·
**{download}`Download NMRPipe example data <../../../tests/fixtures/fileio/data/nmrpipe_2d_cosy_example.ft2>`**

The input is a small CC0 COSY fixture distributed with nmrglue-ng.

```{code-cell} ipython3
:tags: [hide-cell]

from pathlib import Path
from tempfile import TemporaryDirectory

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
```

## Read the NMRPipe spectrum

`pipe.read()` returns the format dictionary and the NumPy data array.

```{code-cell} ipython3
pipe_dic, pipe_data = ng.pipe.read(str(data_path))

print(f"NMRPipe shape: {pipe_data.shape}")
print(f"NMRPipe dtype: {pipe_data.dtype}")
```

## Convert to Sparky metadata and data

The converter keeps the operation explicit: initialize it from NMRPipe, then
request the Sparky representation.

```{code-cell} ipython3
converter = ng.convert.converter()
converter.from_pipe(pipe_dic, pipe_data)
sparky_dic, sparky_data = converter.to_sparky()

print(f"Sparky shape: {sparky_data.shape}")
print(f"Sparky dtype: {sparky_data.dtype}")
```

## Write and verify the UCSF file

The notebook writes to a temporary directory so repeated execution does not
leave generated files in the documentation tree.

```{code-cell} ipython3
with TemporaryDirectory() as output_dir:
    output_path = Path(output_dir) / "cosy.ucsf"
    ng.sparky.write(str(output_path), sparky_dic, sparky_data)
    roundtrip_dic, roundtrip_data = ng.sparky.read(str(output_path))

    print(f"Wrote: {output_path.name}")
    print(f"Round-trip shape: {roundtrip_data.shape}")
    print(f"Data similar: {ng.misc.isdatasimilar(sparky_data, roundtrip_data)}")
```

See also the `nmrglue.fileio.pipe`, `nmrglue.fileio.sparky`, and
`nmrglue.fileio.convert` API reference pages.
