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

DU5-CORPUS extension (2026-10-15): one ``REAL`` claim used to collapse five
different axes into one word, so a named sample with no gold and no measured
read looked identical to a measured, gold-backed one. Every cited sample now
carries an explicit per-sample axis declaration — ``original`` / ``gold`` /
``readable`` / ``selected`` / ``summary_reviewed`` — each ``yes`` / ``no`` /
``unknown`` with its measurement evidence. None of the axes may be inferred
from another: a real original is not gold, gold is not readability, and nothing
here is a reviewed summary.
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

#: The five axes the card names. Values are only ever yes / no / unknown.
AXES = ("original", "gold", "readable", "selected", "summary_reviewed")


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


def _sample(
    gold: str,
    readable: str = "unknown",
    selected: str = "unknown",
    summary_reviewed: str = "unknown",
    evidence: str = "",
) -> dict[str, str]:
    """One sample's five-axis declaration; ``original`` is 'yes' by admission.

    A sample only appears in this table when the project holds the original and
    it is on the contamination list (an admission the tests enforce), so the
    original axis is 'yes' for every entry here.
    """

    return {
        "original": "yes",
        "gold": gold,
        "readable": readable,
        "selected": selected,
        "summary_reviewed": summary_reviewed,
        "axis_evidence": evidence,
    }


_Y, _N, _U = "yes", "no", "unknown"

