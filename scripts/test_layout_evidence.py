"""Capture and compare the one-time test-layout migration evidence."""

import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys


def _value(value):
    if isinstance(value, Path):
        return {"type": "path", "value": value.as_posix()}
    if hasattr(value, "dtype") and hasattr(value, "shape") and hasattr(value, "tobytes"):
        return {
            "type": f"{type(value).__module__}.{type(value).__qualname__}",
            "dtype": str(value.dtype),
            "shape": list(value.shape),
            "sha256": hashlib.sha256(value.tobytes()).hexdigest(),
        }
    if isinstance(value, (str, int, float, bool)) or value is None:
        return {"type": type(value).__name__, "value": value}
    if isinstance(value, complex):
        return {"type": "complex", "real": value.real, "imag": value.imag}
    if isinstance(value, (list, tuple)):
        return {"type": type(value).__name__, "value": [_value(v) for v in value]}
    if isinstance(value, dict):
        return {
            "type": "dict",
            "value": {
                str(name): _value(item) for name, item in sorted(value.items(), key=lambda pair: str(pair[0]))
            },
        }
    if callable(value):
        return {
            "type": "callable",
            "value": f"{value.__module__}.{value.__qualname__}",
        }
    if isinstance(value, slice):
        return {
            "type": "slice",
            "start": _value(value.start),
            "stop": _value(value.stop),
            "step": _value(value.step),
        }
    if hasattr(value, "item"):
        return _value(value.item())
    raise TypeError(f"unsupported parameter value: {type(value)!r}")


def _marker(marker):
    return {
        "name": marker.name,
        "args": [_value(value) for value in marker.args],
        "kwargs": {name: _value(value) for name, value in sorted(marker.kwargs.items())},
    }


class Collector:
    def __init__(self):
        self.items = []

    def pytest_collection_finish(self, session):
        for item in session.items:
            callspec = getattr(item, "callspec", None)
            self.items.append(
                {
                    "nodeid": item.nodeid,
                    "path": item.path.relative_to(session.config.rootpath).as_posix(),
                    "fixtures": sorted(item.fixturenames),
                    "markers": [_marker(marker) for marker in item.iter_markers()],
                    "parameters": None
                    if callspec is None
                    else {
                        "id": callspec.id,
                        "indices": dict(sorted(callspec.indices.items())),
                        "params": {
                            name: _value(value)
                            for name, value in sorted(callspec.params.items())
                        },
                    },
                }
            )


def collect(output):
    import pytest

    collector = Collector()
    status = pytest.main(
        ["--collect-only", "-qq", "-p", "no:cacheprovider", "--strict-markers", "--strict-config"],
        plugins=[collector],
    )
    if status:
        raise SystemExit(status)
    output.write_text(json.dumps(collector.items, indent=2, sort_keys=True) + "\n")


def fixture_inventory(output, roots):
    entries = []
    for root in roots:
        root = Path(root)
        paths = [root] if root.is_file() else sorted(root.rglob("*"))
        for path in paths:
            if path.is_file():
                entries.append(
                    {
                        "path": path.as_posix(),
                        "size": path.stat().st_size,
                        "mode": path.stat().st_mode & 0o777,
                        "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                    }
                )
    output.write_text(json.dumps(entries, indent=2, sort_keys=True) + "\n")


def compare(before_path, after_path, mapping_path):
    before = json.loads(before_path.read_text())
    after = json.loads(after_path.read_text())
    mapping = json.loads(mapping_path.read_text())
    after_by_id = {item["nodeid"]: item for item in after}
    errors = []
    def normalize(value):
        if isinstance(value, str):
            return (
                value.replace(
                    "nmrglue/fileio/tests/bruker_test_data",
                    "tests/fixtures/fileio/bruker_test_data",
                )
                .replace("nmrglue/fileio/tests/data", "tests/fixtures/fileio/data")
                .replace("tests/pipe_proc_tests", "tests/fixtures/process/pipe_proc_tests")
                .replace("/tests/../tests/", "/tests/")
                .replace("/tests/fileio/../fixtures/", "/tests/fixtures/")
            )
        if isinstance(value, list):
            return [normalize(item) for item in value]
        if isinstance(value, dict):
            return {name: normalize(item) for name, item in value.items()}
        return value

    for item in before:
        old = item["nodeid"]
        prefix, suffix = old.split("::", 1)
        expected = mapping[prefix] + "::" + suffix
        candidate = after_by_id.pop(expected, None)
        if candidate is None:
            errors.append(f"missing: {old} -> {expected}")
        elif normalize({key: value for key, value in item.items() if key not in {"nodeid", "path"}}) != normalize({
            key: value for key, value in candidate.items() if key not in {"nodeid", "path"}
        }):
            errors.append(f"metadata differs: {old} -> {expected}")
    errors.extend(f"unexpected: {item}" for item in sorted(after_by_id))
    if errors:
        raise SystemExit("\n".join(errors))
    print(f"Collection parity: {len(before)} items")


def main():
    parser = argparse.ArgumentParser()
    commands = parser.add_subparsers(dest="command", required=True)
    collect_parser = commands.add_parser("collect")
    collect_parser.add_argument("output", type=Path)
    inventory_parser = commands.add_parser("fixtures")
    inventory_parser.add_argument("output", type=Path)
    inventory_parser.add_argument("roots", nargs="+")
    compare_parser = commands.add_parser("compare")
    compare_parser.add_argument("before", type=Path)
    compare_parser.add_argument("after", type=Path)
    compare_parser.add_argument("mapping", type=Path)
    args = parser.parse_args()
    if args.command == "collect":
        collect(args.output)
    elif args.command == "fixtures":
        fixture_inventory(args.output, args.roots)
    else:
        compare(args.before, args.after, args.mapping)


if __name__ == "__main__":
    main()
