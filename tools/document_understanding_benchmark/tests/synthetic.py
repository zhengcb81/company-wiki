"""Shared synthetic builders for DU-BENCH tests.

Everything here is synthetic and small; no original is read and no network or
model call happens. ``good_observed`` is deliberately built from the gold's
own support anchors so that the *positive* case is realistic, while every
``bad_*`` case mutates exactly one thing the oracle must catch.
"""

from __future__ import annotations

from typing import Any

GOLD: dict[str, Any] = {
    "schema_version": "du-gold/1",
    "sample_id": "syn-retail",
    "source_sha256": "a" * 64,
    "scope": "development",
    "expected_route_families": ["annual"],
    "facts": [
        {
            "id": "f-stores-total",
            "importance": "critical",
            "any_support_sets": [
                [
                    {
                        "page": 12,
                        "exact_quote": "门店总数7,504家",
                        "locator": "loc:v1/page:12/table:1/row:3",
                    }
                ]
            ],
            "must_preserve": ["门店总数", "7504", "2024年12月31日"],
            "must_not_assert": ["净新增7,504家"],
            "quantity_basis": "total",
            "modality": "actual",
            "role": "company_filing",
            "reason": "门店总量是经营驱动，不能被当成净新增",
        },
        {
            "id": "f-top-toy-overseas",
            "importance": "critical",
            "any_support_sets": [
                [
                    {
                        "page": 12,
                        "exact_quote": "TOP TOY 海外门店于本年度开始拓展",
                        "locator": "loc:v1/page:12/paragraph:33",
                    }
                ],
                [
                    {
                        "page": 14,
                        "exact_quote": "TOP TOY overseas store expansion commenced during the year",
                        "locator": "loc:v1/page:14/paragraph:5",
                    }
                ],
            ],
            "must_preserve": ["TOP TOY", "海外"],
            "must_not_assert": ["TOP TOY 海外收入已确认"],
            "modality": "actual",
            "role": "company_filing",
            "reason": "计划/起步与已实现收入必须区分；双语等价支持",
        },
        {
            "id": "f-no-vc",
            "importance": "critical",
            "any_support_sets": [
                [
                    {
                        "page": 3,
                        "exact_quote": "公司不生产VC",
                        "locator": "loc:v1/page:3/paragraph:12",
                    }
                ]
            ],
            "must_preserve": ["不生产VC"],
            "must_not_assert": ["公司生产VC", "公司已与提问方合作VC"],
            "quantity_basis": "unknown",
            "modality": "negation",
            "role": "management_answer",
            "reason": "否定与提问前提相反，必须保留否定",
        },
        {
            "id": "f-project-capex",
            "importance": "normal",
            "any_support_sets": [
                [
                    {
                        "page": 62,
                        "exact_quote": "本项目总投资为28,000万元",
                        "locator": "loc:v1/page:62/table:2/row:1",
                    }
                ]
            ],
            "must_preserve": ["总投资", "28000", "万元"],
            "must_not_assert": ["项目收入28,000万元"],
            "quantity_basis": "investment",
            "modality": "plan",
            "role": "company_filing",
            "reason": "投资额不是收入预测",
        },
    ],
}


def _quote_set(fact: dict[str, Any], index: int = 0) -> list[dict[str, Any]]:
    return fact["any_support_sets"][index]


def good_observed() -> dict[str, Any]:
    """An observation that genuinely carries every gold fact correctly."""

    facts = {fact["id"]: fact for fact in GOLD["facts"]}
    stores = _quote_set(facts["f-stores-total"])
    toy = _quote_set(facts["f-top-toy-overseas"], 1)
    vc = _quote_set(facts["f-no-vc"])
    capex = _quote_set(facts["f-project-capex"])
    return {
        "schema_version": "du-observed/1",
        "sample_id": "syn-retail",
        "source_sha256": "a" * 64,
        "route": {
            "family": "annual",
            "regime": "hkex",
            "confidence": "high",
            "document_kind": "annual_report",
        },
        "selected_locators": [
            "loc:v1/page:3/paragraph:12",
            "loc:v1/page:12/table:1/row:3",
            "loc:v1/page:12/paragraph:33",
            "loc:v1/page:14/paragraph:5",
            "loc:v1/page:62/table:2/row:1",
        ],
        "selected_text": (
            "公司不生产VC。门店总数7,504家(2024年12月31日)。"
            "TOP TOY 海外门店于本年度开始拓展。本项目总投资为28,000万元。"
        ),
        "semantic_units": [
            {
                "semantic_id": "m1",
                "kind": "operating_table",
                "locators": ["loc:v1/page:12/table:1/row:3"],
                "completeness": "complete",
                "diagnostics": [],
            },
            {
                "semantic_id": "m2",
                "kind": "qa_exchange",
                "locators": ["loc:v1/page:3/paragraph:12"],
                "completeness": "complete",
                "diagnostics": [],
            },
            {
                "semantic_id": "m3",
                "kind": "project",
                "locators": ["loc:v1/page:62/table:2/row:1"],
                "completeness": "complete",
                "diagnostics": [],
            },
        ],
        "claims": [
            {
                "text": "公司不生产VC。",
                "evidence_locators": [vc[0]["locator"]],
                "role": "management_answer",
                "modality": "negation",
                "quantities": [],
                "language": "zh",
            },
            {
                "text": "截至2024年12月31日，门店总数为7,504家。",
                "evidence_locators": [stores[0]["locator"]],
                "role": "company_filing",
                "modality": "actual",
                "quantities": [
                    {
                        "value": 7504,
                        "unit": "家",
                        "period": "2024-12-31",
                        "basis": "total",
                    }
                ],
                "language": "zh",
            },
            {
                "text": (
                    "TOP TOY overseas store expansion commenced during the year, "
                    "and total stores reached 7,504."
                ),
                "evidence_locators": [toy[0]["locator"]],
                "role": "company_filing",
                "modality": "actual",
                "quantities": [],
                "language": "en",
            },
            {
                "text": "本项目总投资为28,000万元。",
                "evidence_locators": [capex[0]["locator"]],
                "role": "company_filing",
                "modality": "plan",
                "quantities": [
                    {
                        "value": 28000,
                        "unit": "万元",
                        "period": "2020",
                        "basis": "investment",
                    }
                ],
                "language": "zh",
            },
        ],
        "coverage": {
            "native_scan": "complete",
            "complete": True,
            "structured_unit_count": 3,
            "opaque_pages": [],
            "deferred_unit_ids": [],
            "unassigned_unit_ids": [],
        },
        "metrics": {"selected_spans": 5, "candidate_count": 40, "source_units": 900},
        "execution": {
            "entry_point": "synthetic",
            "parser_version": "0.1.1",
            "selector_version": "0.8.0",
            "calls": 0,
            "elapsed_seconds": 0.0,
            "mode": "offline",
        },
    }


def mutated(**changes: Any) -> dict[str, Any]:
    """Return ``good_observed()`` with top-level fields replaced."""

    observed = good_observed()
    observed.update(changes)
    return observed
