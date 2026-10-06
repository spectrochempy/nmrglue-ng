#! /usr/bin/env python
"""
Read and plot a 2D processed Bruker HSQC spectrum.

Uses the packaged 1H/13C HSQC fixture (Ginsenoside Rg1, 600 MHz).
"""
import os
import nmrglue as ng
import matplotlib.pyplot as plt

# Packaged HSQC fixture (pdata/1 contains the processed 2D spectrum)
data_file = os.path.join(
    os.path.dirname(__file__), os.pardir, os.pardir,
    "nmrglue", "fileio", "tests", "data",
    "bruker_pdata", "exp2d_hsqc", "pdata", "1",
)

# Read processed data and build axis parameters
dic, data = ng.bruker.read_pdata(data_file)
udic = ng.bruker.guess_udic(dic, data, pdata=True)

# Direct dimension (1H)
uc_1h = ng.fileiobase.uc_from_udic(udic, dim=1)
ppm_1h_0, ppm_1h_1 = uc_1h.ppm_limits()

# Indirect dimension (13C)
uc_13c = ng.fileiobase.uc_from_udic(udic, dim=0)
ppm_13c_0, ppm_13c_1 = uc_13c.ppm_limits()

plt.figure()
plt.contour(data, extent=(ppm_1h_0, ppm_1h_1, ppm_13c_0, ppm_13c_1))
plt.xlabel("1H (ppm)")
plt.ylabel("13C (ppm)")
plt.gca().invert_xaxis()
plt.title("HSQC — Ginsenoside Rg1, 600 MHz")
plt.show()
