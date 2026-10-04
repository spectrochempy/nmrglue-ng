"""Reject empty, skipped, or failing test runs in required CI profiles."""

import sys
import xml.etree.ElementTree as ET


def check_report(path):
    cases = list(ET.parse(path).getroot().iter("testcase"))
    if not cases:
        raise SystemExit("Required profile executed no tests")
    for case in cases:
        if any(case.find(tag) is not None for tag in ("skipped", "failure", "error")):
            raise SystemExit(f"Required test did not pass: {case.attrib}")
    print(f"Required profile: {len(cases)} tests passed, no skips")


if __name__ == "__main__":
    check_report(sys.argv[1])
