"""Which originals the project has already inspected, and which are genuinely new.

A benchmark that reports "generalisation" is only honest if it can name the
documents its own rules were tuned against. This module is that list. It is the
machine-readable half of ``holdout.json`` plus everything inspected after that
file was written, and it is deliberately explicit rather than inferred: a
sample's status is a human judgement about what was read, and a heuristic that
guessed it would be exactly the kind of self-certification the benchmark exists
to prevent.

Two statuses only:

``contaminated``
    the original (or its content) was read, quoted, tabulated, or used to make
    a routing/selection/threshold decision. It may still be *regression*
    evidence — that is the point of keeping it — but it may never be presented
    as a fresh generalisation result.

``fresh``
    the original and its company appear nowhere in the benchmark's gold,
    findings, rule design or tuning discussion at the time the support set was
    frozen. ``used_for`` is empty by construction, and a fresh sample that is
    later used for tuning must be moved to ``contaminated`` in the same change.

The module reads no files and imports nothing from ``company_wiki``: the list is
data, and a test asserts it stays consistent with the packaged gold.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from typing import Any

CONTAMINATION_SCHEMA_VERSION = "du-contamination/1"

#: Reasons a sample is contaminated. Kept as a closed vocabulary so that a new
#: entry cannot be added with a vague reason.
USED_FOR_SURVEY = "root_survey"
USED_FOR_RULE_TUNING = "rule_tuning"
USED_FOR_THRESHOLD_TUNING = "threshold_tuning"
USED_FOR_GOLD_ITERATION = "gold_iteration"
USED_FOR_DIAGNOSIS = "diagnosis"
USED_FOR_LEGIBILITY_CONTROL = "legibility_control"
#: The *company* (not this document) was already used by the benchmark, so the
#: document may add shape coverage but company-blind generalisation can never
#: be claimed for it. Added by DU5-CORPUS for documents that are new while
#: their issuer is not.
USED_FOR_COMPANY_PRIOR_USE = "company_prior_use"

CONTAMINATION = {
    "schema_version": CONTAMINATION_SCHEMA_VERSION,
    "note": (
        "Every original the project has already read. 'contaminated' is not an "
        "accusation: these samples remain valid regression evidence. It only "
        "means they cannot be reported as fresh generalisation."
    ),
    "fresh_split_note": (
        "Samples whose originals and companies were unused when their support "
        "set was frozen. See support_set_frozen_before_output in each gold file."
    ),
    "samples": [
        # --- the 20 ROOT survey samples (development gold) -------------------
        {"sample_id": "cn-h1", "company": "中微公司", "market": "CN",
         "status": "contaminated", "used_for": [USED_FOR_SURVEY, USED_FOR_RULE_TUNING],
         "why": "used in the ROOT survey and to tune selector rules"},
        {"sample_id": "cn-annual", "company": "中微公司", "market": "CN",
         "status": "contaminated", "used_for": [USED_FOR_SURVEY],
         "why": "read in the ROOT survey"},
        {"sample_id": "cn-ipo", "company": "中微公司", "market": "CN",
         "status": "contaminated", "used_for": [USED_FOR_SURVEY],
         "why": "read in the ROOT survey"},
        {"sample_id": "cn-q-business", "company": "中微公司", "market": "CN",
         "status": "contaminated", "used_for": [USED_FOR_RULE_TUNING],
         "why": "carried the rule-tuning decision about quarterly reports"},
        {"sample_id": "cn-q-sparse", "company": "世华科技", "market": "CN",
         "status": "contaminated", "used_for": [USED_FOR_RULE_TUNING],
         "why": "paired control for the quarterly-report rule decision"},
        {"sample_id": "cn-equity", "company": "恒锋工具", "market": "CN",
         "status": "contaminated", "used_for": [USED_FOR_RULE_TUNING],
         "why": "subject of the routing/budget ablation"},
        {"sample_id": "cn-convertible", "company": "金禾实业", "market": "CN",
         "status": "contaminated", "used_for": [USED_FOR_SURVEY],
         "why": "read in the ROOT survey"},
        {"sample_id": "cn-ipo-confirmation", "company": "鼎龙股份", "market": "CN",
         "status": "contaminated", "used_for": [USED_FOR_DIAGNOSIS],
         "why": "used to diagnose the title-regex trap"},
        {"sample_id": "cn-ir", "company": "万润股份", "market": "CN",
         "status": "contaminated", "used_for": [USED_FOR_DIAGNOSIS],
         "why": "used to diagnose the negation/question case"},
        {"sample_id": "cn-ir-policy", "company": "万润股份", "market": "CN",
         "status": "contaminated", "used_for": [USED_FOR_DIAGNOSIS],
         "why": "used to identify the administrative-skip class"},
        {"sample_id": "hk-annual", "company": "名创优品", "market": "HK",
         "status": "contaminated", "used_for": [USED_FOR_DIAGNOSIS],
         "why": "subject of the bilingual store-table diagnosis"},
        {"sample_id": "hk-interim", "company": "名创优品", "market": "HK",
         "status": "contaminated", "used_for": [USED_FOR_SURVEY],
         "why": "read in the ROOT survey"},
        {"sample_id": "hk-ipo", "company": "名创优品", "market": "HK",
         "status": "contaminated", "used_for": [USED_FOR_SURVEY],
         "why": "read in the ROOT survey"},
        {"sample_id": "hk-release", "company": "腾讯控股", "market": "HK",
         "status": "contaminated", "used_for": [USED_FOR_SURVEY],
         "why": "read in the ROOT survey"},
        {"sample_id": "hk-deck", "company": "腾讯控股", "market": "HK",
         "status": "contaminated", "used_for": [USED_FOR_SURVEY],
         "why": "read in the ROOT survey"},
        {"sample_id": "us-10k", "company": "MICROSOFT CORP", "market": "US",
         "status": "contaminated", "used_for": [USED_FOR_DIAGNOSIS],
         "why": "read into the design findings; the 4/8 critical gap is measured on it"},
        {"sample_id": "us-10q", "company": "VRSK", "market": "US",
         "status": "contaminated", "used_for": [USED_FOR_DIAGNOSIS],
         "why": "read into the design findings"},
        {"sample_id": "us-20f", "company": "TAL", "market": "US",
         "status": "contaminated", "used_for": [USED_FOR_DIAGNOSIS],
         "why": "read into the design findings"},
        {"sample_id": "us-release", "company": "MICROSOFT CORP", "market": "US",
         "status": "contaminated", "used_for": [USED_FOR_SURVEY],
         "why": "read in the ROOT survey"},
        {"sample_id": "us-txt", "company": "MICROSOFT CORP", "market": "US",
         "status": "contaminated", "used_for": [USED_FOR_DIAGNOSIS],
         "why": "used to diagnose speaker-role loss in the transcript path"},
        # --- previously inspected holdout ------------------------------------
        {"sample_id": "holdout-cn-glodon-q1", "company": "广联达", "market": "CN",
         "status": "contaminated", "used_for": [USED_FOR_GOLD_ITERATION],
         "why": "holdout gold authored 2026-10-13; company and trap list appear in holdout.json"},
        {"sample_id": "holdout-cn-yake-q1", "company": "雅克科技", "market": "CN",
         "status": "contaminated", "used_for": [USED_FOR_GOLD_ITERATION],
         "why": "holdout gold authored 2026-10-13; company and trap list appear in holdout.json"},
        {"sample_id": "holdout-hk-alibaba-fy2023", "company": "阿里巴巴", "market": "HK",
         "status": "contaminated", "used_for": [USED_FOR_GOLD_ITERATION],
         "why": "holdout gold authored 2026-10-13; company and trap list appear in holdout.json"},
        {"sample_id": "holdout-hk-biren-fy2025", "company": "壁仞科技", "market": "HK",
         "status": "contaminated", "used_for": [USED_FOR_GOLD_ITERATION],
         "why": "holdout gold authored 2026-10-13; company and trap list appear in holdout.json"},
        {"sample_id": "holdout-us-mongodb-10k", "company": "MongoDB, Inc", "market": "US",
         "status": "contaminated", "used_for": [USED_FOR_GOLD_ITERATION],
         "why": "holdout gold authored 2026-10-13; company and trap list appear in holdout.json"},
        {"sample_id": "holdout-us-nvidia-10k", "company": "NVIDIA CORP", "market": "US",
         "status": "contaminated", "used_for": [USED_FOR_GOLD_ITERATION],
         "why": "holdout gold authored 2026-10-13; company and trap list appear in holdout.json"},
        {"sample_id": "hk-annual-mojibake", "company": "小米集團－Ｗ", "market": "HK",
         "status": "contaminated", "used_for": [USED_FOR_LEGIBILITY_CONTROL],
         "why": "supplied the measured legibility control (2.663% unusable blocks)"},
        # --- genuinely fresh: first inspection is this card ------------------
        {"sample_id": "fresh-cn-smic-fy2025", "company": "中芯国际", "market": "CN",
         "status": "fresh", "used_for": [],
         "why": "company and original absent from every prior gold, finding and tuning note"},
        {"sample_id": "fresh-hk-anta-fy2025", "company": "安踏體育", "market": "HK",
         "status": "fresh", "used_for": [],
         "why": "company and original absent from every prior gold, finding and tuning note"},
        {"sample_id": "fresh-us-apple-10k", "company": "Apple Inc", "market": "US",
         "status": "fresh", "used_for": [],
         "why": "company and original absent from every prior gold, finding and tuning note"},
        # --- DU5-CORPUS set (frozen 2026-10-15, see du5_manifest.json) --------
        {"sample_id": "du5-cn-iflytek-h1", "company": "科大讯飞", "market": "CN",
         "status": "fresh", "used_for": [],
         "why": "company and original absent from every prior gold, finding and "
                "tuning note; searched .planning, docs/plans and docs/implementation "
                "2026-10-15 before freezing"},
        {"sample_id": "du5-cn-fangbang-q1", "company": "方邦股份", "market": "CN",
         "status": "fresh", "used_for": [],
         "why": "this Q1 original and its content were never read before freezing; "
                "the company name only appears in a captured roadshow participant "
                "list (cross-market-rf-e2e-2026-10-08) and in raw-duplicate-audit "
                "path metadata for an unrelated research PDF"},
        {"sample_id": "du5-cn-proya-q1", "company": "珀莱雅", "market": "CN",
         "status": "fresh", "used_for": [],
         "why": "company and original absent from every prior gold, finding and "
                "tuning note; searched 2026-10-15 before freezing"},
        {"sample_id": "du5-cn-zhongmi-offering", "company": "中密控股", "market": "CN",
         "status": "fresh", "used_for": [],
         "why": "this prospectus and its content were never read before freezing; a "
                "different document of the company (a meeting audio) was processed by "
                "the 2026-07-09 meeting-converter e2e (metadata + translation output "
                "only, never benchmark tuning)"},
        {"sample_id": "du5-cn-gbits-call", "company": "吉比特", "market": "CN",
         "status": "fresh", "used_for": [],
         "why": "this call transcript and its content were never read before freezing; "
                "the company name only appears in raw-duplicate-audit path metadata "
                "for annual reports"},
        {"sample_id": "du5-hk-kingsoft-interim", "company": "金山雲", "market": "HK",
         "status": "contaminated", "used_for": [USED_FOR_LEGIBILITY_CONTROL],
         "why": "du-bench sample selection probed this company's extraction quality "
                "(.planning/du-bench/progress.md: '壁仞科技 and 金山雲 extract cleanly, "
                "so 壁仞 was used'); this interim report's content was never used for "
                "rule or gold tuning — it fills the hk_interim shape, not a blind claim"},
        {"sample_id": "du5-hk-kingsoft-q1", "company": "金山雲", "market": "HK",
         "status": "contaminated", "used_for": [USED_FOR_LEGIBILITY_CONTROL],
         "why": "same company-level inspection as du5-hk-kingsoft-interim "
                "(.planning/du-bench/progress.md extraction probe); this quarterly "
                "results announcement fills the hk_quarterly shape"},
        {"sample_id": "du5-us-msft-8k", "company": "MICROSOFT CORP", "market": "US",
         "status": "contaminated", "used_for": [USED_FOR_COMPANY_PRIOR_USE],
         "why": "the 8-K file itself was never read before this card, but the company "
                "already sits in benchmark gold/findings via us-10k/us-txt/us-release, "
                "so it fills the sec_8k container shape and is never a fresh claim"},
        {"sample_id": "du5-us-msft-ex991", "company": "MICROSOFT CORP", "market": "US",
         "status": "contaminated", "used_for": [USED_FOR_COMPANY_PRIOR_USE],
         "why": "the exhibit file itself was never read before this card, but the "
                "company is already diagnosed in the benchmark; it fills the "
                "sec_exhibit business-document shape"},
    ],
}


def contamination_by_id() -> dict[str, dict[str, Any]]:
    return {row["sample_id"]: row for row in CONTAMINATION["samples"]}


def contraction_covered_sample_ids() -> set[str]:
    """Every sample id on the list, whatever its status."""

    return set(contamination_by_id())


def contaminated_sample_ids() -> set[str]:
    return {
        row["sample_id"] for row in CONTAMINATION["samples"]
        if row["status"] == "contaminated"
    }


def fresh_sample_ids() -> set[str]:
    return {
        row["sample_id"] for row in CONTAMINATION["samples"] if row["status"] == "fresh"
    }


def support_set_digest(gold: Mapping[str, Any]) -> str:
    """A content digest of one gold record's frozen business-fact support set.

    Only the support-bearing fields are hashed, so a later wording change to a
    ``reason`` does not look like a support-set change while a changed quote, a
    removed support set or a re-graded fact does.
    """

    facts = []
    for fact in gold.get("facts") or []:
        facts.append(
            {
                "id": fact.get("id"),
                "importance": fact.get("importance"),
                "target_kind": fact.get("target_kind"),
                "quantity_basis": fact.get("quantity_basis"),
                "modality": fact.get("modality"),
                "role": fact.get("role"),
                "must_preserve": list(fact.get("must_preserve") or []),
                "must_not_assert": list(fact.get("must_not_assert") or []),
                "any_support_sets": [
                    [
                        {
                            "page": anchor.get("page"),
                            "line": anchor.get("line"),
                            "location_kind": anchor.get("location_kind"),
                            "exact_quote": anchor.get("exact_quote"),
                        }
                        for anchor in support_set
                    ]
                    for support_set in fact.get("any_support_sets") or []
                ],
            }
        )
    facts.sort(key=lambda row: str(row["id"]))
    payload = json.dumps(
        {"sample_id": gold.get("sample_id"),
         "source_sha256": gold.get("source_sha256"),
         "facts": facts},
        ensure_ascii=False, sort_keys=True, separators=(",", ":"),
    )
    return hashlib.sha256(payload.encode("utf8")).hexdigest()


__all__ = [
    "CONTAMINATION",
    "CONTAMINATION_SCHEMA_VERSION",
    "contaminated_sample_ids",
    "contamination_by_id",
    "contraction_covered_sample_ids",
    "fresh_sample_ids",
    "support_set_digest",
]
