"""Generate a TOML manifest of the local release-critical test-data corpus.

Scans the data/ directory, computes SHA-256 checksums and sizes for every
file, and writes maintainer/testdata-manifest.toml. The manifest documents
each logical group with provenance, license, redistribution status, and
availability.

Beyond the file inventory, the manifest declares the *required components*
of the corpus: the reference paths the tracked dataset tests need
(NMRPipe conversion outputs, RNMRTK .sec/.par pairs, processed datasets,
encoding outputs, ...). Each component is either inventoried (its files are
present and checksummed) or explicitly declared absent. Group availability
is derived from these components and can no longer be asserted by hand.

Generation refuses to write a manifest in which a *recognized static
reference* (the constructions listed in `extract_data_references`) is
neither inventoried nor declared absent. References outside those
constructions are covered by the declarations alone.

Requires Python >= 3.11 (tomllib) or Python 3.10 with tomli installed.
"""

import ast
import hashlib
import re
import sys
from pathlib import Path

try:
    import tomllib
except ModuleNotFoundError:
    import tomli as tomllib


DATA_DIR = Path(__file__).resolve().parents[1] / "data"
MANIFEST_PATH = Path(__file__).resolve().parents[1] / "maintainer" / "testdata-manifest.toml"
TESTS_DIR = Path(__file__).resolve().parents[1] / "tests"

EXCLUDE_NAMES = {"README", "conversion_scripts"}
EXCLUDE_SUFFIXES = {".com"}
EXCLUDE_PREFIXES = {"make_"}

MANIFEST_VERSION = "3"

# Files in the nmrglue v0.5 release archive for each group.
# Derived/generated files (not in the archive) are listed separately.
ARCHIVE_FILES = {
    "agilent_1d": ["fid", "procpar"],
    "agilent_2d": ["fid", "procpar"],
    "agilent_2d_tppi": ["fid", "procpar"],
    "agilent_3d": ["fid", "procpar"],
    "agilent_4d": ["fid"],
    "bruker_1d": ["acqu", "acqus", "fid", "pulseprogram"],
    "bruker_2d": ["acqu", "acqu2", "acqu2s", "acqus", "pulseprogram", "ser"],
    "bruker_3d": ["acqu", "acqu2", "acqu2s", "acqus", "pulseprogram", "ser"],
    "simpson_1d": ["rr.in"],
    "simpson_2d": ["2d.in"],
    "tecmag": ["LiCl_ref1.tnt", "LiCl_ref1.txt"],
}

# Derived files generated locally (e.g., NMRPipe references), not in the archive.
DERIVED_FILES = {
    "bruker_3d": {
        "pattern": "fid/test*.fid",
        "count": 116,
        "source": "NMRPipe-generated indexed references from ser",
        "tool": "NMRPipe (external software), per conversion_scripts/bruker2pipe_3d.com",
        "redistribution_status": "UNRESOLVED",
        "evidence": "generated locally; no explicit license; derivation tool is NMRPipe",
    },
}

# Per-group metadata. Availability and missing-component summaries are
# derived from REQUIRED_COMPONENTS and never asserted here.
GROUP_META = {
    "agilent_1d": {
        "format": "Varian/Agilent",
        "provenance": "nmrglue v0.5 release archive; community contribution",
        "license": "BSD-3-Clause (nmrglue repository license; not separately applied to data)",
        "redistribution_status": "UNRESOLVED",
        "evidence": "release asset has no explicit data license; repository license scope unconfirmed",
        "notes": "real 1D acquisition; read/write and conversion tests",
    },
    "agilent_2d": {
        "format": "Varian/Agilent",
        "provenance": "nmrglue v0.5 release archive; community contribution",
        "license": "BSD-3-Clause (nmrglue repository license; not separately applied to data)",
        "redistribution_status": "UNRESOLVED",
        "evidence": "release asset has no explicit data license; repository license scope unconfirmed",
        "notes": "real 2D blocks; read/low-memory and conversion tests",
    },
    "agilent_2d_tppi": {
        "format": "Varian/Agilent",
        "provenance": "nmrglue v0.5 release archive; community contribution",
        "license": "BSD-3-Clause (nmrglue repository license; not separately applied to data)",
        "redistribution_status": "UNRESOLVED",
        "evidence": "release asset has no explicit data license; repository license scope unconfirmed",
        "notes": "TPPI ordering; read/low-memory tests",
    },
    "agilent_3d": {
        "format": "Varian/Agilent",
        "provenance": "nmrglue v0.5 release archive; community contribution",
        "license": "BSD-3-Clause (nmrglue repository license; not separately applied to data)",
        "redistribution_status": "UNRESOLVED",
        "evidence": "release asset has no explicit data license; repository license scope unconfirmed",
        "notes": "real 3D blocks; read/low-memory and conversion tests",
    },
    "agilent_4d": {
        "format": "Varian/Agilent",
        "provenance": "nmrglue v0.5 release archive; synthetic boundary case",
        "license": "BSD-3-Clause (nmrglue repository license; not separately applied to data)",
        "redistribution_status": "UNRESOLVED",
        "evidence": "release asset has no explicit data license; repository license scope unconfirmed",
        "notes": "4D boundary case without procpar; shape supplied manually",
    },
    "bruker_1d": {
        "format": "Bruker",
        "provenance": "nmrglue v0.5 release archive; community contribution",
        "license": "BSD-3-Clause (nmrglue repository license; not separately applied to data)",
        "redistribution_status": "UNRESOLVED",
        "evidence": "release asset has no explicit data license; repository license scope unconfirmed",
        "notes": "real FID, parameters, pulse program; read tests",
    },
    "bruker_2d": {
        "format": "Bruker",
        "provenance": "nmrglue v0.5 release archive; community contribution",
        "license": "BSD-3-Clause (nmrglue repository license; not separately applied to data)",
        "redistribution_status": "UNRESOLVED",
        "evidence": "release asset has no explicit data license; repository license scope unconfirmed",
        "notes": "ser, padding, parameters; read/low-memory and conversion tests",
    },
    "bruker_3d": {
        "format": "Bruker",
        "provenance": "nmrglue v0.5 release archive (6 original files) + 116 locally generated NMRPipe references",
        "license": "BSD-3-Clause (nmrglue repository license; not separately applied to data)",
        "redistribution_status": "UNRESOLVED",
        "evidence": "original files from release asset; derived references generated by NMRPipe, no explicit license",
        "notes": "3D parameters, ser, indexed fid references; read/low-memory and conversion tests",
    },
    "simpson_1d": {
        "format": "SIMPSON",
        "provenance": "nmrglue v0.5 release archive; simulator input",
        "license": "BSD-3-Clause (nmrglue repository license; not separately applied to data)",
        "redistribution_status": "UNRESOLVED",
        "evidence": "release asset has no explicit data license; repository license scope unconfirmed",
        "notes": "1D input file; encoding-set tests need generated outputs",
    },
    "simpson_2d": {
        "format": "SIMPSON",
        "provenance": "nmrglue v0.5 release archive; simulator input",
        "license": "BSD-3-Clause (nmrglue repository license; not separately applied to data)",
        "redistribution_status": "UNRESOLVED",
        "evidence": "release asset has no explicit data license; repository license scope unconfirmed",
        "notes": "2D input file; encoding-set tests need generated outputs",
    },
    "tecmag": {
        "format": "Tecmag",
        "provenance": "nmrglue v0.5 release archive; community contribution",
        "license": "BSD-3-Clause (nmrglue repository license; not separately applied to data)",
        "redistribution_status": "UNRESOLVED",
        "evidence": "release asset has no explicit data license; repository license scope unconfirmed",
        "notes": "LiCl reference pair (.tnt + .txt); load-time and sign-check tests",
    },
}

