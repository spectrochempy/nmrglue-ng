# Release-critical external dataset audit — 2026-10-01

## Purpose

This audit defines the smallest honest external-data gate proposed for the
first independent nmrglue-ng release. It classifies the residual historical
tests and data; it does not create a manifest, fetcher, archive, data release,
or CI workflow.

The three profiles used here are:

- `RELEASE_CRITICAL`: real data required to validate a first-release
  capability that generated fixtures cannot represent honestly;
- `EXTENDED_VALIDATION`: useful compatibility coverage that should be run
  manually, on schedule, or before release, but does not itself gate release;
- `HISTORICAL_LOW_PRIORITY`: inherited coverage that should not block the
  first release.

## Reconciliation

- nmrglue-ng baseline: `e884192207f05ec5dca07ce299341cd62dcd3a4e`
- upstream baseline: `5e2f095705bb90c6dc2f6a916abdfda82bac8e04`
- upstream commits absent from nmrglue-ng: none
- reconciliation required: no

Upstream PR #274 is already present in both histories. Open PRs #268, #270,
#272, and #275 concern Varian low-memory writing, Varian multi-trace block
headers, shared `data_nd` behavior, and reference-frequency/Tecmag metadata.
They are `RELEVANT_NOT_IN_NMRGLUE_NG`, but none supersedes this audit. They
instead identify release risks that require separate reconciliation or fixes.

Upstream PRs #279–#282 remain open without reviews or comments. The deferred
contribution policy remains current. JCAMP-DX PRs #259, #260, #262, and #277
also remain open; this audit classifies only behavior currently in master.

## Current baseline

The external `data/` directory is absent locally. No historical archive was
downloaded.

| Category | Tests |
|---|---:|
| Total | 328 |
| Autonomous (`not dataset and not external_software`) | 183 |
| Dataset | 98 |
| External software | 47 |
| Optional dependency | 4 |

Marker overlap is now:

~~~text
dataset ∩ optional_dependency           = 1  (RS2D)
dataset ∩ external_software             = 0
external_software ∩ optional_dependency = 0
~~~

The autonomous profile produced:

~~~text
180 passed, 3 skipped, 145 deselected, 10 warnings
~~~

The three skips require the optional `csdmpy` dependency. The 47 NMRPipe
differential tests are an external-software profile, not an external-data
profile.

## Residual test inventory

Every one of the 98 dataset tests is covered by the following groups.

