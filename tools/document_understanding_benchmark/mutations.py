"""Negative mutations: deliberately broken observations the oracle must catch.

Each mutation names the defect it injects and the check that must fail. The
suite is *self-verifying*: :func:`run_mutation_suite` reports, per mutation,
whether the oracle detected it. A mutation the oracle cannot detect is reported
as ``NOT_DETECTED`` — an honest coverage gap, never a silent PASS.

The mutations come from the DU-BENCH card §6 list, plus the additional traps
found while reading the originals.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from typing import Any

from .evaluate import evaluate

MUTATION_SCHEMA_VERSION = "du-mutation/1"


def _clone(observed: Mapping[str, Any]) -> dict[str, Any]:
    import copy

    return copy.deepcopy(dict(observed))


def _first_claim_matching(observed: dict[str, Any], needle: str) -> dict[str, Any] | None:
    for claim in observed.get("claims") or []:
        if needle in (claim.get("text") or ""):
            return claim
    return None


def _drop_claim(observed: dict[str, Any], needle: str) -> None:
    observed["claims"] = [
        claim for claim in observed.get("claims") or [] if needle not in (claim.get("text") or "")
    ]
    observed["selected_text"] = (observed.get("selected_text") or "").replace(needle, "")


# --------------------------------------------------------------------------
# mutations
# --------------------------------------------------------------------------


def m_drop_subject(observed: dict[str, Any], gold: Mapping[str, Any]) -> dict[str, Any]:
    """省主语：delete the actor so the fact becomes ownerless."""

    for claim in observed.get("claims") or []:
        text = claim.get("text") or ""
        if "中国节能" in text:
            claim["text"] = text.replace("中国节能", "")
            return observed
    for claim in observed.get("claims") or []:
        claim["text"] = (claim.get("text") or "").replace("公司", "")
        return observed
    return observed


def m_delete_negation(observed: dict[str, Any], gold: Mapping[str, Any]) -> dict[str, Any]:
    """删否定：turn a denial into its opposite."""

    for claim in observed.get("claims") or []:
        text = claim.get("text") or ""
        if "无生产VC" in text:
            claim["text"] = text.replace("无生产VC", "已生产VC")
            claim["modality"] = "actual"
            return observed
        if "不生产VC" in text:
            claim["text"] = text.replace("不生产VC", "生产VC")
            claim["modality"] = "actual"
            return observed
    return observed


def m_unit_wan_to_yi(observed: dict[str, Any], gold: Mapping[str, Any]) -> dict[str, Any]:
    """万元→亿元：rescale a number without changing its label."""

    for claim in observed.get("claims") or []:
        for quantity in claim.get("quantities") or []:
            if quantity.get("value") in (28000, 35300, 35978.71):
                quantity["value"] = float(quantity["value"]) / 10000
                quantity["unit"] = "亿元"
                return observed
    return observed


def m_total_to_increment(observed: dict[str, Any], gold: Mapping[str, Any]) -> dict[str, Any]:
    """总数→新增：restate a year-end stock as net additions.

    Two shapes are injected together, because both occur in practice: a
    *prefixed* restatement that still contains the original wording, and a
    *replaced* restatement that destroys it.
    """

    for index, claim in enumerate(observed.get("claims") or []):
        text = claim.get("text") or ""
        if "门店总数" in text:
            if index % 2 == 0:
                claim["text"] = text.replace("门店总数", "净新增门店")
            else:
                claim["text"] = f"净新增{text}"
            for quantity in claim.get("quantities") or []:
                quantity["basis"] = "incremental"
            return observed
    return observed


def m_gmv_to_revenue(observed: dict[str, Any], gold: Mapping[str, Any]) -> dict[str, Any]:
    """GMV→收入：relabel a gross-merchandise volume as revenue."""

    for claim in observed.get("claims") or []:
        for quantity in claim.get("quantities") or []:
            if quantity.get("basis") == "period_flow":
                quantity["basis"] = "period_flow"
                claim["text"] = f"GMV口径：{claim.get('text')}"
                return observed
    return observed


def m_future_to_actual(observed: dict[str, Any], gold: Mapping[str, Any]) -> dict[str, Any]:
    """未来→实际：a plan becomes a completed fact."""

    for claim in observed.get("claims") or []:
        if claim.get("modality") == "plan":
            claim["modality"] = "actual"
            text = claim.get("text") or ""
            claim["text"] = text.replace("预计", "已经").replace("拟", "已")
            return observed
    return observed


def m_question_to_statement(observed: dict[str, Any], gold: Mapping[str, Any]) -> dict[str, Any]:
    """问题→公司陈述：an analyst question becomes a company assertion."""

    for claim in observed.get("claims") or []:
        if claim.get("role") in {"analyst_question", "analyst_statement"}:
            claim["role"] = "company_statement"
            claim["modality"] = "actual"
            return observed
    return observed


def m_drop_table_header(observed: dict[str, Any], gold: Mapping[str, Any]) -> dict[str, Any]:
    """丢表头：keep the numbers, lose the column they belong to."""

    for quantity in _all_quantities(observed):
        quantity["period"] = None
        quantity["unit"] = None
        return observed
    return observed


def m_missing_page_but_complete(observed: dict[str, Any], gold: Mapping[str, Any]) -> dict[str, Any]:
    """缺页却 complete：claim structural completeness with a page unread."""

    coverage = observed.setdefault("coverage", {})
    coverage["native_scan"] = "partial"
    coverage["opaque_pages"] = sorted({int(p) for p in coverage.get("opaque_pages") or []} | {12})
    coverage["complete"] = True
    return observed


def m_toc_only(observed: dict[str, Any], gold: Mapping[str, Any]) -> dict[str, Any]:
    """只有目录：nothing but headings, no business content."""

    observed["claims"] = []
    observed["selected_text"] = "目錄 主席報告 管理層討論與分析 財務報表 附註"
    observed["selected_locators"] = ["loc:v1/page:2/paragraph:1"]
    return observed


def m_stale_source_version(observed: dict[str, Any], gold: Mapping[str, Any]) -> dict[str, Any]:
    """同 source 新版本错复用：reuse an old digest for a changed original."""

    observed["source_sha256"] = "0" * 64
    return observed


def m_self_certifying_output(observed: dict[str, Any], gold: Mapping[str, Any]) -> dict[str, Any]:
    """测试输出自证：an assertion citing a locator that was never selected."""

    observed.setdefault("claims", []).append(
        {
            "text": "本次基准测试已通过全部关键事实检查。",
            "evidence_locators": ["loc:v1/page:999/paragraph:1"],
            "role": "company_filing",
            "modality": "actual",
            "quantities": [],
        }
    )
    return observed


def m_invented_fact(observed: dict[str, Any], gold: Mapping[str, Any]) -> dict[str, Any]:
    """幻觉：add a plausible business fact with no support at all."""

    observed.setdefault("claims", []).append(
        {
            "text": "公司2024年海外收入同比增长120%，主要由东南亚市场驱动。",
            "evidence_locators": ["loc:v1/page:88/paragraph:3"],
            "role": "company_filing",
            "modality": "actual",
            "quantities": [{"value": 120, "unit": "%", "basis": "period_flow"}],
        }
    )
    return observed


def m_bilingual_duplicate(observed: dict[str, Any], gold: Mapping[str, Any]) -> dict[str, Any]:
    """双语冗余：summarise one fact once per language lane."""

    source_claim = None
    for claim in observed.get("claims") or []:
        if (claim.get("language") or "") == "zh" and claim.get("evidence_locators"):
            source_claim = claim
            break
    if source_claim is None:
        return observed
    observed.setdefault("claims", []).append(
        {
            "text": f"Duplicate translation: {source_claim.get('text')}",
            "evidence_locators": list(source_claim.get("evidence_locators") or []),
            "role": source_claim.get("role"),
            "modality": source_claim.get("modality"),
            "quantities": list(source_claim.get("quantities") or []),
            "language": "en",
        }
    )
    return observed


def m_derived_bloat(observed: dict[str, Any], gold: Mapping[str, Any]) -> dict[str, Any]:
    """派生超预算：materialise far more derived bytes than the budget."""

    observed["metrics"] = dict(observed.get("metrics") or {}, derived_bytes=5 * 1024 * 1024)
    return observed


def m_wrong_route(observed: dict[str, Any], gold: Mapping[str, Any]) -> dict[str, Any]:
    """类型误判：route a filing to a different family."""

    route = observed.get("route")
    if route is None:
        return observed
    route["family"] = "presentation"
    route["document_kind"] = "presentation"
    return observed


def m_stage_collapse(observed: dict[str, Any], gold: Mapping[str, Any]) -> dict[str, Any]:
    """阶段坍缩：verification-in-progress restated as mass production."""

    for claim in observed.get("claims") or []:
        text = claim.get("text") or ""
        for marker in ("量产验证阶段", "晶圆验证阶段", "客户端验证阶段", "验证成功"):
            if marker in text:
                claim["text"] = text.replace(marker, "已量产")
                return observed
    return observed


def m_plan_as_completed(observed: dict[str, Any], gold: Mapping[str, Any]) -> dict[str, Any]:
    """计划当成完成：an offering cap becomes raised money."""

    for claim in observed.get("claims") or []:
        text = claim.get("text") or ""
        if "不超过" in text:
            claim["text"] = text.replace("拟募集资金总额为不超过", "已募集资金").replace("不超过", "")
            claim["modality"] = "actual"
            return observed
    return observed


def m_scope_confusion(observed: dict[str, Any], gold: Mapping[str, Any]) -> dict[str, Any]:
    """主体串：an affiliate's action attributed to the listed company."""

    for claim in observed.get("claims") or []:
        text = claim.get("text") or ""
        if "中国节能" in text:
            claim["text"] = text.replace("中国节能", "公司")
            claim["role"] = "company_statement"
            return observed
    return observed


