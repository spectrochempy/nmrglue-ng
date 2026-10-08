"""Ensure required CI profiles cannot report skipped or empty runs as passes."""

from pathlib import Path
import runpy
import xml.etree.ElementTree as ET

import pytest


check_report = runpy.run_path(
    str(Path(__file__).resolve().parents[2] / ".github/scripts/check_test_report.py")
)["check_report"]


@pytest.mark.parametrize("outcome", ["empty", "skipped", "failure", "error", "mixed"])
def test_required_report_rejects_incomplete_validation(tmp_path, outcome):
    suite = ET.Element("testsuite")
    if outcome != "empty":
        case = ET.SubElement(suite, "testcase", name="required")
        ET.SubElement(case, "skipped" if outcome == "mixed" else outcome)
    if outcome == "mixed":
        ET.SubElement(suite, "testcase", name="passing")
    report = tmp_path / "report.xml"
    ET.ElementTree(suite).write(report)
    with pytest.raises(SystemExit):
        check_report(report)


def test_required_report_accepts_passing_tests(tmp_path):
    report = tmp_path / "report.xml"
    report.write_text(
        '<testsuites><testsuite><testcase name="passing"/></testsuite></testsuites>',
        encoding="utf-8",
    )
    check_report(report)


def test_required_report_rejects_missing_report(tmp_path):
    with pytest.raises(FileNotFoundError):
        check_report(tmp_path / "missing.xml")


def test_required_report_rejects_malformed_report(tmp_path):
    report = tmp_path / "report.xml"
    report.write_text("<testsuites>", encoding="utf-8")
    with pytest.raises(ET.ParseError):
        check_report(report)