| Module | Test/group | Count | Historical path | Main purpose |
|---|---|---:|---|---|
| `test_agilent.py` | 1D | 1 | `agilent_1d/` | real Varian blocks, values, writer |
| | 2D read/low-memory | 2 | `agilent_2d/` | multidimensional layout and low-memory |
| | 2D TPPI read/low-memory | 2 | `agilent_2d_tppi/` | phase/trace ordering |
| | 3D read/low-memory | 2 | `agilent_3d/` | multidimensional layout and low-memory |
| | fake 4D read/low-memory | 2 | `agilent_4d/fid` | explicit shape and trace order without `procpar` |
| `test_bruker_with_test_data.py` | raw 1D | 1 | `bruker_1d/` | real FID, parameters, padding, writer |
| | raw 2D read/low-memory | 2 | `bruker_2d/` | real `ser`, parameters, low-memory |
| | raw 3D read/low-memory | 2 | `bruker_3d/` | real `ser`, dimensions, low-memory |
| | processed 1D read/write | 2 | `bruker_1d/pdata/1/` | processed layout and processing parameters |
| | processed 2D read/write | 2 | `bruker_2d/pdata/1/` | processed submatrices and parameters |
| `test_convert.py` | Agilent↔Pipe 1D/2D/3D | 3 | `agilent_{1d,2d,3d}` plus Pipe references | independent cross-format values |
| | Agilent↔RNMRTK 1D/2D/3D | 3 | `agilent_*` plus `rnmrtk_*` | cross-format conversion |
| | Agilent↔Pipe low-memory 2D/3D | 2 | `agilent_{2d,3d}` | lazy conversion and writing |
| | Bruker↔Pipe 1D/2D/3D | 3 | `bruker_{1d,2d,3d}` plus Pipe references | independent cross-format values |
| | Bruker↔RNMRTK 1D/2D/3D | 3 | `bruker_*` RNMRTK references | cross-format conversion |
| | Bruker↔Pipe low-memory 2D/3D | 2 | `bruker_{2d,3d}` | lazy conversion and writing |
| | Sparky↔Pipe 2D/3D | 2 | `sparky_*` plus NMRPipe | cross-format frequency data |
| | Sparky↔Pipe low-memory 2D/3D | 2 | same | lazy conversion and writing |
| | Pipe self-conversion 1D | 1 | `nmrpipe_1d/test.fid` | conversion round trip |
| | RNMRTK↔Pipe 1D/2D/3D | 3 | `rnmrtk_*` plus Pipe references | independent cross-format values |
| `test_jcampdx.py` | encoding test set | 1 | `jcampdx/BRUK*.DX`, `TEST*.DX` | AFFN/PAC/SQZ/DIF and NTUPLES |
| | miscellaneous spectra | 1 | `jcampdx/TESTFID.DX`, `bruker*.dx`, `aug07*.dx` | real spectra and metadata variants |
| `test_jeol.py` | 1D complex references and UDIC | 5 | `jeol/*.jdf` plus `.fid` | real JDF, values, 1D metadata |
| | 2D complex/real/NUS references and UDIC | 7 | `jeol/*.jdf` plus `.fid` | 2D quadrature, NUS, values, metadata |
| `test_pipe_with_test_data.py` | 1D time/frequency/cut | 3 | `nmrpipe_1d/` | historical values and extracted region |
| | 2D normal/transposed/low-memory | 6 | `nmrpipe_2d/` | layout, transpose, values, writer |
| | 3D indexed normal/low-memory | 4 | `nmrpipe_3d/{data,ft}/` | indexed templates and values |
| | 3D stream normal/low-memory | 4 | `nmrpipe_3d/full3D.*` | stream layout and values |
| | 3D slicing/transpose | 2 | `nmrpipe_3d/ft/` | `data_nd` slicing and axes |
| | 4D time layouts | 3 | `nmrpipe_4d/time_*`, `full4D.fid` | one-index, two-index, stream |
| | 4D frequency layouts | 3 | `nmrpipe_4d/ft_*`, `full4D.ft4` | one-index, two-index, stream |
| `test_rnmrtk.py` | real 3D time/frequency | 2 | `rnmrtk_3d/{time_3d.sec,freq_3d.sec}` | real layout, values, metadata |
| `test_rs2d.py` | six raw/processed cases | 1 | `rs2d/Installer_Data/` | XML/binary 1D/2D and metadata |
| `test_simpson.py` | 1D/2D time/frequency | 4 | `simpson_{1d,2d}/` | TEXT/BINARY/XREIM/XYREIM/RAWBIN equivalence |
| `test_sparky.py` | 2D read/low-memory | 2 | `sparky_2d/data.ucsf` | UCSF layout, values, writer |
| | 3D read/low-memory | 2 | `sparky_3d/data.ucsf` | 3D UCSF layout, values, writer |
| `test_spinsolve.py` | ethanol acquisition | 5 | `spinsolve/ethanol/` | acquisition, JCAMP, processed data, UDIC |
| `test_tecmag.py` | LiCl real-file regression | 1 | `tecmag/LiCl_ref1.{tnt,txt}` | TNT values and dwell-time reference |

## Residual logical data inventory

The historical paths collapse into 24 logical groups. None is locally
available in this audit checkout; their physical-file membership must be
confirmed during controlled materialization.

