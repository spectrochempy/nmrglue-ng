# Changelog

All notable changes to nmrglue-ng are documented in this file.

nmrglue-ng is an independent continuation of nmrglue. Entries in the Historical nmrglue changelog section below belong to the
original nmrglue project and are preserved for attribution and continuity.

## Unreleased

### Added

- Add packaged JEOL test fixtures (fluorine, phosphorus, Rutin 1H/13C) with
  autonomous reader tests. Data from cheminfo/jeol-data-test (MIT), original
  Harvard Dataverse doi:10.7910/DVN/ZAZDNM (CC0 1.0).
- Add a versioned test-data manifest (`maintainer/testdata-manifest.toml`)
  with SHA-256 checksums, sizes, provenance classes, availability, and
  redistribution status for the release-critical corpus. Include generation
  and verification scripts (Python >= 3.11). (#39)
- Add an explicit self-contained test profile and classify tests requiring
  external datasets, optional dependencies, or NMRPipe. (#5)
- Add maintainer audits and a living development roadmap, including an
  NMRPipe compatibility baseline. (#2, #8)

### Changed

- Modernize packaging with `pyproject.toml`. (#3)
- Rename the distribution to `nmrglue-ng` while preserving the `nmrglue`
  Python import. (#3)
- Update source installation instructions for the independent project. (#11)

### Fixed

- Fix `write_fid_lowmem()` to use each block's own header instead of repeating
  the first block header, matching `write_fid()` behavior. (#38)
- Fix `write_fid_lowmem()` header correction: add the missing `correct`
  parameter and derive all structural file-header fields (`np`, `nblocks`,
  `ntraces`, `ebytes`, `tbytes`, `bbytes`) from the physical data layout.
  Adapted from upstream jjhelmus/nmrglue#268. (#37)
- Fix Varian multi-trace block-header reading: `get_block_ntraces()` referenced
  an undefined `file` variable when `read_blockhead=True`. Adapted from
  upstream jjhelmus/nmrglue#270. (#36)
- Fix `data_nd` copy (`NameError` from a broken `__fcopy__` call) and
  negative-axis handling in `swapaxes`/`transpose`, aligning the base class
  with NumPy axis semantics and fixing incompatible `__fcopy__` hooks in the
  Bruker and RNMRTK subclasses. Adapted from upstream jjhelmus/nmrglue#272. (#33)
- Make numerical tolerance assertions symmetric in dataset and autonomous
  tests. (#29)
- Implement NMRPipe-compatible `HT -ps90-180` mirror-image processing. (#15)
- Restore linear-prediction QR solving with current SciPy. (#14)
- Fix `pipe_proc.save()` to write NMRPipe-compatible `FDPIPECOUNT` metadata. (#13)
- Fix ZD processing with integral floating-point widths and reproduce
  NMRPipe's fractional-width convention in `pipe_proc.zd()`. (#9)

### Documentation

- Define the minimal release-critical external test-data corpus and separate
  extended and historical validation profiles.
- Add contribution guidance for testing, scientific changes, and file-format
  work. (#1)
- Establish the nmrglue-ng changelog policy. (#12)

### Maintenance

- Expand autonomous CI to Windows and macOS, exercise optional CSDM conversion,
  and validate sdist-derived wheels in an isolated installation. Include and
  exercise the CI report test and its helper in the sdist. Retain test reports
  and add weekly/manual validation. Use cross-platform file replacement in the
  Bruker test helper so the Windows isolation test can run. (#34)
- Introduce a minimal pre-commit configuration with structural and
  text-hygiene hooks, explicit fixture exclusions, and a CI quality job.
  Ruff linting/formatting remain a separate future follow-up. (#35)
- Version the agent workflow in the repository: a root `AGENTS.md` with
  permanent rules, plus `nmrglue-ng-dev`, `nmrglue-ng-review`, and
  `nmrglue-ng-release` OpenCode skills. (#28)
- Run 10 RNMRTK file-I/O tests against independently generated fixtures while
  retaining two real 3D references in the external dataset. (#25)
- Run the SIMPSON reader error-path test without the external historical dataset. (#24)
- Run CSDM conversion tests without the external historical dataset. (#23)
- Run JCAMP-DX block-structure tests without the external historical dataset. (#22)
- Run Bruker JCAMP and pulse-program tests without the external historical
  dataset. (#21)
- Run NMRPipe path and bytes file-I/O tests against packaged fixtures instead
  of the external historical dataset.
- Remove the obsolete Travis CI configuration. (#11)
- Replace the historical `TODO.txt` with tracked issues and the maintainer
  roadmap. (#11)

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
