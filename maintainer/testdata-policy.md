# Test-data use and distribution policy

Maintainer decisions: **2026-10-08**, initially recorded against `805c6f2`;
consolidated for delivery on **2026-10-09** against `d9ba184`.
Local-use acceptance is separate from redistribution permission. The separately
approved first-release scope reductions are recorded below; their translation
into the manifest and generator is still pending.

## Accepted historical source

The maintainer accepts the test-data archive published by the historical
nmrglue project as a source for **local validation**:

- [nmrglue v0.5 test archive](https://github.com/jjhelmus/nmrglue/releases/download/v0.5/test_data_v0.5-dev.zip)
- SHA-256: `dbff258fe08a19f1cd08f44b731d3d19e20e54fbb1415d904cd6d03f25209dae`

This is an explicit project acceptance decision based on its publication as
test data by that project. It is not a claim that an explicit data license has
been found for every contributed file. Unresolved redistribution status alone
does not block local tests using this accepted source.

The decision is tied to the identified archive. Record the source/version and
checksum when evaluating a replacement archive. New publication, availability
or licensing information should be assessed when it exists, not assumed from
ongoing work on the historical project's tests.

## Three data-use situations

| Situation | Validation | Redistribution by nmrglue-ng |
|---|---|---|
| Public-domain or licensed redistributable data | Public CI and local tests | Allowed subject to recorded rights and any attribution/notice conditions. |
| Accepted external data with restricted or unresolved redistribution | Local or otherwise authorized private validation | Not included in public distributions, fixtures or uploaded data artifacts without further rights evidence. |
| Unavailable data or unestablished use basis | No validation claim | Record the gap; seek a replacement or a maintainer decision on scope. |

Publicly downloadable is not synonymous with public domain. **Files or groups
from the historical archive may be redistributed when their own provenance
and redistribution basis are established**, including documented public-domain
dedication, CC0, another applicable license, or permission. Do not treat the
entire archive as either forbidden or cleared because one group has that status.
Preserve attribution and notices where required, and select the smallest useful
redistributable fixture rather than republishing the archive indiscriminately.

The manifest's `redistribution_status` continues to describe redistribution:
`UNRESOLVED` does not override the accepted local-use decision above, and that
decision does not turn `UNRESOLVED` into `CLEAR`. A future per-group rights
update must include its evidence in the generator and generated manifest.
No file's license, checksum, availability or status is changed by this policy.

For other restricted datasets, document the basis for authorized access and
test use separately from any distribution rights. Keep restricted payloads
out of public logs/artifacts. Local evidence can be shared as results and
non-restricted metadata without publishing the underlying files.

## Evidence required for release validation

A critical capability may be supported by either public reproducible tests or
documented maintainer validation with accepted external data. Publicly
redistributable fixtures remain preferred, but are not mandatory for every
critical capability. A private/manual run is acceptable when it records:

- the exact tested commit, date, commands, software versions and environment;
- dataset identity, provenance, acquisition instructions and checksums (keep
  restricted identifying details in an authorized private record if necessary);
- the capability and test identities, results, skips and failures;
- the independent reference used, where the scientific claim requires one;
- integrity checks before/after, with writing tests confined to temporary copies.

Critical inputs must be reproducibly obtainable in the authorized validation
environment. G3 may be satisfied by documented retrieval and checksum checks
there; it need not imply a public mirror or unrestricted automatic download.
G4 requires recorded critical-test results, not a public dataset CI job.
Scheduled/manual automation is useful follow-up but cannot replace evidence.

Rights for **actually distributed** data must be established. A gate must not
require redistribution rights for a corpus that is only used locally under
an accepted use basis. Conversely, local acceptance does not establish that
the critical files are present or the tests pass.

Accepting local data does not by itself change scientific coverage. The
first-release scope decisions below are separate, explicit maintainer choices.
Until those decisions are translated into the manifest and its generator, the
verifier still evaluates the historical 16-group / 42-test contract; exit 2
and the 19 missing critical components describe that recorded contract, not
an already updated one. Do not silently suppress missing files or reinterpret
the verifier's result.

## First-release scope decisions — 2026-10-08

| Capability | Maintainer direction | Completion condition |
|---|---|---|
| Agilent 1D/2D/3D and Bruker 1D/2D NMRPipe conversion references | Generate locally from the available raw inputs using NMRPipe. | Reviewed conversion parameters, recorded commands/version/hashes, and passing relevant tests against the resulting independent references. |
| Historical Bruker 1D/2D pdata | Replace these specific datasets with the existing licensed fixtures. | Map the historical read/write requirements to those fixtures; add missing writer round-trip evidence and verify relevant metadata/scaling. Dataset replacement is approved; validation is not yet complete. |
| RNMRTK 3D and Sparky/UCSF 2D historical reference groups | Defer from the first-release critical contract due to limited current demand and unavailable references. | Record the validation limitation, retain existing functionality and tests, and revisit if an interested contributor supplies appropriate data. This is an explicit scope reduction, not a validation claim. |
| SIMPSON 1D/2D encoding sets | Retain the requirement and pursue local generation with SIMPSON. | Check available input scripts, software setup and encoding conventions; generate in a disposable copy and validate equivalence. Do not install into the maintainer's primary environment implicitly. |
| JEOL historical 1D/2D reference pairs | Defer from the first-release critical contract unless user demand or suitable contributed data justifies revisiting it. | Retain the reader and existing licensed fixtures/autonomous tests. Record that the historical independent NMRPipe comparison remains unvalidated; additional evidence is welcome but no longer required for this release. |
| JCAMP-DX encoding/NTUPLES sets | No new scope decision. | Existing equivalence requirements and proposed test split remain open. |

The RNMRTK/Sparky deferral concerns six currently absent components (RNMRTK
time/frequency and associated references, plus the UCSF/Pipe pair); the JEOL
deferral adds two historical reference-pair components. The historical
42-test table associates thirteen tests with these capabilities (nine for
RNMRTK/Sparky, four for JEOL). Do not declare a new total of critical tests
solely by subtraction: replacement
coverage and component/test mappings must be reconciled in the implementation.

Implement these choices in a separate reviewed manifest/test-contract change,
including `CRITICAL_TESTS`, component scope, consumer references and reports.
This decision does not delete tests, add skips, remove format support, or
alter scientific expected values. Existing autonomous RNMRTK tests remain
useful evidence even though the unavailable real-reference profile is deferred.
The same distinction applies to the existing JEOL autonomous tests. A possible
request to the JEOL reader's author for data/reference results is follow-up
work, not a release prerequisite or authorization to contact them.

## Generated references

Record the input identity, tool/version, commands and checksums for generated
NMRPipe, RNMRTK or other references. Work on disposable copies; do not generate
into the canonical corpus during tests. Assess software-use conditions and
source/output redistribution separately. A local generation or validation
does not automatically authorize publishing its outputs.

## Next work

1. Integrate the decisions into the generator/manifest through a separately
   reviewed change. Keep missing files visible, not passing or silently waived.
2. NMRPipe generation and the SIMPSON encoding sets have passed targeted
   validation on disposable copies after #65/#66. Define reproducible local
   corpus integration with source/tool receipts and checksums; the generated
   references are not yet part of the canonical corpus or manifest.
3. Establish per-file/group redistribution evidence where available; eligible
   data may then become public fixtures through a separate reviewed change.
4. Track historical-project data updates without making progress dependent on
   an anticipated archive or license clarification.
