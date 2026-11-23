"""Synthetic nD FID regression for the TopSpin layout in Zenodo 24366286."""

import numpy as np
import pytest

from nmrglue import jcampdx


FID = """##TITLE=two indirect increments
##JCAMPDX=6.0
##DATA TYPE=nD NMR FID
##DATA CLASS=NTUPLES
##NUM DIM=2
##.OBSERVE FREQUENCY=400
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


def test_read_nd_fid_returns_all_scaled_pages(tmp_path):
    path = tmp_path / "fid.dx"
    path.write_text(FID)
    metadata, data = jcampdx.read(path, show_all_data=True)
    assert metadata["DATATYPE"] == ["nD NMR FID"]
    np.testing.assert_array_equal(data["real"], [[2, 4, 6], [8, 10, 12]])
    np.testing.assert_array_equal(data["imaginary"], [[5, 10, 15], [20, 25, 30]])
    assert metadata["PAGE"] == ["T1=0", "T1=0", "T1=0.002", "T1=0.002"]


def test_read_nd_fid_default_retains_first_page_contract(tmp_path):
    path = tmp_path / "fid.dx"
    path.write_text(FID)
    with pytest.warns(UserWarning, match="multiple .* arrays") as caught:
        _, data = jcampdx.read(path, as_complex=True)
    assert len(caught) == 2
    np.testing.assert_array_equal(data, [2 + 5j, 4 + 10j, 6 + 15j])


@pytest.mark.parametrize("declared_type", [True, False])
def test_guess_udic_nd_fid_is_time_domain(declared_type):
    metadata = {
        "DATACLASS": ["NTUPLES"],
        "NTUPLES": ["nD NMR FID"],
        "NUMDIM": ["2"],
        "SYMBOL": ["T1,T2,R,I"],
        "VARTYPE": ["INDEPENDENT,INDEPENDENT,DEPENDENT,DEPENDENT"],
        "FIRST": ["0,0,0,0"],
        "LAST": ["0.02413,0.19437,0,0"],
        "UNITS": ["SECONDS,SECONDS,ARBITRARY UNITS,ARBITRARY UNITS"],
    }
    if declared_type:
        metadata["DATATYPE"] = ["nD NMR FID"]
    with pytest.warns(UserWarning, match="direct dimension only"):
        udic = jcampdx.guess_udic(metadata, {"real": [np.zeros(1024)]})
    assert udic["ndim"] == 1
    assert udic[0]["size"] == 1024
    assert udic[0]["time"] is True
    assert udic[0]["freq"] is False
    assert udic[0]["sw"] == pytest.approx(1 / 0.00019, rel=1e-14)
