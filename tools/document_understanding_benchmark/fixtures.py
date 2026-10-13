"""Offline synthetic fixtures for the no-network benchmark CLI.

Total budget ≤200KiB. Everything is a compact JSON observation paired with a
tiny quoted gold, so the offline suite exercises the oracle's *logic* — route,
recall, replay, role/modality/basis, bilingual redundancy, derived space — with
no original, no network and no model call.
"""

from __future__ import annotations

from typing import Any

FIXTURE_SCHEMA_VERSION = "du-offline-fixture/1"

# Hard budget for everything the offline mode may carry: the fixtures are the
# only synthetic corpus, so this bound is what keeps the offline suite honest
# and cheap. Enforced by the CLI and asserted in tests.
OFFLINE_FIXTURE_BUDGET = 200 * 1024

SHA_A = "a" * 64
SHA_B = "b" * 64
SHA_C = "c" * 64


def _fact(
    fact_id: str,
    quote: str,
    *,
    page: int | None = 1,
    line: int | None = None,
    importance: str = "critical",
    basis: str = "unknown",
    modality: str = "actual",
    role: str = "company_filing",
    must_preserve: list[str] | None = None,
    must_not_assert: list[str] | None = None,
    locator: str | None = None,
    reason: str = "",
) -> dict[str, Any]:
    anchor: dict[str, Any] = {"exact_quote": quote}
    if page is not None:
        anchor["page"] = page
    if line is not None:
        anchor["line"] = line
    if locator:
        anchor["locator"] = locator
    return {
        "id": fact_id,
        "importance": importance,
        "quantity_basis": basis,
        "modality": modality,
        "role": role,
        "any_support_sets": [[anchor]],
        "must_preserve": must_preserve or [],
        "must_not_assert": must_not_assert or [],
        "reason": reason,
    }


def fixture_clean_annual() -> dict[str, Any]:
    """A correct annual-report observation; the oracle must PASS it."""

    return {
        "fixture_id": "clean-annual",
        "gold": {
            "schema_version": "du-gold/1",
            "sample_id": "offline-clean-annual",
            "source_sha256": SHA_A,
            "scope": "development",
            "expected_route_families": ["annual"],
            "facts": [
                _fact(
                    "f-stores",
                    "门店总数7,504家",
                    page=12,
                    basis="total",
                    must_preserve=["7504"],
                    must_not_assert=["净新增7,504家"],
                    locator="loc:v1/page:12/paragraph:4",
                    reason="期末存量，不是净新增",
                ),
                _fact(
                    "f-capex",
                    "本项目总投资为28,000万元",
                    page=62,
                    basis="investment",
                    modality="plan",
                    must_preserve=["28000", "万元"],
                    must_not_assert=["项目收入28,000万元"],
                    locator="loc:v1/page:62/paragraph:1",
                    reason="投资额不是收入；这是募投计划金额而非已完成支出",
                ),
                _fact(
                    "f-overseas",
                    "海外门店于本年度开始拓展",
                    page=12,
                    must_preserve=["海外"],
                    locator="loc:v1/page:12/paragraph:5",
                    reason="已启动的拓展事实",
                ),
            ],
        },
        "observed": {
            "schema_version": "du-observed/1",
            "sample_id": "offline-clean-annual",
            "source_sha256": SHA_A,
            "route": {"family": "annual", "regime": "hkex", "confidence": "high"},
            "selected_locators": [
                "loc:v1/page:12/paragraph:4",
                "loc:v1/page:12/paragraph:5",
                "loc:v1/page:62/paragraph:1",
            ],
            "selected_text": (
                "门店总数7,504家。海外门店于本年度开始拓展。"
                "本项目总投资为28,000万元。"
            ),
            "semantic_units": [
                {
                    "semantic_id": "m1",
                    "kind": "operating_table",
                    "locators": ["loc:v1/page:12/paragraph:4"],
                    "completeness": "complete",
                    "diagnostics": [],
                }
            ],
            "claims": [
                {
                    "text": "截至2024年12月31日，门店总数为7,504家。",
                    "evidence_locators": ["loc:v1/page:12/paragraph:4"],
                    "role": "company_filing",
                    "modality": "actual",
                    "quantities": [
                        {"value": 7504, "unit": "家", "period": "2024-12-31", "basis": "total"}
                    ],
                    "language": "zh",
                },
                {
                    "text": "海外门店于本年度开始拓展。",
                    "evidence_locators": ["loc:v1/page:12/paragraph:5"],
                    "role": "company_filing",
                    "modality": "actual",
                    "quantities": [],
                    "language": "zh",
                },
                {
                    "text": "本项目总投资为28,000万元。",
                    "evidence_locators": ["loc:v1/page:62/paragraph:1"],
                    "role": "company_filing",
                    "modality": "plan",
                    "quantities": [
                        {"value": 28000, "unit": "万元", "period": "2020", "basis": "investment"}
                    ],
                    "language": "zh",
                },
            ],
            "coverage": {
                "native_scan": "complete",
                "complete": True,
                "structured_unit_count": 1,
                "opaque_pages": [],
                "deferred_unit_ids": [],
                "unassigned_unit_ids": [],
            },
            "metrics": {"selected_spans": 3, "derived_bytes": 4096},
            "execution": {
                "entry_point": "synthetic:offline",
                "parser_version": "0.1.1",
                "selector_version": "0.8.0",
                "calls": 0,
                "elapsed_seconds": 0.01,
                "mode": "offline",
            },
        },
    }