| Logical data group | Format/vendor | Tests | Role | Local availability |
|---|---|---|---|---|
| `agilent_1d` | Varian | read/write and Pipe/RNMRTK conversion | real 1D acquisition and references | Absent |
| `agilent_2d` | Varian | read/low-memory and Pipe/RNMRTK conversion | real 2D blocks and references | Absent |
| `agilent_2d_tppi` | Varian | read/low-memory | TPPI ordering | Absent |
| `agilent_3d` | Varian | read/low-memory and Pipe/RNMRTK conversion | real 3D blocks and references | Absent |
| `agilent_4d` | Varian | read/low-memory | fake explicit-shape boundary case | Absent |
| `bruker_1d` | Bruker | raw/pdata and Pipe/RNMRTK conversion | 1D acquisition, processing, references | Absent |
| `bruker_2d` | Bruker | raw/pdata/low-memory and Pipe/RNMRTK conversion | 2D acquisition, processing, references | Absent |
| `bruker_3d` | Bruker | raw/low-memory and Pipe/RNMRTK conversion | 3D acquisition and references | Absent |
| `nmrpipe_1d` | NMRPipe | read and conversion | 1D time/frequency references | Absent |
| `nmrpipe_2d` | NMRPipe | read/low-memory and conversion | 2D time/frequency references | Absent |
| `nmrpipe_3d` | NMRPipe | read/low-memory and conversion | indexed/stream 3D references | Absent |
| `nmrpipe_4d` | NMRPipe | read/low-memory | indexed/stream 4D references | Absent |
| `rnmrtk_1d` | RNMRTK | conversion | 1D frequency reference | Absent |
| `rnmrtk_2d` | RNMRTK | conversion | 2D frequency reference | Absent |
| `rnmrtk_3d` | RNMRTK | read and conversion | real 3D time/frequency references | Absent |
| `sparky_2d` | Sparky/UCSF | read/low-memory and conversion | real tiled 2D spectrum | Absent |
| `sparky_3d` | Sparky/UCSF | read/low-memory and conversion | real tiled 3D spectrum | Absent |
| `jcampdx` | JCAMP-DX | two parameterized groups | encodings and real spectra | Absent |
| `jeol` | JEOL/JDF | 12 format/value/UDIC cases | real 1D/2D vendor binaries and references | Absent |
| `rs2d_installer_data` | RS2D | one six-case group | raw/processed XML and binary variants | Absent |
| `simpson_1d` | SIMPSON | time/frequency | equivalent 1D output encodings | Absent |
| `simpson_2d` | SIMPSON | time/frequency | equivalent 2D output encodings | Absent |
| `spinsolve_ethanol` | Spinsolve | five reader/UDIC cases | real acquisition and processed outputs | Absent |
| `tecmag_licl` | Tecmag/TNT | one numerical regression | real TNT and text reference pair | Absent |

## Test classification

Classification is by collected test, even where a test currently loops over
several logical fixtures.

| Module | Release critical | Extended | Historical low priority | Total |
|---|---:|---:|---:|---:|
| Agilent | 7 | 0 | 2 | 9 |
| Bruker | 9 | 0 | 0 | 9 |
| Convert | 15 | 8 | 1 | 24 |
| JCAMP-DX | 1 | 1 | 0 | 2 |
| JEOL | 4 | 8 | 0 | 12 |
| NMRPipe external data | 0 | 25 | 0 | 25 |
| RNMRTK | 2 | 0 | 0 | 2 |
| RS2D | 0 | 1 | 0 | 1 |
| SIMPSON | 2 | 2 | 0 | 4 |
| Sparky | 2 | 2 | 0 | 4 |
| Spinsolve | 0 | 5 | 0 | 5 |
| Tecmag | 0 | 1 | 0 | 1 |
| **Total** | **42** | **53** | **3** | **98** |

The release-critical conversion tests are Agilent↔Pipe and Bruker↔Pipe in
1D–3D, their 2D/3D low-memory cases, Sparky↔Pipe 2D regular/low-memory,
Agilent↔RNMRTK and Bruker↔RNMRTK in 3D, and RNMRTK↔Pipe in 3D. The 1D/2D
RNMRTK conversion references and Sparky 3D conversions are extended. The
Pipe-only conversion is historical low priority because packaged tests now
cover the same conversion mechanics.

## External conversion inventory

Each row is one collected conversion test or a same-contract pair. The
historical target files provide values produced independently of the
conversion under test; that independence must still be documented before the
references can enter a release corpus.

