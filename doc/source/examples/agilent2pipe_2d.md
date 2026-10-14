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

# Convert 2D Agilent/Varian data to NMRPipe

This notebook reads an Agilent/Varian dataset and writes a 2D NMRPipe FID.

**{nb-download}`Download notebook (.ipynb) <agilent2pipe_2d.ipynb>`** ·
<strong><a class="reference external" href="https://storage.googleapis.com/google-code-archive-downloads/v2/code.google.com/nmrglue/example_agilent2pipe_2d.zip"><code class="xref download myst-nb docutils literal notranslate"><span class="pre">Download</span> <span class="pre">example</span> <span class="pre">data</span></code></a></strong>

```{code-cell} ipython3
:tags: [hide-cell]

from pathlib import Path
from tempfile import TemporaryDirectory
from urllib.request import urlretrieve
from zipfile import ZipFile
import os

import nmrglue as ng


archive_name = "example_agilent2pipe_2d.zip"
archive_url = "https://storage.googleapis.com/google-code-archive-downloads/v2/code.google.com/nmrglue/" + archive_name
work_dir = TemporaryDirectory(prefix="nmrglue-agilent2pipe-2d-")
work_path = Path(work_dir.name)
archive_path = None
for candidate in [Path.cwd(), *Path.cwd().parents]:
    fixture = candidate / "doc/source/_data/historical_examples" / archive_name
    if fixture.is_file():
        archive_path = fixture
        break
if archive_path is None:
    cache_dir = os.environ.get("NMRGLUE_HISTORICAL_EXAMPLES")
    archive_path = Path(cache_dir) / archive_name if cache_dir else work_path / archive_name
if not archive_path.is_file():
    archive_path = work_path / archive_name
    urlretrieve(archive_url, archive_path)
with ZipFile(archive_path) as archive:
    archive.extractall(work_path)
example_dir = work_path / "agilent2pipe_2d"
agilent_dir = example_dir / "agilent_2d"
```

## Read the Agilent/Varian dataset

`varian.read()` returns the acquisition dictionary and the complex 2D time-domain
array.

```{code-cell} ipython3
varian_dic, varian_data = ng.varian.read(str(agilent_dir))
print(f"Agilent/Varian shape: {varian_data.shape}")
print(f"Agilent/Varian dtype: {varian_data.dtype}")
```

## Define the target NMRPipe dimensions

Define the direct and indirect dimensions with explicit NMRPipe metadata.

```{code-cell} ipython3
udic = ng.varian.guess_udic(varian_dic, varian_data)
udic[1].update(size=1500, complex=True, encoding="direct", sw=50000.0, obs=125.691, car=55.0 * 125.691, label="13C")
udic[0].update(size=332, complex=True, encoding="states", sw=5555.556, obs=50.648, car=120.0 * 50.648, label="15N")
```

## Convert and verify the NMRPipe file

```{code-cell} ipython3
converter = ng.convert.converter()
converter.from_varian(varian_dic, varian_data, udic)
pipe_dic, pipe_data = converter.to_pipe()

output_path = example_dir / "2d_pipe.fid"
ng.pipe.write(str(output_path), pipe_dic, pipe_data, overwrite=True)
_, roundtrip_data = ng.pipe.read(str(output_path))

print(f"NMRPipe shape: {pipe_data.shape}")
print(f"NMRPipe dtype: {pipe_data.dtype}")
print(f"Round-trip data match: {ng.misc.isdatasimilar(pipe_data, roundtrip_data)}")
```

See also `nmrglue.fileio.varian`, `nmrglue.fileio.pipe`, and
`nmrglue.fileio.convert` in the API reference.

```{code-cell} ipython3
:tags: [hide-cell]

work_dir.cleanup()
```
