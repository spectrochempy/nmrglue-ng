Tutorial data credits
=====================

This page records the provenance and usage terms for data linked from the
current tutorials. Source data, derived format-conversion fixtures, and
generated synthetic signals are distinguished below.

Synthetic examples
------------------

The Getting started time-domain FID is deterministic synthetic data generated
by `generate_synthetic_1d.py
<https://github.com/spectrochempy/nmrglue-ng/blob/master/doc/source/getting-started/generate_synthetic_1d.py>`_.
It represents three illustrative resonances and noise, not a measured sample.

The compact 2D and 3D NMRPipe time- and frequency-domain fixtures used in the
processing and low-memory tutorials were generated from deterministic synthetic
values by
`create_test_data_nmrpipe.sh
<https://github.com/spectrochempy/nmrglue-ng/blob/master/tests/fixtures/fileio/create_test_data_nmrpipe.sh>`_.
They are test data, not experimental spectra.

Experimental examples
---------------------

1D (-)-epicatechin
~~~~~~~~~~~~~~~~~~

The JCAMP-DX spectrum is from nmrXiv CENAPTNMR project P33,
`sample S192 <https://nmrxiv.org/sample/S192>`_: (-)-epicatechin at 400 MHz in
DMSO-d6. The source dataset and redistributed fixture are CC0 1.0. The
`fixture record <https://github.com/spectrochempy/nmrglue-ng/blob/master/tests/fixtures/fileio/data/jcampdx/README.md>`_
includes the original filename and checksum.

1D commercial-honey spectrum
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The optional 400 MHz Bruker FID in the processing tutorial is from the Zenodo
dataset `10.5281/zenodo.11341174 <https://doi.org/10.5281/zenodo.11341174>`_,
which is released under CC BY 4.0 by Maulidiani (Universiti Malaysia
Terengganu). The tutorial can instead use the bundled 1D sucrose fixture, from
nmrXiv CENAPTNMR project P52 and released under CC0 1.0. Details and checksums
for the bundled fixture are in the
`Bruker fixture record <https://github.com/spectrochempy/nmrglue-ng/blob/master/tests/fixtures/fileio/data/bruker_pdata/README.md>`_.

2D COSY spectrum
~~~~~~~~~~~~~~~~

The NMRPipe file in the Reading tutorial is derived from the processed
real-real (`2rr`) component of an experimental Bruker TopSpin COSY spectrum.
The source is nmrXiv CENAPTNMR project P33,
`sample S213 <https://nmrxiv.org/sample/S213>`_ (Gossypol, 600 MHz in CDCl3),
released under CC0 1.0. The conversion keeps the processed data and the axes
defined by ``procs``/``proc2s``; it does not reconstruct the raw FID or the
other quadrature components. The conversion recipe and checksum for the
derived NMRPipe fixture are in the
`Bruker fixture record <https://github.com/spectrochempy/nmrglue-ng/blob/master/tests/fixtures/fileio/data/bruker_pdata/README.md>`_.

Packaged example archives
~~~~~~~~~~~~~~~~~~~~~~~~~

The conversion, processing, and plotting how-to notebooks use compact archives
from the nmrglue example collection originally distributed through the Google
Code archive. They are included here to make the notebooks reproducible during
documentation builds. The archives are used as example inputs for nmrglue and
retain their original file names under ``doc/source/_data/historical_examples/``.
