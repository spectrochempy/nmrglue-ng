# Test-data infrastructure audit — 2026-10-01

## Purpose

This audit records the historical test-data state of nmrglue-ng before a
reproducible data infrastructure is implemented. It is a snapshot, not a
living status document. Later fixture migrations or dataset releases should
not be backported into this file.

## Baseline

- Audited branch: master
- Audited HEAD: c5e6041118493f3a2886a69fc213c2d9518598d1
- Historical data location: <repository>/data
- Repository state at the end of the audit: clean

The complete collection contained 328 unique tests:

| Category | Unique tests |
|---|---:|
| Autonomous | 152 |
| Dataset | 129 |
| External software | 47 |
| Optional dependency | 4 |
| Total | 328 |

Marker overlap:

~~~text
dataset ∩ optional_dependency           = 4
dataset ∩ external_software             = 0
external_software ∩ optional_dependency = 0
union dataset/external/optional         = 176
~~~

The four optional-dependency tests are also dataset tests: three CSDM
conversion tests require csdmpy, and the RS2D test requires xmltodict. Data
availability and dependency availability must remain separate dimensions.

Autonomous baseline:

~~~text
152 passed, 176 deselected, 10 warnings in 1.63s
~~~

## Dataset inventory

| Module | Tests |
|---|---:|
| test_agilent.py | 9 |
| test_bruker_with_test_data.py | 12 |
| test_convert.py | 27 |
| test_jcampdx.py | 4 |
| test_jeol.py | 12 |
| test_pipe_with_test_data.py | 37 |
| test_rnmrtk.py | 12 |
| test_rs2d.py | 1 |
| test_simpson.py | 5 |
| test_sparky.py | 4 |
| test_spinsolve.py | 5 |
| test_tecmag.py | 1 |
| **Total** | **129** |

Static inspection identified 82 logical fixture groups. This counts semantic
acquisitions, files, source/reference pairs, or multi-file families. It does
not mean that the corpus contains 82 physical files.

| Family | Logical groups | Principal content | Role |
|---|---:|---|---|
| Agilent/Varian | 5 | 1D, 2D, TPPI, 3D, and 4D acquisition groups | Real reader, low-memory, metadata, round trip |
| Bruker | 5 | Three raw acquisitions and two processed-data groups | Real reader, processed reader, metadata, round trip |
| NMRPipe | 17 | 1D–4D files, streams, and indexed templates | Reader, layout, slicing, external references |
| RNMRTK | 12 | Time/frequency 1D–3D and six 3D permutations | Reader, low-memory, transpose, round trip |
| Sparky/UCSF | 2 | 2D and 3D spectra | Reader, low-memory, conversion reference |
| JCAMP-DX | 19 | Encoding variants, miscellaneous spectra, dictionary fixtures | Parser and metadata |
| JEOL | 10 | Ten JDF/NMRPipe reference pairs | Binary reader, metadata, numerical reference |
| RS2D | 6 | Raw and processed 1D/2D cases | XML metadata and binary reader |
| SIMPSON | 4 | 1D/2D time/frequency equivalence sets | Encoding and numerical equivalence |
| Spinsolve | 1 | Ethanol acquisition directory | JCAMP, processed data, acquisition metadata |
| Tecmag | 1 | LiCl TNT file and reference text | Real-file numerical regression |
| **Total** | **82** | | |

Conversion tests often consume more than one family, so family-level usage
counts cannot be summed to obtain 129.

## Existing packaged fixtures

The package already contains:

~~~text
78 small NMRPipe fixtures     188,427 bytes total
 3 small Bruker fixtures        9,599 bytes total
~~~

The NMRPipe fixtures cover 1D through 4D, including stream and multi-file
layouts. They are the strongest immediate opportunity for reducing the 37
dataset-dependent tests in test_pipe_with_test_data.py. Migration must still
be decided test by test; a small fixture does not necessarily cover all
large-data boundary behavior.

## Current path contract

tests/setup.py constructs DATA_DIR as <repository>/data, which is ignored by
Git. At the audited commit there is no environment variable, pytest option,
user cache, manifest, downloader, or checksum verification.

When data are absent, tests/conftest.py classifies the known modules as
dataset and they are excluded from the autonomous profile. The 47 NMRPipe
processing comparisons are separately marked external_software. They do not
currently overlap the dataset marker and should remain a separate workflow.

## Historical dataset

The upstream nmrglue v0.5 release still provides:

~~~text
test_data_v0.5-dev.zip
171,949,037 bytes compressed
~~~

Asset:

<https://github.com/jjhelmus/nmrglue/releases/download/v0.5/test_data_v0.5-dev.zip>

