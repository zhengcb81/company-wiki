"""ZR-503 acceptance tests: multi-entity attribution guard — detection +
fail-closed, no cross-entity pollution.

  C1  detect_entities is a pure, hermetic function over full text +
      declared entity/security ids: multi_entity / single / unverifiable,
      with extracted company-name phrases (zero hardcoded names).
  C2  normalize wiring: multi-entity content yields
      ``detected_entities={verdict: multi_entity, ...}`` in the normalized
      frontmatter plus the ``multi_entity_attribution_needed`` quality
      flag; single / unverifiable stay flag-free.
  C3  no hardcoded company names in product code; golden-corpus anchor for
      the Changjiang comparison report (ZR-503/510 negative example) is
      referenced read-only by its frozen hash.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from company_wiki.source_catalog.entity_detection import (  # noqa: E402
    detect_entities,
    multi_entity_quality_flag,
)
from company_wiki.source_catalog.normalizer import (  # noqa: E402
    _Normalized,
    _frontmatter,
)

_CHANGJIANG_SHA256 = (
    "273d450887eff7c079b28f394c4831092fa3abbb81db86f2544cab425c2719d7"
)

COMPARISON_TEXT = (
    "紫金矿业集团股份有限公司VS陕西煤业股份有限公司，矿企两大模式之辩："
    "资源禀赋、成本曲线与资本开支对比。"
)


# ---------------------------------------------------------------------------
# C1 — pure function
# ---------------------------------------------------------------------------


def test_c1_multi_entity_comparison_report():
    verdict = detect_entities(
        COMPARISON_TEXT,
        declared_entity="紫金矿业集团股份有限公司",
        declared_security_ids=("601899",),
    )
    assert verdict["verdict"] == "multi_entity"
    evidence = verdict["evidence"]
    assert any("紫金矿业" in phrase for phrase in evidence["company_phrases"])
    assert any("陕西煤业" in phrase for phrase in evidence["company_phrases"])
    assert any("陕西煤业" in phrase for phrase in evidence["others_unrelated_to_declared"])


def test_c1_single_entity_report():
    verdict = detect_entities(
        "紫金矿业集团股份有限公司2025年年度报告",
        declared_entity="紫金矿业集团股份有限公司",
        declared_security_ids=("601899",),
    )
    assert verdict["verdict"] == "single"
    assert verdict["evidence"]["company_phrases"] == ["紫金矿业集团股份有限公司"]


def test_c1_unverifiable_no_company_phrases():
    verdict = detect_entities(
        "附件：财务报表附注 主要会计政策",
        declared_entity="紫金矿业集团股份有限公司",
    )
    assert verdict["verdict"] == "unverifiable"
    assert verdict["evidence"]["reason"] == "no_company_name_phrases"
    assert multi_entity_quality_flag(verdict["verdict"]) is None


def test_c1_no_declared_entity_with_several_phrases_is_multi():
    """No declared entity but the text names two companies => conservative
    multi_entity (attribution cannot be assumed)."""
    verdict = detect_entities(COMPARISON_TEXT)
    assert verdict["verdict"] == "multi_entity"


def test_c1_short_and_full_name_same_entity_is_single():
    """Abbreviation + full name of the SAME entity are both related to the
    declared entity => single, not a false multi."""
    verdict = detect_entities(
        "紫金矿业集团股份有限公司（简称：紫金矿业）2025年经营数据",
        declared_entity="紫金矿业集团股份有限公司",
    )
    assert verdict["verdict"] == "single"
    assert not verdict["evidence"]["others_unrelated_to_declared"]


def test_c1_quality_flag_mapping():
    assert multi_entity_quality_flag("multi_entity") == (
        "multi_entity_attribution_needed"
    )
    assert multi_entity_quality_flag("single") is None
    assert multi_entity_quality_flag("unverifiable") is None


def test_c1_hermetic_no_hardcoded_company_names():
    """Zero hardcoded company names: the product module source must not
    contain the golden corpus entity names."""
    source = Path(__file__).resolve().parents[2] / "src" / "company_wiki"
    for name in ("紫金矿业", "陕西煤业"):
        for path in (source / "source_catalog" / "entity_detection.py",):
            assert name not in path.read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# C2 — normalize wiring
# ---------------------------------------------------------------------------


def _doc(title: str, *, entity: str | None, security_ids: tuple[str, ...] = ()) -> dict:
    acquisition = {}
    if entity:
        acquisition["canonical_entity_id"] = entity
    if security_ids:
        acquisition["security_ids"] = list(security_ids)
    acquisition.setdefault("publisher", "长江证券")
    return {
        "document_id": "doc-1",
        "primary_source_id": "src-1",
        "content_sha256": "a" * 64,
        "title": title,
        "document_kind": "broker_research",
        "published_date": "2026-03-01",
        "metadata_json": {"acquisition": acquisition},
    }


def _norm(body: str, first_page_text: str | None = None) -> _Normalized:
    return _Normalized(
        body=body,
        parser_results=(),
        parser_name="pdf_page_aware_core",
        parser_version="1.0.0",
        status="completed",
        quality_flags=(),
        error=None,
        page_count=3,
        first_page_text=first_page_text,
    )


def test_c2_multi_entity_flags_frontmatter_and_quality():
    import yaml

    frontmatter = _frontmatter(
        _doc("紫金矿业VS陕西煤业，矿企两大模式之辩", entity="紫金矿业集团股份有限公司"),
        _norm(COMPARISON_TEXT, first_page_text=COMPARISON_TEXT),
    )
    payload = yaml.safe_load(frontmatter.split("---\n", 2)[1])
    assert payload["detected_entities"]["verdict"] == "multi_entity"
    assert "multi_entity_attribution_needed" in payload["quality_flags"]


def test_c2_single_no_flag():
    import yaml

    frontmatter = _frontmatter(
        _doc("紫金矿业2025年年度报告", entity="紫金矿业集团股份有限公司"),
        _norm("紫金矿业集团股份有限公司2025年年度报告"),
    )
    payload = yaml.safe_load(frontmatter.split("---\n", 2)[1])
    assert payload["detected_entities"]["verdict"] == "single"
    assert "multi_entity_attribution_needed" not in payload["quality_flags"]


def test_c2_unverifiable_no_flag_no_fabrication():
    import yaml

    frontmatter = _frontmatter(
        _doc("某公司深度报告", entity="紫金矿业集团股份有限公司"),
        _norm("本报告仅为内部研究参考，不构成投资建议。"),
    )
    payload = yaml.safe_load(frontmatter.split("---\n", 2)[1])
    assert payload["detected_entities"]["verdict"] == "unverifiable"
    assert "multi_entity_attribution_needed" not in payload["quality_flags"]


def test_c2_zr501_zr502_fields_coexist_with_detection():
    """page_count (ZR-501) and homepage_identity (ZR-502) still present
    alongside detected_entities (ZR-503)."""
    import yaml

    frontmatter = _frontmatter(
        _doc("紫金矿业VS陕西煤业，矿企两大模式之辩", entity="紫金矿业集团股份有限公司"),
        _norm(COMPARISON_TEXT, first_page_text="紫金矿业集团股份有限公司VS陕西煤业股份有限公司"),
    )
    payload = yaml.safe_load(frontmatter.split("---\n", 2)[1])
    assert payload["page_count"] == 3
    assert "homepage_identity" in payload
    assert payload["detected_entities"]["verdict"] == "multi_entity"


# ---------------------------------------------------------------------------
# C3 — zero hardcoding + golden-corpus anchor (read-only)
# ---------------------------------------------------------------------------


def test_c3_golden_corpus_changjiang_anchor_is_frozen():
    """The Changjiang comparison report is the registered multi-entity
    negative example (ZR-503/510); only its frozen hash is referenced —
    the original is never pulled into the repos."""
    corpus = json.loads(
        (
            Path(__file__).resolve().parents[2]
            / ".."
            / "revenue-forecast"
            / "assurance"
            / "unified_completion"
            / "corpus"
            / "golden_corpus.json"
        ).read_text(encoding="utf-8")
    )
    changjiang = next(
        item
        for item in corpus["samples"]
        if item["sample_id"] == "zijin_broker_20240304_changjiang"
    )
    assert changjiang["sha256"] == _CHANGJIANG_SHA256
    assert changjiang["role"] == "broker_research"
    assert set(changjiang["entities"]) == {
        "紫金矿业集团股份有限公司",
        "陕西煤业股份有限公司",
    }


def test_c3_changjiang_shape_text_is_detected_multi_entity():
    """A text shaped like the Changjiang report (declared entity vs other
    entity) is never silently attributed to one issuer."""
    verdict = detect_entities(
        COMPARISON_TEXT,
        declared_entity="紫金矿业集团股份有限公司",
    )
    assert verdict["verdict"] == "multi_entity"
    assert multi_entity_quality_flag(verdict["verdict"]) == (
        "multi_entity_attribution_needed"
    )


if __name__ == "__main__":
    pytest.main([__file__, "-q"])
