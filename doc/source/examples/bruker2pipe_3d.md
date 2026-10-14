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

# Convert 3D Bruker data to NMRPipe

This notebook reads a 3D Bruker dataset and writes an NMRPipe plane series.

**{nb-download}`Download notebook (.ipynb) <bruker2pipe_3d.ipynb>`** ·
<strong><a class="reference external" href="https://storage.googleapis.com/google-code-archive-downloads/v2/code.google.com/nmrglue/example_bruker2pipe_3d.zip"><code class="xref download myst-nb docutils literal notranslate"><span class="pre">Download</span> <span class="pre">example</span> <span class="pre">data</span></code></a></strong>

```{note}
The data archive is large, so this page is not executed during hosted
documentation builds. Download the notebook and data to run it locally.
```

```{code-cell} ipython3
:tags: [hide-cell]

from pathlib import Path
from tempfile import TemporaryDirectory
from urllib.request import urlretrieve
from zipfile import ZipFile
import os

import nmrglue as ng


archive_name = "example_bruker2pipe_3d.zip"
archive_url = "https://storage.googleapis.com/google-code-archive-downloads/v2/code.google.com/nmrglue/" + archive_name
work_dir = TemporaryDirectory(prefix="nmrglue-bruker2pipe-3d-")
work_path = Path(work_dir.name)
cache_dir = os.environ.get("NMRGLUE_HISTORICAL_EXAMPLES")
archive_path = Path(cache_dir) / archive_name if cache_dir else work_path / archive_name
if not archive_path.is_file():
    archive_path = work_path / archive_name
    urlretrieve(archive_url, archive_path)
with ZipFile(archive_path) as archive:
    archive.extractall(work_path)
example_dir = work_path / "bruker2pipe_3d"
bruker_dir = example_dir / "bruker_3d"
(example_dir / "data").mkdir(exist_ok=True)
```

```{code-cell} ipython3
bruker_dic, bruker_data = ng.bruker.read(str(bruker_dir))
print(f"Bruker shape: {bruker_data.shape}")
print(f"Bruker dtype: {bruker_data.dtype}")
```

Expected output:

```text
Bruker shape: (116, 128, 768)
Bruker dtype: complex128
```

```{code-cell} ipython3
udic = ng.bruker.guess_udic(bruker_dic, bruker_data)
udic[2].update(size=768, complex=True, encoding="direct", sw=11061.947, obs=800.134, car=4.784 * 800.134, label="1H")
udic[1].update(size=128, complex=True, encoding="states", sw=2500.0, obs=81.086, car=119.787 * 81.086, label="15N")
udic[0].update(size=116, complex=True, encoding="states", sw=5555.556, obs=201.204, car=55.743 * 201.204, label="13C")

converter = ng.convert.converter()
converter.from_bruker(bruker_dic, bruker_data, udic)
pipe_dic, pipe_data = converter.to_pipe()

output_pattern = example_dir / "data/3d_pipe%03d.fid"
ng.pipe.write(str(output_pattern), pipe_dic, pipe_data, overwrite=True)
_, roundtrip_data = ng.pipe.read(str(output_pattern))

print(f"NMRPipe shape: {pipe_data.shape}")
print(f"NMRPipe dtype: {pipe_data.dtype}")
print(f"Round-trip shape: {roundtrip_data.shape}")
```

Expected output:

```text
NMRPipe shape: (116, 128, 768)
NMRPipe dtype: complex64
Round-trip shape: (116, 128, 768)
```

```{code-cell} ipython3
:tags: [hide-cell]

work_dir.cleanup()
```