# The 42 release-critical tests of the historical contract (PR #26 assessment,
# fdee69f:maintainer/audits/2026-10-release-critical-dataset.md). The scope of
# a required component is "critical" when at least one of its consumers is in
# this set, "extended" otherwise.
CRITICAL_TESTS = frozenset({
    "tests/test_agilent.py::test_1d",
    "tests/test_agilent.py::test_2d",
    "tests/test_agilent.py::test_2d_lowmem",
    "tests/test_agilent.py::test_2d_tppi",
    "tests/test_agilent.py::test_2d_tppi_lowmem",
    "tests/test_agilent.py::test_3d",
    "tests/test_agilent.py::test_3d_lowmem",
    "tests/test_bruker_with_test_data.py::test_1d",
    "tests/test_bruker_with_test_data.py::test_2d",
    "tests/test_bruker_with_test_data.py::test_2d_lowmem",
    "tests/test_bruker_with_test_data.py::test_3d",
    "tests/test_bruker_with_test_data.py::test_3d_lowmem",
    "tests/test_bruker_with_test_data.py::test_read_pdata_1d",
    "tests/test_bruker_with_test_data.py::test_read_pdata_2d",
    "tests/test_bruker_with_test_data.py::test_write_pdata_1d",
    "tests/test_bruker_with_test_data.py::test_write_pdata_2d",
    "tests/test_convert.py::test_agilent_1d",
    "tests/test_convert.py::test_agilent_2d",
    "tests/test_convert.py::test_agilent_2d_lowmem",
    "tests/test_convert.py::test_agilent_3d",
    "tests/test_convert.py::test_agilent_3d_lowmem",
    "tests/test_convert.py::test_agilent_3d_rnmrtk",
    "tests/test_convert.py::test_bruker_1d",
    "tests/test_convert.py::test_bruker_2d",
    "tests/test_convert.py::test_bruker_2d_lowmem",
    "tests/test_convert.py::test_bruker_3d",
    "tests/test_convert.py::test_bruker_3d_lowmem",
    "tests/test_convert.py::test_bruker_3d_rnmrtk",
    "tests/test_convert.py::test_sparky_2d",
    "tests/test_convert.py::test_sparky_2d_lowmem",
    "tests/test_convert.py::test_rnmrtk_3d",
    "tests/test_jcampdx.py::test_jcampdx1",
    "tests/test_jeol.py::test_1d_complex_1",
    "tests/test_jeol.py::test_1d_complex_1_udic",
    "tests/test_jeol.py::test_2d_cc_1",
    "tests/test_jeol.py::test_2d_cc_1_udic",
    "tests/test_rnmrtk.py::test_3d_time",
    "tests/test_rnmrtk.py::test_3d_freq",
    "tests/test_simpson.py::test_1d_time",
    "tests/test_simpson.py::test_2d_freq",
    "tests/test_sparky.py::test_2d",
    "tests/test_sparky.py::test_2d_lowmem",
})

# Dataset-dependent test modules whose data references the manifest accounts
# for. The historical NMRPipe file-I/O module (test_pipe_with_test_data.py)
# and the RS2D/Spinsolve vendor profiles stay outside the manifest scope; see
# maintainer/reports/2026-10-critical-corpus.md.
SCANNED_TEST_MODULES = (
    "test_agilent.py",
    "test_bruker_with_test_data.py",
    "test_convert.py",
    "test_jcampdx.py",
    "test_jeol.py",
    "test_rnmrtk.py",
    "test_simpson.py",
    "test_sparky.py",
    "test_tecmag.py",
)