#: Per-sample axis state. ``gold`` agrees with the gold directory (tested);
#: readable/selected carry only *measured* values from recorded runs and stay
#: ``unknown`` wherever no run exists — a guess here would recreate the
#: collapsed claim this module exists to prevent.
SAMPLE_AXES: dict[str, dict[str, str]] = {
    # --- development survey samples --------------------------------------
    "cn-h1": _sample(_Y, _Y, _Y, _N, "pre-repair replay: 369 candidates, 96 spans (capped); baseline emits no summary"),
    "cn-annual": _sample(_N, _U, _U, _U, "survey original, no observation recorded, no gold"),
    "cn-ipo": _sample(_N, _U, _U, _U, "survey original, no observation recorded, no gold"),
    "cn-q-business": _sample(_Y, _Y, _Y, _N, "pre-repair replay: 28 candidates, 28 spans; baseline emits no summary"),
    "cn-q-sparse": _sample(_Y, _Y, _N, _N, "pre-repair replay: 429 units parsed, 0 candidates produced"),
    "cn-equity": _sample(_Y, _Y, _Y, _N, "pre-repair replay: 449 candidates, 96 spans (capped)"),
    "cn-convertible": _sample(_N, _U, _U, _U, "survey original, no observation recorded, no gold"),
    "cn-ipo-confirmation": _sample(_Y, _N, _N, _N, "measured: 0 units, page 1 opaque (scanned); routed prospectus"),
    "cn-ir": _sample(_Y, _Y, _Y, _N, "pre-repair replay: 11 candidates, 11 spans"),
    "cn-ir-policy": _sample(_N, _U, _U, _U, "survey original, no observation recorded, no gold"),
    "hk-annual": _sample(_Y, _Y, _Y, _N, "pre-repair replay: 254 candidates, 96 spans (capped)"),
    "hk-interim": _sample(_N, _U, _U, _U, "survey original (Dropbox binding), no observation recorded, no gold"),
    "hk-ipo": _sample(_N, _U, _U, _U, "survey original (Dropbox binding), no observation recorded, no gold"),
    "hk-release": _sample(_N, _U, _U, _U, "survey original, no observation recorded, no gold"),
    "hk-deck": _sample(_N, _U, _U, _U, "survey original, no observation recorded, no gold"),
    "hk-annual-mojibake": _sample(_Y, _N, _Y, _N, "measured: 9,618 units parse with zero flags but 0 readable Chinese pages of 415 (2.663% unusable chars); selector picked 12 spans of mojibake — 'readable' is NO on the legibility axis"),
    "us-10k": _sample(_Y, _Y, _Y, _N, "reception-repair measurement: normalize_document read 5,215 units from real HTML, 96 spans all mapped; baseline emits no summary"),
    "us-10q": _sample(_N, _U, _U, _U, "survey original (dayu-agent binding), no observation recorded, no gold"),
    "us-20f": _sample(_Y, _U, _U, _U, "gold exists (15 facts) and the original is read into the design findings, but no du-observed replay record is stored; dayu-agent local binding"),
    "us-release": _sample(_N, _U, _U, _U, "survey original, no observation recorded, no gold"),
    "us-txt": _sample(_Y, _Y, _Y, _N, "measured: transcript path routes, 489 units, 11 selected; role facts lost"),
    # --- holdout gold ----------------------------------------------------
    "holdout-cn-glodon-q1": _sample(_Y, _Y, _N, _N, "pre-repair replay: 257 units parsed, 0 candidates produced"),
    "holdout-cn-yake-q1": _sample(_Y, _Y, _Y, _N, "pre-repair replay: 369 units parsed, 2 spans"),
    "holdout-hk-alibaba-fy2023": _sample(_Y, _Y, _Y, _N, "pre-repair replay: 2,221 candidates, 96 spans (capped)"),
    "holdout-hk-biren-fy2025": _sample(_Y, _U, _U, _U, "original extracts cleanly (probe 2026-10-13); no du-observed run recorded"),
    "holdout-us-mongodb-10k": _sample(_Y, _U, _U, _U, "gold authored 2026-10-13 (16 facts) but no scoring run: pre-repair measurement unavailable via the old HTML route (units=0, transcript_start_missing); normalize frontend later reads HTML but no re-run is recorded"),
    "holdout-us-nvidia-10k": _sample(_Y, _U, _U, _U, "gold authored 2026-10-13 (16 facts) but no scoring run: same as MongoDB — old-route unavailable, no recorded re-run on the new frontend"),
    # --- fresh gold (2026-10-14) ----------------------------------------
    "fresh-cn-smic-fy2025": _sample(_Y, _U, _U, _U, "gold frozen 2026-10-14; anchors verified against the original; no candidate run recorded yet"),
    "fresh-hk-anta-fy2025": _sample(_Y, _U, _U, _U, "gold frozen 2026-10-14; anchors verified; no candidate run recorded yet"),
    "fresh-us-apple-10k": _sample(_Y, _U, _U, _U, "gold frozen 2026-10-14; DOM-locator anchors verified; no candidate run recorded yet"),
    # --- DU5-CORPUS set (frozen 2026-10-15) ------------------------------
    "du5-cn-iflytek-h1": _sample(_Y, _U, _U, _U, "gold frozen 2026-10-15 (du5_manifest.json); all anchors verified; no candidate output read before freeze"),
    "du5-cn-fangbang-q1": _sample(_Y, _U, _U, _U, "gold frozen 2026-10-15; all anchors verified"),
    "du5-cn-proya-q1": _sample(_Y, _U, _U, _U, "gold frozen 2026-10-15; all anchors verified (period/unit table case)"),
    "du5-cn-zhongmi-offering": _sample(_Y, _U, _U, _U, "gold frozen 2026-10-15; all anchors verified (investment/plan case)"),
    "du5-hk-kingsoft-interim": _sample(_Y, _U, _U, _U, "gold frozen 2026-10-15; all anchors verified (千元/百萬元 unit case)"),
    "du5-hk-kingsoft-q1": _sample(_Y, _U, _U, _U, "gold frozen 2026-10-15; all anchors verified (quarter-only period case)"),
    "du5-us-msft-8k": _sample(_Y, _U, _U, _U, "gold frozen 2026-10-15; all anchors verified (container-vs-exhibit case)"),
    "du5-us-msft-ex991": _sample(_Y, _U, _U, _U, "gold frozen 2026-10-15; all anchors verified (plan/metric-definition case)"),
    "du5-cn-gbits-call": _sample(_Y, _U, _U, _U, "gold frozen 2026-10-15; all anchors verified (negation/plan/Q&A case)"),
}


