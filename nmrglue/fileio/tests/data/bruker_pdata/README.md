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
| Archive path | `nmrxiv-pt-succrose/1/` |
| Sample | Sucrose 2 mM, DSS 0.5 mM, NaN₃ 2 mM in H₂O/D₂O 90/10 |

### exp2d_hsqc, exp2d_cosy — 2D natural products

| Field | Value |
|---|---|
| Source | [nmrXiv project P33](https://nmrxiv.org/project/P33) (CENAPTNMR) |
| DOI | [10.57992/nmrxiv.p33](https://doi.org/10.57992/nmrxiv.p33) |
| License | **CC0 1.0** |
| exp2d_hsqc | [Sample S208](https://nmrxiv.org/sample/S208) Ginsenoside Rg1, dir `Ginsenoside_3110ug200uL_HSQC_600MHz_Bruker/` |
| exp2d_cosy | [Sample S213](https://nmrxiv.org/sample/S213) Gossypol, dir `Gossypol_3650ug200uL_CDCl3_COSY_600MHz_JDX/` |

## Files

### exp1 — 1D

| Path | Description |
|---|---|
| `exp1/fid` | Raw FID (512 KB, complex128) |
| `exp1/acqus` | Acquisition parameters |
| `exp1/acqu` | Acquisition parameters (alternate) |
| `exp1/pdata/1/1r` | Processed real (256 KB, float64) |
| `exp1/pdata/1/1i` | Processed imaginary (256 KB, float64) |
| `exp1/pdata/1/procs` | Processing parameters |
| `exp1/pdata/1/proc` | Processing script |
| `exp1/pdata/1/title` | Experiment title |

### exp2d_hsqc — 2D HSQC

| Path | Description |
|---|---|
| `exp2d_hsqc/ser` | Raw 2D (2 MB, complex128, 256×1024) |
| `exp2d_hsqc/acqus` | Acquisition parameters |
| `exp2d_hsqc/acqu` | Acquisition parameters (alternate) |
| `exp2d_hsqc/pdata/1/2rr` | Processed real-real (4 MB, float64, 256×4096) |
| `exp2d_hsqc/pdata/1/2ri` | Processed real-imag |
| `exp2d_hsqc/pdata/1/2ir` | Processed imag-real |
| `exp2d_hsqc/pdata/1/2ii` | Processed imag-imag |
| `exp2d_hsqc/pdata/1/procs` | Processing parameters (direct dim) |
| `exp2d_hsqc/pdata/1/proc2` | Processing parameters (indirect dim) |
| `exp2d_hsqc/pdata/1/proc2s` | Processing parameters (indirect dim, status) |
| `exp2d_hsqc/pdata/1/title` | Experiment title |

### exp2d_cosy — 2D COSY

| Path | Description |
|---|---|
| `exp2d_cosy/ser` | Raw 2D (1 MB, complex128, 128×1024) |
| `exp2d_cosy/acqus` | Acquisition parameters |
| `exp2d_cosy/acqu` | Acquisition parameters (alternate) |
| `exp2d_cosy/pdata/1/2rr` | Processed real-real (4 MB, float64, 512×2048) |
| `exp2d_cosy/pdata/1/procs` | Processing parameters |
| `exp2d_cosy/pdata/1/proc2` | Processing parameters (indirect dim) |
| `exp2d_cosy/pdata/1/proc2s` | Processing parameters (indirect dim, status) |
| `exp2d_cosy/pdata/1/title` | Experiment title |

## SHA-256 checksums

### exp1

| File | SHA-256 |
|---|---|
| `exp1/fid` | `54944667f24e48156de287fc8d014299313f388c1cf86f5608b62a8e55900cfc` |
| `exp1/acqus` | `e5f58d482a45d8435699cf815d654627603e65836942ca3ecc16ca28a4c91f51` |
| `exp1/acqu` | `1047bc400e3f5f1951c4bef802cb6d27b2a16648da4756fa61a55715159b8df1` |
| `exp1/pdata/1/1r` | `0fc9527ba7075ca40e865520bdf734a14b10b65a4865d27c242c26462db5598e` |
| `exp1/pdata/1/1i` | `1caa891d00a0ab76119b755a02540c9eed4a98b6b0b12954729a07d12920dc03` |
| `exp1/pdata/1/procs` | `1b4cfc2fd31b2be0f98a61f20e9515ab8299447b6636ec6afd63b94cf6c7126f` |
| `exp1/pdata/1/proc` | `b32a4e56b165cf47b2249c562c17f51c09c369263dcb0e6bd1f5a907e730fb3d` |
| `exp1/pdata/1/title` | `eb6f06fedbdd25648e5929f3ae715f61f98180ebc098d13f3d6e89e6bb6eb84c` |

### exp2d_hsqc

| File | SHA-256 |
|---|---|
| `exp2d_hsqc/ser` | `9f1a5ac3b311bfff5855e44b48de6e70e3b3af521b36ab8454c936bd59fae859` |
| `exp2d_hsqc/acqus` | `221675a89f741f95a142b445c99a7817d0b96cd4ab89a836b343610bb9eb4a26` |
| `exp2d_hsqc/acqu` | `d2e089119132db5723ed6b3035b41cd60afd75d36d96b34d63bb92d3d0a13e57` |
| `exp2d_hsqc/pdata/1/2rr` | `f2f4ddd3dfe690f409bc070ed0f04588b6330d5f8932bb5179d15e1dcae37b7a` |
| `exp2d_hsqc/pdata/1/2ri` | `0a932b6b5ad502251b990f8063abcc599b5eb0306504c298bd874188394f38fc` |
| `exp2d_hsqc/pdata/1/2ir` | `c7f501e3fa5586558c486a65b905f4dd424b27072aa32ce641f6232c84757fa6` |
| `exp2d_hsqc/pdata/1/2ii` | `d6a9fef8f3cf35a1cb6d4c58b619d8febd0ee7501160b83c87ff97482b383422` |
| `exp2d_hsqc/pdata/1/procs` | `e242cda91aaeb5e289422096a23d7f507fd311ec7cc2b18b3d2d78c1e82df0ba` |
| `exp2d_hsqc/pdata/1/proc2` | `e388266c9312f4f934f0ded0012fe9f1379932a1c4ff0a62ca417db7df6186bc` |
| `exp2d_hsqc/pdata/1/proc2s` | `492cb85e392e869d7d4b5dcae06b4a71ce779e3b8a92db4f074e330b7f53d340` |
| `exp2d_hsqc/pdata/1/title` | `47da861020d3e1adef7183add5a3cad1b43c922c4229065825ad792008fda2c2` |

### exp2d_cosy

| File | SHA-256 |
|---|---|
| `exp2d_cosy/ser` | `cddbbf7650a165b83c89ccf64be62885130c52a4ec4c9d4da002844a354d63f1` |
| `exp2d_cosy/acqus` | `a086d1cbe92edef6d28cc6e0da13245e71c965de5b08ef2df846a1e2d7f2fab2` |
| `exp2d_cosy/acqu` | `0d1dadf699610e55c0f9d31a00a41410c0df8016f7be5cbc1cc72af3fceba444` |
| `exp2d_cosy/pdata/1/2rr` | `e64e82ff73af49679624355792e13caffdd8b81b19389655acdc9a5a43075747` |
| `exp2d_cosy/pdata/1/procs` | `869c95a56fdc1eb40432658862686c6f8c64996ffee84877c760247793da5237` |
| `exp2d_cosy/pdata/1/proc2` | `bb2fb1885649afabb95c50d0da17e60f8b46f275631ea26527c267e879384704` |
| `exp2d_cosy/pdata/1/proc2s` | `accc8b05360d211b5dcdf64923bdee190cd60f0a302b6f55ebb4a15971c65ec0` |
| `exp2d_cosy/pdata/1/title` | `a38c6c91a897ca48b7c793e7e58ec53d9b64f1725a3d5b148d931ed4d7bfafcb` |
