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

# Convert 2D Bruker data to NMRPipe

This notebook reads a 2D Bruker dataset and writes an NMRPipe FID.

**{nb-download}`Download notebook (.ipynb) <bruker2pipe_2d.ipynb>`** ·
<strong><a class="reference external" href="https://storage.googleapis.com/google-code-archive-downloads/v2/code.google.com/nmrglue/example_bruker2pipe_2d.zip"><code class="xref download myst-nb docutils literal notranslate"><span class="pre">Download</span> <span class="pre">example</span> <span class="pre">data</span></code></a></strong>

```{code-cell} ipython3
:tags: [hide-cell]

from pathlib import Path
from tempfile import TemporaryDirectory
from urllib.request import urlretrieve
from zipfile import ZipFile
import os

import nmrglue as ng


archive_name = "example_bruker2pipe_2d.zip"
archive_url = "https://storage.googleapis.com/google-code-archive-downloads/v2/code.google.com/nmrglue/" + archive_name
work_dir = TemporaryDirectory(prefix="nmrglue-bruker2pipe-2d-")
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
example_dir = work_path / "bruker2pipe_2d"
bruker_dir = example_dir / "bruker_2d"
```

## Read the Bruker dataset

```{code-cell} ipython3
bruker_dic, bruker_data = ng.bruker.read(str(bruker_dir), read_pulseprogram=False)
print(f"Bruker shape: {bruker_data.shape}")
print(f"Bruker dtype: {bruker_data.dtype}")
```

## Define NMRPipe metadata and convert

The direct proton dimension and indirect carbon dimension are defined explicitly
before converting to an NMRPipe FID.

```{code-cell} ipython3
udic = ng.bruker.guess_udic(bruker_dic, bruker_data)
udic[1].update(size=768, complex=True, encoding="direct", sw=11061.947, obs=800.134, car=4.773 * 800.134, label="1H")
udic[0].update(size=600, complex=True, encoding="states", sw=4000.0, obs=201.204, car=58.742 * 201.204, label="13C")

converter = ng.convert.converter()
converter.from_bruker(bruker_dic, bruker_data, udic)
pipe_dic, pipe_data = converter.to_pipe()

output_path = example_dir / "2d_pipe.fid"
ng.pipe.write(str(output_path), pipe_dic, pipe_data, overwrite=True)
_, roundtrip_data = ng.pipe.read(str(output_path))

print(f"NMRPipe shape: {pipe_data.shape}")
print(f"NMRPipe dtype: {pipe_data.dtype}")
print(f"Round-trip data match: {ng.misc.isdatasimilar(pipe_data, roundtrip_data)}")
```

```{code-cell} ipython3
:tags: [hide-cell]

work_dir.cleanup()
```