def fixture_negation_qa() -> dict[str, Any]:
    """A QA document where the answer denies the question's premise."""

    return {
        "fixture_id": "negation-qa",
        "gold": {
            "schema_version": "du-gold/1",
            "sample_id": "offline-negation-qa",
            "source_sha256": SHA_B,
            "scope": "development",
            "expected_route_families": ["investor_qa"],
            "facts": [
                _fact(
                    "f-no-vc",
                    "公司现无生产VC（碳酸亚乙烯酯）的情况",
                    page=3,
                    modality="negation",
                    role="management_answer",
                    must_preserve=["无生产VC"],
                    must_not_assert=["公司生产VC", "公司已与宁德时代达成VC带量采购"],
                    locator="loc:v1/page:3/paragraph:1",
                    reason="否定必须保留；提问前提不是公司事实",
                ),
                _fact(
                    "f-controller",
                    "中国节能与宁德时代已经建立了联系，并希望建立业务协同与合作",
                    page=3,
                    modality="plan",
                    role="management_answer",
                    must_preserve=["中国节能", "希望"],
                    must_not_assert=["公司与宁德时代已建立业务协同"],
                    locator="loc:v1/page:3/paragraph:1",
                    reason="主体是控股股东，语态是意愿",
                ),
                _fact(
                    "f-question-premise",
                    "有没有能推动与宁德时代等行业龙头达成电池电解液添加剂VC的带量采购等具体业务？",
                    page=3,
                    modality="question",
                    role="analyst_question",
                    must_preserve=["带量采购"],
                    must_not_assert=["公司已推动达成VC带量采购"],
                    locator="loc:v1/page:3/paragraph:1",
                    reason="提问不是公司陈述；不得把设问写成既成事实",
                ),
            ],
        },
        "observed": {
            "schema_version": "du-observed/1",
            "sample_id": "offline-negation-qa",
            "source_sha256": SHA_B,
            "route": {"family": "investor_qa", "regime": "cn_exchange", "confidence": "high"},
            "selected_locators": ["loc:v1/page:3/paragraph:1"],
            "selected_text": (
                "问：有没有能推动与宁德时代达成电池电解液添加剂VC的带量采购等具体业务？"
                "答：公司现无生产VC（碳酸亚乙烯酯）的情况，根据公司控股股东中国节能信息，"
                "中国节能与宁德时代已经建立了联系，并希望建立业务协同与合作。"
            ),
            "semantic_units": [
                {
                    "semantic_id": "m1",
                    "kind": "qa_exchange",
                    "locators": ["loc:v1/page:3/paragraph:1"],
                    "completeness": "complete",
                    "diagnostics": [],
                }
            ],
            "claims": [
                {
                    "text": "有没有能推动与宁德时代等行业龙头达成电池电解液添加剂VC的带量采购等具体业务？",
                    "evidence_locators": ["loc:v1/page:3/paragraph:1"],
                    "role": "analyst_question",
                    "modality": "question",
                    "quantities": [],
                    "language": "zh",
                },
                {
                    "text": "公司现无生产VC（碳酸亚乙烯酯）的情况。",
                    "evidence_locators": ["loc:v1/page:3/paragraph:1"],
                    "role": "management_answer",
                    "modality": "negation",
                    "quantities": [],
                    "language": "zh",
                },
                {
                    "text": "中国节能与宁德时代已经建立了联系，并希望建立业务协同与合作。",
                    "evidence_locators": ["loc:v1/page:3/paragraph:1"],
                    "role": "management_answer",
                    "modality": "plan",
                    "quantities": [],
                    "language": "zh",
                },
            ],
            "coverage": {
                "native_scan": "complete",
                "complete": True,
                "structured_unit_count": 1,
                "opaque_pages": [],
                "deferred_unit_ids": [],
                "unassigned_unit_ids": [],
            },
            "metrics": {"selected_spans": 1, "derived_bytes": 2048},
            "execution": {
                "entry_point": "synthetic:offline",
                "parser_version": "0.1.1",
                "selector_version": "0.8.0",
                "calls": 0,
                "elapsed_seconds": 0.01,
                "mode": "offline",
            },
        },
    }


