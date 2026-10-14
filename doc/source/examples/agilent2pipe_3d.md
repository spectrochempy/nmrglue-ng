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

# Convert 3D Agilent/Varian data to NMRPipe

This notebook uses the low-memory Agilent/Varian reader and writes the NMRPipe
output as an XYZ-style series of planes.

**{nb-download}`Download notebook (.ipynb) <agilent2pipe_3d.ipynb>`** ·
<strong><a class="reference external" href="https://storage.googleapis.com/google-code-archive-downloads/v2/code.google.com/nmrglue/example_agilent2pipe_3d.zip"><code class="xref download myst-nb docutils literal notranslate"><span class="pre">Download</span> <span class="pre">example</span> <span class="pre">data</span></code></a></strong>

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


archive_name = "example_agilent2pipe_3d.zip"
archive_url = "https://storage.googleapis.com/google-code-archive-downloads/v2/code.google.com/nmrglue/" + archive_name
work_dir = TemporaryDirectory(prefix="nmrglue-agilent2pipe-3d-")
work_path = Path(work_dir.name)
cache_dir = os.environ.get("NMRGLUE_HISTORICAL_EXAMPLES")
archive_path = Path(cache_dir) / archive_name if cache_dir else work_path / archive_name
if not archive_path.is_file():
    archive_path = work_path / archive_name
    urlretrieve(archive_url, archive_path)
with ZipFile(archive_path) as archive:
    archive.extractall(work_path)
example_dir = work_path / "agilent2pipe_3d"
agilent_dir = example_dir / "agilent_3d"
(example_dir / "data").mkdir(exist_ok=True)
```

```{code-cell} ipython3
varian_dic, varian_data = ng.varian.read_lowmem(str(agilent_dir))
print(f"Agilent/Varian low-memory shape: {varian_data.shape}")
print(f"Agilent/Varian dtype: {varian_data.dtype}")
```

Expected output:

```text
Agilent/Varian low-memory shape: (128, 88, 1250)
Agilent/Varian dtype: complex64
```

```{code-cell} ipython3
udic = ng.varian.guess_udic(varian_dic, varian_data)
udic[2].update(size=1250, complex=True, encoding="direct", sw=50000.0, obs=125.676, car=56.0 * 125.676, label="CX")
udic[1].update(size=88, complex=True, encoding="states", sw=2777.778, obs=50.648, car=120.0 * 50.648, label="N")
udic[0].update(size=128, complex=True, encoding="states", sw=5555.556, obs=125.676, car=56.0 * 125.676, label="CA")

converter = ng.convert.converter()
converter.from_varian(varian_dic, varian_data, udic)
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
NMRPipe shape: (128, 88, 1250)
NMRPipe dtype: complex64
Round-trip shape: (128, 88, 1250)
```

```{code-cell} ipython3
:tags: [hide-cell]

work_dir.cleanup()
```