MUTATIONS: tuple[tuple[str, str, Callable[[dict[str, Any], Mapping[str, Any]], dict[str, Any]], str], ...] = (
    ("drop_subject", "省主语", m_drop_subject, "basis."),
    ("delete_negation", "删否定", m_delete_negation, "basis.f-no-vc"),
    ("unit_wan_to_yi", "万元→亿元", m_unit_wan_to_yi, "basis."),
    ("total_to_increment", "总数→新增", m_total_to_increment, "basis."),
    ("gmv_to_revenue", "GMV→收入", m_gmv_to_revenue, "basis."),
    ("future_to_actual", "未来→实际", m_future_to_actual, "basis."),
    ("question_to_statement", "问题→公司陈述", m_question_to_statement, "basis."),
    ("drop_table_header", "丢表头", m_drop_table_header, "basis."),
    ("missing_page_but_complete", "缺页却complete", m_missing_page_but_complete, "recall."),
    ("toc_only", "只有目录", m_toc_only, "recall."),
    ("stale_source_version", "同source新版本错复用", m_stale_source_version, "integrity.source_identity"),
    ("self_certifying_output", "测试输出自证", m_self_certifying_output, "integrity.unsupported_claims"),
    ("invented_fact", "无支撑幻觉事实", m_invented_fact, "integrity.unsupported_claims"),
    ("bilingual_duplicate", "双语冗余", m_bilingual_duplicate, "bilingual.duplicate_summary"),
    ("derived_bloat", "派生空间超预算", m_derived_bloat, "derived_space.budget"),
    ("wrong_route", "类型误判", m_wrong_route, "route.family"),
    ("stage_collapse", "验证阶段坍缩为量产", m_stage_collapse, "basis."),
    ("plan_as_completed", "计划当成已完成", m_plan_as_completed, "basis."),
    ("scope_confusion", "主体串（关联方→上市公司）", m_scope_confusion, "basis."),
)


