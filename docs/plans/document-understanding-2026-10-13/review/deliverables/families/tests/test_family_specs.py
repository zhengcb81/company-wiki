"""du2-family-spec/1 记录的结构不变量（RED→GREEN 数据验证，不含语义判断）。"""
from __future__ import annotations

import pytest

from _support import (
    CASES_DIR, CONTEXT_SLOTS, CONTEXT_WHEN, DESIGN_STATUS, EXTENTS,
    FALLBACK_KEYS, FAMILIES, FORBIDDEN_COMPANY_TOKENS, ID_RE, LOCATIONS,
    METADATA_FIELDS, MISSING_BEHAVIORS, PAGE_REF_RE, REGEX_META_RE, REGIMES,
    REVISIONS, ROLES, SIGNAL_KINDS, SPEC_SCHEMA, VERSION_RE,
    contains_forbidden_token, load_cases, load_records,
    merge_section_aliases, record_files,
)

REQUIRED_FIELDS = [
    "schema_version", "id", "version", "applies_to", "recognition", "sections",
    "reading_questions", "context_requirements", "deprioritize", "fallback",
    "evidence_status", "case_ids",
]


def test_record_files_exist():
    assert record_files(), "records/ 至少要有一份规格"


@pytest.mark.parametrize("rid", [p.stem for p in record_files()] or ["__none__"])
def test_record_required_fields_and_enums(rid):
    records = load_records()
    if rid == "__none__":
        pytest.skip("no records yet (RED)")
    rec = records[rid]
    missing = [f for f in REQUIRED_FIELDS if f not in rec]
    assert not missing, f"{rid} 缺必填字段 {missing}"
    assert rec["schema_version"] == SPEC_SCHEMA
    assert rec["id"] == rid, "文件名与 id 必须一致"
    assert ID_RE.match(rec["id"])
    assert VERSION_RE.match(rec["version"]), "version 必须是语义版本且内容变动时变化"
    assert contains_forbidden_token(rec["id"]) is None, "id 不得含公司名"

    applies = rec["applies_to"]
    for key in ("regimes", "forms", "family", "purposes", "modifiers"):
        assert key in applies, f"{rid}.applies_to 缺 {key}"
    assert set(applies["regimes"]) <= REGIMES
    assert applies["family"] in FAMILIES
    assert applies["purposes"], "purposes 非空"
    modifiers = applies["modifiers"]
    assert set(modifiers) == {"extent", "revision"}, "生命周期修饰只有 extent/revision 两条轴"
    assert modifiers["extent"] in EXTENTS
    assert modifiers["revision"] in REVISIONS


def test_recognition_signals_are_phrases_not_dsl():
    for rid, rec in load_records().items():
        pos = rec["recognition"]["positive"]
        assert pos, f"{rid} recognition.positive 非空"
        for item in pos:
            signal = item["signal"]
            assert set(signal) == {"kind", "value", "field"}, f"{rid} signal 字段固定 kind/value/field"
            assert signal["kind"] in SIGNAL_KINDS
            assert item["location"] in LOCATIONS
            assert item["reason"].strip(), f"{rid} 每条识别信号要有非空理由"
            value = signal["value"]
            assert "\n" not in value and value.strip() == value
            if signal["kind"] == "metadata_equals":
                assert signal["field"] in METADATA_FIELDS
            else:
                assert signal["field"] is None, "literal_phrase 不带 field"
                assert not REGEX_META_RE.search(value), f"{rid} literal_phrase 只交短语，不交 regex/DSL: {value!r}"
            assert not PAGE_REF_RE.search(value), f"{rid} 识别信号不得含固定页码: {value!r}"
            token = contains_forbidden_token(value)
            assert token is None, f"{rid} 识别信号含公司特判词 {token!r}"
        counterexamples = rec["recognition"]["counterexamples"]
        assert counterexamples, f"{rid} 必须有反例"
        for text in counterexamples:
            assert text.strip(), "反例非空"
            assert not PAGE_REF_RE.search(text), f"{rid} 反例不得把固定页码当执行信号"
            token = contains_forbidden_token(text)
            assert token is None, f"{rid} 反例含公司特判词 {token!r}"


