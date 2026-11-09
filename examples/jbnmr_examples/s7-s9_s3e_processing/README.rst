Processing S3E filtered data example
====================================

Introduction
------------

This example is taken from Listing S7, S8 and S9 in the 2013 JBNMR nmrglue
paper.  A 2D Agilent/Varian acquisition collected with an S3E filter is
separated (`separate_s3e.py`), converted to NMRPipe format (`convert.py`),
and processed and recombined (`xy_s3e.py`).


Instructions
------------

Execute `python separate_s3e.py` to separate the S3E sum and difference
spectra from data set in the Agilent/Varian `fid` file.  This creates the files
fid_dif and fid_sum.

Execute `python convert.py` to convert these two files to NMRPipe format.  This
step creates the files `test_sum.fid` and `test_dif.fid`.

Execute `python xy_s3e.py` to process and combine the sum and difference
spectra. This step creates the `test.ft2` file.
