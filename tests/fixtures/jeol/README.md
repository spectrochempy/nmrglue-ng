# JEOL JDF qualification

The self-contained tests construct a small synthetic JDF in both byte
orders. The external reference is `PN3-PPEG-b-PBn_1H.jdf` from
[Michelle Chen's Zenodo dataset, version 1](https://doi.org/10.5281/zenodo.10463168).
The JDF reports Delta 6.0 on Windows and a fluorine-19 time axis despite the
filename. Its SHA-256 is
`8709f7e15dbdbdd79882a1b05e89ad49037f588b6a0b4eda00491fd26989ed38`.
Local qualification uses the public download. Redistribution rights have
not been assessed and the experimental file is kept outside the repository.

Set `JEOL_INTEROP_JDF` to the downloaded file and run
`python -m pytest tests/interop/test_interop_jeol.py`. The test compares
both complete storage sections with their on-disk float64 words, and
compares explicit conjugation and trimming with the historical reader.
The header gives 353,155 acquired points and 353,160 stored points.
The 8.46 µs time increment from `x_sweep` agrees with the header's last
valid coordinate of 2.98768284 s.
