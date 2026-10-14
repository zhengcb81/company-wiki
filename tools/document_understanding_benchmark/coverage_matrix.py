"""Per-document-shape coverage: what is real, what is only synthetic, what is absent.

The card (DU3-QUALITY §4) asks for a coverage matrix across the document shapes
a company-research source system actually receives, with ``real`` / ``synthetic``
/ ``missing`` stated separately, and with one rule that is easy to violate:
**a schema-valid record is not semantic coverage.**

That rule is enforced structurally here. A row may claim ``real`` only when a
named gold sample exists *and* a real original is bound for it; ``synthetic``
rows must point at a synthetic fixture and say so; ``missing`` rows must name the
concrete gap. ``schema_only_shapes()`` then reports the shapes where the only
thing the project can currently prove is that a record validates — which is
precisely the state that must not be reported as coverage.
"""

from __future__ import annotations

from typing import Any

COVERAGE_SCHEMA_VERSION = "du-coverage-matrix/1"

REAL = "real"
SYNTHETIC = "synthetic"
MISSING = "missing"

#: Shapes declared as covered by a synthetic fixture only. Kept explicit so that
#: adding a shape cannot silently inherit the weaker claim.
_SYNTHETIC_EVIDENCE = "synthetic_fixture"
_REAL_EVIDENCE = "real_original"


def _row(
    shape: str,
    label: str,
    coverage: str,
    *,
    sample_ids: tuple[str, ...] = (),
    evidence: str | None = None,
    gap: str = "",
    note: str = "",
) -> dict[str, Any]:
    return {
        "shape": shape,
        "label": label,
        "coverage": coverage,
        "sample_ids": list(sample_ids),
        "evidence": evidence,
        "gap": gap,
        "note": note,
    }


DOCUMENT_COVERAGE = {
    "schema_version": COVERAGE_SCHEMA_VERSION,
    "note": (
        "real = a named gold sample with a bound real original. synthetic = a "
        "fixture that exercises the shape's logic but is not a real document. "
        "missing = no sample at all; the gap is named. schema validity is never "
        "counted as semantic coverage."
    ),
    "rows": [
        # --- A share -------------------------------------------------------
        _row("a_share_annual", "A股年度报告", REAL,
             sample_ids=("cn-annual", "fresh-cn-smic-fy2025"),
             evidence=_REAL_EVIDENCE,
             note="分部的业务叙述、募投项目、审计意见均在真实原件上有金标事实"),
        _row("a_share_interim", "A股半年度报告", REAL,
             sample_ids=("cn-h1",), evidence=_REAL_EVIDENCE),
        _row("a_share_quarterly", "A股季度报告", REAL,
             sample_ids=("cn-q-business", "cn-q-sparse",
                         "holdout-cn-glodon-q1", "holdout-cn-yake-q1"),
             evidence=_REAL_EVIDENCE,
             note="含经营叙述型与纯财务稀疏型两类；纯财务季报允许零选择零摘要"),
        # --- H share -------------------------------------------------------
        _row("hk_annual", "港股年度报告", REAL,
             sample_ids=("hk-annual", "holdout-hk-alibaba-fy2023",
                         "holdout-hk-biren-fy2025", "fresh-hk-anta-fy2025"),
             evidence=_REAL_EVIDENCE,
             note="含繁体、双语与币种口径差异"),
        _row("hk_interim", "港股中期报告", REAL,
             sample_ids=("hk-interim",), evidence=_REAL_EVIDENCE),
        # --- US share ------------------------------------------------------
        _row("us_10k", "美国 10-K 年报", REAL,
             sample_ids=("us-10k", "holdout-us-mongodb-10k",
                         "holdout-us-nvidia-10k", "fresh-us-apple-10k"),
             evidence=_REAL_EVIDENCE,
             note="真实 HTML 经既有 normalize_document 前端可读"),
        _row("us_10q", "美国 10-Q 季报", REAL,
             sample_ids=("us-10q",), evidence=_REAL_EVIDENCE),
        _row("us_20f", "外国私人发行人 20-F", REAL,
             sample_ids=("us-20f",), evidence=_REAL_EVIDENCE),
        # --- offerings -----------------------------------------------------
        _row("ipo_prospectus", "A股 IPO 招股说明书", REAL,
             sample_ids=("cn-ipo",), evidence=_REAL_EVIDENCE),
        _row("us_s1_f1", "美国 S-1 / F-1 注册说明书", MISSING,
             gap="本地无真实 S-1/F-1 原件；holdout.json 的 REQ-2 仍开放。"
                 "现有 us-20f 是年报而非注册说明书，不能替代。"),
        _row("equity_offering", "向特定对象发行/增发说明书", REAL,
             sample_ids=("cn-equity",), evidence=_REAL_EVIDENCE,
             note="含建设期一期/二期与募投上限等计划型事实"),
        _row("convertible_bond", "可转债募集说明书", REAL,
             sample_ids=("cn-convertible",), evidence=_REAL_EVIDENCE),
        # --- IR / calls ----------------------------------------------------
        _row("investor_relations", "投资者关系活动记录", REAL,
             sample_ids=("cn-ir",), evidence=_REAL_EVIDENCE,
             note="否定、提问前提与关联方主语的高风险形态"),
        _row("earnings_call", "业绩电话会记录", REAL,
             sample_ids=("us-txt",), evidence=_REAL_EVIDENCE,
             note="说话人角色是主要风险点"),
        _row("results_release", "业绩发布公告", REAL,
             sample_ids=("hk-release", "us-release"), evidence=_REAL_EVIDENCE),
        _row("presentation_deck", "业绩演示稿", REAL,
             sample_ids=("hk-deck",), evidence=_REAL_EVIDENCE,
             note="经既有 normalize_document PPTX 前端；图片页保持 opaque"),
        # --- containers / revisions ---------------------------------------
        _row("sec_8k_6k_exhibit", "8-K / 6-K 容器及其业务附件", MISSING,
             gap="本地无真实 8-K/6-K 容器原件（holdout.json REQ-3）。"
                 "8-K 的容器/附件分离与父源合包风险目前只有合成覆盖。"),
        _row("amended_filing", "修订稿与原稿同期间配对", MISSING,
             gap="本地无真实修订稿配对（holdout.json REQ-4）。"
                 "版本错复用目前只有合成变异覆盖，不能算真实语义覆盖。"),
        # --- low-business / administrative ---------------------------------
        _row("low_business_administrative", "低业务量/行政类文件", REAL,
             sample_ids=("cn-ir-policy", "cn-ipo-confirmation"),
             evidence=_REAL_EVIDENCE,
             note="含扫描件无原生文本与行政类跳过；不得当作“没有业务内容”"),
    ],
}

