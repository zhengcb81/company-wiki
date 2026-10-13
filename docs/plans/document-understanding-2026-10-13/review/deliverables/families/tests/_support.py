"""DU2-FAMILIES 数据包结构校验 helper（本包自有，非第二 registry/router/orbe）。

只做 du2-family-spec/1、du2-reading-case/1、du2-family-index/1 的结构不变量检查：
枚举、引用、非空理由、配额、别名保留。不做语义蕴含判断，不执行生产路由。
"""
from __future__ import annotations

import json
import re
from pathlib import Path

PKG_ROOT = Path(__file__).resolve().parents[1]
RECORDS_DIR = PKG_ROOT / "records"
CASES_DIR = PKG_ROOT / "cases"
INDEX_PATH = PKG_ROOT / "index.json"

SPEC_SCHEMA = "du2-family-spec/1"
CASE_SCHEMA = "du2-reading-case/1"
INDEX_SCHEMA = "du2-family-index/1"

ROLES = {
    "business", "industry", "management_discussion", "outlook", "risk",
    "operating_metrics", "fundraising", "financial_notes", "questions",
    "administrative", "unknown",
}
REGIMES = {"cn_exchange", "hkex", "sec", "other", "unknown"}
FAMILIES = {
    "annual", "interim", "quarterly", "prospectus", "offering",
    "results_release", "presentation", "investor_qa", "earnings_call",
    "administrative", "unknown",
}
EXTENTS = {"full", "summary", "unknown"}
REVISIONS = {"original", "amended", "supplement", "unknown"}
SIGNAL_KINDS = {"literal_phrase", "metadata_equals"}
METADATA_FIELDS = {"title", "regime", "form_type", "declared_kind", "mime_type", "language", "revision"}
LOCATIONS = {"metadata", "cover", "toc", "body", "attachment"}
CONTEXT_WHEN = {"always_for_assertion", "quantity_emitted", "project_emitted", "explicit_condition_present"}
CONTEXT_SLOTS = {
    "subject", "product", "project", "geography", "period", "role",
    "modality", "stage", "quantity", "unit", "denominator", "condition",
}
MISSING_BEHAVIORS = {"unknown", "partial", "deferred"}
DESIGN_STATUS = {"verified", "proposed"}
INDEX_SPEC_STATUS = {"implemented", "proposed"}
INDEX_EVIDENCE_STATUS = {"real", "synthetic_only", "missing"}
INTEGRATION_STATUS = {"not_integrated"}
CASE_KINDS = {"synthetic", "real_excerpt"}
DISPOSITIONS = {"read", "generic_read", "eligible_skip_after_read", "needs_source", "unread"}
IMPORTANCE = {"critical", "normal"}
FALLBACK_KEYS = {"unread", "ambiguous", "no_business"}

ID_RE = re.compile(r"^[a-z0-9][a-z0-9_]*$")
VERSION_RE = re.compile(r"^\d+\.\d+\.\d+$")
# 公司/证券特判禁入执行信号：识别信号与策略字段不得含公司名或固定页码
FORBIDDEN_COMPANY_TOKENS = [
    "中微", "世华", "金禾", "恒锋", "鼎龙", "万润", "名创", "腾讯", "微软",
    "Microsoft", "Tencent", "MINISO", "Azure", "Verisk", "VRSK", "TAL",
    "好未来", "新东方", "永輝", "永辉",
]
PAGE_REF_RE = re.compile(r"第\s*\d+\s*页|\bp\s?\d{1,4}\b|page\s+\d+|pp?\.\s?\d+", re.I)
REGEX_META_RE = re.compile(r"[\\^$()\[\]|*+?{}]")

QUOTE_QUOTA_BYTES = 8 * 1024


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def record_files() -> list[Path]:
    return sorted(RECORDS_DIR.glob("*.json"))


def case_files() -> list[Path]:
    return sorted(CASES_DIR.glob("*.json"))


def load_records() -> dict[str, dict]:
    return {p.stem: load_json(p) for p in record_files()}


def load_cases() -> dict[str, dict]:
    return {p.stem: load_json(p) for p in case_files()}


def merge_section_aliases(sections: list[dict]) -> dict[str, list[str]]:
    """同 role 别名可组合且不丢：返回 role -> 去重保序别名并集。"""
    merged: dict[str, list[str]] = {}
    for section in sections:
        role = section["role"]
        bucket = merged.setdefault(role, [])
        for alias in section["aliases"]:
            if alias not in bucket:
                bucket.append(alias)
    return merged


def quote_chars_per_source(cases: dict[str, dict]) -> dict[str, int]:
    totals: dict[str, int] = {}
    for case in cases.values():
        key = case["source"].get("source_sha256") or f"synthetic:{case['case_id']}"
        for unit in case["observation"]["units"]:
            totals[key] = totals.get(key, 0) + len(unit.get("text") or "")
    return totals


def contains_forbidden_token(text: str) -> str | None:
    """公司/证券特判词检查：中文按子串，拉丁词按整词边界（避免 Capitalization 误命中 TAL）。"""
    lowered = text.lower()
    for token in FORBIDDEN_COMPANY_TOKENS:
        if re.search(r"[^\x00-\x7f]", token):
            if token.lower() in lowered:
                return token
        else:
            if re.search(rf"\b{re.escape(token.lower())}\b", lowered):
                return token
    return None