| Test | Source format | Target/contract | Independent reference value | Classification |
|---|---|---|---|---|
| `test_agilent_1d` | Varian 1D | Pipe round trip | historical Pipe 1D output | RELEASE_CRITICAL |
| `test_agilent_2d` / `_lowmem` | Varian 2D | Pipe regular/lazy round trip | historical Pipe 2D output | RELEASE_CRITICAL |
| `test_agilent_3d` / `_lowmem` | Varian 3D | Pipe regular/lazy round trip | historical indexed Pipe 3D output | RELEASE_CRITICAL |
| `test_agilent_1d_rnmrtk` | Varian 1D | RNMRTK round trip | historical RNMRTK 1D output | EXTENDED_VALIDATION |
| `test_agilent_2d_rnmrtk` | Varian 2D | RNMRTK round trip | historical RNMRTK 2D output | EXTENDED_VALIDATION |
| `test_agilent_3d_rnmrtk` | Varian 3D | RNMRTK round trip | historical RNMRTK 3D output | RELEASE_CRITICAL |
| `test_bruker_1d` | Bruker 1D | Pipe round trip | historical Pipe 1D output | RELEASE_CRITICAL |
| `test_bruker_2d` / `_lowmem` | Bruker 2D | Pipe regular/lazy round trip | historical Pipe 2D output | RELEASE_CRITICAL |
| `test_bruker_3d` / `_lowmem` | Bruker 3D | Pipe regular/lazy round trip | historical indexed Pipe 3D output | RELEASE_CRITICAL |
| `test_bruker_1d_rnmrtk` | Bruker 1D | RNMRTK round trip | historical RNMRTK 1D output | EXTENDED_VALIDATION |
| `test_bruker_2d_rnmrtk` | Bruker 2D | RNMRTK round trip | historical RNMRTK 2D output | EXTENDED_VALIDATION |
| `test_bruker_3d_rnmrtk` | Bruker 3D | RNMRTK round trip | historical RNMRTK 3D output | RELEASE_CRITICAL |
| `test_sparky_2d` / `_lowmem` | Sparky 2D | Pipe regular/lazy round trip | historical Pipe 2D output | RELEASE_CRITICAL |
| `test_sparky_3d` / `_lowmem` | Sparky 3D | Pipe regular/lazy round trip | historical Pipe 3D output | EXTENDED_VALIDATION |
| `test_pipe_1d` | Pipe 1D | Pipe self-conversion | same-format historical file | HISTORICAL_LOW_PRIORITY |
| `test_rnmrtk_1d` | RNMRTK 1D | Pipe round trip | historical Pipe 1D output | EXTENDED_VALIDATION |
| `test_rnmrtk_2d` | RNMRTK 2D | Pipe round trip | historical Pipe 2D output | EXTENDED_VALIDATION |
| `test_rnmrtk_3d` | RNMRTK 3D | Pipe round trip | historical Pipe 3D output | RELEASE_CRITICAL |

## First-release capability matrix

`Yes` records code that exists; it does not imply every mode is release-gated.

| Format/vendor | Read | Write | Low-memory | Processed | Conversion | First-release critical? |
|---|---|---|---|---|---|---|
| Agilent/Varian | Yes | Yes | Yes | No | Yes | Yes: real 1D–3D and TPPI |
| Bruker | Yes | Yes | Yes | Yes | Yes | Yes: raw 1D–3D and processed 1D/2D |
| NMRPipe | Yes | Yes | Yes | n/a | Yes | Packaged gate; external corpus extended |
| Sparky/UCSF | Yes | Yes | Yes | n/a | Yes | Yes: one real 2D file |
| RNMRTK | Yes | Yes | Yes | n/a | Yes | Yes: real 3D time and frequency |
| JCAMP-DX | Yes | No | No | spectrum | UDIC | Yes: canonical AFFN and NTUPLES spectra |
| JEOL/JDF | Yes | No | No | No | UDIC | Yes: one complex 1D and one complex 2D |
| SIMPSON | Yes | No | No | time/frequency | No | Yes: one 1D-time and one 2D-frequency set |
| RS2D | Yes | No | No | Yes | UDIC | No; extended optional-dependency profile |
| Spinsolve | Yes | No | No | Yes | UDIC | No; extended vendor profile |
| Tecmag/TNT | Yes | No | No | No | UDIC | No; synthetic reader coverage exists |

