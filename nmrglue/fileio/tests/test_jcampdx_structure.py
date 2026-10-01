"""Self-contained tests for nmrglue.fileio.jcampdx."""

from pathlib import Path

import nmrglue as ng


DATA_DIR = Path(__file__).with_name("data")
BLOCK_STRUCTURE = DATA_DIR / "synthetic_jcampdx_blocks.jdx"


def test_jcampdx_dicstructure():
    """Select the primary spectrum and group all remaining block types."""
    dic, data = ng.jcampdx.read(BLOCK_STRUCTURE)

    assert data.tolist() == [1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0]
    assert dic["TITLE"] == ["Primary synthetic spectrum"]
    assert dic["DATATYPE"] == ["NMR SPECTRUM"]
    assert dic[".OBSERVENUCLEUS"] == ["^1H"]

    assert [block["DUMMYENTRY"][0] for block in dic["_datatype_LINK"]] == [
        "STANDALONE LINK",
        "INNER LINK",
        "OUTER LINK",
    ]
    assert dic["_datatype_NMRPEAKTABLE"][0]["DUMMYENTRY"] == [
        "SYNTHETIC PEAK TABLE"
    ]
    assert dic["_datatype_NA"][0]["DUMMYENTRY"] == ["UNTYPED METADATA"]
    assert dic["_datatype_NA"][0]["_comments"] == [
        "first synthetic comment",
        "second synthetic comment",
    ]

    # The primary spectrum is promoted; only the additional spectrum remains.
    assert len(dic["_datatype_NMRSPECTRUM"]) == 1
    assert dic["_datatype_NMRSPECTRUM"][0]["TITLE"] == [
        "Secondary synthetic spectrum"
    ]


def test_jcampdx_dicstructure2():
    """Keep nested LINK blocks separate and retain additional spectrum data."""
    dic, _ = ng.jcampdx.read(BLOCK_STRUCTURE)

    links = dic["_datatype_LINK"]
    assert [block["TITLE"][0] for block in links[-2:]] == [
        "Inner synthetic link",
        "Outer synthetic link",
    ]
    assert [block["DUMMYENTRY"][0] for block in links[-2:]] == [
        "INNER LINK",
        "OUTER LINK",
    ]
    assert all("XYDATA" not in block for block in links)

    secondary = dic["_datatype_NMRSPECTRUM"][0]
    assert "DUMMYENTRY" not in secondary
    assert ng.jcampdx.getdataarray(secondary).tolist() == [
        8.0,
        7.0,
        6.0,
        5.0,
        4.0,
        3.0,
        2.0,
        1.0,
    ]