# Required reference components, by owning entry. A component's paths are
# corpus-relative; they live under the declaring group's directory whenever
# the corpus layout provides one (home-by-prefix), and under
# [missing.extended_test_references] otherwise. Every path consumed by a
# scanned test must be inventoried or declared in exactly one component.
REQUIRED_COMPONENTS = {
    "agilent_1d": {
        "raw": {
            "paths": ["agilent_1d/fid", "agilent_1d/procpar"],
            "required_by": [
                "tests/test_agilent.py::test_1d",
                "tests/test_convert.py::test_agilent_1d",
            ],
            "notes": "real 1D acquisition block and parameters",
        },
        "pipe_reference": {
            "paths": ["agilent_1d/test.fid"],
            "required_by": ["tests/test_convert.py::test_agilent_1d"],
            "notes": "NMRPipe-generated 1D conversion reference",
        },
    },
    "agilent_2d": {
        "raw": {
            "paths": ["agilent_2d/fid", "agilent_2d/procpar"],
            "required_by": [
                "tests/test_agilent.py::test_2d",
                "tests/test_agilent.py::test_2d_lowmem",
                "tests/test_convert.py::test_agilent_2d",
                "tests/test_convert.py::test_agilent_2d_lowmem",
            ],
            "notes": "real 2D blocks and parameters",
        },
        "pipe_reference": {
            "paths": ["agilent_2d/test.fid"],
            "required_by": [
                "tests/test_convert.py::test_agilent_2d",
                "tests/test_convert.py::test_agilent_2d_lowmem",
            ],
            "notes": "NMRPipe-generated 2D conversion reference",
        },
    },
    "agilent_2d_tppi": {
        "raw": {
            "paths": ["agilent_2d_tppi/fid", "agilent_2d_tppi/procpar"],
            "required_by": [
                "tests/test_agilent.py::test_2d_tppi",
                "tests/test_agilent.py::test_2d_tppi_lowmem",
            ],
            "notes": "real 2D TPPI blocks and parameters",
        },
    },
    "agilent_3d": {
        "raw": {
            "paths": ["agilent_3d/fid", "agilent_3d/procpar"],
            "required_by": [
                "tests/test_agilent.py::test_3d",
                "tests/test_agilent.py::test_3d_lowmem",
                "tests/test_convert.py::test_agilent_3d",
                "tests/test_convert.py::test_agilent_3d_lowmem",
                "tests/test_convert.py::test_agilent_3d_rnmrtk",
            ],
            "notes": "real 3D blocks and parameters",
        },
        "pipe_reference": {
            "paths": ["agilent_3d/data/test%03d.fid"],
            "required_by": [
                "tests/test_convert.py::test_agilent_3d",
                "tests/test_convert.py::test_agilent_3d_lowmem",
            ],
            "notes": "indexed NMRPipe-generated 3D conversion reference series",
        },
    },
    "agilent_4d": {
        "raw": {
            "paths": ["agilent_4d/fid"],
            "required_by": [
                "tests/test_agilent.py::test_4d",
                "tests/test_agilent.py::test_4d_lowmem",
            ],
            "notes": "synthetic boundary case read with an explicit shape",
        },
    },
    "bruker_1d": {
        "raw": {
            "paths": ["bruker_1d/acqu", "bruker_1d/acqus", "bruker_1d/fid",
                      "bruker_1d/pulseprogram"],
            "required_by": [
                "tests/test_bruker_with_test_data.py::test_1d",
                "tests/test_convert.py::test_bruker_1d",
            ],
            "notes": "real FID, parameters and pulse program",
        },
        "pdata": {
            "paths": ["bruker_1d/pdata/1"],
            "required_by": [
                "tests/test_bruker_with_test_data.py::test_read_pdata_1d",
                "tests/test_bruker_with_test_data.py::test_write_pdata_1d",
            ],
            "notes": "processed 1D dataset (1r/1i, procs and related files)",
        },
        "pipe_reference": {
            "paths": ["bruker_1d/test.fid"],
            "required_by": ["tests/test_convert.py::test_bruker_1d"],
            "notes": "NMRPipe-generated 1D conversion reference",
        },
        "rnmrtk_reference": {
            "paths": ["bruker_1d/time_1d.sec", "bruker_1d/time_1d.par"],
            "required_by": ["tests/test_convert.py::test_bruker_1d_rnmrtk"],
            "notes": "RNMRTK 1D time-domain reference and its parameter file",
        },
    },
    "bruker_2d": {
        "raw": {
            "paths": ["bruker_2d/acqu", "bruker_2d/acqu2", "bruker_2d/acqu2s",
                      "bruker_2d/acqus", "bruker_2d/pulseprogram", "bruker_2d/ser"],
            "required_by": [
                "tests/test_bruker_with_test_data.py::test_2d",
                "tests/test_bruker_with_test_data.py::test_2d_lowmem",
                "tests/test_convert.py::test_bruker_2d",
                "tests/test_convert.py::test_bruker_2d_lowmem",
            ],
            "notes": "ser, parameters and pulse program",
        },
        "pdata": {
            "paths": ["bruker_2d/pdata/1"],
            "required_by": [
                "tests/test_bruker_with_test_data.py::test_read_pdata_2d",
                "tests/test_bruker_with_test_data.py::test_write_pdata_2d",
            ],
            "notes": "processed 2D dataset (2rr/2ri, proc2s and related files)",
        },
        "pipe_reference": {
            "paths": ["bruker_2d/test.fid"],
            "required_by": [
                "tests/test_convert.py::test_bruker_2d",
                "tests/test_convert.py::test_bruker_2d_lowmem",
            ],
            "notes": "NMRPipe-generated 2D conversion reference",
        },
        "rnmrtk_reference": {
            "paths": ["bruker_2d/time_2d.sec", "bruker_2d/time_2d.par"],
            "required_by": ["tests/test_convert.py::test_bruker_2d_rnmrtk"],
            "notes": "RNMRTK 2D time-domain reference and its parameter file",
        },
    },
    "bruker_3d": {
        "raw": {
            "paths": ["bruker_3d/acqu", "bruker_3d/acqu2", "bruker_3d/acqu2s",
                      "bruker_3d/acqus", "bruker_3d/pulseprogram", "bruker_3d/ser"],
            "required_by": [
                "tests/test_bruker_with_test_data.py::test_3d",
                "tests/test_bruker_with_test_data.py::test_3d_lowmem",
                "tests/test_convert.py::test_bruker_3d",
                "tests/test_convert.py::test_bruker_3d_lowmem",
                "tests/test_convert.py::test_bruker_3d_rnmrtk",
            ],
            "notes": "3D parameters and ser",
        },
        "pipe_reference": {
            "paths": ["bruker_3d/fid/test%03d.fid"],
            "required_by": [
                "tests/test_convert.py::test_bruker_3d",
                "tests/test_convert.py::test_bruker_3d_lowmem",
            ],
            "notes": "indexed NMRPipe-generated 3D conversion reference series",
        },
        "rnmrtk_reference": {
            "paths": ["bruker_3d/time_3d.sec", "bruker_3d/time_3d.par"],
            "required_by": ["tests/test_convert.py::test_bruker_3d_rnmrtk"],
            "notes": "RNMRTK 3D time-domain reference and its parameter file",
        },
        "pdata": {
            "paths": ["bruker_3d/pdata"],
            "required_by": [],
            "notes": "processed 3D dataset; no tracked test consumes it, kept as "
                     "a declared gap from the historical manifest",
        },
    },
    "simpson_1d": {
        "simulator_input": {
            "paths": ["simpson_1d/rr.in"],
            "required_by": [],
            "notes": "SIMPSON input script; regeneration source for the encoding outputs",
        },
        "time_outputs": {
            "paths": ["simpson_1d/1d_text.fid", "simpson_1d/1d_bin.fid",
                      "simpson_1d/1d_ftext.fid", "simpson_1d/1d_rawbin.fid"],
            "required_by": ["tests/test_simpson.py::test_1d_time"],
            "notes": "1D time-domain encoding set (TEXT/BINARY/XREIM/RAWBIN)",
        },
        "freq_outputs": {
            "paths": ["simpson_1d/1d_text.spe", "simpson_1d/1d_bin.spe",
                      "simpson_1d/1d_ftext.spe", "simpson_1d/1d_rawbin.spe"],
            "required_by": ["tests/test_simpson.py::test_1d_freq"],
            "notes": "1D frequency-domain encoding set (extended-validation test)",
        },
    },
    "simpson_2d": {
        "simulator_input": {
            "paths": ["simpson_2d/2d.in"],
            "required_by": [],
            "notes": "SIMPSON input script; regeneration source for the encoding outputs",
        },
        "freq_outputs": {
            "paths": ["simpson_2d/2d_text.spe", "simpson_2d/2d.spe",
                      "simpson_2d/2d_ftext.spe", "simpson_2d/2d_raw.spe"],
            "required_by": ["tests/test_simpson.py::test_2d_freq"],
            "notes": "2D frequency-domain encoding set (TEXT/BINARY/XREIM/RAWBIN)",
        },
        "time_outputs": {
            "paths": ["simpson_2d/2d_text.fid", "simpson_2d/2d.fid",
                      "simpson_2d/2d_ftext.fid", "simpson_2d/2d_raw.fid"],
            "required_by": ["tests/test_simpson.py::test_2d_time"],
            "notes": "2D time-domain encoding set (extended-validation test)",
        },
    },
    "tecmag": {
        "raw": {
            "paths": ["tecmag/LiCl_ref1.tnt", "tecmag/LiCl_ref1.txt"],
            "required_by": ["tests/test_tecmag.py::test_tecmag_load_time_domain"],
            "notes": "LiCl reference pair (.tnt + .txt)",
        },
    },
    "jeol_1d_complex_pipe_reference": {
        "reference_pair": {
            "paths": ["jeol/cyclosporine_Carbon-1-1.jdf",
                      "jeol/cyclosporine_Carbon-1-1.fid"],
            "required_by": [
                "tests/test_jeol.py::test_1d_complex_1",
                "tests/test_jeol.py::test_1d_complex_1_udic",
            ],
            "notes": "real 1D JDF binary structure and independent NMRPipe reference",
        },
    },
    "jeol_2d_complex_pipe_reference": {
        "reference_pair": {
            "paths": ["jeol/cyclosporine_tocsy-1-1.jdf",
                      "jeol/cyclosporine_tocsy-1-1.fid"],
            "required_by": [
                "tests/test_jeol.py::test_2d_cc_1",
                "tests/test_jeol.py::test_2d_cc_1_udic",
            ],
            "notes": "real 2D JDF quadrature/layout and independent NMRPipe reference",
        },
    },
    "sparky_2d_ucsf_pipe_reference": {
        "ucsf_spectrum": {
            "paths": ["sparky_2d/data.ucsf"],
            "required_by": [
                "tests/test_sparky.py::test_2d",
                "tests/test_sparky.py::test_2d_lowmem",
                "tests/test_convert.py::test_sparky_2d",
                "tests/test_convert.py::test_sparky_2d_lowmem",
            ],
            "notes": "tiled UCSF 2D spectrum",
        },
        "pipe_reference": {
            "paths": ["nmrpipe_2d/test.ft2"],
            "required_by": [
                "tests/test_convert.py::test_sparky_2d",
                "tests/test_convert.py::test_sparky_2d_lowmem",
            ],
            "notes": "NMRPipe-generated 2D conversion reference",
        },
    },
    "rnmrtk_3d_time_reference": {
        "time_reference": {
            "paths": ["rnmrtk_3d/time_3d.sec", "rnmrtk_3d/time_3d.par"],
            "required_by": [
                "tests/test_rnmrtk.py::test_3d_time",
                "tests/test_convert.py::test_agilent_3d_rnmrtk",
            ],
            "notes": "real complex 3D RNMRTK file and its parameter file",
        },
    },
    "rnmrtk_3d_frequency_pipe_reference": {
        "frequency_reference": {
            "paths": ["rnmrtk_3d/freq_3d.sec", "rnmrtk_3d/freq_3d.par"],
            "required_by": [
                "tests/test_rnmrtk.py::test_3d_freq",
                "tests/test_convert.py::test_rnmrtk_3d",
            ],
            "notes": "real 3D RNMRTK frequency file and its parameter file",
        },
        "pipe_reference": {
            "paths": ["rnmrtk_3d/test.ft3"],
            "required_by": ["tests/test_convert.py::test_rnmrtk_3d"],
            "notes": "NMRPipe-generated 3D conversion reference",
        },
    },
    "jcampdx_affn_spectrum": {
        "encoding_set": {
            "paths": ["jcampdx/BRUKAFFN.DX", "jcampdx/BRUKPAC.DX",
                      "jcampdx/BRUKSQZ.DX", "jcampdx/BRUKDIF.DX",
                      "jcampdx/TEST32.DX", "jcampdx/TESTSPEC.DX"],
            "required_by": ["tests/test_jcampdx.py::test_jcampdx1"],
            "notes": "AFFN/PAC/SQZ/DIF encoding equivalence cases; the historical "
                     "encoding test is monolithic and also reads the NTUPLES cases",
        },
    },
    "jcampdx_ntuples_spectrum": {
        "ntuples_arrays": {
            "paths": ["jcampdx/BRUKNTUP.DX", "jcampdx/TESTNTUP.DX"],
            "required_by": ["tests/test_jcampdx.py::test_jcampdx1"],
            "notes": "real 2D NTUPLES arrays; shared with the monolithic encoding test",
        },
    },
    "extended_test_references": {
        "rnmrtk_1d_conversion": {
            "paths": ["rnmrtk_1d/time_1d.sec", "rnmrtk_1d/time_1d.par",
                      "rnmrtk_1d/freq_1d.sec", "rnmrtk_1d/freq_1d.par",
                      "rnmrtk_1d/test.ft"],
            "required_by": [
                "tests/test_convert.py::test_agilent_1d_rnmrtk",
                "tests/test_convert.py::test_rnmrtk_1d",
            ],
            "notes": "1D RNMRTK time/frequency references and Pipe output",
        },
        "rnmrtk_2d_conversion": {
            "paths": ["rnmrtk_2d/time_2d.sec", "rnmrtk_2d/time_2d.par",
                      "rnmrtk_2d/freq_2d.sec", "rnmrtk_2d/freq_2d.par",
                      "rnmrtk_2d/test.ft2"],
            "required_by": [
                "tests/test_convert.py::test_agilent_2d_rnmrtk",
                "tests/test_convert.py::test_rnmrtk_2d",
            ],
            "notes": "2D RNMRTK time/frequency references and Pipe output",
        },
        "sparky_3d_conversion": {
            "paths": ["sparky_3d/data.ucsf", "nmrpipe_3d/ft/test%03d.ft3"],
            "required_by": [
                "tests/test_sparky.py::test_3d",
                "tests/test_sparky.py::test_3d_lowmem",
                "tests/test_convert.py::test_sparky_3d",
                "tests/test_convert.py::test_sparky_3d_lowmem",
            ],
            "notes": "3D UCSF spectrum and indexed NMRPipe conversion reference",
        },
        "pipe_1d_self_conversion": {
            "paths": ["nmrpipe_1d/test.fid"],
            "required_by": ["tests/test_convert.py::test_pipe_1d"],
            "notes": "same-format historical 1D Pipe file",
        },
        "jeol_extended_samples": {
            "paths": ["jeol/cyclosporine_Proton-1-1.jdf",
                      "jeol/cyclosporine_Proton-1-1.fid",
                      "jeol/2mM sucrose_WATERGATE-3-1.jdf",
                      "jeol/2mM sucrose_WATERGATE-3-1.fid",
                      "jeol/2-ethyl-1-indanone 1_PROTON-21-1.jdf",
                      "jeol/2-ethyl-1-indanone 1_PROTON-21-1.fid",
                      "jeol/cyclosporine_HSQC-1-1.jdf",
                      "jeol/cyclosporine_HSQC-1-1.fid",
                      "jeol/2-ethyl-1-indanone 1_HSQC_NUS-3-1.jdf",
                      "jeol/2-ethyl-1-indanone 1_HSQC_NUS-3-1.fid",
                      "jeol/2-ethyl-1-indanone 1_HMBC_NUS-2-1.jdf",
                      "jeol/2-ethyl-1-indanone 1_HMBC_NUS-2-1.fid",
                      "jeol/cyclosporine_dqf_cosy_pfg-1-1.jdf",
                      "jeol/cyclosporine_dqf_cosy_pfg-1-1.fid",
                      "jeol/jeol-2d_1.jdf",
                      "jeol/jeol-2d_1.fid"],
            "required_by": [
                "tests/test_jeol.py::test_1d_complex_2",
                "tests/test_jeol.py::test_1d_complex_3",
                "tests/test_jeol.py::test_1d_complex_4",
                "tests/test_jeol.py::test_2d_cc_2",
                "tests/test_jeol.py::test_2d_cc_nus",
                "tests/test_jeol.py::test_2d_rc_nus",
                "tests/test_jeol.py::test_2d_rc",
                "tests/test_jeol.py::test_2d_cr",
            ],
            "notes": "additional real JEOL samples read by extended-validation tests",
        },
        "jcampdx_extended_spectra": {
            "paths": ["jcampdx/TESTFID.DX", "jcampdx/bruker1.dx",
                      "jcampdx/bruker2.dx", "jcampdx/bruker3.dx",
                      "jcampdx/aug07.dx", "jcampdx/aug07b.dx",
                      "jcampdx/aug07c.dx", "jcampdx/aug07d.dx",
                      "jcampdx/aug07e.dx"],
            "required_by": ["tests/test_jcampdx.py::test_jcampdx2"],
            "notes": "miscellaneous real spectra read by the extended-validation test",
        },
    },
}

