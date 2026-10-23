# Integration-noise uncertainty correction

**Date:** 2026-10-23
**Baseline:** `661e5b2` (`master`) before the local working change
**Attribution:** upstream nmrglue [#295](https://github.com/jjhelmus/nmrglue/pull/295) and [#296](https://github.com/jjhelmus/nmrglue/pull/296), both open when assessed.

## Finding

`integration.integrate` computes an integrated value as a sampled sum times
the ppm bin width, but its baseline-noise uncertainty omitted that width.
`integration.ndintegrate` likewise omitted the product of bin widths, used the
noise-region size instead of the number of integrated signal bins, and indexed
the noise region with an invalid list of slices.

For independent baseline samples with common standard deviation `sigma`, an
integrated volume is `V = (sum(s_i)) * product(dx_j)`. Its propagated baseline
uncertainty is therefore:

```text
sigma(V) = sigma * sqrt(N_signal) * product(dx_j)
```

This has the same volume units as `V`; the noise region estimates `sigma` but
does not determine the number of terms in the integrated sum.

## Reproduction and correction

On the baseline, a 12-point 1D array with 0.1 ppm bins returned an integrated
value/error pair of `[1.4, 1.0]`, although the uncertainty in integral units is
`0.1`. The equivalent `ndintegrate` call raised `IndexError` because NumPy does
not accept a list of slices as multidimensional indexing.

The local working correction multiplies errors by the same `dx` or bin-volume
factor as the value, counts selected signal bins, and indexes the noise region
with a tuple of slices. Function signatures, value-only results, and values
when `noise_limits` is supplied are unchanged.

Independent review found that the initial local normalization accepted a flat
three-value 1D `noise_limits` array and silently ignored its third value. The
correction now requires both `limits` and `noise_limits` to have the exact
`(dimensions, 2)` shape after valid flat 1D inputs are normalized. Malformed
one-dimensional and nested three-bound inputs raise `ValueError` rather than
selecting an unintended region.

## Validation

Current-author, self-contained test execution after the local working change:

```console
$ python -m pytest tests/analysis/test_analysis_integration.py --strict-markers --strict-config -ra
27 passed in 0.88s

$ python -m pytest -m "not dataset and not external_software" --strict-markers --strict-config -ra
551 passed, 142 deselected, 42 warnings in 12.00s
```

The new tests cover 1D normalization, ppm and Hz coordinates, reversed bounds,
and 1D through 3D integrations with unequal bin widths and distinct
signal/noise region sizes. No external corpus or external software was used.
The deselected cases are marked as requiring an external dataset or external
software; they are not validated by this CI-equivalent profile. This is
implementer verification, not independent review.

## Conclusion

The correction is portable: it is generic, API-compatible, reproducible
without `nmrglue-ng`-specific infrastructure, and is already represented by
the attributed upstream proposals. It requires independent scientific-change
review before delivery.
