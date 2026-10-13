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

# Reading NMR files

nmrglue-ng reads and writes common NMR file formats through modules imported
from `nmrglue`. The currently supported formats include:

| Module | File format | Reference |
| --- | --- | --- |
| `bruker` | Bruker | [Bruker manuals](https://www.bruker.com/service/information-communication/user-manuals/nmr.html) |
| `pipe` | NMRPipe | [NMRPipe](https://www.ibbr.umd.edu/nmrpipe/index.html) |
| `sparky` | Sparky/Poky | [NMRFAM-Sparky](https://nmrfam.wisc.edu/nmrfam-sparky-distribution/) |
| `varian` | Varian/Agilent | |
| `rnmrtk` | Rowland NMR Toolkit | [RNMRTK](https://rnmrtk.uchc.edu/rnmrtk/RNMRTK.html) |
| `jcampdx` | JCAMP-DX | [JCAMP-DX](http://www.jcamp-dx.org/) |
| `nmrml` | NMR Markup Language | [nmrML](https://github.com/nmrML/nmrML) |
| `simpson` | SIMPSON | [SIMPSON](https://inano.au.dk/about/research-centers-and-projects/nmr/software-and-tools/downloads/) |
| `spinsolve` | Magritek or JCAMP-DX | [Magritek](https://magritek.com/products/spinsolve/) |
| `tecmag` | Tecmag | [Tecmag](https://www.tecmag.com/) |

**{nb-download}`Download notebook (.ipynb) <reading.ipynb>`** ·
{download}`Download 1D JCAMP-DX spectrum <../../../tests/fixtures/fileio/data/jcampdx/epicatechin_1h.jdx>` ·
{download}`Download 2D NMRPipe COSY spectrum <../../../tests/fixtures/fileio/data/nmrpipe_2d_cosy_example.ft2>`

The notebook reads both a processed 1D JCAMP-DX spectrum and a processed 2D
NMRPipe spectrum. Hidden setup cells locate downloaded data files or use the
repository fixtures during a documentation build; reveal them to adapt the
paths.

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


def first_value(header, key):
    value = header.get(key)
    if value is None:
        return "not recorded"
    if isinstance(value, (list, tuple)):
        return value[0] if value else "not recorded"
    return value
```

## Read a 1D JCAMP-DX spectrum

The first example is a processed ¹H spectrum of (-)-epicatechin. JCAMP-DX
stores the spectrum and experiment details in a text-based file.

```{code-cell} ipython3
:tags: [hide-cell]

jcamp_path = find_data_file("epicatechin_1h.jdx", "jcampdx")
```

```{code-cell} ipython3
jcamp_dic, jcamp_data = ng.jcampdx.read(str(jcamp_path))

print(f"Array dimensions: {jcamp_data.ndim}")
print(f"Array shape: {jcamp_data.shape}")
print(f"Array data type: {jcamp_data.dtype}")
for key in ("TITLE", ".OBSERVENUCLEUS", ".OBSERVEFREQUENCY", "XUNITS", "YUNITS"):
    print(f"{key}: {first_value(jcamp_dic, key)}")
```

This file has one spectral dimension, so its NumPy array is one-dimensional.
The metadata keys and values in `jcamp_dic` follow JCAMP-DX conventions.

## Read a 2D NMRPipe file

The second example is a processed COSY spectrum. NMRPipe stores its data in a
binary file and returns format-specific header values in a Python dictionary.

```{code-cell} ipython3
:tags: [hide-cell]

pipe_path = find_data_file("nmrpipe_2d_cosy_example.ft2", "")
```

```{code-cell} ipython3
pipe_dic, pipe_data = ng.pipe.read(str(pipe_path))

print(f"Array dimensions: {pipe_data.ndim}")
print(f"Array shape (indirect, direct): {pipe_data.shape}")
print(f"Array data type: {pipe_data.dtype}")
for key in ("FDF1LABEL", "FDF2LABEL", "FDF1SW", "FDF2SW"):
    print(f"{key}: {first_value(pipe_dic, key)}")
```

The `read` function returns a metadata dictionary and a NumPy array. Here the
array has 512 indirect-dimension points and 2048 direct-dimension points; its
shape follows NumPy order, with the indirect axis first and direct axis last.

## Reader-specific options

Some formats do not contain all the information needed to determine the array
shape or FID ordering automatically. When necessary, provide those details to
the reader. For example, the `varian` reader may need explicit `shape` and
`torder` values for 3D data; see {ref}`varian_module`.

Next, compare how these 1D and 2D headers are represented by a
[universal dictionary](universal-dictionaries.md).