Upstream issue [#87](https://github.com/jjhelmus/nmrglue/issues/87) documents
the loss of the earlier Google Code hosting and the absence of a maintained
current corpus. The archive predates parts of the current suite. A later
private reconstruction was reported at approximately 5.7 GiB, but was not a
published, verified dataset at audit time.

The v0.5 archive was not downloaded during this audit. Its extracted size,
physical file count, duplicates, and per-family sizes remain unknown. It is
not a canonical modern corpus merely because it is publicly downloadable.

## Provenance and redistribution

The audit used four conservative states:

- CLEAR: documented origin, license, and redistribution permission;
- LIKELY_CLEAR: apparently generated or historically distributed, but missing
  a complete provenance record;
- UNKNOWN: insufficient evidence;
- POTENTIALLY_RESTRICTED: vendor/example origin is plausible and explicit
  redistribution permission was not found.

No historical external fixture can currently be classified CLEAR.

| Classification | Families | Reason |
|---|---|---|
| LIKELY_CLEAR | SIMPSON outputs; small packaged fixtures | Apparently generated or historically distributed; incomplete source record |
| UNKNOWN | Agilent, Bruker, RNMRTK, Sparky, JCAMP-DX, Tecmag, derived NMRPipe references | Origin, license, or permission is incomplete |
| POTENTIALLY_RESTRICTED | JEOL, RS2D, Magritek Spinsolve | Vendor/example material is plausible and permission was not found |

Public availability is not evidence of redistribution permission. Derived
conversion files also retain unresolved provenance from their source spectra.

## Migration opportunities

### High priority and low cost

1. Reuse packaged NMRPipe fixtures for applicable path, byte-buffer, header,
   layout, low-memory, and dimensional tests.
2. Replace CSDM conversion inputs with small arrays and dictionaries where a
   vendor reader is not the behavior under test.
3. Package or generate minimal Bruker JCAMP and pulse-program fixtures.
4. Generate the two JCAMP dictionary/nesting documents.
5. Generate minimal inputs for SIMPSON exception paths.

About 30 tests appear quickly migrable. After RNMRTK, Sparky, SIMPSON
encodings, and simple conversions, approximately 45–60 additional autonomous
tests appear realistic. These are planning ranges, not promises.

### Subsequent candidates

- RNMRTK permutation and low-memory tests using small, independently specified
  fixtures;
- small frozen Sparky/UCSF fixtures while retaining a real reference;
- generated SIMPSON encodings based on fixed values;
- conversion cases with independently produced small expected results.

### Data that must remain real

The residual corpus should retain verified real examples for:

- Agilent/Varian acquisition headers, blocks, TPPI, padding, and endianness;
- Bruker raw and processed directory structures;
- JEOL JDF structure and NUS/complex variants;
- RS2D XML/binary raw and processed relationships;
- Spinsolve acquisition, JCAMP, and processed-file relationships;
- Tecmag TNT sections and tables;
- at least one Sparky/UCSF file;
- at least one RNMRTK file;
- independent cross-format references where a nmrglue writer would otherwise
  validate its matching reader circularly.

## Proposed architecture

Reduce the historical corpus first, then define a manifest for the residual
release-critical data. A complete manifest of all 82 historical groups should
not be formalized before that reduction.

The target architecture is:

~~~text
TOML manifest
+ versioned dataset
+ archive and per-file SHA-256 checksums
+ explicit download
+ cache separate from canonical storage
+ standard CI without a large dataset
+ separate scheduled/manual dataset validation
~~~

TOML avoids a new parser dependency on supported Python versions. The
manifest should record logical path, size, SHA-256, source and provenance,
license and redistribution status, test groups, and release-critical or
extended profile.

For the first managed dataset, a versioned GitHub release asset plus pinned
SHA-256 is the simplest canonical storage. The identical artifact may later
be archived on Zenodo for a durable DOI. A GitHub Actions cache is not
canonical storage.

The future fetcher should read the manifest, reuse verified files, fetch only
requested content, verify checksums, extract safely, refuse unexpected links
or paths, install atomically, accept a configurable destination, and never
execute scripts from the archive.

Path resolution should prefer an explicit CLI/pytest option, then
NMRGLUE_TEST_DATA, then a versioned user cache, with <repository>/data accepted
only as an existing compatibility fallback. Missing data must not trigger an
implicit download.

Standard CI should run autonomous tests and packaged fixtures. Dataset CI
should be separate and run by schedule, workflow_dispatch, and release
validation, with a cache keyed by manifest version and checksum.

## Release criterion

~~~text
all autonomous tests green
+ all release-critical data reproducibly fetched and verified
+ all release-critical tests green
+ manifest/provenance checks green
+ extended dataset suite run and reported before release
+ NMRPipe differential baseline explicitly recorded
~~~

Running all 129 historical dataset tests on every pull request is not a
release requirement.

## Defects discovered

Three generic test defects were recorded:

- [#16](https://github.com/spectrochempy/nmrglue-ng/issues/16): Bruker
  conversion tests mutate DATA_DIR by copying acqu2s to acqu3s;
- [#17](https://github.com/spectrochempy/nmrglue-ng/issues/17): several JEOL
  and Bruker processed-data assertions use one-sided tolerances;
- [#18](https://github.com/spectrochempy/nmrglue-ng/issues/18): two collected
  JEOL tests contain only pass and validate no behavior.

The audit does not fix these defects. They are generic upstream candidates
only after correction and validation in nmrglue-ng.

## Recommended implementation sequence

~~~text
P0.1  Migrate applicable NMRPipe tests to packaged fixtures.
P0.2  Migrate small parser and conversion tests.
P0.3  Recount the residual external-data dependency.
P0.4  Define the manifest for the residual corpus.
P0.5  Clear provenance and redistribution for release-critical data.
P0.6  Add the explicit checksum-verifying fetcher.
P0.7  Add scheduled/manual dataset validation.
P0.8  Add a durable archive such as Zenodo if useful.
~~~

The next campaign should inspect the 37 tests in
test_pipe_with_test_data.py against the 78 packaged NMRPipe fixtures. It must
not assume in advance that all 37 can safely become autonomous.

## Upstream opportunities

Generic candidates include stopping mutation of the source corpus, correcting
one-sided assertions, implementing or explicitly classifying empty JEOL
tests, reusing existing small NMRPipe fixtures, and introducing a configurable
data path and checksum manifest.

Dataset hosting, release profiles, CI policy, and the first-release gate are
nmrglue-ng governance decisions rather than generic upstream fixes.
