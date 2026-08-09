"""WU-404 RED/audit tests: legacy bridge + visibility separation (VIS-01..05)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))
from company_wiki.source_catalog.visibility_bridge import (  # noqa: E402
    active_assertions,
    legacy_bridge_candidate,
    set_visibility,
)


def _assertion(**overrides) -> dict:
    base = {
        "assertion_id": "a1",
        "visibility_state": "legacy",
        "activation_epoch": None,
        "decision": "verified",
        "adapter_id": "sidecar_filing_v1",
    }
    base.update(overrides)
    return base


def test_vis01_v1_reader_ignores_shadow():
    rows = [
        _assertion(assertion_id="a-legacy", visibility_state="legacy"),
        _assertion(assertion_id="a-shadow", visibility_state="shadow"),
    ]
    visible = active_assertions(rows, reader="v1")
    assert {r["assertion_id"] for r in visible} == {"a-legacy"}


def test_vis02_v2_reader_ignores_unactivated():
    rows = [
        _assertion(assertion_id="a-active", visibility_state="active",
                   activation_epoch="epoch-2"),
        _assertion(assertion_id="a-shadow", visibility_state="shadow"),
    ]
    visible = active_assertions(rows, reader="v2", current_epoch="epoch-2")
    assert {r["assertion_id"] for r in visible} == {"a-active"}


def test_vis02b_v2_reader_ignores_wrong_epoch():
    rows = [
        _assertion(assertion_id="a-old", visibility_state="active",
                   activation_epoch="epoch-1"),
    ]
    assert active_assertions(rows, reader="v2", current_epoch="epoch-2") == []


def test_vis04_rollback_switches_visibility_not_delete():
    rows = [
        _assertion(assertion_id="a1", visibility_state="active",
                   activation_epoch="epoch-2"),
    ]
    rolled = set_visibility(rows, "a1", "legacy")
    assert rolled[0]["visibility_state"] == "legacy"
    assert len(rolled) == 1  # record kept, only visibility flipped


def test_legacy_bridge_produces_v2_candidate():
    legacy = {
        "acquisition": {
            "fiscal_year": 2025,
            "form_type": "annual",
            "source_url": "https://x/2025",
            "provider": "example",
        },
        "dayu_meta": None,
    }
    candidate = legacy_bridge_candidate(legacy)
    assert candidate["fiscal_year"] == "2025"
    assert candidate["document_kind"] == "annual"
    assert candidate["source_url"] == "https://x/2025"
    assert candidate["schema_version"] == "2.0"
