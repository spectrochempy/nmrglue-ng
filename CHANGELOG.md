# Changelog

All notable changes to nmrglue-ng are documented in this file.

nmrglue-ng is an independent continuation of nmrglue. Entries in the Historical nmrglue changelog section below belong to the
original nmrglue project and are preserved for attribution and continuity.

## Unreleased

- Fix automatic peak-minima phasing when a scoring window reaches a
  spectrum boundary.

- Fix Cadzow enhancement for 2D arrays by processing each row independently. (#205)

- Allow Bruker raw readers to retain flat samples after a declared shape
  mismatch and skip opening the NUS schedule independently.

- Add opt-in Bruker 2D pdata normalization for calibrated complex channel pairs,
  with acquisition or processing axes and explicit receiver gain.

- Normalize complete uniform Bruker echo/anti-echo SER storage and retain
  both branches in file order for downstream reconstruction.

- Normalize complete uniform Bruker States-TPPI SER storage, preserving
  acquired E1/E2 branches and deferring indirect alternation. (#201)

- Offer explicit per-trace DC removal, digital-filter correction and scan/gain
  normalization for complete Bruker QF SER data. (#200)

- Normalize complete uncorrected Bruker QF SER grids for interop while
  preserving the stored complex convention and calibrated time axes. (#199)

- Describe deferred DC, digital-filter and scan/gain preparation for
  normalized Bruker 1D FIDs without applying the corrections at import. (#198)

- Extend Bruker 1D FID interop with optional storage-length preservation,
  DC removal before digital filtering, and scan/gain normalization. (#197)

## 1.2.1 - 2026-11-08

- Offer acquisition-centered axes and optional receiver-gain normalization for
  the Bruker 1D processed interop profile. (#195)

- Document the Bruker post-FFT digital-filter phase convention and how to use
  it with NMRPipe-style positive-exponent FFTs. (#194)

- Normalize complete raw NMRPipe QF 2D grids after explicit confirmation. (#193)

## 1.2.0 - 2026-11-08

### Interoperability

- Use `nmrglue.interop.read(path, profile=None, **options)` to select a profile
  explicitly or detect recognized headers and dataset directories. Use
  `nmrglue.interop.normalize(result, **options)` to validate and normalize a
  supported result using its reported profile. Profile-specific options and
  confirmations still apply. (#180, #181)
- **Bruker/TopSpin:** Read raw 1D FIDs, stored 2D SER traces, and qualified QF
  and States-TPPI acquisitions. Normalize complex QSIM/DQD 1D FIDs with
  documented padding, sign, and optional digital-filter handling. Read
  processed 1D and stored 2D data and normalize complete 1D spectra and
  qualified four-component 2D int32 spectra with calibrated axes.
  (#140, #142, #144, #156, #158, #162, #164)
- **Agilent/Varian:** Read stored traces, descriptive 2D States acquisitions,
  and complex 1D FIDs. Normalize the supported 1D profile without rescaling
  samples and expose reference candidates and requested and completed
  scan-count evidence. Use the observed transmitter nucleus `tn` for the
  acquisition label, leaving it unknown when absent. (#146, #151, #152, #153, #154, #155, #164)
- **NMRPipe:** Read and normalize complete processed 1D spectra with
  last-point ORIG calibration. Read 2D storage in file order and normalize
  qualified frequency, time, and mixed-domain grids, including supported
  States and pure TPPI layouts. Export qualified 1D and raw 2D QF and
  States-TPPI `ReadResult` profiles to float32 NMRPipe storage.
  (#141, #143, #145, #159, #161, #165, #166, #167)
- **nmrML:** Extend 1D reading and add a precision-preserving writer with
  optional XSD validation. Interop supports raw and processed 1D, real
  processed 2D, and qualified raw 2D echo/anti-echo pairs. Reduce decoding
  time and peak memory for the official 2D HSQC compatibility profile.
  (#160, #168, #169, #185)
- **JEOL JDF:** Read and normalize complex 1D FIDs and qualified regular or
  listed-axis 2D acquisitions. Preserve 2D storage geometry and the
  acquired indirect branches for NUS data. (#170, #171, #172)
- **JCAMP-DX:** Read and normalize regular real 1D spectra, complex 1D
  NTUPLES FIDs, and real 2D NTUPLES spectra with explicit F1 pages.
  (#173, #174, #175)
- **SIMPSON:** Read and normalize native complex 1D and 2D FIDs and spectra
  in TEXT and BINARY formats. (#176, #177, #178, #179)

### Compatibility and fixes

- Fix indexing and slicing of 1D Bruker FIDs opened with `read_lowmem()`. (#189, #190)
- Fix Bruker low-memory trace offsets for real int32 and real or complex
  float64 data. Preserve fractional values in real float64 reads. (#191)
- The package attribute `nmrglue.interop.normalize` now refers to the generic
  function. Import individual normalizers from `nmrglue.interop.normalize`
  or from `nmrglue.interop`. (#180)
- Automatic Bruker pdata 1D detection uses stored scale
  (`scale_data=False`). Pass `scale_data` explicitly when the scale matters,
  especially when comparing with the specialized reader. (#181)
- Preserve real and imaginary samples independently when decoding NMRPipe
  complex traces containing infinities or NaNs. (#165)

### Documentation

- Put installation, a runnable example, and the additions in released
  versions of nmrglue-ng at the top of the repository and PyPI README. (#186)
- Add a home-page migration guide for users of the historical nmrglue distribution. (#188)
- Clarify the interop workflow and restore mobile documentation navigation.
  Shorten the tutorial and add a profile table covering detection, reader
  options, and normalization, with format conventions on a separate page.
  (#163, #187)

### Project infrastructure

- Derive the Conda package version from the release tag and automate PyPI
  and GitHub Release publication from validated tags. (#134, #136, #139)
- Align commit-subject and pull-request-title prefixes with SpectroChemPy and
  validate pull-request titles in CI. (#157)

## 1.1.2 - 2026-10-23

- Link the complete release notes from the documentation home page.
- Update the publication and artifact workflows to a hash-verified pip
  security release and document temporary certificate guidance. (#130)

## 1.1.1 - 2026-10-23

- Publish noarch Conda packages on `spectrocat`, with a constraint against
  installing both distributions in one environment. (#117)
- Correct 1D and multidimensional integration noise estimates to use the
  same bin width or volume as the integral. Fix multidimensional noise-region
  indexing. (upstream #295, #296, fork #128)
- Restore slicing, iteration and axis transforms for the HDF5 low-memory
  wrappers `glue_2d` and `glue_3d`. Their `order` argument uses numeric
  file-axis indices. (#122)
- Simplify the documentation home page labels. (#127)
- Add spelling and import checks for maintained sources and extend static
  typing checks from interop to the whole package. Improve the missing-key
  error for Spinsolve acquisition metadata. (#118, #120, #121, #124, #125)

## 1.1.0 - 2026-10-16

- Introduce the optional `nmrglue.interop` API with `ReadResult`. Its first
  profile reads processed Bruker/TopSpin 1D data with a calibrated Hz axis,
  named components and validated diagnostics. Historical `(dic, data)`
  readers keep their existing return values. (#113)
- Publish the public documentation in English at the version root, clarify
  the project's relationship to upstream, and explain Bruker status
  parameter files and explicit `procs_files` selection. (#104, #114, #115)

## 1.0.2 - 2026-10-14

- Derive the package version from Git tags with setuptools-scm. Display the
  version in the documentation navigation, or `dev` for development builds.
- Point package metadata to the stable documentation and publish release
  notes generated from the changelog.

## 1.0.1 - 2026-10-14

- Point the README and package metadata to stable Read the Docs. Build the
  English API reference at the version root and keep the historical JBNMR
  examples and glossary available by direct link.

## 1.0.0 - 2026-10-14

- Preserve descending processed JCAMP-DX `FIRSTX` and `LASTX` coordinates
  when building axes with `guess_udic()` and `uc_from_udic()`.
  (#87, issue #86)
- Introduce tutorial-first documentation with downloadable MyST-NB notebooks
  and reproducible inputs. Cover reading and calibrated axes, plotting,
  conversion, processing, quantification, simulation and low-memory access.
  Keep historical examples available and provide a fast documentation build.
  (#85, #90, #92, #93, #94, #95)
- Publish English and French documentation builds and provide a dedicated
  contributor guide. (#96)
- Add the CC0 JEOL epicatechin fixture and verify its samples and metadata.
  Stop retaining built distributions from routine CI and release dry runs
  while continuing to validate them. (#89, #91)

## 1.0.0rc1 - 2026-10-11

### Installation and compatibility

- Publish under the distribution name `nmrglue-ng` with a `pyproject.toml`
  build, retaining the `nmrglue` import. Update source installation
  instructions. The wheel contains runtime code only and drops the
  `nmrglue.fileio.tests` and `nmrglue.analysis.tests` namespaces. Tests and
  fixtures remain in the source distribution. (#3, #11, #64)

### File formats and processing

- **Bruker:** Support explicit processing-parameter axis selection with
  `pdata=True`, preserving default acquisition precedence. Add optional
  `remove_dc_offset` before digital-filter removal, incompatible with
  `post_proc=True`, and support older `DSPFVS` values via the DQD lookup
  default. Make JCAMP text decoding locale-independent and handle CR-only
  records. The decoding fixes adapt jjhelmus/nmrglue#261 (harivyasi).
  (#50, #51, #53, #55, #81)
- **JCAMP-DX:** Read multiple and nested LINK blocks, multidimensional
  NTUPLES pages, and XYPOINTS/PEAKTABLE coordinate pairs with scaling and
  decimal commas. Add configurable decoding errors via `read_err`.
  These reader changes adapt jjhelmus/nmrglue#259, #260, #262 and #277
  (harivyasi). Correct FID sweep width to `(N - 1) / span`, improve complex
  data and domain metadata, and derive the carrier for processed spectra.
  Related upstream work includes jjhelmus/nmrglue#231, #284 and #291.
  (#46, #47, #49, #52, #54, #63)
- **NMRPipe:** Preserve `FDDMXVAL` in conversions and write compatible
  `FDPIPECOUNT` metadata. Correct 2D extraction bounds and indirect sizes,
  including rounded-window placement after clipping. The extraction fix
  adapts jjhelmus/nmrglue#289 (reneeotten). Match NMRPipe's ZD width and
  `HT -ps90-180` conventions. (#9, #13, #15, #62, #65)
- **SIMPSON:** Return shape `(NP,)` for single-element 1D TEXT and BINARY
  data, matching XREIM and RAWBIN. Multi-element 1D and 2D shapes are
  unchanged. (#66)
- **Agilent/Varian:** Fix multi-trace block-header reads and preserve each
  block's header in low-memory writes. Add the `correct` option and derive
  structural header fields from the written data layout. Includes
  adaptations of jjhelmus/nmrglue#268 and #270. (#36, #37, #38)
- **Low-memory access:** Repair copying and negative-axis handling, including
  Bruker and RNMRTK subclasses, based on jjhelmus/nmrglue#272. Match NumPy
  for 1D transpose and reject floating-point axes. Restore linear prediction
  with current SciPy. (#14, #33, #56, #57)

### Validation and documentation

- Define self-contained, external dataset, optional dependency and NMRPipe
  test profiles. Add a versioned manifest with integrity, availability and
  redistribution evidence. Separate local corpus use from redistribution
  and make the verifier report incomplete critical coverage separately.
  (#5, #39, #61, #67, #68)
- Package redistributable Bruker, JEOL and JCAMP-DX fixtures, including
  nmrXiv P33 and P52, Harvard Dataverse Rutin, and MIT-licensed cheminfo
  JEOL samples. Replace release-critical Bruker pdata and JCAMP-DX corpus
  dependencies with checked fixtures and document unavailable real-axis
  JEOL cases. (#18, #40, #41, #42, #43, #44, #45, #69, #74)
- Expand autonomous coverage for Bruker, JCAMP-DX, CSDM, NMRPipe, RNMRTK and
  SIMPSON, and use symmetric numerical tolerances. Validate on Windows and
  macOS and test the wheel built from the source distribution.
  (#21, #22, #23, #24, #25, #29, #34)
- Restore Read the Docs builds, add a release-artifact dry run and
  pre-commit checks, and document the contribution process, roadmap,
  changelog policy and agent workflow. Replace Travis CI and TODO.txt.
  (#1, #2, #8, #11, #12, #28, #35, #70, #84)

---

## Historical nmrglue changelog

0.12 (2026-08-16)
=================
* Bruker to csdm conversion returns the correct dimension units (#227)
* When reading bruker files both utf-8 and cp1252 encodings are tried (#239)
* Correctly read Bruker data  in floating point format (#249)
* Support reading partially acquired Bruker data (#252)
* Add support for reading JEOL jdf format (#228)
* Add support for reading RS2D/QUAD format (#230)
* Add the update_uc function to update a unit_conversion object (#250)
* Add a guess_tables function for use when reading Tecmat sequence tables (#257)
* The read function in nmrml can optionally return processed data (#232)
* Add support for Numpy 2.0+ (#224, #248)
* Various minor fixes (#233, #236, #242, #238, #246, #245, #251)


0.11 (2024-10-29)
=================

* Add support for Python 3.12, drop support for Python 3.7 (#208)
* Bruker vd list can be read (#212, #213)
* Minor typos and fixes (#209, #210, #211)
* Tests for peak picking (#216)
* Sparky related fix (#222)


0.10 (2023-11-14)
=================

* Remove use of deprecated np.float compatibility with NumPy 1.24+ (#193)
* Remove use of deprecated np.prod function (#207)
* Switch from nose to pytest for running tests (#201, #206)
* Bruker NUS data can now be expanded (#189)
* Fix JCAMP-DX digit parsing (#198)
* Fix JCAMP-DX block reading (#191)
* Fix a bug with ndimage slices (#197)
* Updates to the CI (#185, #183)
* Code changes to reflect Python 3 preferred syntax (#179, #180, #181, #204, #205)
* Fixed various typos and misspelling (#172, #173, #177, #182, #203)


0.9 (2022-04-20)
================

FileIO
------
* Fix a bug fix passing specific procs_file in read_fid or read_pdata (#134, #141)
* Add support for reading 4D UCSF (sparky) files (#142)
* Update NMRPipe metadata keys (#144)
* Support for reading Spinsolve files (#147, #151, #155, #161)
* The converter objects can output csdm-formatted data (#152)
* nmrglue.pipe.read can read from io.Bytes objects (#153)
* nmrglue.pipe can read from Path objects (#159)
* Fix a bug in reading sparky .save files (#164)


Documentation
-------------
* Update examples with python 3 syntax (#137, #138)
* Document support for reading spinsolve files (#151)
* Spelling fixes in documentation (#153, #165)
* Example of using the peakpick.pick function (#163)
* Various other small fixes to the documentation (#162)


Analysis
--------
* Update leastsqbound to support scipy 1.8 (#167)


Misc
----
* CI framework using GitHub Actions (#132)
* Fix various test warnings (#133)
* Drop Python 2.7 support (#131)

0.8 (2020-10-29)
================

File IO
-------
* Handle data processed with nmrPipe EXT in the z-dimension (#92)
* Guess spectral widths in multi-dimensional Bruker datasets (#98)
* Allow bracket-less text values in JCAMP files (#100)
* Allow different character encodings in JCAMP files (#101)
* Only consider relevant DATATYPEs when reading JCAMP-DX files (#120)
* Support reading of Sparky .save files (#118)

Processing
----------
* Add the util/xcpy.py module for interfacing nmrglue with TopSpin (#103, #105)
* Add additional options to the autops function (#108)
* Improvements to the autops function (#124)

Documentation
-------------
* Clarify tutorial documentation (#96)
* Docstring fixes (#107)
* Document the use of nmrglue on Google Colabs (#125)
* Documentation can be built with sphinx 2.1.0 (127)
* Documentation is update at ReadTheDocs
* Various updates to the documentation (#129)
* Added a CHANGELOG.md file (#130)


Misc
----
* Replace deprecated matplotlib axisbg keyword with facecolor (#93)
* Case to int after round (#95, #106)
* Fix FutureWarnings from recent NumPy releases (#99)
* Support numpy >=1.18 (#114)
