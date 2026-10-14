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

# Process a 2D NMRPipe FID

This how-to processes a 2D NMRPipe time-domain dataset in the direct dimension,
transposes the data, processes the indirect dimension, then transposes back
before writing a processed NMRPipe file.

**{nb-download}`Download notebook (.ipynb) <process_pipe_2d.ipynb>`** ·
**{download}`Download example data <../_data/historical_examples/example_process_pipe_2d.zip>`**

```{code-cell} ipython3
:tags: [hide-cell]

from pathlib import Path
from tempfile import TemporaryDirectory
from urllib.request import urlretrieve
from zipfile import ZipFile
import os

import nmrglue as ng


archive_name = "example_process_pipe_2d.zip"
archive_url = "https://storage.googleapis.com/google-code-archive-downloads/v2/code.google.com/nmrglue/" + archive_name
work_dir = TemporaryDirectory(prefix="nmrglue-process-pipe-2d-")
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
data_path = example_dir / "nmrpipe_2d/test.fid"
```

## Read the time-domain plane

```{code-cell} ipython3
dic, time_data = ng.pipe.read(str(data_path))

print(f"Input shape: {time_data.shape}")
print(f"Input dtype: {time_data.dtype}")
```

## Process the direct dimension

```{code-cell} ipython3
proc_dic, direct = ng.pipe_proc.sp(dic, time_data, off=0.35, end=0.98, pow=1, c=1.0)
proc_dic, direct = ng.pipe_proc.zf(proc_dic, direct, auto=True)
proc_dic, direct = ng.pipe_proc.ft(proc_dic, direct, auto=True)
proc_dic, direct = ng.pipe_proc.ps(proc_dic, direct, p0=-29.0, p1=0.0)
proc_dic, direct = ng.pipe_proc.di(proc_dic, direct)

print(f"After direct dimension: {direct.shape}, {direct.dtype}")
```

## Process the indirect dimension

Transposition makes the indirect dimension the active processing dimension for
the same `pipe_proc` functions.

```{code-cell} ipython3
proc_dic, indirect = ng.pipe_proc.tp(proc_dic, direct)
proc_dic, indirect = ng.pipe_proc.sp(proc_dic, indirect, off=0.35, end=0.9, pow=1, c=0.5)
proc_dic, indirect = ng.pipe_proc.zf(proc_dic, indirect, size=2048)
proc_dic, indirect = ng.pipe_proc.ft(proc_dic, indirect, auto=True)
proc_dic, indirect = ng.pipe_proc.ps(proc_dic, indirect, p0=0.0, p1=0.0)
proc_dic, indirect = ng.pipe_proc.di(proc_dic, indirect)
proc_dic, spectrum = ng.pipe_proc.tp(proc_dic, indirect)

print(f"Processed shape: {spectrum.shape}")
print(f"Processed dtype: {spectrum.dtype}")
```

## Write and read back the processed spectrum

```{code-cell} ipython3
with TemporaryDirectory() as output_dir:
    output_path = Path(output_dir) / "2d_pipe.ft2"
    ng.pipe.write(str(output_path), proc_dic, spectrum)
    _, roundtrip = ng.pipe.read(str(output_path))

    print(f"Wrote: {output_path.name}")
    print(f"Round-trip shape: {roundtrip.shape}")
    print(f"Round-trip data match: {ng.misc.isdatasimilar(spectrum, roundtrip)}")
```

```{code-cell} ipython3
:tags: [hide-cell]

work_dir.cleanup()
```

See also the `nmrglue.fileio.pipe` and `nmrglue.process.pipe_proc` API
reference pages.
