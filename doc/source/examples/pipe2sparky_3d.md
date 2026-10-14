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

# Convert a 3D NMRPipe file to Sparky

This notebook reads a processed 3D NMRPipe fixture and writes a Sparky UCSF file.
The fixture keeps the documentation self-contained and independent of an
external NMRPipe install.

**{nb-download}`Download notebook (.ipynb) <pipe2sparky_3d.ipynb>`** ·
**{download}`Download 3D NMRPipe fixture <../../../tests/fixtures/fileio/data/nmrpipe_3d_freq.ft3>`** ·
<strong><a class="reference external" href="https://storage.googleapis.com/google-code-archive-downloads/v2/code.google.com/nmrglue/example_pipe2sparky_3d.zip"><code class="xref download myst-nb docutils literal notranslate"><span class="pre">Download</span> <span class="pre">example</span> <span class="pre">archive</span></code></a></strong>

```{code-cell} ipython3
:tags: [hide-cell]

from pathlib import Path
from tempfile import TemporaryDirectory

import nmrglue as ng


filename = "nmrpipe_3d_freq.ft3"
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

```{code-cell} ipython3
pipe_dic, pipe_data = ng.pipe.read(str(data_path))
print(f"NMRPipe shape: {pipe_data.shape}")
print(f"NMRPipe dtype: {pipe_data.dtype}")
```

```{code-cell} ipython3
udic = ng.pipe.guess_udic(pipe_dic, pipe_data)
converter = ng.convert.converter()
converter.from_pipe(pipe_dic, pipe_data, udic)
sparky_dic, sparky_data = converter.to_sparky()

with TemporaryDirectory() as output_dir:
    output_path = Path(output_dir) / "sparky_3d.ucsf"
    ng.sparky.write(str(output_path), sparky_dic, sparky_data)
    _, roundtrip_data = ng.sparky.read(str(output_path))

    print(f"Sparky shape: {sparky_data.shape}")
    print(f"Sparky dtype: {sparky_data.dtype}")
    print(f"Round-trip data match: {ng.misc.isdatasimilar(sparky_data, roundtrip_data)}")
```

See also `nmrglue.fileio.pipe`, `nmrglue.fileio.sparky`, and
`nmrglue.fileio.convert` in the API reference.
