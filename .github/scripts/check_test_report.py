"""Reject empty, skipped, or failing test runs in required CI profiles."""

import sys
import xml.etree.ElementTree as ET


def check_report(path, expected_count=None):
    cases = list(ET.parse(path).getroot().iter("testcase"))
    if not cases:
        raise SystemExit("Required profile executed no tests")
    if expected_count is not None and len(cases) != expected_count:
        raise SystemExit(
            f"Required profile executed {len(cases)} tests, expected {expected_count}"
        )
    for case in cases:
        if any(case.find(tag) is not None for tag in ("skipped", "failure", "error")):
            raise SystemExit(f"Required test did not pass: {case.attrib}")
    print(f"Required profile: {len(cases)} tests passed, no skips")


if __name__ == "__main__":
    check_report(sys.argv[1], int(sys.argv[2]) if len(sys.argv) == 3 else None)
