# JEOL test fixtures

These JEOL JDF files are packaged test fixtures for the nmrglue JEOL reader.

## Provenance

### Group 1 — Fluorine and phosphorus

| Field | Value |
|---|---|
| Files | `fluorine.jdf`, `phosphorus.jdf` |
| Source | [cheminfo/jeol-data-test](https://github.com/cheminfo/jeol-data-test) |
| Revision | [`70bf716`](https://github.com/cheminfo/jeol-data-test/commit/70bf71612900fd158c3e482af86f48655ca86352) |
| Added | May 2023 |
| Header date | 2023-05-07 (`MSC007_001`) |
| License | MIT (see below) |
| Redistribution | Permitted under MIT |

### Group 2 — Rutin 1H and 13C

| Field | Value |
|---|---|
| Files | `Rutin_3080ug200uL_DMSOd6_qHNMR_400MHz_Jeol.jdf`, `Rutin_3080ug200uL_DMSOd6_13CNMR_400MHz_Jeol.jdf` |
| Source | [cheminfo/jeol-data-test](https://github.com/cheminfo/jeol-data-test) |
| Original data | Harvard Dataverse |
| DOI | [10.7910/DVN/ZAZDNM](https://doi.org/10.7910/DVN/ZAZDNM) |
| Original license | CC0 1.0 (public domain dedication) |
| Sample | Rutin, 3080 µg / 200 µL DMSO-d6, 400 MHz |
| Redistribution | Permitted under CC0 1.0 |

### Group 3 — Epicatechin HSQC 2D

| Field | Value |
|---|---|
| File | `epicatechin_hsqc.jdf` |
| Source | [nmrXiv CENAPTNMR project P33](https://nmrxiv.org/project/P33) |
| DOI | [10.57992/nmrxiv.p33](https://doi.org/10.57992/nmrxiv.p33) |
| License | **CC0 1.0** |
| Sample | (-)-Epicatechin 2880 µg / 200 µL DMSO-d6, 400 MHz |
| Experiment | HSQC 2D |
| Directory | `(-)-Epicatechin 400 MHz in DMSOd6 NMR data /` |

## SHA-256 checksums

| File | SHA-256 |
|---|---|
| `fluorine.jdf` | `9cd2692c0b258d38212c800f722ad56b0d4f991a49b2946b8652290b3cef1711` |
| `phosphorus.jdf` | `18251908cfb159f82472680801aab9a3ba062248283024e5f542742008629f03` |
| `Rutin_*_qHNMR_*.jdf` | `bb76e9d4a8bb9dd66b8ddbaeffcee10ce3635f615861caa75630a46453e0cf71` |
| `Rutin_*_13CNMR_*.jdf` | `c870bd413d4be6b31c17d7e8995a63bfef031777c26bad61aa2ff48e1eb43e46` |
| `epicatechin_hsqc.jdf` | `eaa28b4b1fe05f95a41ace4f69f33ee6f31f26f392d3aea1d94bf3978b153625` |

## MIT License (cheminfo/jeol-data-test)

Copyright (c) 2020 cheminfo

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
THE SOFTWARE.
