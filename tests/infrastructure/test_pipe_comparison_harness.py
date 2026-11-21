import hashlib
import importlib.util
from pathlib import Path
import subprocess

import pytest


@pytest.fixture
def harness():
    path = Path(__file__).resolve().parents[1] / 'process' / 'test_pipe_proc.py'
    spec = importlib.util.spec_from_file_location('pipe_comparison_harness', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_native_failure_is_not_ignored(harness, tmp_path, monkeypatch):
    script = tmp_path / 'noop.py'
    script.write_text('pass\n')
    monkeypatch.setattr(harness.os, 'system', lambda command: 7)
    def fail(*args, **kwargs):
        raise subprocess.CalledProcessError(7, args[0])
    monkeypatch.setattr(subprocess, 'run', fail)
    with pytest.raises(subprocess.CalledProcessError):
        harness._perform_test(str(script), './failure.com', [], [])


@pytest.mark.parametrize('raise_error', [False, True])
def test_fixture_isolates_writes_restores_cwd_and_cleans_up(harness, tmp_path, monkeypatch,
                                                         raise_error):
    original = Path.cwd()
    source = harness.FIXTURE_DIR / 'time_real.fid'
    digest = hashlib.sha256(source.read_bytes()).hexdigest()
    generator = harness._comparison_directory.__wrapped__(tmp_path, monkeypatch)
    next(generator)
    work = Path.cwd()
    try:
        assert work.is_relative_to(tmp_path)
        (work / 'time_real.fid').write_bytes(b'test-only changed copy')
        if raise_error:
            with pytest.raises(RuntimeError, match='forced failure'):
                generator.throw(RuntimeError('forced failure'))
        else:
            with pytest.raises(StopIteration):
                next(generator)
    finally:
        generator.close()
    assert Path.cwd() == original
    assert not work.exists()
    assert hashlib.sha256(source.read_bytes()).hexdigest() == digest