# Release-critical groups NOT present in the local corpus. Rights and
# evidence strings are preserved; required reference paths live in
# REQUIRED_COMPONENTS.
MISSING_GROUPS = {
    "jeol_1d_complex_pipe_reference": {
        "format": "JEOL + Pipe",
        "redistribution_status": "NOT_AVAILABLE",
        "evidence": "absent from nmrglue repository, v0.5 release archive, and local corpus; PR #228 added code+tests only; maintainer asked about data availability but no resolution recorded",
        "notes": "real JDF binary structure; data not found in examined sources",
    },
    "jeol_2d_complex_pipe_reference": {
        "format": "JEOL + Pipe",
        "redistribution_status": "NOT_AVAILABLE",
        "evidence": "absent from nmrglue repository, v0.5 release archive, and local corpus; PR #228 added code+tests only; maintainer asked about data availability but no resolution recorded",
        "notes": "real 2D JDF quadrature/layout; data not found in examined sources",
    },
    "sparky_2d_ucsf_pipe_reference": {
        "format": "UCSF + Pipe",
        "redistribution_status": "UNRESOLVED",
        "evidence": "not present in local corpus or v0.5 archive",
        "notes": "tiled UCSF layout; requires acquisition or licensed spectrum",
    },
    "rnmrtk_3d_time_reference": {
        "format": "RNMRTK",
        "redistribution_status": "UNRESOLVED",
        "evidence": "not present in local corpus or v0.5 archive",
        "notes": "real complex 3D file; requires independent generation",
    },
    "rnmrtk_3d_frequency_pipe_reference": {
        "format": "RNMRTK + Pipe",
        "redistribution_status": "UNRESOLVED",
        "evidence": "not present in local corpus or v0.5 archive",
        "notes": "real frequency file and independent conversion reference",
    },
    "jcampdx_affn_spectrum": {
        "format": "JCAMP-DX",
        "redistribution_status": "UNRESOLVED",
        "evidence": "not present in local corpus or v0.5 archive",
        "notes": "human-auditable real spectrum; requires licensed test set",
    },
    "jcampdx_ntuples_spectrum": {
        "format": "JCAMP-DX",
        "redistribution_status": "UNRESOLVED",
        "evidence": "not present in local corpus or v0.5 archive",
        "notes": "real NTUPLES arrays; requires licensed test set",
    },
    "simpson_1d_encoding_set": {
        "format": "SIMPSON",
        "redistribution_status": "UNRESOLVED",
        "evidence": "input .in present; encoding outputs not generated",
        "notes": "TEXT/BINARY/XREIM/RAWBIN equivalence; requires SIMPSON regeneration; "
                 "output paths are declared as components of group simpson_1d",
    },
    "simpson_2d_encoding_set": {
        "format": "SIMPSON",
        "redistribution_status": "UNRESOLVED",
        "evidence": "input .in present; encoding outputs not generated",
        "notes": "2D encoding variants; requires SIMPSON regeneration; "
                 "output paths are declared as components of group simpson_2d",
    },
    "extended_test_references": {
        "format": "various",
        "redistribution_status": "UNRESOLVED",
        "evidence": "consumed only by extended-validation or historical low-priority tests; outside the 16-group release-critical contract (PR #26 assessment)",
        "notes": "recorded so that no reference consumed by a scanned dataset test is "
                 "silent; promotion into the release-critical contract is a maintainer decision",
    },
}


