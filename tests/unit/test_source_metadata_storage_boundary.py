"""Source policy consumes named facts and write operations, not a SQL client."""
import ast
from pathlib import Path
from types import SimpleNamespace

from company_wiki.source_catalog import assertion_service


def test_assertion_resolution_uses_only_its_named_owner_read_port():
    prior = {"assertion_id": "1", "source_id": "source", "document_id": "doc",
             "content_sha256": "digest", "supersedes_assertion_id": None}
    current = {**prior, "assertion_id": "2", "supersedes_assertion_id": "1"}

    class Port:
        def visible_verified(self, identity, *, by_document, reader, current_epoch, active_cohorts):
            assert (identity, by_document, reader, current_epoch, active_cohorts) == (
                "source", False, "steady", None, (),
            )
            return [current, prior]

    reader = SimpleNamespace(assertions=Port())
    assert assertion_service.get_verified_assertion(reader, "source", "digest", reader="steady") == current


def test_source_policy_does_not_use_generic_sql_methods():
    source_dir = Path(assertion_service.__file__).parent
    drivers = {"execute", "fetchall", "fetchone", "transaction"}
    for filename in ("assertion_service.py", "canonical_writer.py"):
        tree = ast.parse((source_dir / filename).read_text(encoding="utf-8"))
        bypasses = [
            node.lineno for node in ast.walk(tree)
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
            and node.func.attr in drivers
        ]
        assert not bypasses, f"{filename} uses raw storage at {bypasses}"
