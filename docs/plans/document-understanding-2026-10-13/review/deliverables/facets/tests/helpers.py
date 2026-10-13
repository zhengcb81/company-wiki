"""Shared loaders and frozen vocabularies for DU2-FACETS structural tests.

Pure data loading only: no network, no clock, no config, no LLM. The tests in this
directory check structural invariants of the facet/case data package. They never
execute natural-language inference and never generate summaries.

The vocabularies below are frozen copies of the public contracts in
docs/plans/document-understanding-2026-10-13/review/INTERFACES.md (du2-facet-spec/1,
du2-facet-index/1, du2-reading-case/1) plus the DU/1 unit-kind vocabulary that already
exists in src/company_wiki/document_normalization. Deviations are recorded in the
lane handoff (.planning/du2-facets/handoff.md).
"""

from __future__ import annotations

import json
import re
from pathlib import Path

TESTS_DIR = Path(__file__).resolve().parent
FACETS_ROOT = TESTS_DIR.parent
RECORDS_DIR = FACETS_ROOT / "records"
CASES_DIR = FACETS_ROOT / "cases"
C_CHECKS_PATH = FACETS_ROOT / "c_verification" / "real_excerpt_checks.json"
INDEX_PATH = FACETS_ROOT / "index.json"

SCHEMA_FACET = "du2-facet-spec/1"
SCHEMA_CASE = "du2-reading-case/1"
SCHEMA_INDEX = "du2-facet-index/1"
SCHEMA_C_CHECKS = "du2-facet-c-checks/1"

MECHANISM_IDS = {
    "generic",
    "subscription",
    "consumption",
    "store_network",
    "manufacturing",
    "biopharma",
    "cdmo",
}

SLOT_NAMES = {
    "subject",
    "product",
    "project",
    "geography",
    "period",
    "role",
    "modality",
    "stage",
    "quantity",
    "unit",
    "denominator",
    "condition",
}

REQUIRED_WHEN = {
    "always_for_assertion",
    "quantity_emitted",
    "project_emitted",
    "explicit_condition_present",
}

MISSING_BEHAVIOR = {"unknown", "partial", "deferred"}

FACT_IMPORTANCE = {"required_business", "disposition_context", "correctness_if_emitted"}

DISPOSITIONS = {"read", "generic_read", "eligible_skip_after_read", "needs_source", "unread"}

MUTATION_DIMENSIONS = {
    "subject",
    "period",
    "unit",
    "scope",
    "modality",
    "condition",
    "negation",
    "project",
    "role",
    "geography",
    "denominator",
    "stage",
}

SPEC_STATUS = {"implemented", "proposed"}
EVIDENCE_STATUS = {"real", "synthetic_only", "missing"}

# DU/1 unit kinds produced by the existing normalization front ends.
UNIT_KINDS = {
    "pdf_text_block",
    "pdf_table_row",
    "pdf_table_qa_fragment",
    "transcript_speaker_block",
    "official_json_field",
    "html_heading",
    "html_paragraph",
    "html_list_item",
    "html_table_cell",
    "html_footnote",
    "pptx_paragraph",
    "pptx_table_cell",
    "pptx_notes_paragraph",
    "pptx_image_ocr_line",
    "docx_heading",
    "docx_paragraph",
    "docx_table_cell",
}

RECORD_REQUIRED_FIELDS = {
    "schema_version",
    "id",
    "version",
    "business_questions",
    "applicable_mechanisms",
    "positive_evidence",
    "required_context",
    "confusions",
    "absence_rules",
    "summary_focus",
    "case_ids",
}

CASE_REQUIRED_FIELDS = {"case_id", "kind", "source", "observation", "expectations"}

RECORD_REQUIRED_KEYS = {"assertion", "slots", "required_when", "missing_behavior", "reason"}
POSITIVE_EVIDENCE_KEYS = {"description", "unit_kinds", "signals"}
CONFUSION_KEYS = {"source_meaning", "wrong_assertion", "why_wrong", "required_context_slots"}
FACT_KEYS = {"id", "objective", "importance", "any_support_sets", "must_preserve", "must_not_assert"}
UNIT_KEYS = {"unit_id", "locator", "anchor", "page", "text", "role", "hints"}
MUTATION_KEYS = {"id", "change", "dimension", "expected_failure", "reason"}

