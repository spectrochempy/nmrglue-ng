# Bruker processed-data test fixtures

These Bruker TopSpin directories contain raw and processed data for testing
`ng.bruker.read()` and `ng.bruker.read_pdata()`.

## Provenance

### exp1 — 1D sucrose standard

| Field | Value |
|---|---|
| Source | [nmrXiv project P52](https://nmrxiv.org/project/P52) |
| DOI | [10.57992/nmrxiv.p52](https://doi.org/10.57992/nmrxiv.p52) |
| License | **CC0 1.0** |
| Sample | Sucrose 2 mM, DSS 0.5 mM, NaN₃ 2 mM in H₂O/D₂O 90/10 |

### exp2d_hsqc, exp2d_cosy — 2D natural products

| Field | Value |
|---|---|
| Source | nmrXiv CENAPTNMR dataset |
| DOI | [10.57992/nmrxiv.cenaptnmr](https://doi.org/10.57992/nmrxiv.cenaptnmr) |
| License | **CC0 1.0** |
| Samples | Ginsenoside Rg1 (HSQC), Gossypol (COSY) |

## Files

### exp1 — 1D

| Path | Description |
|---|---|
| `exp1/fid` | Raw FID (512 KB, complex128) |
| `exp1/acqus` | Acquisition parameters |
| `exp1/pdata/1/1r` | Processed real (256 KB, float64) |
| `exp1/pdata/1/1i` | Processed imaginary (256 KB, float64) |
| `exp1/pdata/1/procs` | Processing parameters |

### exp2d_hsqc — 2D HSQC

| Path | Description |
|---|---|
| `exp2d_hsqc/ser` | Raw 2D (2 MB, complex128, shape 256×1024) |
| `exp2d_hsqc/acqus` | Acquisition parameters |
| `exp2d_hsqc/pdata/1/2rr` | Processed real-real (4 MB, float64, shape 256×4096) |
| `exp2d_hsqc/pdata/1/2ri` | Processed real-imag |
| `exp2d_hsqc/pdata/1/2ir` | Processed imag-real |
| `exp2d_hsqc/pdata/1/2ii` | Processed imag-imag |
| `exp2d_hsqc/pdata/1/procs` | Processing parameters (direct dim) |
| `exp2d_hsqc/pdata/1/proc2s` | Processing parameters (indirect dim) |

### exp2d_cosy — 2D COSY

| Path | Description |
|---|---|
| `exp2d_cosy/ser` | Raw 2D (1 MB, complex128, shape 128×1024) |
| `exp2d_cosy/acqus` | Acquisition parameters |
| `exp2d_cosy/pdata/1/2rr` | Processed real-real (4 MB, float64, shape 512×2048) |
| `exp2d_cosy/pdata/1/procs` | Processing parameters |
| `exp2d_cosy/pdata/1/proc2s` | Processing parameters (indirect dim) |

## Checksums

| File | SHA-256 |
|---|---|
| `exp1/fid` | `54944667f24e48156de287fc8d014299313f388c1cf86f5608b62a8e55900cfc` |
| `exp1/acqus` | `e5f58d482a45d8435699cf815d654627603e65836942ca3ecc16ca28a4c91f51` |
| `exp1/pdata/1/1r` | `0fc9527ba7075ca40e865520bdf734a14b10b65a4865d27c242c26462db5598e` |
| `exp1/pdata/1/procs` | `1b4cfc2fd31b2be0f98a61f20e9515ab8299447b6636ec6afd63b94cf6c7126f` |
| `exp2d_hsqc/ser` | `9f1a5ac3b311bfff5855e44b48de6e70e3b3af521b36ab8454c936bd59fae859` |
| `exp2d_hsqc/pdata/1/2rr` | `f2f4ddd3dfe690f409bc070ed0f04588b6330d5f8932bb5179d15e1dcae37b7a` |
| `exp2d_cosy/ser` | `cddbbf7650a165b83c89ccf64be62885130c52a4ec4c9d4da002844a354d63f1` |
| `exp2d_cosy/pdata/1/2rr` | `e64e82ff73af49679624355792e13caffdd8b81b19389655acdc9a5a43075747` |
