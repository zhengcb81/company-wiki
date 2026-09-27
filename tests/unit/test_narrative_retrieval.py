from __future__ import annotations

import hashlib
from dataclasses import replace
from pathlib import Path
from typing import Any

import pytest

from company_wiki.source_catalog.narrative_retrieval import (
    NARRATIVE_EVIDENCE_BUNDLE_SCHEMA_VERSION,
    NARRATIVE_REPLAY_CONTRACT_SCHEMA_VERSION,
    NarrativeEvidenceResolveError,
    NarrativeEvidenceResolver,
    NarrativeEvidenceSearch,
    NarrativeEvidenceSearchError,
)
from company_wiki.source_catalog.narrative_evidence import (
    NARRATIVE_PARSER_NAME,
    NARRATIVE_PARSER_VERSION,
    NARRATIVE_SELECTOR_NAME,
    NARRATIVE_SELECTOR_VERSION,
    parse_transcript_text,
    select_narrative_evidence,
)
from company_wiki.source_contract import source_id_for_sha256


def _record(
    sample_id: str,
    text: str,
    *,
    status: str = "selected",
    coverage_complete: bool = True,
    evidence_ids: list[str] | None = None,
    locators: list[str] | None = None,
    summary_scope: str = "selected_evidence_only",
) -> dict[str, Any]:
    source_sha256 = hashlib.sha256(sample_id.encode("utf-8")).hexdigest()
    return {
        "sample_id": sample_id,
        "title": sample_id,
        "selection_status": status,
        "coverage_complete": coverage_complete,
        "summary_input": {
            "schema_version": "narrative-summary-input/0.2.0",
            "source_id": f"urn:company-wiki:source:sha256:{source_sha256}",
            "source_sha256": source_sha256,
            "document_kind": "annual_report",
            "summary_scope": summary_scope,
            "evidence": [
                {
                    "evidence_id": (evidence_ids or [f"evidence-{sample_id}"])[0],
                    "evidence_ids": evidence_ids or [f"evidence-{sample_id}"],
                    "locator": (locators or [f"loc:v1/page:{len(sample_id)}/paragraph:0"])[0],
                    "locators": locators or [f"loc:v1/page:{len(sample_id)}/paragraph:0"],
                    "context_group_id": f"group-{sample_id}",
                    "raw_text": text,
                }
            ],
        },
    }


def _search(*records: dict[str, Any]) -> NarrativeEvidenceSearch:
    return NarrativeEvidenceSearch(
        {
            "schema_version": NARRATIVE_EVIDENCE_BUNDLE_SCHEMA_VERSION,
            "sources": list(records),
        }
    )


def _transcript_bundle(tmp_path: Path) -> tuple[dict[str, Any], Path]:
    raw_text = (
        "Editorial summary: demand is rising.\n\n"
        "Full Conference Call Transcript\n"
        "CEO: We launched a new product and expanded overseas capacity.\n\n"
        "Questions & Answers\n"
        "Analyst: Is the new product ready for commercial launch?\n\n"
        "CEO: It is too early to speculate on launch, though customer validation continues.\n"
    )
    raw_path = tmp_path / "transcript.txt"
    raw_path.write_bytes(raw_text.encode("utf-8"))
    source_sha256 = hashlib.sha256(raw_path.read_bytes()).hexdigest()
    source_id = source_id_for_sha256(source_sha256)
    parsed = parse_transcript_text(
        raw_text,
        source_id=source_id,
        source_sha256=source_sha256,
        language="en",
    )
    package = select_narrative_evidence(
        parsed,
        title="Example earnings call transcript.txt",
        existing_kind="investor_call_transcript",
    )
    record = {
        "sample_id": "T-UNIT",
        "title": "Example earnings call transcript.txt",
        "selection_status": package.status,
        "coverage_complete": package.coverage_complete,
        "replay_contract": {
            "schema_version": NARRATIVE_REPLAY_CONTRACT_SCHEMA_VERSION,
            "source_format": "transcript_txt",
            "language": "en",
            "existing_kind": "investor_call_transcript",
            "parser_name": NARRATIVE_PARSER_NAME,
            "parser_version": NARRATIVE_PARSER_VERSION,
            "parser_options": {},
            "selector_name": NARRATIVE_SELECTOR_NAME,
            "selector_version": NARRATIVE_SELECTOR_VERSION,
            "max_selected": package.selection_limit,
        },
        "summary_input": package.summary_input(),
    }
    bundle = {
        "schema_version": NARRATIVE_EVIDENCE_BUNDLE_SCHEMA_VERSION,
        "sources": [record],
    }
    return bundle, raw_path


def test_two_character_chinese_query_returns_source_anchors_and_partial_status() -> None:
    evidence = _record(
        "P02",
        "公司持续推进出海布局，新增欧洲客户验证。",
        status="partial",
        coverage_complete=False,
        evidence_ids=["span-a", "span-b"],
        locators=["loc:v1/page:21/paragraph:4", "loc:v1/page:21/paragraph:5"],
    )

    hits = _search(evidence).search("出海")

    assert len(hits) == 1
    assert hits[0].source_id == evidence["summary_input"]["source_id"]
    assert hits[0].source_sha256 == evidence["summary_input"]["source_sha256"]
    assert hits[0].selection_status == "partial"
    assert hits[0].coverage_complete is False
    assert hits[0].evidence_ids == ("span-a", "span-b")
    assert hits[0].locators == (
        "loc:v1/page:21/paragraph:4",
        "loc:v1/page:21/paragraph:5",
    )
    assert hits[0].phrase_match is True