DOCUMENT_COVERAGE = {
    "schema_version": COVERAGE_SCHEMA_VERSION,
    "note": (
        "real = a named sample on the contamination list with a real local original "
        "(whether it also carries gold facts is a separate axis, so a real row is not "
        "claimed gold-backed). synthetic = a fixture that exercises the shape's logic "
        "but is not a real document. missing = no sample at all; the gap is named. "
        "schema validity is never counted as semantic coverage. Since DU5-CORPUS every "
        "cited sample carries sample_axes: original / gold / readable / selected / "
        "summary_reviewed, each yes/no/unknown with measurement evidence — the five "
        "are different axes and none is inferred from another."
    ),
    "rows": [
        # --- A share -------------------------------------------------------
        _row("a_share_annual", "A股年度报告", REAL,
             sample_ids=("cn-annual", "fresh-cn-smic-fy2025"),
             evidence=_REAL_EVIDENCE,
             note="fresh-cn-smic-fy2025 在真实原件上有金标事实（产能口径/利用率/审计意见）；"
                  "cn-annual 仅是已持有原件（survey 读过、无金标）——两者按 sample_axes 区分"),
        _row("a_share_interim", "A股半年度报告", REAL,
             sample_ids=("cn-h1", "du5-cn-iflytek-h1"), evidence=_REAL_EVIDENCE,
             note="cn-h1 有金标+回放测量；du5-cn-iflytek-h1 为 DU5 新增（亏损收窄方向、"
                  "投资vs收入、计划vs实际陷阱）"),
        _row("a_share_quarterly", "A股季度报告", REAL,
             sample_ids=("cn-q-business", "cn-q-sparse",
                         "holdout-cn-glodon-q1", "holdout-cn-yake-q1",
                         "du5-cn-fangbang-q1", "du5-cn-proya-q1"),
             evidence=_REAL_EVIDENCE,
             note="含经营叙述型与纯财务稀疏型；纯财务季报允许零选择零摘要。"
                  "du5-cn-proya-q1 是指定的期间/单位表样本（本报告期 vs 本报告期末 vs 上年度末）；"
                  "du5-cn-fangbang-q1 为双单位（元表/万叙述）经营季报"),
        # --- H share -------------------------------------------------------
        _row("hk_annual", "港股年度报告", REAL,
             sample_ids=("hk-annual", "holdout-hk-alibaba-fy2023",
                         "holdout-hk-biren-fy2025", "fresh-hk-anta-fy2025"),
             evidence=_REAL_EVIDENCE,
             note="含繁体、双语与币种口径差异"),
        _row("hk_interim", "港股中期报告", REAL,
             sample_ids=("hk-interim", "du5-hk-kingsoft-interim"),
             evidence=_REAL_EVIDENCE,
             note="hk-interim 仅原件无金标（survey 读过）；du5-hk-kingsoft-interim 有金标"
                  "（千元表 vs 百萬元叙述、US GAAP 非 IFRS、收入类别非报告分部）"),
        _row("hk_quarterly", "港股季度报告", REAL,
             sample_ids=("du5-hk-kingsoft-q1",),
             evidence=_REAL_EVIDENCE,
             note="香港主板无强制季度披露；本行为金山雲按上市规则13.09自愿刊发的季度未经审计"
                  "业绩公告（內幕消息形式）——真实港股季度披露原件，口径与A股季报不同"
                  "（止三个月、US GAAP、千元表、同比/环比双比较）。旧『本地无真实季度报告原件』"
                  "的缺口陈述已被此原件修正"),
        # --- US share ------------------------------------------------------
        _row("us_10k", "美国 10-K 年报", REAL,
             sample_ids=("us-10k", "holdout-us-mongodb-10k",
                         "holdout-us-nvidia-10k", "fresh-us-apple-10k"),
             evidence=_REAL_EVIDENCE,
             note="us-10k 经既有 normalize_document HTML 前端实测可读（5,215 units）；"
                  "两个 holdout 10-K 的旧 HTML 路径实测 units=0，新前端下尚无重放记录（见 sample_axes）"),
        _row("us_10q", "美国 10-Q 季报", REAL,
             sample_ids=("us-10q",), evidence=_REAL_EVIDENCE,
             note="仅有原件（VRSK，dayu-agent 本地绑定）：无金标、无观察记录（sample_axes 全列明）"),
        _row("us_interim", "美国半年度/中期业绩（6-K）", MISSING,
             gap="美国本土公司无半年报（10-Q即中期）；外国发行人半年业绩走6-K容器，"
                 "本地无真实6-K原件（同 sec_8k_6k_exhibit 的 REQ-3 缺口）。"
                 "du5 的 8-K/exhibit 配对是不同容器类型，不能顶替 6-K。"),
        _row("us_20f", "外国私人发行人 20-F", REAL,
             sample_ids=("us-20f",), evidence=_REAL_EVIDENCE,
             note="有金标（TAL FY2024，15 facts）但无 du-observed 回放记录；"
                  "原件为 dayu-agent 本地绑定，可读性未在现路径实测（见 sample_axes）"),
        # --- offerings -----------------------------------------------------
        _row("ipo_prospectus", "A股 IPO 招股说明书", REAL,
             sample_ids=("cn-ipo",), evidence=_REAL_EVIDENCE,
             note="仅有原件（survey 读过）：无金标、无观察记录"),
        _row("us_s1_f1", "美国 S-1 / F-1 注册说明书", MISSING,
             gap="本地无真实 S-1/F-1 原件；holdout.json 的 REQ-2 仍开放。"
                 "现有 us-20f 是年报而非注册说明书，不能替代。"),
        _row("equity_offering", "向特定对象发行/增发说明书", REAL,
             sample_ids=("cn-equity", "du5-cn-zhongmi-offering"),
             evidence=_REAL_EVIDENCE,
             note="cn-equity 含建设期一期/二期与募投上限等计划型事实；"
                  "du5-cn-zhongmi-offering 为另一公司的投资/计划/条件样本"
                  "（46,000万募集上限、业绩承诺、不产生直接经济效益否定）"),
        _row("convertible_bond", "可转债募集说明书", REAL,
             sample_ids=("cn-convertible",), evidence=_REAL_EVIDENCE,
             note="仅有原件（金禾实业，survey 读过）：无金标、无观察记录"),
        # --- IR / calls ----------------------------------------------------
        _row("investor_relations", "投资者关系活动记录", REAL,
             sample_ids=("cn-ir",), evidence=_REAL_EVIDENCE,
             note="否定、提问前提与关联方主语的高风险形态"),
        _row("earnings_call", "业绩电话会记录", REAL,
             sample_ids=("us-txt", "du5-cn-gbits-call"), evidence=_REAL_EVIDENCE,
             note="us-txt 说话人角色是主要风险点；du5-cn-gbits-call 为另一公司原语言"
                  "中文转写电话会——指定的否定/计划/问答样本（分析师前提≠公司事实、"
                  "ASR 噪声保留、计划≠已实现）"),
        _row("results_release", "业绩发布公告", REAL,
             sample_ids=("hk-release", "us-release"), evidence=_REAL_EVIDENCE,
             note="仅有原件（腾讯/微软 survey 读过）：无金标、无观察记录"),
        _row("presentation_deck", "业绩演示稿", REAL,
             sample_ids=("hk-deck",), evidence=_REAL_EVIDENCE,
             note="仅有原件（腾讯 survey 读过）：无金标、无观察记录。"
                  "du5-us-msft-ex991 是 SEC exhibit 形态的投资者演示，计入 sec_8k_6k_exhibit"),
        # --- containers / revisions ---------------------------------------
        _row("sec_8k_6k_exhibit", "8-K / 6-K 容器及其业务附件", REAL,
             sample_ids=("du5-us-msft-8k", "du5-us-msft-ex991"),
             evidence=_REAL_EVIDENCE,
             note="DU5 用真实配对填补：8-K 容器（du5-us-msft-8k）与业务附件 "
                  "EX-99.1（du5-us-msft-ex991）是两份独立原件、独立金标，"
                  "容器金标明确『主表不是完整附件』。生产层 REQ-3 的验收"
                  "（附件作为独立 SourceRef 到达、容器不当作已读内容）仍未测，"
                  "该轴保持 open，不由本行的 benchmark 覆盖冒充。"),
        _row("amended_filing", "修订稿与原稿同期间配对", MISSING,
             gap="本地无真实修订稿配对（holdout.json REQ-4）。"
                 "版本错复用目前只有合成变异覆盖，不能算真实语义覆盖。"),
        # --- low-business / administrative ---------------------------------
        _row("low_business_administrative", "低业务量/行政类文件", REAL,
             sample_ids=("cn-ir-policy", "cn-ipo-confirmation"),
             evidence=_REAL_EVIDENCE,
             note="含扫描件无原生文本与行政类跳过；不得当作“没有业务内容”。"
                  "cn-ir-policy 仅原件无金标；cn-ipo-confirmation 有金标（扫描不透明案例）"),
    ],
}