JEOL real-dimension and NUS variants, Sparky 3D, RS2D, Spinsolve, and Tecmag
remain useful supported-format evidence, but their absence does not block the
first independent release under this proposal.

## Minimal release-critical logical corpus

The target contains 16 logical groups. A logical group may contain a vendor
directory and independently derived reference files.

| Proposed group | Format | Tests protected | Why real data is required | Redistribution |
|---|---|---:|---|---|
| `varian_1d_raw_pipe_reference` | Varian + Pipe | 2 | real block headers, status, endianness, independent conversion | UNCLEAR |
| `varian_2d_raw_pipe_reference` | Varian + Pipe | 4 | multidimensional blocks, padding, low-memory, conversion | UNCLEAR |
| `varian_2d_tppi_reference` | Varian | 2 | real TPPI phase/trace ordering | UNCLEAR |
| `varian_3d_raw_crossformat_reference` | Varian + Pipe + RNMRTK | 5 | real multidimensional layout, lazy access, independent values | UNCLEAR |
| `bruker_1d_raw_processed_crossformat` | Bruker + Pipe | 4 | real FID, parameters, processed structure, conversion | UNCLEAR |
| `bruker_2d_raw_processed_crossformat` | Bruker + Pipe | 6 | `ser`, padding, pdata submatrices, low-memory, conversion | UNCLEAR |
| `bruker_3d_raw_crossformat_reference` | Bruker + Pipe + RNMRTK | 5 | 3D parameters/layout and low-memory conversion | UNCLEAR |
| `jeol_1d_complex_pipe_reference` | JEOL + Pipe | 2 | real JDF binary structure and independent numerical reference | UNCLEAR |
| `jeol_2d_complex_pipe_reference` | JEOL + Pipe | 2 | real 2D JDF quadrature/layout and metadata | UNCLEAR |
| `sparky_2d_ucsf_pipe_reference` | UCSF + Pipe | 4 | real tiled UCSF layout, low-memory, independent conversion | UNCLEAR |
| `rnmrtk_3d_time_reference` | RNMRTK | 2 | real complex 3D file beyond generated fixtures | UNCLEAR |
| `rnmrtk_3d_frequency_pipe_reference` | RNMRTK + Pipe | 2 | real frequency file and independent conversion | UNCLEAR |
| `simpson_1d_time_encoding_set` | SIMPSON | 1 | real TEXT/BINARY/XREIM/RAWBIN equivalence | UNCLEAR |
| `simpson_2d_frequency_encoding_set` | SIMPSON | 1 | real 2D TEXT/BINARY/XYREIM/RAWBIN behavior | UNCLEAR |
| `jcampdx_affn_spectrum` | JCAMP-DX | 1 shared | human-auditable real spectrum and metadata | UNCLEAR |
| `jcampdx_ntuples_spectrum` | JCAMP-DX | 1 shared | real NTUPLES real/imaginary arrays | UNCLEAR |

Test counts in this table overlap because cross-format tests consume multiple
logical groups. Before manifest work, the monolithic JCAMP encoding test must
be split or parameterized: it currently requires eight files although only an
AFFN and an NTUPLES case are proposed for the release-critical profile.

## Provenance and rights

No candidate historical external group has complete evidence for `CLEAR`.

