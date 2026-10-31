"""ROOT reception counterexamples for W22's declared path/error contract."""
import os
from pathlib import Path

import pytest

from company_wiki._atomic_file import atomic_output


def _extended(path):
    absolute = os.path.abspath(path)
    if absolute.startswith("\\\\?\\"):
        return absolute
    if absolute.startswith("\\\\"):
        return "\\\\?\\UNC\\" + absolute.lstrip("\\")
    return "\\\\?\\" + absolute


@pytest.mark.skipif(os.name != "nt", reason="native Windows path boundary")
def test_short_relative_target_in_deep_cwd(tmp_path, monkeypatch):
    parent = tmp_path / ("d" * (240 - len(str(tmp_path)) - 1))
    os.makedirs(_extended(parent))
    target = parent / ("r" * 30 + ".json")
    Path(_extended(target)).write_bytes(b"original")
    monkeypatch.chdir(parent)
    with atomic_output(Path(target.name)) as stream:
        stream.write(b"replacement")
    assert Path(_extended(target)).read_bytes() == b"replacement"
    assert sorted(os.listdir(_extended(parent))) == [target.name]


@pytest.mark.skipif(os.name != "nt", reason="Win32 lengths count UTF-16 units")
def test_non_bmp_parent_uses_win32_length_budget(tmp_path):
    root_units = len(str(tmp_path).encode("utf-16-le")) // 2
    parent = tmp_path / ("\U0001f600" * ((240 - root_units - 1) // 2))
    os.makedirs(_extended(parent))
    target = parent / ("u" * 30 + ".json")
    assert len(str(target)) < 259
    assert len(str(target).encode("utf-16-le")) // 2 > 259
    Path(_extended(target)).write_bytes(b"original")
    with atomic_output(target) as stream:
        stream.write(b"replacement")
    assert Path(_extended(target)).read_bytes() == b"replacement"
    assert sorted(os.listdir(_extended(parent))) == [target.name]


def test_cleanup_preserves_exception_without_add_note(tmp_path, monkeypatch):
    # Model Python 3.10's exception API on the installed interpreter.
    class LegacyError(RuntimeError):
        def __getattribute__(self, name):
            if name == "add_note":
                raise AttributeError("Python 3.10 has no add_note")
            return super().__getattribute__(name)

    from company_wiki import _atomic_file
    target = tmp_path / "existing.bin"
    target.write_bytes(b"original")
    original = LegacyError("original body error")
    real_unlink = os.unlink

    def deny_stage(path, *args, **kwargs):
        if Path(path).name.startswith(".atomic-"):
            raise PermissionError("stage is held open")
        return real_unlink(path, *args, **kwargs)

    with monkeypatch.context() as patch:
        patch.setattr(_atomic_file.os, "unlink", deny_stage)
        with pytest.raises(LegacyError) as caught:
            with atomic_output(target) as stream:
                stream.write(b"partial")
                raise original
    assert caught.value is original
    assert target.read_bytes() == b"original"
    # The deliberately denied stage remains owned by this test.
    for stage in tmp_path.glob(".atomic-*.tmp"):
        stage.unlink()


@pytest.mark.skipif(os.name != "nt", reason="plain rmtree cannot traverse this tree")
def test_real_probe_removes_its_extended_length_tree(tmp_path, monkeypatch, capsys):
    from tools import w22_atomic_probe as probe
    scratch = tmp_path / "probe-owned"
    scratch.mkdir()
    monkeypatch.setattr(probe.tempfile, "mkdtemp", lambda **kwargs: str(scratch))
    try:
        assert probe.main([]) == 0
        assert not os.path.exists(_extended(scratch))
    finally:
        # Own and clean the neutral fixture even when the delivery leaks it.
        if os.path.exists(_extended(scratch)):
            import shutil
            shutil.rmtree(_extended(scratch))
    capsys.readouterr()


def test_gate_sorts_resolved_candidate_lengths(tmp_path, monkeypatch):
    from tools import pre_push_gate as gate
    deep = tmp_path / "long-current-working-directory"
    deep.mkdir()
    monkeypatch.chdir(deep)
    monkeypatch.setenv("TEMP", ".")
    monkeypatch.delenv("TMP", raising=False)
    monkeypatch.delenv("TMPDIR", raising=False)
    monkeypatch.setattr(gate, "PROJECT_ROOT", tmp_path)
    assert gate._scratch_candidate_roots() == [str(tmp_path), str(deep)]


@pytest.mark.skipif(os.name != "nt", reason="existing Windows scratch budget")
def test_gate_rejects_over_budget_candidate_before_probe(monkeypatch):
    from tools import pre_push_gate as gate
    candidate = "C:\\" + "d" * 44
    probes = []
    monkeypatch.setattr(gate, "_probe_writable", lambda root: probes.append(root))
    with pytest.raises(RuntimeError, match="candidate path too deep") as caught:
        gate._open_scratch([candidate])
    assert "requires 61 UTF-16 units; budget 60" in str(caught.value)
    assert not probes


@pytest.mark.skipif(os.name != "nt", reason="existing Windows scratch budget")
def test_gate_uses_short_candidate_after_over_budget(tmp_path_factory):
    from tools import pre_push_gate as gate
    short = tmp_path_factory.mktemp("s")
    long = short / "long-but-still-an-existing-writable-directory"
    long.mkdir()
    scratch = gate._open_scratch([str(long), str(short)])
    try:
        assert Path(scratch.name).parent == short
        assert gate._scratch_path_units(scratch.name) <= 60
    finally:
        scratch.cleanup()
    assert list(short.iterdir()) == [long]


@pytest.mark.skipif(os.name != "nt", reason="existing Windows scratch budget")
def test_gate_reports_no_short_candidate():
    from tools import pre_push_gate as gate
    # Non-BMP characters count twice in the Windows budget.
    roots = ["C:\\" + "d" * 44, "C:\\" + "\U0001f600" * 22 + "x"]
    with pytest.raises(RuntimeError) as caught:
        gate._open_scratch(roots)
    message = str(caught.value)
    assert all(root in message for root in roots)
    assert message.count("candidate path too deep") == 2
    assert "no writable scratch root within the pytest path budget" in message


@pytest.mark.skipif(os.name != "nt", reason="existing Windows scratch budget")
def test_gate_accepts_exact_budget(tmp_path_factory):
    from tools import pre_push_gate as gate
    base = tmp_path_factory.getbasetemp()
    padding = 60 - 14 - gate._scratch_path_units(str(base)) - 1
    assert padding > 0, "reception basetemp must leave room for the exact boundary"
    root = base / ("b" * padding)
    root.mkdir()
    scratch = gate._open_scratch([str(root)])
    try:
        assert gate._scratch_path_units(scratch.name) == 60
    finally:
        scratch.cleanup()
    assert not list(root.iterdir())


@pytest.mark.skipif(os.name != "nt", reason="existing Windows scratch budget")
def test_gate_cleans_actual_scratch_if_name_reserve_changes(
        tmp_path_factory, monkeypatch):
    from tools import pre_push_gate as gate
    root = tmp_path_factory.mktemp("s")
    real_directory = gate.tempfile.TemporaryDirectory

    def longer_directory(*, prefix, dir):
        return real_directory(prefix=prefix + "x" * 30, dir=dir)

    monkeypatch.setattr(gate.tempfile, "TemporaryDirectory", longer_directory)
    with pytest.raises(RuntimeError, match="created scratch path too deep"):
        gate._open_scratch([str(root)])
    assert not list(root.iterdir())