def rows_by_shape() -> dict[str, dict[str, Any]]:
    return {row["shape"]: row for row in DOCUMENT_COVERAGE["rows"]}


def _declare_row_axes() -> None:
    """Attach the per-sample axis declaration to every row (contract surface)."""

    for row in DOCUMENT_COVERAGE["rows"]:
        row["sample_axes"] = {
            sample_id: dict(SAMPLE_AXES.get(sample_id) or {
                **{axis: "unknown" for axis in AXES},
                "axis_evidence": "not declared",
            })
            for sample_id in row["sample_ids"]
        }


_declare_row_axes()


def sample_axis_report() -> dict[str, dict[str, str]]:
    """Per-sample five-axis declarations, resolved for every cited sample.

    A cited sample with no explicit declaration gets an all-unknown record so
    the absence is visible instead of silently equated with coverage.
    """

    report: dict[str, dict[str, str]] = {}
    for row in DOCUMENT_COVERAGE["rows"]:
        for sample_id in row["sample_ids"]:
            declared = SAMPLE_AXES.get(sample_id)
            if declared is None:
                declared = {axis: "unknown" for axis in AXES}
                declared["original"] = "unknown"
                declared["axis_evidence"] = "not declared"
            report[sample_id] = declared
    return report


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
    """Counts per bucket plus the schema-only list, stated apart from counts.

    ``axis_counts`` counts the five sample axes separately, because the bug
    this module had was exactly the merging of those axes into one ``REAL``.
    """

    counts = {REAL: 0, SYNTHETIC: 0, MISSING: 0}
    for row in DOCUMENT_COVERAGE["rows"]:
        counts[row["coverage"]] += 1
    axis_counts = {
        axis: {"yes": 0, "no": 0, "unknown": 0} for axis in AXES
    }
    for declared in sample_axis_report().values():
        for axis in AXES:
            value = declared.get(axis, "unknown")
            axis_counts[axis][value] = axis_counts[axis].get(value, 0) + 1
    return {
        "schema_version": COVERAGE_SCHEMA_VERSION,
        "shapes_total": len(DOCUMENT_COVERAGE["rows"]),
        "counts": counts,
        "axis_counts": axis_counts,
        "schema_only_shapes": schema_only_shapes(),
        "missing_shapes": [row["shape"] for row in DOCUMENT_COVERAGE["rows"]
                           if row["coverage"] == MISSING],
        "note": (
            "A shape in schema_only_shapes has no real-document semantic "
            "evidence. Passing schema validation for it must not be reported "
            "as coverage. axis_counts keep the five axes apart on purpose."
        ),
    }


__all__ = [
    "AXES",
    "COVERAGE_SCHEMA_VERSION",
    "DOCUMENT_COVERAGE",
    "MISSING",
    "REAL",
    "SAMPLE_AXES",
    "SYNTHETIC",
    "rows_by_shape",
    "sample_axis_report",
    "schema_only_shapes",
    "semantic_coverage_summary",
]