def should_exclude(name: str) -> bool:
    if name in EXCLUDE_NAMES:
        return True
    if any(name.startswith(p) for p in EXCLUDE_PREFIXES):
        return True
    if any(name.endswith(s) for s in EXCLUDE_SUFFIXES):
        return True
    return False


def classify_file(rel_path: str, group_name: str) -> str:
    """Classify a file by its exact relative path.

    Returns 'original' for files whose relative path matches an entry in the
    v0.5 archive (group_name/filename at the top level of the group),
    'derived' for locally generated references matching a known derived
    pattern (applied to the relative path within the group),
    or 'unknown' for unrecognized files.
    """
    prefix = f"{group_name}/"
    if not rel_path.startswith(prefix):
        return "unknown"
    group_rel = rel_path[len(prefix):]

    archive_files = ARCHIVE_FILES.get(group_name, [])
    if group_rel in archive_files:
        return "original"

    derived = DERIVED_FILES.get(group_name, {})
    if derived:
        pattern = derived.get("pattern", "")
        if pattern:
            import fnmatch
            if fnmatch.fnmatch(group_rel, pattern):
                return "derived"
    return "unknown"


def compute_group(root: Path, group_dir: Path, group_name: str) -> dict:
    files = {}
    total_size = 0
    for path in sorted(group_dir.rglob("*")):
        if not path.is_file():
            continue
        rel = path.relative_to(root).as_posix()
        if should_exclude(path.name):
            continue
        data = path.read_bytes()
        sha256 = hashlib.sha256(data).hexdigest()
        size = len(data)
        provenance_class = classify_file(rel, group_name)
        files[rel] = {"sha256": sha256, "size": size, "provenance_class": provenance_class}
        total_size += size
    return {"files": files, "total_size": total_size, "file_count": len(files)}


def pattern_to_regex(pattern: str) -> re.Pattern:
    """Translate a component path into a regular expression.

    ``%03d``-style C masks match their digit count, ``*`` matches a single
    path segment, and every other character is literal.
    """
    out = []
    i = 0
    while i < len(pattern):
        if i + 3 < len(pattern) and pattern.startswith("%0", i) \
                and pattern[i + 2].isdigit() and pattern[i + 3] == "d":
            out.append(r"\d{%d}" % int(pattern[i + 2]))
            i += 4
        elif pattern[i] == "*":
            out.append(r"[^/]*")
            i += 1
        else:
            out.append(re.escape(pattern[i]))
            i += 1
    return re.compile("^" + "".join(out) + "$")


