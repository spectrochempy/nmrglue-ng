"""Regression coverage for older SpectroChemPy SIMPSON imports."""

import numpy as np
import pytest

from nmrglue.fileio import simpson


@pytest.mark.parametrize("separator", ["", "\n", "\n" * 10])
def test_short_xreim_with_optional_blanks(tmp_path, separator):
    path = tmp_path / "short.spe"
    path.write_text(f"{separator}4 1 2\n{separator}2 3 4\n{separator}")
    metadata, data = simpson.read(path)
    np.testing.assert_array_equal(metadata["units"], [4, 2])
    np.testing.assert_array_equal(data, [1 + 2j, 3 + 4j])


@pytest.mark.parametrize("separator", ["", "\n"])
def test_xyreim_keeps_default_order_and_can_match_legacy(tmp_path, separator):
    path = tmp_path / "descending.spe"
    path.write_text(separator.join(
        "".join(f"{y} {x} {10 * y + x} {y - x}\n" for x in (4, 3, 2, 1))
        for y in (2, 1)
    ) + separator)
    first_seen, original = simpson.read(path)
    sorted_grid, sorted_data = simpson.read(path, legacy_layout=True)
    np.testing.assert_array_equal(original.real, [[24, 23, 22, 21], [14, 13, 12, 11]])
    np.testing.assert_array_equal(sorted_data.real, [[11, 12, 13, 14], [21, 22, 23, 24]])
    np.testing.assert_array_equal(sorted_data, original[::-1, ::-1])
    np.testing.assert_array_equal(first_seen["units"].ni_unit[:, 0], [2, 1])
    np.testing.assert_array_equal(sorted_grid["units"].np_unit[0], [1, 2, 3, 4])


@pytest.mark.parametrize("rows", [
    "0 0 1 2\n0 1 3 4\n1 0 5 6\n",
    "0 0 1 2\n0 1 3 4\n1 0 5 6\n1 0 7 8\n",
])
def test_xyreim_rejects_missing_or_duplicate_samples(tmp_path, rows):
    path = tmp_path / "incomplete.spe"
    path.write_text(rows)
    with pytest.raises(ValueError, match="complete grid"):
        simpson.read(path, legacy_layout=True)


def test_text_tolerates_padded_header_and_rejects_truncation(tmp_path):
    path = tmp_path / "padded.fid"
    header = "\n SIMP \n NP = 2 \n SW = 4000 \n TYPE = FID \n DATA \n"
    path.write_text(header + "1 2\n\n3 4\n END \n")
    metadata, data = simpson.read(path)
    assert metadata["SW"] == 4000.0
    np.testing.assert_array_equal(data, [1 + 2j, 3 + 4j])
    path.write_text(header + "1 2\nEND\n")
    with pytest.raises(ValueError, match="declared shape"):
        simpson.read(path)
