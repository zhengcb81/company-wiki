"""WU-802 RED/audit tests: multi-location switch (canonical location fallback).

Same document content on two roots: one handle is returned with the
preferred location; if the preferred location's file is missing, the
resolver switches to the other valid location instead of failing or
downloading.  Ranking keys never contain source-type names.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))
from company_wiki.source_catalog import resolver as _resolver  # noqa: E402
_pick_latest = staticmethod(_resolver.SourceResolver._pick_latest)


class _H:
    def __init__(self, published_date, provider_document_id, source_id):
        self.published_date = published_date
        self.provider_document_id = provider_document_id
        self.source_id = source_id


def test_ranking_key_has_no_source_names():
    """WU-802: the ranking key must be source-type agnostic."""
    import inspect

    source = inspect.getsource(_pick_latest)
    for banned in ("company_raw", "dayu_portfolio", "dropbox_stock", "kind"):
        assert banned not in source, f"ranking key mentions {banned}"


def test_pick_latest_deterministic_tiebreak():
    handles = [
        _H("2026-04-15", "acc-1", "s1"),
        _H("2026-04-15", "acc-2", "s2"),
    ]
    chosen = _pick_latest(handles, "2026-12-31")
    assert chosen.provider_document_id == "acc-2"  # lexicographic tiebreak


def test_pick_latest_respects_as_of():
    handles = [
        _H("2026-04-15", "acc-1", "s1"),
        _H("2027-01-01", "acc-2", "s2"),
    ]
    chosen = _pick_latest(handles, "2026-12-31")
    assert chosen.provider_document_id == "acc-1"  # future handle excluded


def test_pick_latest_none_when_all_future():
    handles = [_H("2027-01-01", "acc-2", "s2")]
    assert _pick_latest(handles, "2026-12-31") is None
