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

# Writing NMR files

After changing data in memory, use the corresponding writer to save it in a
format that nmrglue-ng supports. This example writes a modified NMRPipe file to
a temporary directory, reads it back, and compares the values and metadata.

**{nb-download}`Download notebook (.ipynb) <writing-data.ipynb>`** ·
{download}`Download NMRPipe example data <../../../tests/fixtures/fileio/data/nmrpipe_2d_cosy_example.ft2>`

The hidden setup cell makes the notebook executable with the downloaded file
or the repository fixture used when building the documentation. Reveal it to
inspect the file-loading code.

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

## Edit a copy of the data

The read array is independent of the file on disk. Copy it before making
changes, and retain the original metadata dictionary for the NMRPipe writer.

```{code-cell} ipython3
modified_data = data.copy()
modified_data[0, 0] = 100.0

print(f"Original value: {data[0, 0]}")
print(f"Modified value: {modified_data[0, 0]}")
```

## Write and read back the new file

This example uses a temporary output directory so repeated notebook runs do
not overwrite a file or leave generated data beside the tutorial. NMRPipe
writers refuse to overwrite an existing path unless `overwrite=True` is
explicitly supplied.

```{code-cell} ipython3
with TemporaryDirectory() as output_dir:
    output_path = Path(output_dir) / "modified.ft2"
    ng.pipe.write(str(output_path), dic, modified_data)

    try:
        ng.pipe.write(str(output_path), dic, modified_data)
    except OSError as error:
        print(f"Existing-file protection: {error}")

    ng.pipe.write(str(output_path), dic, modified_data, overwrite=True)
    new_dic, new_data = ng.pipe.read(str(output_path))

    print(f"Data changed: {not ng.misc.isdatasimilar(data, new_data)}")
    print(f"Header preserved: {ng.misc.isdicsimilar(dic, new_dic)}")
    print(f"Written shape: {new_data.shape}")
```

The round trip shows that the edited array was saved while its NMRPipe header
remained the same. For a persistent output, pass a destination path in your
working folder instead of the temporary directory. To intentionally replace an
existing file, pass `overwrite=True` to the writer.

See [Converting between file formats](converting-formats.md) to write
data in a different NMR format.