| Groups | Provenance source | Redistribution evidence | Provenance | Redistribution action |
|---|---|---|---|---|
| `varian_*` | inherited test directories; historical values in Git | no explicit permission found | UNKNOWN | identify owner or replace with freely donated acquisitions |
| `bruker_*` | inherited test directories; instrument-style metadata | no explicit permission found | UNKNOWN | identify owner or regenerate freely licensed acquisitions |
| `jeol_*` | filenames describe samples; likely vendor/instrument exports | no explicit permission found | POTENTIALLY_RESTRICTED | obtain permission or replace; do not publish by default |
| `sparky_2d_*` | inherited UCSF file and derived Pipe reference | no explicit permission found | UNKNOWN | trace source or regenerate from licensed spectrum |
| `rnmrtk_3d_*` | inherited RNMRTK files and derived references | no explicit permission found | UNKNOWN | trace source or regenerate independently with documented tool |
| `simpson_*` | apparently generated simulator outputs | historical distribution only | LIKELY_CLEAR | recover input/generator and attach an explicit license |
| `jcampdx_*` | historical JCAMP test-set filenames | public availability is not permission | UNKNOWN | identify test-set license or choose licensed replacements |

Known provenance and redistribution permission are separate. Until explicit
permission exists, every release-critical group above has redistribution
status `UNCLEAR`; the JEOL groups additionally carry a plausible vendor-data
restriction.

## Size and duplication

Exact group sizes, physical-file count, and SHA-256 duplication are:

~~~text
UNKNOWN UNTIL DATASET MATERIALIZATION
~~~

A conservative lower bound can nevertheless be derived without downloading
data. The asserted Bruker raw file sizes total 94,928,896 bytes. The RNMRTK
3D time/frequency payload shapes and dtypes require 381,075,456 bytes. The
Sparky 2D float payload requires 33,554,432 bytes. Therefore the known minimum
for only these payloads is 509,558,784 bytes, excluding headers, parameters,
JCAMP text, SIMPSON variants, JEOL files, Varian files, and cross-format
references. The largest evidenced single payload is the 268,435,456-byte
RNMRTK 3D frequency `.sec` file.

The historical release asset is 171,949,037 bytes compressed, but its
extracted composition is not verified and it predates part of the suite. It
is not used as a size estimate for the proposed corpus.

Probable numerical duplication exists between:

- Varian, Bruker, RNMRTK, Sparky, and their derived NMRPipe references;
- NMRPipe stream and indexed representations of the same arrays;
- regular and low-memory tests that share a fixture.

These are not probable byte-identical duplicates across formats. Exact
deduplication requires materialization and SHA-256 comparison; nothing should
be removed based on names alone.

## Extended validation corpus

The extended profile should contain:

- all 25 large historical NMRPipe tests, including 3D/4D indexed and stream
  layouts; packaged fixtures remain the standard release gate;
- Agilent/Bruker↔RNMRTK 1D/2D conversion references and RNMRTK↔Pipe 1D/2D;
- Sparky 3D regular, low-memory, and cross-format references;
- the other eight JEOL cases, especially NUS and real/complex axis variants;
- the complete RS2D six-case installer set;
- the Magritek Spinsolve ethanol acquisition;
- the Tecmag LiCl TNT/text numerical pair;
- SIMPSON 1D frequency and 2D time encoding sets;
- the non-minimal JCAMP encoding and real-spectrum variants.

The 47 NMRPipe executable comparisons are a separate extended-software
profile. Their current recorded result is 44/47 with JMOD, HT6, and TP9
classified as historical or NMRPipe-version differences. NMRPipe itself is
not required by standard CI or by the standard external-data gate.

## Historical low-priority corpus

- `agilent_4d/fid`: two tests use a fake 4D file without `procpar` and supply
  shape/order manually; useful boundary coverage, but not a representative
  acquisition.
- `test_convert.py::test_pipe_1d`: a Pipe-to-Pipe conversion round trip now
  overlaps the packaged NMRPipe and converter coverage.
- The two empty JEOL placeholders tracked by #18 are not dataset tests and do
  not justify any external fixture. They protect no behavior until implemented.

No test or file is deleted by this classification.

## Release-critical tests blocked by known defects

Issue #16 blocks activation of:

- `test_convert.py::test_bruker_3d`;
- `test_convert.py::test_bruker_3d_lowmem`.

They modify the canonical `bruker_3d` directory by creating and deleting
`acqu3s`, which is incompatible with a read-only, checksummed corpus.