def resolve_matches(files: dict, path: str) -> set:
    """Return the inventoried files matched by a component path.

    An exact path matches one file; a mask or wildcard path matches every
    inventoried file it covers; a directory path covers every inventoried
    file under it.
    """
    if "%" in path or "*" in path:
        rx = pattern_to_regex(path)
        return {f for f in files if rx.match(f)}
    if path in files:
        return {path}
    prefix = path.rstrip("/") + "/"
    return {f for f in files if f.startswith(prefix)}


def derive_component_status(files: dict, paths: list) -> str:
    per_path = {p: resolve_matches(files, p) for p in paths}
    matched = [p for p, m in per_path.items() if m]
    if not matched:
        return "absent"
    if len(paths) > 1 and len(matched) != len(paths):
        missing = [p for p in paths if not per_path[p]]
        raise ValueError(
            f"mixed materialization for component paths {paths}: missing {missing}"
        )
    return "present"


def is_accounted(path: str, declared: set, files: set) -> bool:
    """A consumed path is accounted when inventoried, declared, or a parent
    directory of an inventoried or declared path."""
    if path in declared or path in files:
        return True
    prefix = path.rstrip("/") + "/"
    if any(d.startswith(prefix) for d in declared):
        return True
    if any(f.startswith(prefix) for f in files):
        return True
    return False


def derive_availability(statuses: list) -> str:
    if statuses and all(s == "present" for s in statuses):
        return "complete"
    if any(s == "present" for s in statuses):
        return "partial"
    return "not_available"


def component_scope(required_by: list) -> str:
    return "critical" if set(required_by) & CRITICAL_TESTS else "extended"


def iter_components():
    for entry, comps in REQUIRED_COMPONENTS.items():
        for comp_id, comp in comps.items():
            yield entry, comp_id, comp


def all_component_paths() -> dict:
    mapping = {}
    for entry, comp_id, comp in iter_components():
        for p in comp["paths"]:
            if p in mapping:
                raise ValueError(
                    f"path {p} declared by both {mapping[p]} and {entry}.{comp_id}"
                )
            mapping[p] = f"{entry}.{comp_id}"
    return mapping


# ---------------------------------------------------------------------------
# Static extraction of data references consumed by tests
# ---------------------------------------------------------------------------

class _DataPath(str):
    """A corpus-relative path rooted at DATA_DIR."""


def _literal(node, env):
    """Resolve a string-valued expression, or return None."""
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    if isinstance(node, ast.Name):
        value = env.get(node.id)
        return None if isinstance(value, _DataPath) else value
    if isinstance(node, ast.JoinedStr):
        out = ""
        for v in node.values:
            if isinstance(v, ast.Constant):
                out += v.value
            elif isinstance(v, ast.FormattedValue):
                piece = _literal(v.value, env)
                if piece is None:
                    return None
                out += piece
            else:
                return None
        return out
    return None


def _is_path_call(node):
    func = node.func
    return (
        (isinstance(func, ast.Name) and func.id == "Path")
        or (isinstance(func, ast.Attribute) and func.attr == "Path")
    )


def _datapath(node, env):
    """Resolve a DATA_DIR-rooted expression to a corpus-relative path."""
    if isinstance(node, ast.Name):
        value = env.get(node.id)
        return value if isinstance(value, _DataPath) else None
    if isinstance(node, ast.Call):
        if isinstance(node.func, ast.Attribute) and node.func.attr == "join" and node.args:
            root = _datapath(node.args[0], env)
            if root is None:
                return None
            parts = [str(root)] if str(root) else []
            for a in node.args[1:]:
                piece = _literal(a, env)
                if piece is None:
                    return None
                parts.append(piece)
            return _DataPath("/".join(p.strip("/") for p in parts if p.strip("/")))
        if _is_path_call(node) and node.args:
            return _datapath(node.args[0], env)
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Div):
        left = _datapath(node.left, env)
        if left is None:
            return None
        right = _literal(node.right, env)
        if right is None:
            return None
        return _DataPath("/".join(p.strip("/") for p in (str(left), right) if p.strip("/")))
    if isinstance(node, ast.JoinedStr):
        rooted = any(
            isinstance(v, ast.FormattedValue) and _datapath(v.value, env) is not None
            for v in node.values
        )
        if not rooted:
            return None
        parts = []
        for v in node.values:
            if isinstance(v, ast.Constant):
                parts.append(v.value)
            elif isinstance(v, ast.FormattedValue):
                piece = _datapath(v.value, env) or _literal(v.value, env)
                if piece is None:
                    return None
                parts.append(str(piece))
            else:
                return None
        return _DataPath("/".join(p.strip("/") for p in "".join(parts).split("/") if p.strip("/")))
    return None


def _collect_lists(nodes):
    """Map names built by ``x.append(...)`` to the string values they hold.

    Both ``x.append("name")`` and ``x.append(("name", ...))`` contribute the
    first string literal of the appended value. This is the form used by
    ``tests/test_jcampdx.py`` (a ``cases`` list iterated by the test loop).
    """
    lists = {}
    for node in ast.walk(ast.Module(body=list(nodes), type_ignores=[])):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) \
                and node.func.attr == "append" and node.args:
            target = node.func.value
            if not isinstance(target, ast.Name):
                continue
            value = node.args[0]
            if isinstance(value, ast.Constant) and isinstance(value.value, str):
                lists.setdefault(target.id, set()).add(value.value)
            elif isinstance(value, (ast.Tuple, ast.List)) and value.elts:
                first = value.elts[0]
                if isinstance(first, ast.Constant) and isinstance(first.value, str):
                    lists.setdefault(target.id, set()).add(first.value)
    return lists


def _assign_env(nodes, env):
    for node in ast.walk(ast.Module(body=list(nodes), type_ignores=[])):
        if isinstance(node, ast.ImportFrom):
            for alias in node.names:
                if alias.name == "DATA_DIR":
                    env[alias.asname or alias.name] = _DataPath("")
        if isinstance(node, ast.Assign) and len(node.targets) == 1 \
                and isinstance(node.targets[0], ast.Name):
            value = _datapath(node.value, env) or _literal(node.value, env)
            if value is not None:
                env[node.targets[0].id] = value


