"""Regular QF FID pages, independent component scaling and time geometry."""

from dataclasses import replace

import numpy as np
import pytest

from nmrglue import interop


FID = """##TITLE=Synthetic regular QF
##JCAMPDX=6.0
##DATA TYPE=nD NMR FID
##DATA CLASS=NTUPLES
##NUM DIM=2
##.ACQUISITION SCHEME=NOT PHASE SENSITIVE
##NTUPLES=nD NMR FID
##SYMBOL=T1,T2,R,I
##VAR_TYPE=INDEPENDENT,INDEPENDENT,DEPENDENT,DEPENDENT
##VAR_DIM=2,3,3,3
##UNITS=SECONDS,SECONDS,ARBITRARY UNITS,ARBITRARY UNITS
##FACTOR=0.002,0.001,2,0.5
##FIRST=0,0,2,5
##LAST=0.002,0.002,12,30
##PAGE=T1=0
##DATA TABLE=(T2++(R..R)), PROFILE
0 1 2 3
##PAGE=T1=0
##DATA TABLE=(T2++(I..I)), PROFILE
0 10 20 30
##PAGE=T1=0.002
##DATA TABLE=(T2++(R..R)), PROFILE
0 4 5 6
##PAGE=T1=0.002
##DATA TABLE=(T2++(I..I)), PROFILE
0 40 50 60
##END NTUPLES=nD NMR FID
##END=
"""


@pytest.mark.parametrize("rows", [
    ("0 1 2 3", "0 10 20 30", "0 4 5 6", "0 40 50 60"),
    ("0+1+2+3", "0+10+20+30", "0+4+5+6", "0+40+50+60"),
    ("0ABC", "0A0B0C0", "0DEF", "0D0E0F0"),
    ("0AJJ\n2C", "0A0J0J0\n2C0", "0DJJ\n2F", "0D0J0J0\n2F0"),
    ("0AJT\n2C", "0A0J0T\n2C0", "0DJT\n2F", "0D0J0T\n2F0"),
], ids=["AFFN", "PAC", "SQZ", "DIF", "DIF-DUP"])
def test_qf_profile_through_dispatch(tmp_path, rows):
    path = tmp_path / "fid.dx"
    contents = FID
    for original, replacement in zip(("0 1 2 3", "0 10 20 30", "0 4 5 6", "0 40 50 60"), rows):
        contents = contents.replace(original, replacement)
    path.write_text(contents)
    read = interop.read(path, profile="jcampdx-fid-2d")
    expected = np.array([[2 + 5j, 4 + 10j, 6 + 15j], [8 + 20j, 10 + 25j, 12 + 30j]])
    np.testing.assert_array_equal(read.data, expected)
    for conjugation in ("none", "conjugate"):
        normalized = interop.normalize(read, quadrature="qf", conjugation=conjugation)
        samples = normalized.data[0] + 1j * normalized.data[1]
        np.testing.assert_array_equal(samples, expected if conjugation == "none" else expected.conj())
        assert normalized.acquisition["spectral_width_hz"] == (500, 1000)
        np.testing.assert_array_equal(normalized.axes[0].values, [0, .002])
        np.testing.assert_array_equal(normalized.axes[1].values, [0, .001, .002])
        assert normalized.encoding == ("real", "complex")
    np.testing.assert_array_equal(read.data, expected)
    with pytest.raises(ValueError, match="description disagrees"):
        interop.normalize(replace(read, axes=read.axes[::-1]), quadrature="qf", conjugation="none")


@pytest.mark.parametrize("old,new", [
    ("PAGE=T1=0.002", "PAGE=T1=0.001"),
    ("VAR_DIM=2,3,3,3", "VAR_DIM=3,3,3,3"),
    ("0 4 5 6", "0 4 5"),
    ("0 4 5 6", "0 4\n8 5 6"),
    ("T2++(I..I)", "T2++(R..R)"),
    ("SECONDS,SECONDS", "HZ,SECONDS"),
    ("FACTOR=0.002,0.001,2,0.5", "FACTOR=0.002,0.001,2,0"),
    ("##PAGE=T1=0\n", ""),
])
def test_invalid_fid_geometry_and_tables_are_rejected(tmp_path, old, new):
    path = tmp_path / "bad.dx"
    path.write_text(FID.replace(old, new))
    with pytest.raises(ValueError):
        interop.read(path, profile="jcampdx-fid-2d")


def test_echo_antiecho_is_not_reinterpreted_as_qf(tmp_path):
    path = tmp_path / "echo.dx"
    path.write_text(FID.replace("NOT PHASE SENSITIVE", "Echo-Antiecho"))
    read = interop.read(path, profile="jcampdx-fid-2d")
    with pytest.raises(ValueError, match="declared QF"):
        interop.normalize(read, quadrature="qf", conjugation="none")


@pytest.mark.parametrize("delay,expected", [(68, 68), (-1, None)])
def test_group_delay_is_retained_without_applying_a_correction(tmp_path, delay, expected):
    path = tmp_path / "delay.dx"
    path.write_text(FID.replace("##NTUPLES=", f"##$GRPDLY={delay}\n##NTUPLES="))
    read = interop.read(path, profile="jcampdx-fid-2d")
    normalized = interop.normalize(read, quadrature="qf", conjugation="none")
    assert normalized.acquisition["digital_filter"] == {
        "applied": False, "group_delay_points": expected, "source": "$GRPDLY",
    }
    np.testing.assert_array_equal(normalized.data[0], read.data.real)


@pytest.mark.parametrize("options", [
    {"quadrature": "states", "conjugation": "none"},
    {"quadrature": "qf", "conjugation": "auto"},
])
def test_normalization_options_must_be_explicit_and_supported(tmp_path, options):
    path = tmp_path / "options.dx"
    path.write_text(FID)
    read = interop.read(path, profile="jcampdx-fid-2d")
    with pytest.raises(ValueError):
        interop.normalize(read, **options)
