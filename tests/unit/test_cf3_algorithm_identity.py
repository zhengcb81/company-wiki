"""A source algorithm change must reach the existing selection/cache identity."""
from pathlib import Path
import tempfile

from company_wiki.document_understanding import decision_inventory
from company_wiki.document_understanding.structure import relations
from company_wiki.source_catalog import narrative_decision_inventory as inventory_owner


def test_relation_owner_change_invalidates_current_decision_identity(monkeypatch):
    from company_wiki.automation.narrative_generation import current_reading_decision_matches
    from company_wiki.document_understanding.decision_dependencies import freeze_decision_dependencies
    from unit.document_understanding_selection.test_reading_decision_inventory import _real_interim_pipeline

    owner = Path(relations.__file__).resolve()
    original = Path.read_bytes
    before = decision_inventory._versions()["business_algorithms"]
    observed = _real_interim_pipeline()
    observed["observation"]["metadata"]["mime_type"] = "text/plain"
    frozen = freeze_decision_dependencies(decision_inventory.build_decision_trace(observed))
    assert frozen["status"] == "complete"
    manifest = {"reading_dependencies": frozen,
                "selection_generation": {"decision_digest": frozen["decision_digest"]}}
    assert current_reading_decision_matches(manifest)

    def changed(path):
        value = original(path)
        return value + b"\n# hypothetical source upgrade\n" if path.resolve() == owner else value

    monkeypatch.setattr(Path, "read_bytes", changed)
    assert decision_inventory._versions()["business_algorithms"] != before
    assert not current_reading_decision_matches(manifest)


def test_structure_owner_closure_tracks_new_modules_and_ignores_host_location():
    with tempfile.TemporaryDirectory(prefix="cf3-identity-") as name:
        root = Path(name)
        first, second = root / "one", root / "different-host-folder"
        first.mkdir()
        second.mkdir()
        for directory in (first, second):
            (directory / "__init__.py").write_bytes(b"# owner\n")
        initial = inventory_owner._structure_algorithm_hashes(first)
        assert initial == inventory_owner._structure_algorithm_hashes(second)
        (first / "new_relation.py").write_bytes(b"# added source rule\n")
        assert inventory_owner._structure_algorithm_hashes(first) != initial
        (first / "notes.txt").write_bytes(b"not runtime code")
        before = inventory_owner._structure_algorithm_hashes(first)
        (first / "notes.txt").write_bytes(b"changed incidental text")
        assert inventory_owner._structure_algorithm_hashes(first) == before