def extract_data_references(module_path: Path) -> dict:
    """Return ``{function_name: set(corpus-relative paths)}`` for one test module.

    This is a complementary control limited to the statically resolvable
    constructions it recognizes:

    - ``os.path.join(DATA_DIR, ...)``, ``Path(DATA_DIR) / ...``, and
      f-strings interpolating a DATA_DIR-resolved alias, with literal
      segments;
    - alias assignments that resolve to such expressions, and direct uses
      of a module-level DATA_DIR alias;
    - segments taken from a loop variable bound to a name filled by
      ``x.append(...)`` (the ``for case in cases`` / ``for i, case in
      enumerate(cases)`` form of ``tests/test_jcampdx.py``, including the
      ``case[0]`` subscript).

    Not recognized (and therefore reported as no reference): iterating a
    literal list directly (``for name in ["a.bin", "b.bin"]``), segments
    coming from function parameters, glob or temporary-directory results,
    or any other runtime-built value. Extraction does not claim
    exhaustiveness over a module. The release-critical contract is enforced
    independently by the declarative checks (every ``CRITICAL_TESTS`` id
    declared in a component, unknown ids rejected), and generation refuses
    to write a manifest that leaves a recognized reference unaccounted for.
    """
    tree = ast.parse(module_path.read_text(encoding="utf-8"), filename=str(module_path))
    env = {}
    _assign_env(tree.body, env)
    module_lists = _collect_lists(tree.body)
    module_datanames = {k for k, v in env.items() if isinstance(v, _DataPath)}

    out = {}
    for node in ast.walk(tree):
        if not isinstance(node, ast.FunctionDef):
            continue
        local = dict(env)
        _assign_env(node.body, local)
        lists = dict(module_lists)
        lists.update(_collect_lists(node.body))

        loop_vars = {}
        for sub in ast.walk(node):
            if not isinstance(sub, ast.For):
                continue
            name = None
            if isinstance(sub.iter, ast.Name):
                name = sub.iter.id
            elif isinstance(sub.iter, ast.Call) and sub.iter.args \
                    and isinstance(sub.iter.args[0], ast.Name):
                name = sub.iter.args[0].id
            if name not in lists:
                continue
            targets = []
            for t in ast.walk(sub.target) if isinstance(sub.target, ast.Tuple) else [sub.target]:
                if isinstance(t, ast.Name):
                    targets.append(t)
            for t in targets:
                loop_vars[t.id] = lists[name]

        paths = set()
        for sub in ast.walk(node):
            value = _datapath(sub, local)
            if value is not None:
                paths.add(str(value))
        for sub in ast.walk(node):
            if not (isinstance(sub, ast.Call) and isinstance(sub.func, ast.Attribute)
                    and sub.func.attr == "join" and sub.args):
                continue
            root = _datapath(sub.args[0], local)
            if root is None:
                continue
            options = []
            ok = True
            for a in sub.args[1:]:
                if isinstance(a, ast.Name) and a.id in loop_vars:
                    options.append(sorted(loop_vars[a.id]))
                elif isinstance(a, ast.Subscript) and isinstance(a.value, ast.Name) \
                        and a.value.id in loop_vars:
                    options.append(sorted(loop_vars[a.value.id]))
                else:
                    piece = _literal(a, local)
                    if piece is None:
                        ok = False
                        break
                    options.append([piece])
            if not ok:
                continue
            combos = [""]
            for group in options:
                combos = [f"{c}/{o}".lstrip("/") for c in combos for o in group]
            for combo in combos:
                paths.add("/".join(p for p in (str(root), combo) if p))
        used_names = {n.id for n in ast.walk(node) if isinstance(n, ast.Name)}
        for name in used_names & module_datanames:
            paths.add(str(env[name]))
        out[node.name] = {p for p in paths if p}
    return out


def known_test_ids() -> set:
    ids = set()
    for module in SCANNED_TEST_MODULES:
        path = TESTS_DIR / module
        if not path.is_file():
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef) and node.name.startswith("test"):
                ids.add(f"tests/{module}::{node.name}")
    return ids


def validate_declarations(files: dict) -> list:
    errors = []
    try:
        all_component_paths()
    except ValueError as exc:
        errors.append(str(exc))
        return errors

    known = known_test_ids()
    for entry, comp_id, comp in iter_components():
        for test_id in comp["required_by"]:
            if test_id not in known:
                errors.append(
                    f"UNKNOWN TEST: {entry}.{comp_id} requires {test_id}"
                )
    covered = set()
    for entry, comp_id, comp in iter_components():
        covered.update(comp["required_by"])
    for test_id in sorted(CRITICAL_TESTS - covered):
        errors.append(f"UNDECLARED CRITICAL TEST: {test_id} appears in no component")

    declared = set(all_component_paths())
    for module in SCANNED_TEST_MODULES:
        path = TESTS_DIR / module
        if not path.is_file():
            errors.append(f"MISSING MODULE: {path}")
            continue
        refs = extract_data_references(path)
        for func, paths in refs.items():
            for p in sorted(paths):
                if is_accounted(p, declared, files):
                    continue
                errors.append(
                    f"UNACCOUNTED REFERENCE: tests/{module}::{func} consumes {p}"
                )
    return errors


def _toml_str(value: str) -> str:
    escaped = value.replace("\\", "\\\\").replace('"', '\\"')
    return f'"{escaped}"'


def _toml_value(value) -> str:
    if isinstance(value, str):
        return _toml_str(value)
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (list, tuple)):
        return "[" + ", ".join(_toml_value(v) for v in value) + "]"
    return str(value)


def emit_component(lines, section, comp_id, comp, status):
    scope = component_scope(comp["required_by"])
    lines.append(f"[{section}.{comp_id}]")
    lines.append(f"status = {_toml_value(status)}")
    lines.append(f"scope = {_toml_value(scope)}")
    lines.append(f"paths = {_toml_value(list(comp['paths']))}")
    lines.append(f"required_by = {_toml_value(list(comp['required_by']))}")
    lines.append(f"notes = {_toml_value(comp['notes'])}")
    lines.append("")


