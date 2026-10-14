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

# Process a 2D TPPI NMRPipe FID

This notebook processes a TPPI-style NMRPipe FID in the direct dimension,
transposes the data, processes the indirect dimension, reverses the sweep, and
writes a processed 2D NMRPipe spectrum.

**{nb-download}`Download notebook (.ipynb) <process_pipe_2d_tppi.ipynb>`** ·
<strong><a class="reference external" href="https://storage.googleapis.com/google-code-archive-downloads/v2/code.google.com/nmrglue/example_process_pipe_2d_tppi.zip"><code class="xref download myst-nb docutils literal notranslate"><span class="pre">Download</span> <span class="pre">example</span> <span class="pre">data</span></code></a></strong>

```{code-cell} ipython3
:tags: [hide-cell]

from pathlib import Path
from tempfile import TemporaryDirectory
from urllib.request import urlretrieve
from zipfile import ZipFile
import os

import nmrglue as ng


archive_name = "example_process_pipe_2d_tppi.zip"
archive_url = "https://storage.googleapis.com/google-code-archive-downloads/v2/code.google.com/nmrglue/" + archive_name
work_dir = TemporaryDirectory(prefix="nmrglue-process-pipe-tppi-")
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
example_dir = work_path / "processing"
input_path = example_dir / "nmrpipe_2d_tppi/test.fid"
```

## Read the TPPI time-domain data

```{code-cell} ipython3
dic, time_data = ng.pipe.read(str(input_path))
print(f"Input shape: {time_data.shape}")
print(f"Input dtype: {time_data.dtype}")
```

## Process both dimensions

The direct dimension is processed first. After transposition, the indirect TPPI
dimension is processed, reversed, and transposed back.

```{code-cell} ipython3
# Direct dimension.
proc_dic, data = ng.pipe_proc.sp(dic, time_data, off=0.35, end=0.98, pow=2, c=1.0)
proc_dic, data = ng.pipe_proc.zf(proc_dic, data, auto=True)
proc_dic, data = ng.pipe_proc.ft(proc_dic, data, auto=True)
proc_dic, data = ng.pipe_proc.ps(proc_dic, data, p0=151.0, p1=0.0)
proc_dic, data = ng.pipe_proc.di(proc_dic, data)

# Indirect dimension after transposition.
proc_dic, data = ng.pipe_proc.tp(proc_dic, data)
proc_dic, data = ng.pipe_proc.sp(proc_dic, data, off=0.35, end=0.98, pow=2, c=0.5)
proc_dic, data = ng.pipe_proc.zf(proc_dic, data, auto=True)
proc_dic, data = ng.pipe_proc.ft(proc_dic, data, auto=True)
proc_dic, data = ng.pipe_proc.ps(proc_dic, data, p0=0.0, p1=0.0)
proc_dic, data = ng.pipe_proc.di(proc_dic, data)
proc_dic, data = ng.pipe_proc.rev(proc_dic, data, sw=True)
proc_dic, spectrum = ng.pipe_proc.tp(proc_dic, data)
```

## Write and verify the processed spectrum

```{code-cell} ipython3
output_path = example_dir / "2d_pipe_tppi.ft2"
ng.pipe.write(str(output_path), proc_dic, spectrum, overwrite=True)
_, roundtrip_data = ng.pipe.read(str(output_path))

print(f"Processed shape: {spectrum.shape}")
print(f"Processed dtype: {spectrum.dtype}")
print(f"Round-trip data match: {ng.misc.isdatasimilar(spectrum, roundtrip_data)}")
```

```{code-cell} ipython3
:tags: [hide-cell]

work_dir.cleanup()
```