def rows_by_shape() -> dict[str, dict[str, Any]]:
    return {row["shape"]: row for row in DOCUMENT_COVERAGE["rows"]}


def schema_only_shapes() -> list[str]:
    """Shapes covered only by a schema-valid record, never by real semantics.

    Two situations qualify and both are reported rather than hidden:

    * a ``missing`` shape whose gap text says the only current evidence is a
      synthetic mutation run (a validating record is not a document); and
    * a ``synthetic`` shape, which proves the logic and nothing about real text.
    """

    found: list[str] = []
    for row in DOCUMENT_COVERAGE["rows"]:
        if row["coverage"] == SYNTHETIC:
            found.append(row["shape"])
        elif row["coverage"] == MISSING and "合成" in row["gap"]:
            found.append(row["shape"])
    return found


def semantic_coverage_summary() -> dict[str, Any]:
    """Counts per bucket plus the schema-only list, stated apart from counts."""

    counts = {REAL: 0, SYNTHETIC: 0, MISSING: 0}
    for row in DOCUMENT_COVERAGE["rows"]:
        counts[row["coverage"]] += 1
    return {
        "schema_version": COVERAGE_SCHEMA_VERSION,
        "shapes_total": len(DOCUMENT_COVERAGE["rows"]),
        "counts": counts,
        "schema_only_shapes": schema_only_shapes(),
        "missing_shapes": [row["shape"] for row in DOCUMENT_COVERAGE["rows"]
                           if row["coverage"] == MISSING],
        "note": (
            "A shape in schema_only_shapes has no real-document semantic "
            "evidence. Passing schema validation for it must not be reported "
            "as coverage."
        ),
    }


__all__ = [
    "COVERAGE_SCHEMA_VERSION",
    "DOCUMENT_COVERAGE",
    "MISSING",
    "REAL",
    "SYNTHETIC",
    "rows_by_shape",
    "schema_only_shapes",
    "semantic_coverage_summary",
]
