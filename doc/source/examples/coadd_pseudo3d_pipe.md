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

# Coadd pseudo-3D NMRPipe directories

This how-to averages matching 2D planes from multiple pseudo-3D NMRPipe
directories. Each input run has the same subdirectory layout, and each matching
`test.fid` plane is averaged into `coadded_data.dir`.

**{nb-download}`Download notebook (.ipynb) <coadd_pseudo3d_pipe.ipynb>`** ·
**{download}`Download historical script <../../../examples/coadd/coadd_pseudo3d_pipe/coadd_pseudo3d.py>`**

```{code-cell} ipython3
:tags: [hide-cell]

from pathlib import Path
from tempfile import TemporaryDirectory

import nmrglue as ng
import numpy as np


work_dir = TemporaryDirectory(prefix="nmrglue-coadd-pseudo3d-")
work_path = Path(work_dir.name)

udic = {"ndim": 2}
udic[0] = {
    "size": 12,
    "complex": True,
    "encoding": "states",
    "sw": 1800.0,
    "obs": 125.0,
    "car": 56.0 * 125.0,
    "label": "C13",
    "time": True,
    "freq": False,
}
udic[1] = {
    "size": 48,
    "complex": True,
    "encoding": "direct",
    "sw": 4000.0,
    "obs": 500.0,
    "car": 4.7 * 500.0,
    "label": "H1",
    "time": True,
    "freq": False,
}
pipe_dic = ng.pipe.create_dic(udic)

indirect, direct = np.indices((udic[0]["size"], udic[1]["size"]), dtype=np.float32)
base = np.exp(-direct / 20.0 - indirect / 7.0) * np.exp(1j * (0.20 * direct + 0.30 * indirect))
for run_index, scale in enumerate([0.95, 1.05], start=1):
    for plane_index, plane_scale in enumerate([0.8, 1.0, 1.2], start=1):
        plane_dir = work_path / f"run{run_index}.dir" / f"plane{plane_index:03d}.fid"
        plane_dir.mkdir(parents=True)
        data = (scale * plane_scale * base).astype(np.complex64)
        ng.pipe.write(str(plane_dir / "test.fid"), pipe_dic, data)
```

## Find matching planes

Use the first run as the template. Each template path is matched in every other
run by replacing the run directory name.

```{code-cell} ipython3
run_dirs = sorted(work_path.glob("run*.dir"))
template_paths = sorted(run_dirs[0].glob("*.fid/test.fid"))

print(f"Runs found: {len(run_dirs)}")
print(f"Planes per run: {len(template_paths)}")
```

## Coadd each pseudo-3D plane

```{code-cell} ipython3
output_root = work_path / "coadded_data.dir"

for template_path in template_paths:
    coadd_dic, first_data = ng.pipe.read(str(template_path))
    coadd_data = np.zeros_like(first_data)

    for run_dir in run_dirs:
        input_path = run_dir / template_path.relative_to(run_dirs[0])
        _, data = ng.pipe.read(str(input_path))
        coadd_data += data / len(run_dirs)

    output_path = output_root / template_path.relative_to(run_dirs[0])
    output_path.parent.mkdir(parents=True, exist_ok=True)
    ng.pipe.write(str(output_path), coadd_dic, coadd_data, overwrite=True)

print(f"Wrote planes: {len(sorted(output_root.glob('*.fid/test.fid')))}")
```

## Check one output plane

```{code-cell} ipython3
check_path = output_root / "plane001.fid" / "test.fid"
_, coadded_plane = ng.pipe.read(str(check_path))

print(f"Example output: {check_path.relative_to(work_path)}")
print(f"Output shape: {coadded_plane.shape}")
print(f"Mean real intensity: {coadded_plane.real.mean():.6f}")
```

```{code-cell} ipython3
:tags: [hide-cell]

work_dir.cleanup()
```

For measured pseudo-3D data, keep each `run*.dir` tree on the same grid and
with the same plane names before averaging corresponding `test.fid` files.