def _all_quantities(observed: Mapping[str, Any]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for claim in observed.get("claims") or []:
        out.extend(claim.get("quantities") or [])
    return out


def run_mutation_suite(
    observed: Mapping[str, Any],
    gold: Mapping[str, Any],
    *,
    limits: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Apply every mutation and report whether the oracle detected it.

    Three outcomes are reported honestly and are **not** conflated:

    ``DETECTED``
        the mutated observation no longer PASSes.
    ``NOT_DETECTED``
        a real oracle coverage gap: the defect was injected and the oracle
        still passed. This is reported as a gap, never hidden.
    ``NOT_APPLICABLE``
        the mutation's target does not exist in this observation (e.g. no
        negation to delete), so nothing was actually mutated. Counting these as
        misses would inflate the gap; counting them as hits would fake it.
    """

    baseline = evaluate(observed, gold, limits=limits)
    rows: list[dict[str, Any]] = []
    for mutation_id, label, mutator, expected_check_prefix in MUTATIONS:
        original = _clone(observed)
        mutated = mutator(_clone(observed), gold)
        if mutated == original:
            rows.append(
                {
                    "mutation_id": mutation_id,
                    "label": label,
                    "expected_check": expected_check_prefix,
                    "outcome": "NOT_APPLICABLE",
                    "detected": False,
                    "applicable": False,
                    "targeted_check_hit": False,
                    "failing_checks": [],
                    "result_status": baseline["status"],
                    "detail": "mutation target not present in this observation",
                }
            )
            continue
        result = evaluate(mutated, gold, limits=limits)
        detected = result["status"] != "PASS"
        failing = [row["check_id"] for row in result["checks"] if row["status"] == "FAIL"]
        not_pass = [
            row["check_id"] for row in result["checks"] if row["status"] != "PASS"
        ]
        targeted = [check_id for check_id in not_pass if check_id.startswith(expected_check_prefix)]
        rows.append(
            {
                "mutation_id": mutation_id,
                "label": label,
                "expected_check": expected_check_prefix,
                "outcome": "DETECTED" if detected else "NOT_DETECTED",
                "detected": detected,
                "applicable": True,
                "targeted_check_hit": bool(targeted),
                "failing_checks": failing,
                "not_pass_checks": not_pass,
                "result_status": result["status"],
                "detail": "",
            }
        )

    applicable = [row for row in rows if row["applicable"]]
    detected = sum(1 for row in applicable if row["detected"])
    targeted_hits = sum(1 for row in applicable if row["targeted_check_hit"])
    return {
        "schema_version": MUTATION_SCHEMA_VERSION,
        "sample_id": gold.get("sample_id"),
        "baseline_status": baseline["status"],
        "mutations_total": len(rows),
        "mutations_applicable": len(applicable),
        "mutations_not_applicable": len(rows) - len(applicable),
        "mutations_detected": detected,
        "mutations_not_detected": len(applicable) - detected,
        "detection_rate": (detected / len(applicable)) if applicable else None,
        "targeted_hit_rate": (targeted_hits / len(applicable)) if applicable else None,
        "rows": rows,
    }
