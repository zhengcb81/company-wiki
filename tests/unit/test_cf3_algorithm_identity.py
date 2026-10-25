"""A source algorithm change must reach the existing selection/cache identity."""
from pathlib import Path
import tempfile

from company_wiki.document_understanding import decision_inventory
from company_wiki.document_understanding.structure import relations


def test_relation_owner_change_invalidates_current_decision_identity(monkeypatch):
    owner = Path(relations.__file__).resolve()
    original = Path.read_bytes
    before = decision_inventory._versions()["business_algorithms"]

    def changed(path):
        value = original(path)
        return value + b"\n# hypothetical source upgrade\n" if path.resolve() == owner else value

    monkeypatch.setattr(Path, "read_bytes", changed)
    assert decision_inventory._versions()["business_algorithms"] != before


def test_structure_owner_closure_tracks_new_modules_and_ignores_host_location():
    with tempfile.TemporaryDirectory(prefix="cf3-identity-") as name:
        root = Path(name)
        first, second = root / "one", root / "different-host-folder"
        first.mkdir()
        second.mkdir()
        for directory in (first, second):
            (directory / "__init__.py").write_bytes(b"# owner\n")
        initial = decision_inventory._structure_algorithm_hashes(first)
        assert initial == decision_inventory._structure_algorithm_hashes(second)
        (first / "new_relation.py").write_bytes(b"# added source rule\n")
        assert decision_inventory._structure_algorithm_hashes(first) != initial
        (first / "notes.txt").write_bytes(b"not runtime code")
        before = decision_inventory._structure_algorithm_hashes(first)
        (first / "notes.txt").write_bytes(b"changed incidental text")
        assert decision_inventory._structure_algorithm_hashes(first) == before
