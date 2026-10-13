"""跨市场与生命周期反例的显式差异（结构性检查，不做语义判断）。"""
from __future__ import annotations

import pytest

from _support import load_records


def _counter_text(rid: str) -> str:
    rec = load_records()[rid]
    return "\n".join(rec["recognition"]["counterexamples"])


def _sections_text(rid: str) -> str:
    rec = load_records()[rid]
    return "\n".join(
        alias + "\n" + "\n".join(level for path in s["heading_path"] for level in path)
        for s in rec["sections"]
        for alias in s["aliases"]
    )


def test_annual_family_cross_market_counterexamples_differ():
    records = load_records()
    for rid in ("cn_annual_report", "hk_annual_report", "sec_10k"):
        assert rid in records, f"缺 {rid} 规格"
    cn, hk, sec = (_counter_text(r) for r in ("cn_annual_report", "hk_annual_report", "sec_10k"))
    assert cn != hk != sec, "同 family 跨市场反例必须显式不同"
    assert "摘要" in cn, "A股反例必须点明年报摘要件不是全文"
    assert ("Business Review" in hk) or ("双语" in hk) or ("雙語" in hk), "港股反例必须点明双语/章节体系差异"
    assert "20-F" in sec and "10-Q" in sec, "10-K 反例必须点明与 20-F/10-Q 的编号差异"


def test_sec_items_and_parts_are_not_mixed():
    records = load_records()
    for rid in ("sec_10k", "sec_10q", "sec_20f"):
        assert rid in records, f"缺 {rid} 规格"
    sections_10k = _sections_text("sec_10k")
    sections_10q = _sections_text("sec_10q")
    sections_20f = _sections_text("sec_20f")
    assert "Item 7" in sections_10k and "Part I" not in sections_10k, "10-K 不用 Part 层级索引"
    assert "Part I" in sections_10q and "Item 2" in sections_10q, "10-Q MD&A 在 Part I Item 2，Part 层级不能丢"
    assert "Item 5" in sections_20f, "20-F 经营回顾在 Item 5，不能照搬 10-K 章节"
    assert "Item 7" not in sections_20f, "20-F 不用 10-K 的 Item 7 编号"
    counter_10q = _counter_text("sec_10q")
    counter_20f = _counter_text("sec_20f")
    assert "Part" in counter_10q, "10-Q 反例必须点明 Part 不可混"
    assert "20-F" in counter_20f and "10-K" in counter_20f, "20-F 反例必须点明与 10-K 编号不同"


def test_prospectus_family_cross_market_counterexamples_differ():
    records = load_records()
    for rid in ("prospectus_cn", "prospectus_hk", "prospectus_us"):
        assert rid in records, f"缺 {rid} 规格"
    cn, hk, us = (_counter_text(r) for r in ("prospectus_cn", "prospectus_hk", "prospectus_us"))
    assert cn != hk != us
    assert "确认意见" in cn, "A股招股反例必须点明确认意见/确认函不是招股说明书正文"
    assert ("全球發售" in hk) or ("全球发售" in hk) or ("雙語" in hk) or ("繁" in hk), (
        "港股招股反例必须点明全球发售/繁简英别名与正文的关系"
    )
    assert ("转售" in us) or ("resale" in us.lower()) or ("S-1" in us) or ("F-1" in us), (
        "US 招股反例必须点明注册表单/转售与公司募资的区别"
    )


def test_offering_family_variants_are_distinct():
    records = load_records()
    for rid in ("offering_cn_equity", "offering_cn_convertible", "offering_feasibility"):
        assert rid in records, f"缺 {rid} 规格"
    texts = {rid: _counter_text(rid) for rid in ("offering_cn_equity", "offering_cn_convertible", "offering_feasibility")}
    assert len(set(texts.values())) == 3, "定增/可转债/可研 反例不得互相复制"


def test_lifecycle_overlay_is_orthogonal():
    records = load_records()
    rid = "lifecycle_revision_overlay"
    assert rid in records, "缺摘要/修订/补充/更正的正交修饰记录"
    rec = records[rid]
    blob = "\n".join(rec["reading_questions"] + [rec["fallback"][k] for k in rec["fallback"]])
    for word in ("摘要", "修订", "更正"):
        assert word in blob, f"生命周期修饰记录必须覆盖 {word}"
    assert len(rec["sections"]) <= 2, "正交修饰不得复制各 family 的全部章节策略"


def test_administrative_negative_never_deletes_by_filename():
    rec = load_records()["administrative_document"]
    blob = "\n".join(rec["recognition"]["counterexamples"] + rec["reading_questions"])
    assert "文件名" in blob or "标题" in blob, "行政类必须写明不按文件名/标题直接跳过"
    assert rec["fallback"]["no_business"].strip(), "合法无业务必须走 fallback 而不是删除原件"
