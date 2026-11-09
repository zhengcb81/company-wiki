"""A source algorithm change must reach the existing selection/cache identity."""
from pathlib import Path

from company_wiki.source_catalog import narrative_decision_inventory as decision_inventory
from company_wiki.document_understanding.structure import relations


def test_relation_owner_change_invalidates_current_decision_identity(monkeypatch):
    from company_wiki.automation.narrative_generation import current_reading_decision_matches
    from company_wiki.document_understanding.decision_dependencies import freeze_decision_dependencies
    from unit.document_understanding_selection.test_reading_decision_inventory import _real_interim_pipeline

    owner = Path(relations.__file__).resolve()
    original = Path.read_bytes
    before = decision_inventory.decision_versions()["business_algorithms"]
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
    assert decision_inventory.decision_versions()["business_algorithms"] != before
    assert not current_reading_decision_matches(manifest)


def test_structure_owner_closure_tracks_new_modules_and_ignores_host_location(tmp_path, monkeypatch):
    from company_wiki.document_understanding import structure
    from company_wiki.document_understanding.reading_identity import reading_algorithm_hashes

    first, second = tmp_path / "one", tmp_path / "different-host-folder"
    for directory in (first, second):
        directory.mkdir()
        (directory / "__init__.py").write_bytes(b"# owner\n")

    def hashes_at(directory):
        monkeypatch.setattr(structure, "__path__", [str(directory)])
        return reading_algorithm_hashes(pdf_frontend=False)

    initial = hashes_at(first)
    assert hashes_at(second) == initial
    (first / "new_relation.py").write_bytes(b"raise RuntimeError('hashing must not import me')\n")
    before = hashes_at(first)
    assert before.keys() - initial.keys() == {"company_wiki.document_understanding.structure.new_relation"}
    (first / "notes.txt").write_bytes(b"not runtime code")
    assert hashes_at(first) == before
