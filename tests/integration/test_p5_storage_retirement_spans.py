"""S5 completed: its one-off span DELETE is no longer a supported writer.

No parser lifecycle can safely be inferred from its name; current and unknown
parsers have identical retirement behavior and never open the database.
"""
from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "tools"))

from legacy_storage.spans import run_prune_spans  # noqa: E402


@pytest.mark.parametrize("parser", ["plain_text", "current_parser", "future_parser_9", None])
@pytest.mark.parametrize("dry_run", [True, False])
def test_completed_prune_has_no_catalog_access(parser, dry_run):
    class NoCatalogIO:
        def __getattr__(self, name):
            raise AssertionError(f"unexpected catalog access: {name}")

    result = run_prune_spans(NoCatalogIO(), {"parser_name": parser}, dry_run=dry_run)
    assert result["status"] == "retired"
    assert result["deleted"] == 0
    assert result["dry_run"] is dry_run