def fixture_opaque_scan() -> dict[str, Any]:
    """A scanned page with no native text: recall must be UNAVAILABLE."""

    return {
        "fixture_id": "opaque-scan",
        "gold": {
            "schema_version": "du-gold/1",
            "sample_id": "offline-opaque-scan",
            "source_sha256": SHA_C,
            "scope": "development",
            "expected_route_families": ["administrative"],
            "facts": [
                _fact(
                    "f-confirmation",
                    "控股股东、实际控制人对招股说明书的确认意见",
                    page=1,
                    must_preserve=["确认意见"],
                    locator="loc:v1/page:1/paragraph:1",
                    reason="扫描页原生文本为空；不得因标题含招股说明书而当招股正文",
                )
            ],
        },
        "observed": {
            "schema_version": "du-observed/1",
            "sample_id": "offline-opaque-scan",
            "source_sha256": SHA_C,
            "route": {"family": "administrative", "regime": "cn_exchange", "confidence": "low"},
            "selected_locators": [],
            "selected_text": "",
            "semantic_units": [],
            "claims": [],
            "coverage": {
                "native_scan": "partial",
                "complete": False,
                "structured_unit_count": 0,
                "opaque_pages": [1],
                "deferred_unit_ids": [],
                "unassigned_unit_ids": [],
            },
            "metrics": {"selected_spans": 0, "derived_bytes": 128},
            "execution": {
                "entry_point": "synthetic:offline",
                "parser_version": "0.1.1",
                "selector_version": "0.8.0",
                "calls": 0,
                "elapsed_seconds": 0.01,
                "mode": "offline",
            },
        },
    }


def fixture_offering_plan() -> dict[str, Any]:
    """An offering document: plan amounts, two-phase construction, capex.

    Created so the plan-vs-actual, scope and table-header mutations have a
    real target instead of being reported NOT_APPLICABLE.
    """

    return {
        "fixture_id": "offering-plan",
        "gold": {
            "schema_version": "du-gold/1",
            "sample_id": "offline-offering-plan",
            "source_sha256": "d" * 64,
            "scope": "development",
            "expected_route_families": ["offering"],
            "facts": [
                _fact(
                    "f-raise-cap",
                    "本次拟募集资金总额为不超过35,978.71万元",
                    page=61,
                    basis="investment",
                    modality="plan",
                    must_preserve=["35978.71", "不超过"],
                    must_not_assert=["公司已募集资金35,978.71万元"],
                    locator="loc:v1/page:61/paragraph:1",
                    reason="拟募集上限是计划，不是已完成募集",
                ),
                _fact(
                    "f-two-phases",
                    "项目建设期两期，新建厂房为一期，老厂区改建为二期",
                    page=61,
                    basis="projected_output",
                    modality="plan",
                    must_preserve=["两期"],
                    must_not_assert=["项目建设期为一年"],
                    locator="loc:v1/page:61/paragraph:2",
                    reason="两期建设，二期带前置条件",
                ),
                _fact(
                    "f-land-cost",
                    "土地款2,053.00万元",
                    page=62,
                    basis="investment",
                    modality="plan",
                    must_preserve=["2053"],
                    must_not_assert=["土地款为2,147.00万元"],
                    locator="loc:v1/page:62/paragraph:1",
                    reason="土地款是工程建设其它费用的子项",
                ),
            ],
        },
        "observed": {
            "schema_version": "du-observed/1",
            "sample_id": "offline-offering-plan",
            "source_sha256": "d" * 64,
            "route": {"family": "offering", "regime": "cn_exchange", "confidence": "high"},
            "selected_locators": [
                "loc:v1/page:61/paragraph:1",
                "loc:v1/page:61/paragraph:2",
                "loc:v1/page:62/paragraph:1",
            ],
            "selected_text": (
                "本次拟募集资金总额为不超过35,978.71万元。"
                "项目建设期两期，新建厂房为一期，老厂区改建为二期。"
                "土地款2,053.00万元。"
            ),
            "semantic_units": [
                {
                    "semantic_id": "m1",
                    "kind": "project",
                    "locators": ["loc:v1/page:61/paragraph:2"],
                    "completeness": "complete",
                    "diagnostics": [],
                }
            ],
            "claims": [
                {
                    "text": "本次拟募集资金总额为不超过35,978.71万元。",
                    "evidence_locators": ["loc:v1/page:61/paragraph:1"],
                    "role": "company_filing",
                    "modality": "plan",
                    "quantities": [
                        {
                            "value": 35978.71,
                            "unit": "万元",
                            "period": "2020",
                            "basis": "investment",
                        }
                    ],
                    "language": "zh",
                },
                {
                    "text": "项目建设期两期，新建厂房为一期，老厂区改建为二期。",
                    "evidence_locators": ["loc:v1/page:61/paragraph:2"],
                    "role": "company_filing",
                    "modality": "plan",
                    "quantities": [],
                    "language": "zh",
                },
                {
                    "text": "土地款2,053.00万元。",
                    "evidence_locators": ["loc:v1/page:62/paragraph:1"],
                    "role": "company_filing",
                    "modality": "plan",
                    "quantities": [
                        {"value": 2053, "unit": "万元", "period": "2020", "basis": "investment"}
                    ],
                    "language": "zh",
                },
            ],
            "coverage": {
                "native_scan": "complete",
                "complete": True,
                "structured_unit_count": 1,
                "opaque_pages": [],
                "deferred_unit_ids": [],
                "unassigned_unit_ids": [],
            },
            "metrics": {"selected_spans": 3, "derived_bytes": 3072},
            "execution": {
                "entry_point": "synthetic:offline",
                "parser_version": "0.1.1",
                "selector_version": "0.8.0",
                "calls": 0,
                "elapsed_seconds": 0.01,
                "mode": "offline",
            },
        },
    }