# Frozen deliverable shape of this package. A test that merely globbed the data
# directory would silently pass while the package is empty, so the expected ids
# are pinned here.
EXPECTED_RECORD_IDS = [
    "facet_core_business",
    "facet_industry_competition",
    "facet_new_business",
    "facet_overseas",
    "facet_customer_orders",
    "facet_capacity_projects",
    "facet_operating_metrics",
    "facet_risk_denial",
    "semantic_stage_progression",
    "semantic_capacity_project",
    "mechanism_subscription_consumption",
    "mechanism_store_network",
    "mechanism_manufacturing",
    "mechanism_biopharma_cdmo",
]

EXPECTED_CASE_IDS = [
    "real_cn_equity_capacity_phasing",
    "real_cn_convertible_capacity_funding",
    "real_cn_ir_premise_denial",
    "real_hk_annual_store_network",
    "real_us_release_subscription",
    "real_us_call_roles",
    "syn_stage_ladder",
    "syn_capacity_project",
    "syn_negation_scope",
    "syn_quantity_slots",
    "syn_exit_low_information",
    "syn_exit_no_business",
    "syn_exit_no_answer",
    "syn_financial_numbers",
    "syn_qualitative_cooperation",
    "syn_qualitative_funding",
]

RECORD_FILE_NAMES = {rid: f"{rid}.json" for rid in EXPECTED_RECORD_IDS}
CASE_FILE_NAMES = {cid: f"{cid}.json" for cid in EXPECTED_CASE_IDS}

ID_PATTERN = re.compile(r"^[a-z0-9_]+$")
VERSION_PATTERN = re.compile(r"^[0-9]+\.[0-9]+\.[0-9]+$")
SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")
REGEX_METACHAR_PATTERN = re.compile(r"[\^\$\*\+\?\{\}\[\]\|\\()]")

# Concrete company / product tokens that must not appear in mechanism specs:
# mechanisms describe generic commercial mechanics, never a company's product list.
FORBIDDEN_COMPANY_TOKENS = [
    "microsoft",
    "msft",
    "miniso",
    "top toy",
    "azure",
    "windows",
    "xbox",
    "linkedin",
    "dynamics",
    "名创",
    "恒锋",
    "金禾",
    "万润",
    "中微",
    "世华",
    "鼎龙",
    "腾讯",
    "英伟达",
    "nvidia",
    "三氯蔗糖",
    "吡啶盐",
    "沸石",
    "泮托拉唑",
]

ABSSENCE_MARKERS = {
    "undisclosed": re.compile(r"未披露|未提及|未说明|未给出|没有披露"),
    "unanswered": re.compile(r"未答|未回答|未回应|回避|拒绝回答|未正面回答"),
    "denial": re.compile(r"否定|否认|明确否认|明确否定"),
    "unread": re.compile(r"未读|未覆盖|读取缺口|unread|deferred|未识别到"),
}

QUOTE_BUDGET_BYTES_PER_SOURCE = 8 * 1024
PERSISTENT_BUDGET_BYTES = 512 * 1024


def load_json(path: Path):
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def record_path(record_id: str) -> Path:
    return RECORDS_DIR / RECORD_FILE_NAMES[record_id]


def case_path(case_id: str) -> Path:
    return CASES_DIR / CASE_FILE_NAMES[case_id]


def load_record(record_id: str):
    path = record_path(record_id)
    assert path.exists(), f"missing record file: {path}"
    return load_json(path)


def load_case(case_id: str):
    path = case_path(case_id)
    assert path.exists(), f"missing case file: {path}"
    return load_json(path)


def normalized_quote(text: str) -> str:
    return re.sub(r"\s+", "", text)


def utf8_len(text: str) -> int:
    return len(text.encode("utf-8"))