**Status (2026-10-02):** resolved by PR #27 once merged; see
[`2026-10-issue-16-corpus-mutation-fix.md`](2026-10-issue-16-corpus-mutation-fix.md).
Code fix, autonomous test, and full real-corpus validation (all four conversion
branches via NMRPipe-generated `fid/`) confirmed. Corpus integrity verified.
NMRPipe remains a reproducibility/CI constraint for these tests.

Issue #17 blocks trustworthy numerical validation in:

- `test_bruker_with_test_data.py::test_read_pdata_1d`;
- `test_bruker_with_test_data.py::test_read_pdata_2d`;
- `test_jeol.py::test_1d_complex_1_udic`;
- `test_jeol.py::test_2d_cc_1_udic`.

Their one-sided tolerances can accept arbitrarily low incorrect values.
Expected values must remain unchanged when the assertions are corrected.

Issue #18 affects two empty autonomous JEOL placeholders. Because real-axis
JEOL modes are not in the proposed minimal corpus, #18 is not a release gate;
the tests must not be cited as evidence of coverage.

Open upstream fixes #268, #270, and #272 affect release-critical Varian or
shared low-memory capabilities. They require explicit resolution or a
documented nmrglue-ng decision before those capabilities can be release-gated.
PR #275 affects extended Tecmag metadata and broader reference-frequency
semantics; it remains a separate scientific decision.

## Manifest design recommendation

Use mixed granularity with the logical fixture as the primary versioned unit:

~~~text
logical fixture
  -> one or more physical files/directories
  -> exact sizes and SHA-256 checksums
  -> tests and profile
  -> provenance and license evidence
  -> generation/acquisition notes
~~~

Vendor acquisitions must remain atomic logical directories even though the
manifest checks individual physical files. Cross-format reference sets should
be atomic groups so a source and its independently produced references cannot
silently drift apart. Archive subsets may package multiple groups, but archive
boundaries must not replace per-file checksums and logical identities.

The 16 proposed identifiers in the minimal-corpus table are the initial
candidate group names for a future manifest. They are proposals, not a TOML
schema or authorization to publish the files.

## Ordered blockers

### BLOCKER BEFORE MANIFEST

1. Materialize only the 16 candidate groups in a controlled local workspace.
2. Split mixed-profile JCAMP tests so the manifest can select the minimal
   AFFN and NTUPLES cases honestly.
3. Resolve #16 so all corpus access is read-only.
4. Record physical paths, sizes, SHA-256 checksums, and exact duplicates.
5. Confirm that each cross-format reference was produced independently.

### BLOCKER BEFORE RELEASE

1. Resolve #17 for the four release-critical numerical tests.
2. Resolve or explicitly reconcile Varian/data_nd risks represented by
   upstream #268, #270, and #272.
3. Establish acceptable provenance and redistribution for all 16 groups, or
   replace groups that cannot be distributed lawfully.
4. Make every release-critical group reproducibly obtainable and verified.
5. Run all 42 release-critical tests successfully against the immutable
   corpus.

### NON-BLOCKING FOLLOW-UP

- resolve the empty JEOL placeholders in #18;
- run and record the 53-test extended dataset profile;
- retain the three historical-low-priority tests without making them release
  gates;
- evaluate Tecmag/reference-frequency semantics from upstream #275;
- keep the NMRPipe 44/47 differential result explicit;
- revisit rights and retention for optional RS2D and Spinsolve data.

## Release rule

A first independent release can proceed when:

1. the autonomous suite is green;
2. all 16 release-critical logical groups are reproducibly available;
3. every release-critical physical file passes its recorded checksum;
4. all 42 release-critical dataset tests pass against an immutable corpus;
5. #16 and the release-critical parts of #17 are resolved;
6. Varian and shared low-memory blockers have an explicit validated outcome;
7. provenance and redistribution are acceptable for every distributed group;
8. the extended dataset and NMRPipe differential profiles have been run and
   their outcomes recorded.

Failures confined to `HISTORICAL_LOW_PRIORITY` do not block release. An
extended-profile failure is assessed and recorded, but blocks release only if
it reveals a defect in a capability explicitly promoted into the
release-critical contract.