def fixture_stage_progress() -> dict[str, Any]:
    """Product verification stages that must not be collapsed into mass production."""

    return {
        "fixture_id": "stage-progress",
        "gold": {
            "schema_version": "du-gold/1",
            "sample_id": "offline-stage-progress",
            "source_sha256": "e" * 64,
            "scope": "development",
            "expected_route_families": ["quarterly"],
            "facts": [
                _fact(
                    "f-epi-stage",
                    "减压EPI设备已在成熟制程客户端验证成功，部分先进工艺已进入量产验证阶段",
                    page=3,
                    modality="actual",
                    must_preserve=["验证成功", "量产验证阶段"],
                    must_not_assert=["减压EPI设备已实现量产"],
                    locator="loc:v1/page:3/paragraph:1",
                    reason="量产验证不等于量产",
                ),
                _fact(
                    "f-dev-stage",
                    "常压外延设备现已完成开发，进入晶圆验证阶段",
                    page=3,
                    modality="actual",
                    must_preserve=["晶圆验证阶段"],
                    must_not_assert=["常压外延设备已验证成功"],
                    locator="loc:v1/page:3/paragraph:2",
                    reason="完成开发不等于验证通过",
                ),
            ],
        },
        "observed": {
            "schema_version": "du-observed/1",
            "sample_id": "offline-stage-progress",
            "source_sha256": "e" * 64,
            "route": {"family": "quarterly", "regime": "cn_exchange", "confidence": "high"},
            "selected_locators": ["loc:v1/page:3/paragraph:1", "loc:v1/page:3/paragraph:2"],
            "selected_text": (
                "减压EPI设备已在成熟制程客户端验证成功，部分先进工艺已进入量产验证阶段。"
                "常压外延设备现已完成开发，进入晶圆验证阶段。"
            ),
            "semantic_units": [
                {
                    "semantic_id": "m1",
                    "kind": "paragraph_event",
                    "locators": ["loc:v1/page:3/paragraph:1"],
                    "completeness": "complete",
                    "diagnostics": [],
                }
            ],
            "claims": [
                {
                    "text": (
                        "减压EPI设备已在成熟制程客户端验证成功，"
                        "部分先进工艺已进入量产验证阶段。"
                    ),
                    "evidence_locators": ["loc:v1/page:3/paragraph:1"],
                    "role": "company_filing",
                    "modality": "actual",
                    "quantities": [],
                    "language": "zh",
                },
                {
                    "text": "常压外延设备现已完成开发，进入晶圆验证阶段。",
                    "evidence_locators": ["loc:v1/page:3/paragraph:2"],
                    "role": "company_filing",
                    "modality": "actual",
                    "quantities": [],
                    "language": "zh",
                },
            ],
            "coverage": {
                "native_scan": "complete",
                "complete": True,
                "structured_unit_count": 1,
                "opaque_pages": [],
                "deferred_unit_ids": [],
                "unassigned_unit_ids": [],
            },
            "metrics": {"selected_spans": 2, "derived_bytes": 2048},
            "execution": {
                "entry_point": "synthetic:offline",
                "parser_version": "0.1.1",
                "selector_version": "0.8.0",
                "calls": 0,
                "elapsed_seconds": 0.01,
                "mode": "offline",
            },
        },
    }


def all_fixtures() -> list[dict[str, Any]]:
    return [
        fixture_clean_annual(),
        fixture_negation_qa(),
        fixture_opaque_scan(),
        fixture_offering_plan(),
        fixture_stage_progress(),
    ]


def fixture_bytes() -> int:
    """Serialized size of the whole offline fixture set, for the 200KiB budget."""

    import json

    return len(json.dumps(all_fixtures(), ensure_ascii=False).encode("utf8"))
