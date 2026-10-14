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

# Process a 1D NMRPipe FID

This how-to applies core NMRPipe-style operations to a 1D FID: sine-bell
apodization, zero filling, Fourier transform, phase correction, and discarding
the imaginary channel.

**{nb-download}`Download notebook (.ipynb) <process_pipe_1d.ipynb>`** ·
**{download}`Download example data <../_data/historical_examples/example_process_pipe_1d.zip>`**

```{code-cell} ipython3
:tags: [hide-cell]

from pathlib import Path
from tempfile import TemporaryDirectory
from urllib.request import urlretrieve
from zipfile import ZipFile
import os

import nmrglue as ng


archive_name = "example_process_pipe_1d.zip"
archive_url = "https://storage.googleapis.com/google-code-archive-downloads/v2/code.google.com/nmrglue/" + archive_name
work_dir = TemporaryDirectory(prefix="nmrglue-process-pipe-1d-")
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
data_path = example_dir / "nmrpipe_1d/test.fid"
```

## Read the time-domain data

```{code-cell} ipython3
dic, time_data = ng.pipe.read(str(data_path))

print(f"Input shape: {time_data.shape}")
print(f"Input dtype: {time_data.dtype}")
```

## Apply NMRPipe-style processing

The `pipe_proc` functions update both the data and the NMRPipe header dictionary
as the processing state changes.

```{code-cell} ipython3
proc_dic, spectrum = ng.pipe_proc.sp(dic, time_data, off=0.35, end=0.98, pow=2, c=1.0)
proc_dic, spectrum = ng.pipe_proc.zf(proc_dic, spectrum, auto=True)
proc_dic, spectrum = ng.pipe_proc.ft(proc_dic, spectrum, auto=True)
proc_dic, spectrum = ng.pipe_proc.ps(proc_dic, spectrum, p0=-17.7, p1=-36.0)
proc_dic, spectrum = ng.pipe_proc.di(proc_dic, spectrum)

print(f"Processed shape: {spectrum.shape}")
print(f"Processed dtype: {spectrum.dtype}")
print(f"First three points: {spectrum[:3]}")
```

## Write and read back the processed file

```{code-cell} ipython3
with TemporaryDirectory() as output_dir:
    output_path = Path(output_dir) / "1d_pipe.ft"
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
