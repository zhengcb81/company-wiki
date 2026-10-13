"""du2-reading-case/1 case 结构不变量与引用配额。"""
from __future__ import annotations

import re

import pytest

from _support import (
    CASE_KINDS, CASE_SCHEMA, CONTEXT_SLOTS, DISPOSITIONS, ID_RE, IMPORTANCE,
    QUOTE_QUOTA_BYTES, ROLES, case_files, load_cases, load_records,
    quote_chars_per_source,
)

SHA_RE = re.compile(r"^[0-9a-f]{64}$")
CASE_ID_RE = re.compile(r"^[a-z0-9][a-z0-9_-]*$")
CASE_REQUIRED = ["case_id", "kind", "source", "observation", "expectations"]
SOURCE_REQUIRED = ["sample_id", "source_sha256", "origin", "local_binding_key"]
CLAIM_SLOTS = {"subject", "modality", "quantity", "unit", "period", "condition"}


def test_case_files_exist():
    assert case_files(), "cases/ 至少要有一个 case"


@pytest.mark.parametrize("cid", [p.stem for p in case_files()] or ["__none__"])
def test_case_required_fields(cid):
    cases = load_cases()
    if cid == "__none__":
        pytest.skip("no cases yet (RED)")
    case = cases[cid]
    missing = [f for f in CASE_REQUIRED if f not in case]
    assert not missing, f"{cid} 缺必填字段 {missing}"
    assert case["schema_version"] == CASE_SCHEMA
    assert case["case_id"] == cid
    assert CASE_ID_RE.match(cid), "case_id 只用小写字母/数字/下划线/连字符"
    assert case["kind"] in CASE_KINDS

    source = case["source"]
    assert all(k in source for k in SOURCE_REQUIRED), f"{cid} source 缺字段"
    sha = source["source_sha256"]
    if case["kind"] == "real_excerpt":
        assert sha and SHA_RE.match(sha), f"{cid} 真实摘录必须固定原 SHA"
    else:
        assert sha is None or SHA_RE.match(sha or "")
    assert isinstance(source["origin"], dict) and source["origin"], f"{cid} origin 记录已核出处"
    assert source["local_binding_key"]

    obs = case["observation"]
    assert isinstance(obs.get("metadata"), dict) and obs["metadata"], f"{cid} observation.metadata 非空"
    units = obs["units"]
    assert units, f"{cid} observation.units 非空"
    ids = [u["unit_id"] for u in units]
    assert len(ids) == len(set(ids)), f"{cid} unit_id 唯一（仅 case 内引用键）"
    for unit in units:
        assert isinstance(unit.get("locator"), (str, type(None)))
        legal_empty = bool(unit.get("hints", {}).get("native_text_empty"))
        if not legal_empty:
            assert unit.get("text", "").strip(), f"{cid} unit 文本非空（空文本须显式 native_text_empty 标记）"
        assert unit["role"] in ROLES, f"{cid} unit.role 用 DU/1 角色"
        anchor = unit.get("anchor")
        if case["kind"] == "real_excerpt":
            assert anchor, f"{cid} 真实摘录必须给 quote anchor"
            assert set(anchor) == {"physical_page", "line", "exact_quote"}
            quote = anchor["exact_quote"]
            # 合法空值：扫描/空原生文本单元以 hints.native_text_empty 显式标记
            legal_empty = bool(unit.get("hints", {}).get("native_text_empty"))
            if legal_empty:
                assert unit.get("text", "") == "", f"{cid} native_text_empty 单元文本必须为空"
            else:
                assert quote.strip(), f"{cid} exact_quote 非空"
                assert anchor["physical_page"] is not None or anchor["line"] is not None, (
                    f"{cid} locator 为空时必须给页或行 + exact_quote"
                )
                norm_text = re.sub(r"\s+", " ", unit["text"])
                norm_quote = re.sub(r"\s+", " ", quote)
                assert norm_quote in norm_text, f"{cid} exact_quote 必须能在 unit 文本中回放"


def test_expectations_facts_and_support_sets():
    cases = load_cases()
    for cid, case in cases.items():
        exp = case["expectations"]
        assert isinstance(exp.get("routing_notes"), list)
        facts = exp["facts"]
        assert facts, f"{cid} facts 非空"
        seen = set()
        unit_ids = {u["unit_id"] for u in case["observation"]["units"]}
        for fact in facts:
            assert fact["id"] not in seen, f"{cid} fact id 唯一"
            seen.add(fact["id"])
            assert fact["objective"].strip(), f"{cid} fact.objective 非空"
            assert fact["importance"] in IMPORTANCE
            support_sets = fact["any_support_sets"]
            assert support_sets, f"{cid} fact {fact['id']} 支持集非空"
            for sset in support_sets:
                assert sset, f"{cid} 支持组内 AND，组不能为空"
                for uid in sset:
                    assert uid in unit_ids, f"{cid} 支持集引用不存在的 unit {uid}"
            for item in fact["must_preserve"] + fact["must_not_assert"]:
                assert item.strip(), f"{cid} must_preserve/must_not_assert 条目非空"
        assert exp["disposition"] in DISPOSITIONS
        assert isinstance(exp.get("not_evaluated"), list)
        assert case.get("execution_status") == "NOT_RUN_ROOT_INTEGRATION", (
            f"{cid} 语义生产执行只能记 NOT_RUN_ROOT_INTEGRATION"
        )


def test_mutations_and_candidate_claim():
    for cid, case in load_cases().items():
        mutations = case.get("mutations")
        assert mutations, f"{cid} 每个 case 要有失败反例（mutation）"
        seen = set()
        for mut in mutations:
            assert set(mut) == {"id", "change", "expected_failure", "reason"}
            assert mut["id"] not in seen
            seen.add(mut["id"])
            for key in ("change", "expected_failure", "reason"):
                assert mut[key].strip(), f"{cid} mutation {key} 非空"
        claim = case.get("candidate_claim")
        if claim is not None:
            assert set(claim) == CLAIM_SLOTS, f"{cid} candidate_claim 槽位固定"
            for slot in claim:
                assert claim[slot] is None or isinstance(claim[slot], str)
        missing = case.get("expected_missing_slots", [])
        assert set(missing) <= CONTEXT_SLOTS, f"{cid} expected_missing_slots 超出槽位枚举"


def test_quote_quota_per_source():
    totals = quote_chars_per_source(load_cases())
    for source_key, chars in totals.items():
        assert chars <= QUOTE_QUOTA_BYTES, (
            f"{source_key} 摘录 {chars} 字符超过每 source 8KiB 配额"
        )


def test_no_orphan_cases():
    records = load_records()
    referenced = {cid for rec in records.values() for cid in rec["case_ids"]}
    for cid in load_cases():
        assert cid in referenced, f"case {cid} 未被任何规格引用（孤儿）"
