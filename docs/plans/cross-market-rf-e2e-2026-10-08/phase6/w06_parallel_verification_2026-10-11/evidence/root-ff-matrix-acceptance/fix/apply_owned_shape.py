from pathlib import Path
ROOT = Path('C:/Users/郑曾波/Projects/_harness_worktrees/w06/ff-contract-matrix-root')
p = ROOT / 'tools/offline_contract_matrix/runtime.py'
s = p.read_text(encoding='utf-8')
s = s.replace('    before_out: dict\n', '    before_out: dict\n    owned_existed: bool\n    out_existed: bool\n    created_owned_dirs: list[Path]\n')
s = s.replace('        before_owned, before_out = _children_metadata(owned_parent), _children_metadata(out_parent)', '''        if owned_parent == out_parent:
            raise ValueError("scratch and retained output parents must differ")
        owned_existed, out_existed = owned_parent.exists(), out_parent.exists()
        before_owned, before_out = _children_metadata(owned_parent), _children_metadata(out_parent)
        created_owned_dirs = []
        created_out_dirs = []
        def mkdir_chain(parent, record):
            missing = []
            while not parent.exists():
                missing.append(parent)
                parent = parent.parent
            for item in reversed(missing):
                item.mkdir()
                record.append(item)''')
s = s.replace('            owned_parent.mkdir(parents=True, exist_ok=True)\n            out_parent.mkdir(parents=True, exist_ok=True)', '            mkdir_chain(owned_parent, created_owned_dirs)\n            mkdir_chain(out_parent, created_out_dirs)')
s = s.replace('return cls(scratch, output, owned_parent, out_parent, before_owned, before_out)', 'return cls(scratch, output, owned_parent, out_parent, before_owned, before_out, owned_existed, out_existed, created_owned_dirs)')
s = s.replace('            raise\n\n    def cleanup', '''            for item in reversed(created_out_dirs + created_owned_dirs):
                if item.exists() and not any(item.iterdir()):
                    item.rmdir()
            raise

    def cleanup''')
s = s.replace('        return {"scratch_torn_down": not self.scratch.exists(),', '''        for item in reversed(self.created_owned_dirs):
            if item.exists() and not any(item.iterdir()):
                item.rmdir()
        shape_preserved = self.owned_parent.exists() == self.owned_existed
        return {"owned_parent_shape_preserved":shape_preserved,
                "output_parent_initially_existed":self.out_existed,
                "retained_output_is_explicit_evidence":True,
                "scratch_torn_down": not self.scratch.exists(),''')
s = s.replace('"restored": preserved and not self.scratch.exists()', '"restored": preserved and shape_preserved and not self.scratch.exists()')
p.write_text(s, encoding='utf-8')
p = ROOT / 'tests/test_w06_matrix_runtime.py'
s = p.read_text(encoding='utf-8') + '''

def test_owned_absent_and_existing_empty_parent_shapes_restore(tmp_path):
    import runtime
    absent = tmp_path / "absent/nested"
    out = tmp_path / "retained"
    first = runtime.OwnedAttempt.create(absent, out)
    restore = first.cleanup()
    assert restore["restored"]
    assert not absent.exists() and not absent.parent.exists()
    assert first.output.is_dir()
    empty = tmp_path / "existing-empty"
    empty.mkdir()
    second = runtime.OwnedAttempt.create(empty, out)
    assert second.cleanup()["restored"]
    assert empty.is_dir() and not list(empty.iterdir())

def test_initialization_failure_restores_only_created_items(tmp_path):
    import runtime
    import pytest
    owned = tmp_path / "existing-empty"
    owned.mkdir()
    out = tmp_path / "new-output"
    original_mkdir = Path.mkdir
    def fail_output(path, *args, **kwargs):
        if path.parent == out and path.name.startswith("attempt-"):
            raise OSError("synthetic output initialization failure")
        return original_mkdir(path, *args, **kwargs)
    with patch.object(Path, "mkdir", fail_output):
        with pytest.raises(OSError):
            runtime.OwnedAttempt.create(owned, out)
    assert owned.is_dir() and not list(owned.iterdir())
    assert not out.exists()
'''
p.write_text(s, encoding='utf-8')
