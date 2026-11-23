"""Declared real-F1 schemes and explicit physical time calibration."""
from dataclasses import replace
import numpy as np
import pytest
from nmrglue import interop


def _write(path, scheme="TPPI", mode="SIMULTANEOUS (DQD)"):
    values = np.arange(24).reshape(4, 6) + 1j * np.arange(24, 48).reshape(4, 6)
    text = (
        "##TITLE=Synthetic real F1\n##DATA TYPE=nD NMR FID\n"
        "##DATA CLASS=NTUPLES\n##NUM DIM=2\n"
        f"##.ACQUISITION SCHEME={scheme}\n##.ACQUISITION MODE={mode}\n"
        "##$GRPDLY=0\n##NTUPLES=nD NMR FID\n##SYMBOL=T1,T2,R,I\n"
        "##VAR_TYPE=INDEPENDENT,INDEPENDENT,DEPENDENT,DEPENDENT\n"
        "##VAR_DIM=4,6,6,6\n##UNITS=SECONDS,SECONDS,ARBITRARY UNITS,ARBITRARY UNITS\n"
        "##FACTOR=0.00025,0.000125,1,1\n##FIRST=0,0,0,0\n"
        "##LAST=0.00075,0.000625,0,0\n"
    )
    for index, trace in enumerate(values):
        for symbol, data in [("R", trace.real), ("I", trace.imag)]:
            text += f"##PAGE=T1={index*.00025}\n##DATA TABLE=(T2++({symbol}..{symbol})), PROFILE\n"
            text += "0 " + " ".join(str(float(x)) for x in data) + "\n"
    path.write_text(text + "##END NTUPLES=nD NMR FID\n##END=\n")
    return values


@pytest.mark.parametrize("scheme", ["tppi", "qseq"])
@pytest.mark.parametrize("conjugation", ["none", "conjugate"])
def test_real_f1_normalization(tmp_path, scheme, conjugation):
    path = tmp_path / "real.dx"
    values = _write(path, scheme.upper())
    stored = interop.read(path, profile="jcampdx-fid-2d")
    result = interop.normalize(stored, quadrature=scheme, conjugation=conjugation,
                               indirect_dwell_s=.000125)
    expected = values.conj() if conjugation == "conjugate" else values.copy()
    if scheme == "qseq":
        expected[2:] *= -1
    np.testing.assert_array_equal(result.data, expected)
    np.testing.assert_array_equal(stored.data, values)
    np.testing.assert_array_equal(result.axes[0].values, np.arange(4)*.000125)
    assert result.acquisition["spectral_widths_hz"] == (8000, 8000)
    assert result.acquisition["declared_indirect_dwell_s"] == .00025
    assert result.acquisition["physical_indirect_increments"] == 4
    assert result.acquisition["indirect_sampling"] == scheme
    assert result.quadrature_mode == "tppi-stored-2d"
    assert result.encoding == ("tppi", "complex")
    assert result.dimensions == ("F1", "F2")
    assert result.applied_operations[-1]["sign"] == ("alternate-pairs" if scheme == "qseq" else "none")
    assert result.acquisition["digital_filter"]["group_delay_points"] == 0


@pytest.mark.parametrize("dwell", [None, False, True, 0, -1, np.nan, np.inf, 1e-320, 1e308, 10**400])
@pytest.mark.parametrize("scheme", ["tppi", "qseq"])
def test_real_f1_requires_representable_physical_dwell(tmp_path, dwell, scheme):
    path = tmp_path / "real.dx"
    _write(path, scheme.upper())
    stored = interop.read(path, profile="jcampdx-fid-2d")
    with pytest.raises(ValueError, match="dwell|time grids"):
        interop.normalize(stored, quadrature=scheme, conjugation="none", indirect_dwell_s=dwell)


@pytest.mark.parametrize("scheme", ["tppi", "qseq"])
def test_real_f1_requires_matching_scheme_dqd_and_unchanged_storage(tmp_path, scheme):
    path = tmp_path / "real.dx"
    _write(path, scheme.upper())
    stored = interop.read(path, profile="jcampdx-fid-2d")
    options = dict(quadrature=scheme, conjugation="none", indirect_dwell_s=.000125)
    with pytest.raises(ValueError, match="adjacent-pair"):
        interop.normalize(stored, confirm_adjacent_pairs=True, **options)
    with pytest.raises(ValueError, match="description disagrees"):
        interop.normalize(replace(stored, data=stored.data[::-1]), **options)
    for declaration, mode in [("States", "SIMULTANEOUS (DQD)"), (scheme.upper(), "SEQUENTIAL")]:
        _write(path, declaration, mode)
        with pytest.raises(ValueError, match="declared|DQD"):
            interop.normalize(interop.read(path, profile="jcampdx-fid-2d"), **options)
