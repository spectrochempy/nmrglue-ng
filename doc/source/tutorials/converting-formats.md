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

# Converting between file formats

The converter API maps data and metadata between supported NMR formats. This
example converts a 2D NMRPipe spectrum to Sparky, writes a UCSF file, and reads
it back to check the converted data.

**{nb-download}`Download notebook (.ipynb) <converting-formats.ipynb>`** ·
{download}`Download NMRPipe example data <../../../tests/fixtures/fileio/data/nmrpipe_2d_cosy_example.ft2>`

The downloaded COSY example is a processed NMRPipe file. The hidden setup cell
loads it either from the current directory or from the repository fixture;
reveal it to inspect those steps.

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

dic, data = ng.pipe.read(str(data_path))
```

## Convert NMRPipe data to Sparky

Create a converter, load the NMRPipe dictionary and array, then request the
Sparky representation. The converter prepares the target-format metadata and
performs format-specific data transformations.

```{code-cell} ipython3
converter = ng.convert.converter()
converter.from_pipe(dic, data)
sparky_dic, sparky_data = converter.to_sparky()

print(f"NMRPipe shape and type: {data.shape}, {data.dtype}")
print(f"Sparky shape and type: {sparky_data.shape}, {sparky_data.dtype}")
```

## Write the converted file

Write to a temporary directory for a safe, repeatable example. The file is
removed when the cell finishes; replace the temporary path with a location in
your working folder when you want to keep the converted file.

```{code-cell} ipython3
with TemporaryDirectory() as output_dir:
    output_path = Path(output_dir) / "converted.ucsf"
    ng.sparky.write(str(output_path), sparky_dic, sparky_data)
    roundtrip_dic, roundtrip_data = ng.sparky.read(str(output_path))

    print(f"Sparky data round trip matches: {ng.misc.isdatasimilar(sparky_data, roundtrip_data)}")
    print(f"Read-back shape: {roundtrip_data.shape}")
```

The converter also supports other source and destination formats. See the
[conversion examples](../how-to/conversion) for additional workflows and the
<a href="../reference/index.html">API reference</a> for format-specific
readers and writers.
