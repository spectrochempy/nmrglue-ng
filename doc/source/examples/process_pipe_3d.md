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

# Process a 3D NMRPipe dataset plane by plane

This notebook uses `pipe.iter3D()` to process 3D NMRPipe data plane by plane
without loading every intermediate plane manually.

**{nb-download}`Download notebook (.ipynb) <process_pipe_3d.ipynb>`** ·
<strong><a class="reference external" href="https://storage.googleapis.com/google-code-archive-downloads/v2/code.google.com/nmrglue/example_process_pipe_3d.zip"><code class="xref download myst-nb docutils literal notranslate"><span class="pre">Download</span> <span class="pre">example</span> <span class="pre">data</span></code></a></strong>

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


archive_name = "example_process_pipe_3d.zip"
archive_url = "https://storage.googleapis.com/google-code-archive-downloads/v2/code.google.com/nmrglue/" + archive_name
work_dir = TemporaryDirectory(prefix="nmrglue-process-pipe-3d-")
work_path = Path(work_dir.name)
cache_dir = os.environ.get("NMRGLUE_HISTORICAL_EXAMPLES")
archive_path = Path(cache_dir) / archive_name if cache_dir else work_path / archive_name
if not archive_path.is_file():
    archive_path = work_path / archive_name
    urlretrieve(archive_url, archive_path)
with ZipFile(archive_path) as archive:
    archive.extractall(work_path)
example_dir = work_path / "processing"
(example_dir / "ft").mkdir(exist_ok=True)
```

## Process XY planes

The first iterator reads YX planes from the input FID series. Each plane is
processed in the direct and first indirect dimensions, then written as an
intermediate FT2 series.

```{code-cell} ipython3
xy_planes = 0
xiter = ng.pipe.iter3D(str(example_dir / "nmrpipe_3d/data/test%03d.fid"), "x", "x")
for xy_planes, (dic, plane) in enumerate(xiter, start=1):
    dic, plane = ng.pipe_proc.zf(dic, plane, auto=True)
    dic, plane = ng.pipe_proc.ft(dic, plane, auto=True)
    dic, plane = ng.pipe_proc.ps(dic, plane, p0=0.0, p1=0.0)
    dic, plane = ng.pipe_proc.di(dic, plane)

    dic, plane = ng.pipe_proc.tp(dic, plane)
    dic, plane = ng.pipe_proc.zf(dic, plane, auto=True)
    dic, plane = ng.pipe_proc.ft(dic, plane, auto=True)
    dic, plane = ng.pipe_proc.ps(dic, plane, p0=0.0, p1=0.0)
    dic, plane = ng.pipe_proc.di(dic, plane)
    dic, plane = ng.pipe_proc.tp(dic, plane)

    xiter.write(str(example_dir / "ft/test%03d.ft2"), plane, dic)

print(f"Processed XY planes: {xy_planes}")
```

Expected output:

```text
Processed XY planes: 128
```

## Process ZX planes

The second iterator reads the intermediate FT2 series along the Z dimension and
writes the final FT3 series.

```{code-cell} ipython3
zx_planes = 0
ziter = ng.pipe.iter3D(str(example_dir / "ft/test%03d.ft2"), "z", "z")
for zx_planes, (dic, plane) in enumerate(ziter, start=1):
    dic, plane = ng.pipe_proc.zf(dic, plane, auto=True)
    dic, plane = ng.pipe_proc.ft(dic, plane, auto=True)
    dic, plane = ng.pipe_proc.ps(dic, plane, p0=-92.0, p1=65.0)
    dic, plane = ng.pipe_proc.di(dic, plane)
    ziter.write(str(example_dir / "ft/test%03d.ft3"), plane, dic)

_, processed = ng.pipe.read(str(example_dir / "ft/test%03d.ft3"))
print(f"Processed ZX planes: {zx_planes}")
print(f"Final shape: {processed.shape}")
print(f"Final dtype: {processed.dtype}")
```

Expected output:

```text
Processed ZX planes: 128
Final shape: (128, 128, 4096)
Final dtype: float32
```

```{code-cell} ipython3
:tags: [hide-cell]

work_dir.cleanup()
```
