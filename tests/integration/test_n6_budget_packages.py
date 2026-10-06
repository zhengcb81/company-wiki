"""N6-BUDGET integration: real原文 candidates through finalize to summary input."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from company_wiki.source_catalog.n6_budget_dedup import deduplicate_candidates
from company_wiki.source_catalog.narrative_budget import budget_diagnostics
from company_wiki.source_catalog.narrative_candidates import EvidenceCandidate
from company_wiki.source_catalog.narrative_document import DocumentStructure
from company_wiki.source_catalog.narrative_finalize import finalize_selection
from company_wiki.source_catalog.narrative_evidence import _HEADING_ONLY, _make_unit
from company_wiki.source_catalog.narrative_routing import route_document
from company_wiki.source_contract import EvidenceCoordinates

REPO_ROOT = Path(__file__).resolve().parents[2]
FIXTURE_PATH = REPO_ROOT / "tests" / "fixtures" / "n6_budget" / "real_candidates.json"
MANIFEST_PATH = REPO_ROOT / "benchmarks" / "narrative_document_types" / "samples.json"
INVESTMENT_KEYS = {
    "target_price",
    "rating",
    "position",
    "valuation",
    "sotp",
    "buy",
    "sell",
    "overweight",
    "underweight",
    "price_target",
    "investment_conclusion",
}


@pytest.fixture(scope="module")
def payload() -> dict:
    return json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def registered() -> dict[str, dict]:
    rows = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))["samples"]
    return {row["sample_id"]: row for row in rows}


def _coordinates(rec: dict) -> EvidenceCoordinates:
    return EvidenceCoordinates(
        page_number=rec["page"],
        paragraph_index=rec["paragraph"],
        table_index=rec["table"],
        row_index=rec["row"],
        column_index=rec["column"],
        char_start=rec["char_start"],
        char_end=rec["char_end"],
    )


def _unit(rec: dict, source_id: str):
    return _make_unit(
        source_id=source_id,
        parser_version=rec["parser_version"],
        coordinates=_coordinates(rec),
        raw_text=rec["text"],
        unit_kind=rec["unit_kind"],
        source_role=rec["source_role"],
        language=rec["language"],
        metadata={},
        quality_flags=rec["quality_flags"],
    )


def _candidate(rec: dict, source_id: str) -> EvidenceCandidate:
    return EvidenceCandidate(
        _unit(rec, source_id),
        tuple(rec["topics"]),
        tuple(rec["reasons"]),
        rec["score"],
    )


def _structure(sample: dict) -> DocumentStructure:
    source_id = sample["source_id"]
    units = tuple(_unit(rec, source_id) for rec in sample["units"])
    page_count = max(rec["page"] for rec in sample["units"])
    return DocumentStructure(
        source_id=sample["source_id"],
        source_sha256=sample["source_sha256"],
        language="zh",
        units=units,
        page_count=page_count,
        pages_read=page_count,
    )


def _finalize(sample: dict, *, reverse: bool = False):
    source_id = sample["source_id"]
    candidates = [_candidate(rec, source_id) for rec in sample["units"]]
    if reverse:
        candidates = list(reversed(candidates))
    group_ids = {
        rec["unit_id"]: rec["group_id"]
        for rec in sample["units"]
        if rec["group_id"] is not None
    }
    route = route_document(sample["title"], existing_kind=sample["existing_kind"])
    package = finalize_selection(
        _structure(sample),
        route,
        tuple(candidates),
        group_ids=group_ids,
        heading_pattern=_HEADING_ONLY,
        dropped_financial_count=0,
    )
    return package, tuple(candidates), group_ids, route


def _key(unit_or_span) -> tuple:
    coordinates = unit_or_span.coordinates
    return (
        coordinates.page_number,
        coordinates.paragraph_index,
        coordinates.table_index,
        coordinates.row_index,
        coordinates.column_index,
        unit_or_span.raw_text,
    )


def test_fixture_carries_registered_original_identity(payload, registered) -> None:
    provenance = payload["provenance"]
    assert (
        provenance["real_vs_fixture"] == "real_original_text_hand_assembled_candidates"
    )
    assert "NOT the production parser" in provenance["note"]

    for sample in payload["samples"]:
        row = registered[sample["sample_id"]]
        assert sample["source_sha256"] == row["sha256"]
        assert sample["registered_sha256"] == row["sha256"]
        assert sample["source_id"].endswith(row["sha256"])
        for rec in sample["units"]:
            digest = hashlib.sha256(rec["text"].encode("utf-8")).hexdigest()
            assert digest == rec["text_sha256"]
            unit = _unit(rec, sample["source_id"])
            assert unit.unit_id == rec["unit_id"]
            assert unit.raw_text == rec["text"]


def test_finalize_preserves_source_identity_locators_and_roles(payload) -> None:
    for sample in payload["samples"]:
        package, candidates, _group_ids, route = _finalize(sample)

        assert package.source_id == sample["source_id"]
        assert package.source_sha256 == sample["source_sha256"]
        assert package.document_kind == sample["document_kind"]
        assert (
            package.selection_limit
            == sample["selection_limit"]
            == route.selection_limit
        )
        assert len(package.evidence_spans) <= package.selection_limit

        unit_by_key = {_key(candidate.unit): candidate.unit for candidate in candidates}
        keys = []
        for span in package.evidence_spans:
            unit = unit_by_key[_key(span)]
            assert span.locator == unit.coordinates.locator()
            assert span.raw_text == unit.raw_text
            assert span.structured_value["source_role"] == unit.source_role
            assert span.structured_value["text_sha256"] == unit.text_sha256
            assert span.structured_value["language"] == unit.language
            keys.append(span.locator)
        assert keys == sorted(keys)
        assert len(keys) == len(set(keys))


def test_counts_are_truthful_and_never_hide_deduplication(payload) -> None:
    saw_dedup = False
    for sample in payload["samples"]:
        package, candidates, group_ids, _route = _finalize(sample)
        dedup = deduplicate_candidates(candidates, group_ids)

        assert package.candidate_count == len(candidates)
        assert package.omitted_candidate_count == (
            package.candidate_count - len(package.evidence_spans)
        )
        assert package.source_units == len(sample["units"])
        assert len(dedup.candidates) + len(dedup.drops) == len(candidates)
        assert package.candidate_count - len(dedup.candidates) == len(dedup.drops)
        assert set(dedup.group_ids) <= {
            candidate.unit.unit_id for candidate in dedup.candidates
        }

        kept_texts = {
            "".join(candidate.unit.raw_text.split()) for candidate in dedup.candidates
        }
        for drop in dedup.drops:
            source = next(
                candidate
                for candidate in candidates
                if candidate.unit.unit_id == drop.unit_id
            )
            normalized = "".join(source.unit.raw_text.split())
            assert normalized in kept_texts, (
                f"{sample['sample_id']}: dedup dropped unique content"
            )
            assert drop.locator
            assert drop.text_sha256 == source.unit.text_sha256
        if dedup.drops:
            saw_dedup = True
            diagnostics = budget_diagnostics(
                tuple(_budget_item(candidate, dedup) for candidate in dedup.candidates),
                limit=package.selection_limit,
            )
            assert {row.reason for row in diagnostics} <= {
                "group_exceeds_limit",
                "budget_full",
            }
    assert saw_dedup, "fixture must contain real duplicate candidates"


def _budget_item(candidate: EvidenceCandidate, dedup):
    from company_wiki.source_catalog.narrative_budget import BudgetItem

    unit = candidate.unit
    coordinates = unit.coordinates
    return BudgetItem(
        item_id=unit.unit_id,
        group_id=dedup.group_ids.get(unit.unit_id),
        page_key=("page", coordinates.page_number),
        locator=coordinates.locator(),
        order_key=tuple(
            -1 if value is None else value
            for value in (
                coordinates.page_number,
                coordinates.paragraph_index,
                coordinates.table_index,
                coordinates.row_index,
                coordinates.column_index,
                coordinates.char_start,
                coordinates.char_end,
            )
        ),
        reasons=candidate.reasons,
        score=candidate.score,
        is_heading=_HEADING_ONLY.search(unit.raw_text) is not None,
        payload=candidate,
    )


def test_summary_input_stays_source_only_and_groups_real_locators(payload) -> None:
    for sample in payload["samples"]:
        package, _candidates, _group_ids, _route = _finalize(sample)
        summary = package.summary_input()

        assert summary["schema_version"] == "narrative-summary-input/0.2.0"
        assert summary["source_id"] == sample["source_id"]
        assert summary["source_sha256"] == sample["source_sha256"]
        assert summary["summary_scope"] == "selected_evidence_only"
        assert summary["document_kind"] == sample["document_kind"]

        keys = set()

        def walk(node) -> None:
            if isinstance(node, dict):
                for key, value in node.items():
                    keys.add(key)
                    walk(value)
            elif isinstance(node, list):
                for value in node:
                    walk(value)

        walk(summary)
        assert not keys & INVESTMENT_KEYS
        assert summary["evidence"]
        for row in summary["evidence"]:
            assert row["locators"]
            assert row["evidence_ids"]
            assert row["source_role"] == "company_filing"
            assert row["topics"]
            assert row["selection_reasons"]
            digest = hashlib.sha256(row["raw_text"].encode("utf-8")).hexdigest()
            assert digest == row["raw_text_sha256"]
            if len(row["evidence_ids"]) > 1:
                assert row["context_group_id"]
                assert row["context_member_count"] == len(row["evidence_ids"])
            else:
                assert row["locator"]


def test_status_keeps_source_only_meaning(payload) -> None:
    allowed = {
        "selected",
        "partial",
        "skipped_no_narrative",
        "needs_review",
        "blocked",
    }
    for sample in payload["samples"]:
        package, _candidates, _group_ids, _route = _finalize(sample)
        assert package.status in allowed
        assert package.coverage_complete is True
        assert package.dropped_financial_count == 0


def test_finalization_is_deterministic_for_input_order(payload) -> None:
    for sample in payload["samples"]:
        forward, _c, _g, _r = _finalize(sample)
        backward, _c2, _g2, _r2 = _finalize(sample, reverse=True)

        assert forward.status == backward.status
        assert forward.candidate_count == backward.candidate_count
        assert forward.omitted_candidate_count == backward.omitted_candidate_count
        assert [span.span_id for span in forward.evidence_spans] == [
            span.span_id for span in backward.evidence_spans
        ]