def test_sections_roles_aliases_and_questions():
    for rid, rec in load_records().items():
        sections = rec["sections"]
        assert isinstance(sections, list)
        if rid == "lifecycle_revision_overlay":
            assert len(sections) <= 2, "摘要是正交修饰，不得复制全部章节策略"
        assert sections, f"{rid} sections 非空"
        seen_pairs = set()
        all_aliases = [a for s in sections for a in s["aliases"]]
        assert len(all_aliases) == len(set(all_aliases)), (
            f"{rid} 同一记录内别名不得重复登记（重复规则要去重，别名合并不丢≠允许重复）"
        )
        for section in sections:
            assert section["role"] in ROLES, f"{rid} role 只用 DU/1 角色，新 role 仅可提案"
            assert isinstance(section["aliases"], list) and section["aliases"], f"{rid} aliases 非空"
            for alias in section["aliases"]:
                assert alias.strip()
                assert not PAGE_REF_RE.search(alias)
                assert contains_forbidden_token(alias) is None, f"{rid} 别名不得含公司名"
            assert section["priority"] in (1, 2, 3)
            assert section["questions"] and all(q.strip() for q in section["questions"])
            heading_path = section["heading_path"]
            assert isinstance(heading_path, list)
            for level in heading_path:
                assert isinstance(level, list) and level, "heading_path 每层数组内别名 OR，空数组表示无层级限制"
                for alias in level:
                    assert isinstance(alias, str) and alias.strip()
                    assert contains_forbidden_token(alias) is None
            key = (section["role"], tuple(tuple(level) for level in heading_path))
            assert key not in seen_pairs, f"{rid} 存在完全重复的 role+heading_path 条目"
            seen_pairs.add(key)


def test_duplicate_role_aliases_are_preserved_when_merged():
    for rid, rec in load_records().items():
        sections = rec["sections"]
        merged = merge_section_aliases(sections)
        expected = sorted({a for s in sections for a in s["aliases"]})
        assert sorted({a for v in merged.values() for a in v}) == expected, (
            f"{rid} 同 role 别名合并不允许丢块（R01 类缺陷）"
        )
        for role, aliases in merged.items():
            assert aliases, f"{rid} 合并后 role={role} 别名为空"


def test_reading_questions_and_context_requirements():
    for rid, rec in load_records().items():
        assert rec["reading_questions"] and all(q.strip() for q in rec["reading_questions"])
        reqs = rec["context_requirements"]
        assert reqs, f"{rid} context_requirements 非空"
        period_bound = False
        for req in reqs:
            assert req["when"] in CONTEXT_WHEN
            assert set(req["slots"]) <= CONTEXT_SLOTS, f"{rid} slots 超出固定枚举"
            assert req["slots"], f"{rid} slots 非空"
            assert req["missing_behavior"] in MISSING_BEHAVIORS
            assert req["reason"].strip(), f"{rid} context_requirement 必须有非空理由"
            if req["when"] == "always_for_assertion" and "period" in req["slots"]:
                period_bound = True
        assert period_bound, f"{rid} scope/生命周期：always_for_assertion 必须绑定 period"


def test_deprioritize_and_fallback():
    for rid, rec in load_records().items():
        for item in rec["deprioritize"]:
            assert set(item) == {"content", "unless"}
            assert item["content"].strip() and item["unless"].strip(), f"{rid} 降权项须写明内容与例外"
        fallback = rec["fallback"]
        assert set(fallback) == FALLBACK_KEYS
        for key, text in fallback.items():
            assert text.strip(), f"{rid} fallback.{key} 非空"


def test_evidence_status_and_case_references():
    cases = load_cases()
    for rid, rec in load_records().items():
        ev = rec["evidence_status"]
        assert ev["design"] in DESIGN_STATUS
        assert isinstance(ev["real_samples"], list)
        assert isinstance(ev["missing_shapes"], list)
        for cid in ev["real_samples"]:
            assert cid in rec["case_ids"], f"{rid} evidence_status.real_samples 必须也是 case_ids"
        assert rec["case_ids"], f"{rid} 至少关联一个 case"
        for cid in rec["case_ids"]:
            assert cid in cases, f"{rid} 引用的 case {cid} 不存在"
        for cid in ev["real_samples"]:
            assert cases[cid]["kind"] == "real_excerpt", f"{rid} real_samples 必须是真实摘录 case"