def test_exact_chinese_phrase_ranks_ahead_of_disjoint_bigram_matches() -> None:
    exact = _record("exact", "新建中试线已经投产并开始客户验证。")
    disjoint = _record("disjoint", "中试项目完成审批；后续试线尚未通过。")

    hits = _search(disjoint, exact).search("中试线")

    assert len(hits) == 2
    assert hits[0].source_id == exact["summary_input"]["source_id"]
    assert hits[0].phrase_match is True
    assert hits[1].phrase_match is False


def test_english_query_is_case_insensitive_and_preserves_original_excerpt() -> None:
    evidence = _record("T02", "Too early to speculate about this customer ramp.")

    hits = _search(evidence).search("TOO EARLY TO SPECULATE")

    assert len(hits) == 1
    assert hits[0].phrase_match is True
    assert hits[0].snippet.startswith("Too early")
    assert hits[0].document_kind == "annual_report"


def test_blocked_and_skipped_sources_are_not_searchable_but_review_state_is_visible() -> None:
    visible = _record("review", "客户确认进入送样阶段。", status="needs_review")
    blocked = _record("blocked", "出海进展", status="blocked")
    skipped = _record("skip", "出海进展", status="skipped_no_narrative")

    search = _search(visible, blocked, skipped)

    assert search.indexed_group_count == 1
    hits = search.search("送样")
    assert len(hits) == 1
    assert hits[0].selection_status == "needs_review"


def test_full_document_scope_is_rejected() -> None:
    evidence = _record("bad", "公司主营业务", summary_scope="full_document")

    with pytest.raises(NarrativeEvidenceSearchError, match="selected evidence"):
        _search(evidence)


def test_each_evidence_id_must_have_one_locator() -> None:
    evidence = _record(
        "bad",
        "公司主营业务",
        evidence_ids=["span-a", "span-b"],
        locators=["loc:v1/page:1/paragraph:0"],
    )

    with pytest.raises(NarrativeEvidenceSearchError, match="exactly one locator"):
        _search(evidence)


def test_empty_query_and_result_limit_are_handled_explicitly() -> None:
    search = _search(
        _record("one", "海外拓展持续推进。"),
        _record("two", "海外客户已完成验证。"),
    )

    assert search.search("   ") == ()
    assert len(search.search("海外", limit=1)) == 1
    with pytest.raises(ValueError, match="positive integer"):
        search.search("海外", limit=0)


def test_resolver_replays_selected_transcript_group_from_hashed_raw(tmp_path: Path) -> None:
    bundle, raw_path = _transcript_bundle(tmp_path)
    search = NarrativeEvidenceSearch(bundle)
    hits = search.search("expanded overseas")
    assert hits
    resolver = NarrativeEvidenceResolver(
        bundle,
        raw_paths_by_source_id={hits[0].source_id: raw_path},
    )

    resolved = resolver.resolve(hits[0])

    assert resolved.source_id == hits[0].source_id
    assert resolved.source_sha256 == hits[0].source_sha256
    assert resolved.evidence_ids == hits[0].evidence_ids
    assert resolved.locators == hits[0].locators
    assert resolved.raw_text_sha256 == hashlib.sha256(
        resolved.raw_text.encode("utf-8")
    ).hexdigest()
    assert "expanded overseas" in resolved.raw_text
    assert resolved.selection_status in {"selected", "partial", "needs_review"}


def test_resolver_fails_closed_when_raw_source_hash_changes(tmp_path: Path) -> None:
    bundle, raw_path = _transcript_bundle(tmp_path)
    hit = NarrativeEvidenceSearch(bundle).search("expanded overseas")[0]
    resolver = NarrativeEvidenceResolver(
        bundle,
        raw_paths_by_source_id={hit.source_id: raw_path},
    )
    raw_path.write_text("replacement content", encoding="utf-8")

    with pytest.raises(NarrativeEvidenceResolveError, match="SHA-256"):
        resolver.resolve(hit)


def test_resolver_rejects_a_hit_with_forged_locator(tmp_path: Path) -> None:
    bundle, raw_path = _transcript_bundle(tmp_path)
    hit = NarrativeEvidenceSearch(bundle).search("expanded overseas")[0]
    resolver = NarrativeEvidenceResolver(
        bundle,
        raw_paths_by_source_id={hit.source_id: raw_path},
    )

    with pytest.raises(NarrativeEvidenceResolveError, match="exact package group"):
        resolver.resolve(replace(hit, locators=("loc:v1/page:999/paragraph:1",)))


def test_resolver_rejects_package_text_tampering(tmp_path: Path) -> None:
    bundle, raw_path = _transcript_bundle(tmp_path)
    row = bundle["sources"][0]["summary_input"]["evidence"][0]
    row["raw_text"] = "A forged claim about a completed launch."
    hit = NarrativeEvidenceSearch(bundle).search("forged claim")[0]
    resolver = NarrativeEvidenceResolver(
        bundle,
        raw_paths_by_source_id={hit.source_id: raw_path},
    )

    with pytest.raises(NarrativeEvidenceResolveError, match="package evidence text hash"):
        resolver.resolve(hit)


def test_resolver_rejects_unknown_selector_contract(tmp_path: Path) -> None:
    bundle, raw_path = _transcript_bundle(tmp_path)
    bundle["sources"][0]["replay_contract"]["selector_version"] = "9.9.9"
    hit = NarrativeEvidenceSearch(bundle).search("expanded overseas")[0]
    resolver = NarrativeEvidenceResolver(
        bundle,
        raw_paths_by_source_id={hit.source_id: raw_path},
    )

    with pytest.raises(NarrativeEvidenceResolveError, match="selector version"):
        resolver.resolve(hit)
