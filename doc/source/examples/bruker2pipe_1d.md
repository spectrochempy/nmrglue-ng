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

# Convert 1D Bruker data to NMRPipe

This notebook reads a 1D Bruker FID and writes an NMRPipe FID.

**{nb-download}`Download notebook (.ipynb) <bruker2pipe_1d.ipynb>`** ·
<strong><a class="reference external" href="https://storage.googleapis.com/google-code-archive-downloads/v2/code.google.com/nmrglue/example_bruker2pipe_1d.zip"><code class="xref download myst-nb docutils literal notranslate"><span class="pre">Download</span> <span class="pre">example</span> <span class="pre">data</span></code></a></strong>

```{code-cell} ipython3
:tags: [hide-cell]

from pathlib import Path
from tempfile import TemporaryDirectory
from urllib.request import urlretrieve
from zipfile import ZipFile
import os

import nmrglue as ng


archive_name = "example_bruker2pipe_1d.zip"
archive_url = "https://storage.googleapis.com/google-code-archive-downloads/v2/code.google.com/nmrglue/" + archive_name
work_dir = TemporaryDirectory(prefix="nmrglue-bruker2pipe-1d-")
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
example_dir = work_path / "bruker2pipe_1d"
bruker_dir = example_dir / "bruker_1d"
```

## Read the Bruker FID

```{code-cell} ipython3
bruker_dic, bruker_data = ng.bruker.read(str(bruker_dir), read_pulseprogram=False)
print(f"Bruker shape: {bruker_data.shape}")
print(f"Bruker dtype: {bruker_data.dtype}")
```

## Define NMRPipe metadata and convert

Start from Bruker metadata guessed by nmrglue, then set the NMRPipe axis fields
used for this example.

```{code-cell} ipython3
udic = ng.bruker.guess_udic(bruker_dic, bruker_data)
udic[0].update(size=2048, complex=True, encoding="direct", sw=10000.0, obs=600.133, car=4.773 * 600.133, label="1H")

converter = ng.convert.converter()
converter.from_bruker(bruker_dic, bruker_data, udic)
pipe_dic, pipe_data = converter.to_pipe()

output_path = example_dir / "1d_pipe.fid"
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
