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

# Simulate 1D line shapes

This how-to compares common one-dimensional line shapes and combines several
pseudo-Voigt peaks into a synthetic 1D spectrum. It is useful when choosing a
model for simulation, peak picking, or fitting workflows.

**{nb-download}`Download notebook (.ipynb) <simulate_lineshapes_1d.ipynb>`**

```{code-cell} ipython3
:tags: [hide-cell]

import matplotlib.pyplot as plt
import nmrglue as ng
import numpy as np
```

## Compare normalized line shapes

The line-shape helper functions return profiles with unit height at the center.
Using the same full width at half maximum (FWHM) makes the tail behavior easy to
compare.

```{code-cell} ipython3
x = np.linspace(-50.0, 50.0, 1001)
center = 0.0
fwhm = 12.0

gaussian = ng.lineshapes1d.sim_gauss_fwhm(x, center, fwhm)
lorentzian = ng.lineshapes1d.sim_lorentz_fwhm(x, center, fwhm)
voigt = ng.lineshapes1d.sim_voigt_fwhm(x, center, fwhm_g=10.0, fwhm_l=4.0)
pseudo_voigt = ng.lineshapes1d.sim_pvoigt_fwhm(x, center, fwhm=fwhm, eta=0.35)

print(f"Gaussian maximum: {gaussian.max():.3f}")
print(f"Lorentzian maximum: {lorentzian.max():.3f}")
print(f"Pseudo-Voigt maximum: {pseudo_voigt.max():.3f}")
```

```{code-cell} ipython3
fig, ax = plt.subplots(figsize=(8, 4), constrained_layout=True)
ax.plot(x, gaussian, label="Gaussian")
ax.plot(x, lorentzian, label="Lorentzian")
ax.plot(x, voigt, label="Voigt")
ax.plot(x, pseudo_voigt, label="Pseudo-Voigt")
ax.set_xlabel("Point offset")
ax.set_ylabel("Normalized intensity")
ax.set_title("Common 1D line shapes")
ax.legend()
_ = fig
```

## Build a synthetic 1D spectrum

`sim_NDregion()` uses the same line-shape labels as the fitting and peak-picking
helpers. For a one-dimensional pseudo-Voigt region, each peak parameter tuple is
`(position, fwhm, eta)`.

```{code-cell} ipython3
shape = (512,)
params = [[(120.0, 9.0, 0.20)], [(240.0, 14.0, 0.45)], [(360.0, 11.0, 0.70)]]
amps = [80.0, 120.0, 60.0]

spectrum = ng.linesh.sim_NDregion(shape, lineshapes=["pv"], params=params, amps=amps)

print(f"Synthetic shape: {spectrum.shape}")
print(f"Maximum intensity: {spectrum.max():.3f}")
```

```{code-cell} ipython3
points = np.arange(shape[0])

fig_spectrum, ax_spectrum = plt.subplots(figsize=(9, 4), constrained_layout=True)
ax_spectrum.plot(points, spectrum, color="tab:blue")
ax_spectrum.set_xlabel("Point")
ax_spectrum.set_ylabel("Intensity")
ax_spectrum.set_title("Synthetic pseudo-Voigt spectrum")
for peak in params:
    ax_spectrum.axvline(peak[0][0], color="tab:red", linestyle="--", linewidth=0.8)
_ = fig_spectrum
```

```{code-cell} ipython3
:tags: [hide-cell]

plt.close(fig)
plt.close(fig_spectrum)
```

Use this pattern to generate controlled test spectra: choose peak positions,
widths, mixing factors, and amplitudes, then pass them to `sim_NDregion()` with
the desired line-shape labels.
