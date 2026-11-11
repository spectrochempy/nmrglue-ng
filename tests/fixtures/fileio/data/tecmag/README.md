# Tecmag reference spectrum

`LiCl_ref2-ftp.tnt` is an unmodified file from Christopher Kerr and Matthew
Lawson, [pytnt test data, version 14](https://doi.org/10.6084/m9.figshare.1228508.v14),
licensed [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/).

- [TNT file](https://doi.org/10.6084/m9.figshare.1228508.v14), Figshare file
  1778524, SHA-256 `b303cda127753d7b44da498a93ccb00250a57490b71a33a48f733acaeab22c0f`.
- TNMR data-point listing `LiCl_ref2-ftp.txt`, Figshare file 1778530,
  SHA-256 `658c239e9f0dfa59eb441cba7d86600b9dc5d69fd8f40e679ad635334129b51c`.
  Four rounded coordinate and sample pairs from this export are recorded in
  the test.

TNMR's export has 16,384 points, in descending order, at about 6.103516 Hz
per point. The direct dimension is the first NumPy dimension in the TNT
reader. The middle bin is at −25.940 Hz and the observed frequency in the
TNT header is about 117.211250 MHz. The ppm test converts the exported Hz
coordinates using that observation frequency, the same divisor documented
by [pytnt's ppm conversion](https://github.com/chatcannon/pytnt/blob/50f56e731ef3095c52f34ec000f51b2282f5bc72/pytnt/processTNT.py#L190-L204).

The acquisition width field is 50,000 Hz and the dwell is 10 µs. The
processed export spans a 100,000 Hz DFT grid, as implied by that dwell.
This pair qualifies the direct processed 1D axis for an even number of bins.
Odd-length grids and multidimensional spectra require further reference data.