def main():
    if not DATA_DIR.is_dir():
        print(f"Error: data directory not found: {DATA_DIR}", file=sys.stderr)
        return 1

    groups = {}
    for entry in sorted(DATA_DIR.iterdir()):
        if not entry.is_dir() or entry.name in EXCLUDE_NAMES:
            continue
        group_name = entry.name
        info = compute_group(DATA_DIR, entry, group_name)
        if info["file_count"] == 0:
            continue
        meta = GROUP_META.get(group_name, {})
        original_count = sum(1 for f in info["files"].values() if f["provenance_class"] == "original")
        derived_count = sum(1 for f in info["files"].values() if f["provenance_class"] == "derived")
        groups[group_name] = {
            "format": meta.get("format", "unknown"),
            "provenance": meta.get("provenance", "unknown"),
            "license": meta.get("license", "UNRESOLVED"),
            "redistribution_status": meta.get("redistribution_status", "UNRESOLVED"),
            "evidence": meta.get("evidence", ""),
            "notes": meta.get("notes", ""),
            "file_count": info["file_count"],
            "original_count": original_count,
            "derived_count": derived_count,
            "total_size": info["total_size"],
            "files": info["files"],
        }

    errors = [f"UNKNOWN GROUP: {g}" for g in sorted(set(REQUIRED_COMPONENTS) - set(groups) - set(MISSING_GROUPS))]
    for g in sorted(set(REQUIRED_COMPONENTS) & set(MISSING_GROUPS)):
        if g in groups:
            errors.append(f"GROUP BOTH PRESENT AND MISSING: {g}")
    errors.extend(validate_declarations({f for g in groups.values() for f in g["files"]}))
    if errors:
        for e in errors:
            print(f"ERROR: {e}", file=sys.stderr)
        print("FAILED: declaration validation; manifest not written", file=sys.stderr)
        return 1

    all_files = {f for g in groups.values() for f in g["files"]}
    component_states = {}
    for entry, comp_id, comp in iter_components():
        matches = set()
        for p in comp["paths"]:
            matches |= resolve_matches(all_files, p)
        try:
            status = derive_component_status(all_files, comp["paths"])
        except ValueError as exc:
            print(f"ERROR: {entry}.{comp_id}: {exc}", file=sys.stderr)
            return 1
        if entry in MISSING_GROUPS and status != "absent":
            print(
                f"ERROR: {entry}.{comp_id} is declared in a missing entry but "
                f"matches {sorted(matches)}",
                file=sys.stderr,
            )
            return 1
        component_states[(entry, comp_id)] = (status, matches)

    for gname, gdata in groups.items():
        comps = REQUIRED_COMPONENTS.get(gname, {})
        statuses = [component_states[(gname, c)][0] for c in comps]
        gdata["availability"] = derive_availability(statuses)
        gdata["missing_components"] = ", ".join(
            sorted(c for c in comps if component_states[(gname, c)][0] == "absent")
        )
        gdata["component_count"] = len(comps)
        gdata["absent_component_count"] = sum(
            1 for c in comps if component_states[(gname, c)][0] == "absent"
        )

    total_components = 0
    absent_components = 0
    critical_components = 0
    absent_critical_components = 0
    for entry, comp_id, comp in iter_components():
        status = component_states[(entry, comp_id)][0]
        scope = component_scope(comp["required_by"])
        total_components += 1
        if status == "absent":
            absent_components += 1
        if scope == "critical":
            critical_components += 1
            if status == "absent":
                absent_critical_components += 1

    lines = []
    lines.append("# nmrglue-ng release-critical test-data manifest")
    lines.append("# Generated by scripts/generate_testdata_manifest.py")
    lines.append("# Do not edit manually; regenerate when the corpus changes.")
    lines.append("#")
    lines.append("# Redistribution status values:")
    lines.append("#   UNRESOLVED    - no explicit license or rights evidence found")
    lines.append("#   NOT_AVAILABLE - data not found in examined sources")
    lines.append("#   CLEAR         - explicit redistribution permission documented")
    lines.append("#")
    lines.append("# Component status values:")
    lines.append("#   present - every listed path is inventoried below")
    lines.append("#   absent  - explicitly declared missing; no file matches the paths")
    lines.append("#")
    lines.append("# Component scope values:")
    lines.append("#   critical - consumed by at least one release-critical test")
    lines.append("#   extended - consumed only by extended-validation or low-priority tests")
    lines.append("")
    lines.append("[manifest]")
    lines.append(f"version = {_toml_value(MANIFEST_VERSION)}")
    lines.append(f"total_groups = {len(groups)}")
    lines.append(f"total_files = {sum(g['file_count'] for g in groups.values())}")
    lines.append(f"total_size = {sum(g['total_size'] for g in groups.values())}")
    lines.append(f"missing_groups = {len(MISSING_GROUPS)}")
    lines.append(f"total_components = {total_components}")
    lines.append(f"absent_components = {absent_components}")
    lines.append(f"critical_components = {critical_components}")
    lines.append(f"absent_critical_components = {absent_critical_components}")
    lines.append(f"critical_tests = {_toml_value(sorted(CRITICAL_TESTS))}")
    lines.append("")

    for gname, gdata in groups.items():
        lines.append(f"[groups.{gname}]")
        lines.append(f"format = {_toml_value(gdata['format'])}")
        lines.append(f"provenance = {_toml_value(gdata['provenance'])}")
        lines.append(f"license = {_toml_value(gdata['license'])}")
        lines.append(f"redistribution_status = {_toml_value(gdata['redistribution_status'])}")
        lines.append(f"evidence = {_toml_value(gdata['evidence'])}")
        lines.append(f"availability = {_toml_value(gdata['availability'])}")
        lines.append(f"missing_components = {_toml_value(gdata['missing_components'])}")
        lines.append(f"notes = {_toml_value(gdata['notes'])}")
        lines.append(f"file_count = {gdata['file_count']}")
        lines.append(f"original_count = {gdata['original_count']}")
        lines.append(f"derived_count = {gdata['derived_count']}")
        lines.append(f"total_size = {gdata['total_size']}")
        lines.append(f"component_count = {gdata['component_count']}")
        lines.append(f"absent_component_count = {gdata['absent_component_count']}")
        lines.append("")
        for fname, fdata in gdata["files"].items():
            lines.append(f'[groups.{gname}.files."{fname}"]')
            lines.append(f"sha256 = {_toml_value(fdata['sha256'])}")
            lines.append(f"size = {fdata['size']}")
            lines.append(f"provenance_class = {_toml_value(fdata['provenance_class'])}")
        lines.append("")
        for comp_id in sorted(REQUIRED_COMPONENTS.get(gname, {})):
            comp = REQUIRED_COMPONENTS[gname][comp_id]
            status = component_states[(gname, comp_id)][0]
            emit_component(lines, f"groups.{gname}.components", comp_id, comp, status)

    lines.append("# Release-critical groups and reference sets NOT present in the")
    lines.append("# local corpus. extended_test_references is not a contract group: it")
    lines.append("# records references consumed only by extended-validation or")
    lines.append("# low-priority tests so that no consumed path stays silent.")
    lines.append("")
    for gname, gdata in MISSING_GROUPS.items():
        lines.append(f"[missing.{gname}]")
        lines.append(f"format = {_toml_value(gdata['format'])}")
        lines.append(f"redistribution_status = {_toml_value(gdata['redistribution_status'])}")
        lines.append(f"evidence = {_toml_value(gdata['evidence'])}")
        lines.append(f"notes = {_toml_value(gdata['notes'])}")
        comps = REQUIRED_COMPONENTS.get(gname, {})
        lines.append(f"component_count = {len(comps)}")
        lines.append(
            "absent_component_count = "
            + str(sum(1 for c in comps if component_states[(gname, c)][0] == "absent"))
        )
        lines.append("")
        for comp_id in sorted(comps):
            comp = comps[comp_id]
            status = component_states[(gname, comp_id)][0]
            emit_component(lines, f"missing.{gname}.components", comp_id, comp, status)

    MANIFEST_PATH.write_text("\n".join(lines).rstrip("\n") + "\n", encoding="utf-8")
    print(f"Manifest written: {MANIFEST_PATH}")
    print(f"  Groups available: {len(groups)}")
    print(f"  Groups missing:   {len(MISSING_GROUPS)}")
    print(f"  Total files:      {sum(g['file_count'] for g in groups.values())}")
    print(f"  Total size:       {sum(g['total_size'] for g in groups.values())} bytes")
    print(f"  Components:       {total_components} ({absent_components} absent)")
    print(f"  Critical:         {critical_components} ({absent_critical_components} absent)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
