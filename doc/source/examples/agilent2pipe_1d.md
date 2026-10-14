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

# Convert 1D Agilent/Varian data to NMRPipe

This how-to reads Agilent/Varian `fid` and `procpar` files, maps the metadata
into a universal dictionary, and writes an NMRPipe FID.

**{nb-download}`Download notebook (.ipynb) <agilent2pipe_1d.ipynb>`** ·
<strong><a class="reference external" href="https://storage.googleapis.com/google-code-archive-downloads/v2/code.google.com/nmrglue/example_agilent2pipe_1d.zip"><code class="xref download myst-nb docutils literal notranslate"><span class="pre">Download</span> <span class="pre">example</span> <span class="pre">data</span></code></a></strong>

```{code-cell} ipython3
:tags: [hide-cell]

from pathlib import Path
from tempfile import TemporaryDirectory
from urllib.request import urlretrieve
from zipfile import ZipFile
import os

import nmrglue as ng


archive_url = (
    "https://storage.googleapis.com/google-code-archive-downloads/v2/"
    "code.google.com/nmrglue/example_agilent2pipe_1d.zip"
)
archive_name = "example_agilent2pipe_1d.zip"
work_dir = TemporaryDirectory(prefix="nmrglue-agilent2pipe-1d-")
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

example_dir = work_path / "agilent2pipe_1d"
agilent_dir = example_dir / "agilent_1d"
if not (agilent_dir / "fid").is_file() or not (agilent_dir / "procpar").is_file():
    raise FileNotFoundError("The downloaded archive does not contain agilent_1d/fid and procpar")
```

## Read the Agilent/Varian dataset

`varian.read()` returns the acquisition dictionary and the complex time-domain
array.

```{code-cell} ipython3
varian_dic, varian_data = ng.varian.read(str(agilent_dir))

print(f"Agilent/Varian shape: {varian_data.shape}")
print(f"Agilent/Varian dtype: {varian_data.dtype}")
```

## Define the target NMRPipe axis metadata

Start from `guess_udic()` and then set the NMRPipe conversion parameters used by
the matching `var2pipe` script.

```{code-cell} ipython3
udic = ng.varian.guess_udic(varian_dic, varian_data)
udic[0]["size"] = 1500
udic[0]["complex"] = True
udic[0]["encoding"] = "direct"
udic[0]["sw"] = 50000.0
udic[0]["obs"] = 125.681
udic[0]["car"] = 99.0 * 125.681
udic[0]["label"] = "C13"

print(f"Target direct points: {udic[0]['size']}")
print(f"Target sweep width: {udic[0]['sw']} Hz")
print(f"Target nucleus label: {udic[0]['label']}")
```

## Convert and write the NMRPipe file

The converter prepares an NMRPipe dictionary and array, then writes the NMRPipe
FID.

```{code-cell} ipython3
converter = ng.convert.converter()
converter.from_varian(varian_dic, varian_data, udic)
pipe_dic, pipe_data = converter.to_pipe()

output_path = example_dir / "1d_pipe.fid"
ng.pipe.write(str(output_path), pipe_dic, pipe_data, overwrite=True)
roundtrip_dic, roundtrip_data = ng.pipe.read(str(output_path))

print(f"NMRPipe shape: {pipe_data.shape}")
print(f"NMRPipe dtype: {pipe_data.dtype}")
print(f"Round-trip data match: {ng.misc.isdatasimilar(pipe_data, roundtrip_data)}")
```

The archive also contains a `var2pipe` script. Running that script requires
NMRPipe and is outside this self-contained documentation build.

See also `nmrglue.fileio.varian`, `nmrglue.fileio.pipe`, and
`nmrglue.fileio.convert` in the API reference.

```{code-cell} ipython3
:tags: [hide-cell]

work_dir.cleanup()
```
