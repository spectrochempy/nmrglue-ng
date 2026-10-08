# Bruker processed-axis parameter selection

Consolidated 2026-10-07 at `ce98382`. Covers PR #55 (`ff0c160`, base
`fd84c06`), its independent review on `34e057c`, and the corrected interpretation
documented by PR #58. This is a synthesis of those records, not another
independent review or a new TopSpin execution.

The live fixture link below reflects the 2026-10-08 single-tree relocation;
the historical evidence remains otherwise unchanged.

## Current conclusion

`pdata=True` is an explicit choice to construct an axis from processing
parameters. The examined implementation and formulas are supported by the
review. **The HSQC fixture does not demonstrate a general defect in the
historical acquisition-parameter precedence.** Its raw and processed material
describe different acquisitions.

The initial explanation, "re-referenced spectrum with a wrong default axis",
was superseded by provenance analysis and the
[technical conclusion in issue #285](https://github.com/jjhelmus/nmrglue/issues/285#issuecomment-6037369653).
That discussion also reports agreement between the historical calculation and
processing OFFSET on coherent datasets from the collection. It is evidence
against the original general-defect claim, not proof about every Bruker dataset.

## API contract

- `guess_udic(..., pdata=True)` selects processing metadata for dimensions
  with processing parameters: `OFFSET`, `SF`, `SW_p`.
- `pdata=None` (default) and `pdata=False` preserve the historical choice:
  acquisition metadata has precedence when both sets are present, with the
  existing processing fallback when acquisition metadata is absent.
- No automatic warning or default change was introduced. The option is not a
  mandatory step for coherent datasets whose two parameter sets agree.
- `strip_fake` remains the existing extraction adjustment; its interaction
  with genuine extracted data needs stronger fixture evidence.

Implementation and tests:
[bruker.py](../../nmrglue/fileio/bruker.py),
[test_bruker_pdata.py](../../tests/fileio/test_bruker_pdata.py).

## Scientific convention and sources

For a full processed dimension of `SI` points using observation/reference
value `SF` in MHz and `SW_p` in Hz, the selected processing convention is:

```text
car (Hz)      = OFFSET * SF - SW_p / 2
bin (ppm)     = SW_p / (SI * SF)
first (ppm)   = OFFSET
last (ppm)    = OFFSET - (SI - 1) * bin
```

The far spectral boundary `OFFSET - SW_p/SF` is not the last sampled point.
`first == OFFSET` follows algebraically from construction; alone it is not
an independent measurement. Bin spacing, last-point behavior and source
semantics are part of the justification.

Vendor reference: Bruker, *TopSpin — Processing Commands and Parameters*,
User Manual Version 007, document `H9776SA3_7_007`, 2020, 396 pages.
[PDF source](https://nmr.chem.ucsb.edu/docs/Bruker_NMR_Manuals/processing-reference_v007.pdf).
The reviewer recorded SHA-256
`b161cddea0bfe8ea6d7cf310d7d1ff80fccb001cb1150c7e0e44bf62188caaca`.

- p. 27 defines OFFSET as the ppm value of the first data point and gives
  default calibration `OFFSET = (SFO1/SF - 1)*1e6 + 0.5*SW*SFO1/SF`.
- pp. 31/36 define processed size `SI` and spectral width `SW_p`.
- pp. 83–84 describe `sref`/`cal`, including changes to `OFFSET`, `SF`, `SR`.
- p. 121 uses `tiltfactor = (SW_p1/SI1)/(SW_p2/SI2)`, supporting `SW_p/SI`
  bin spacing. This does not independently validate every extraction case.

With `SW_h = SW*SFO1`, the default-calibration formula matches the existing
acquisition-derived calculation. Validity of a formula and the decision to
select a particular metadata set are distinct questions.

## Fixture provenance and numeric evidence

The CC0 Ginsenoside Rg1 HSQC comes from
[nmrXiv S208](https://doi.org/10.57992/nmrxiv.p33.s208), with original dataset
[Harvard Dataverse](https://doi.org/10.7910/DVN/Y9A6DJ).
See the [fixture README](../../tests/fixtures/fileio/data/bruker_pdata/README.md)
for file-level provenance and hashes.

Its processed metadata is dated 2019-08-19, acquisition metadata 2019-08-20.
The direct carrier implied by processing is approximately 5 ppm, while
`acqus` describes 3 ppm. The packaged fixture has no `acqu2s`; the reported
approximately 30 ppm indirect mismatch concerns the fuller source dataset,
not a reproducible acquisition/processing conflict in this packaged F1 axis.

For direct dimension size 4096:

| Quantity | Value |
|---|---:|
| `SF` | 600.150000007829 MHz |
| `SW_p` (also `SW_h` here) | 3597.12230215827 Hz |
| `OFFSET` | 7.99684 ppm |
| Processing-derived carrier | 3000.742374983 Hz |
| Bin width | approximately 0.001463307 ppm |
| Processing first / last | 7.996840 / 2.004598 ppm |
| Acquisition first / last | 5.996840 / 0.004598 ppm |

The earlier work recorded -2.0000003399 ppm for the direct first-point
difference. Removing `acqus` from an in-memory dictionary invokes the historical
processing fallback and yields 7.99684 ppm without changing any file.

The review additionally reported direct-projection correlation of raw and
processed spectra at about a 2.0018 ppm lag (r = 0.941), consistent with the
carrier/run mismatch. Chemistry supported the processed-axis labels (residual
CD3OD proton near 3.326 ppm and anomeric signal near 4.618 ppm). This is not a
complete 2D processing reproduction or a vendor-software cross-check.

The F1 methanol label near 47.904 ppm differs by roughly 1.1 ppm from the
tabulated value used in the review; the coarse 256-point axis does not resolve
all referencing questions. Do not treat that fixture as an absolute F1 standard.

## Validation and review record

The independent review on `34e057c` recorded:

```bash
python -m pytest tests/test_bruker_pdata.py -q
python -m pytest -m "not dataset and not external_software" --strict-markers --strict-config -ra --tb=short -q
```

Results: **32 passed** focused; **385 passed, 3 skipped, 147 deselected**
autonomous. Skips were CSDM without `csdmpy`. No executable TopSpin or NMRPipe
axis comparison was run in that review; NMRPipe's availability in a separate
session is not axis-validation evidence.

Against base `fd84c06`, copying the new tests yielded 9 failures because the
new keyword did not exist. That demonstrates an API addition, not wrong
scientific values. Separate numeric evaluation of the base showed only the
HSQC direct first/last assertions discriminate the two parameter choices;
the other axis assertions establish agreement or compatibility. Ten added
tests are not ten independent demonstrations of a default-path defect.

Review verdict was **changes requested**, with four documentation findings:
wrong changelog reference, missing entry-point guidance, missing vendor citation,
and stale counts. PR #58 addressed those and the provenance interpretation.
The tested axis logic had no introduced behavioral defect identified by the
review. This report does not replace the original review verdict with a new
independent approval of #58.

## Remaining work

- Obtain a coherent same-acquisition before/after re-referencing pair, ideally
  1D and 2D with each axis varied separately in TopSpin. Record software version,
  operation, peak positions, full parameters and redistribution permission.
- Add evidence with `acqu2s` present and genuine `STSR`/`STSI` extraction.
  Existing constructed cases do not substitute for all vendor behaviors.
- Repair the separate processed-1D example and retain an extraction example.
- Reconsider default behavior only with new evidence and an explicit
  compatibility decision. This fixture alone does not justify a default change.
