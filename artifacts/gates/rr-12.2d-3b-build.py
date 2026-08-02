"""Deterministic builder for RR-12.2d-3B synthetic draft cohorts.

The script is intentionally scoped to tests/fixtures/gold_corpus.  It refuses
partial/repeated cohorts and never reads production company documents.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
CORPUS = ROOT / "tests" / "fixtures" / "gold_corpus"


CASES = {
    "a": [
        {
            "n": 36,
            "source_id": "gk-zw-ambig3",
            "path": "sources/中微公司/中微简称歧义报道.md",
            "source_kind": "original_news",
            "publisher": "合成财经媒体（fixture）",
            "entity_hints": ["中微公司", "中微半导体"],
            "published_at": "2025-07-01",
            "period": "2025-07",
            "tags": ["ambiguity", "original_news"],
            "title": "“中微”简称主体歧义报道",
            "evidence": "报道仅使用“中微”简称，无法确认指中微公司还是其他同名主体。",
            "claim": "“中微”简称存在主体歧义，需人工确认",
            "entity_id": "中微公司",
            "source_entity": "中微",
            "targets": [("中微公司", "company", "ambiguous", "简称歧义，需人工确认")],
            "has_ambiguity": True,
            "disambiguation": "中微可能指中微公司（688012）或其他同名半导体主体",
        },
        {
            "n": 37,
            "source_id": "gk-smic-ambig4",
            "path": "sources/中芯国际/中芯简称歧义报道.md",
            "source_kind": "original_news",
            "publisher": "合成科技媒体（fixture）",
            "entity_hints": ["中芯国际", "中芯集成"],
            "published_at": "2025-07-02",
            "period": "2025-07",
            "tags": ["ambiguity", "original_news"],
            "title": "“中芯”简称主体歧义报道",
            "evidence": "稿件只写“中芯扩产”，无法判断所指为中芯国际还是中芯集成。",
            "claim": "“中芯扩产”表述无法唯一定位公司主体",
            "entity_id": "中芯国际",
            "source_entity": "中芯",
            "targets": [("中芯国际", "company", "ambiguous", "简称歧义，需人工确认")],
            "has_ambiguity": True,
            "disambiguation": "中芯可能指中芯国际或中芯集成，正文未给出证券代码",
        },
        {
            "n": 38,
            "source_id": "gk-consumer-irrelevant3",
            "path": "sources/合成消费/合成消费新品发布.md",
            "source_kind": "original_news",
            "publisher": "合成消费媒体（fixture）",
            "entity_hints": ["合成消费"],
            "published_at": "2025-07-03",
            "period": "2025-07",
            "tags": ["irrelevant", "negative", "original_news"],
            "title": "合成消费品牌发布饮料新品",
            "evidence": "合成消费品牌发布无糖饮料新品，与半导体设备公司和行业均无关系。",
            "claim": "合成消费发布无糖饮料新品",
            "entity_id": "合成消费",
            "source_entity": "合成消费",
            "targets": [("合成消费", "company", "high", "新闻主实体")],
            "is_irrelevant": True,
            "not_expected": ["北方华创", "中微公司", "中芯国际", "半导体设备"],
            "materiality": "low",
        },
        {
            "n": 39,
            "source_id": "gk-logistics-irrelevant4",
            "path": "sources/合成物流/合成物流仓储升级.md",
            "source_kind": "original_news",
            "publisher": "合成物流媒体（fixture）",
            "entity_hints": ["合成物流"],
            "published_at": "2025-07-04",
            "period": "2025-07",
            "tags": ["irrelevant", "negative", "original_news"],
            "title": "合成物流升级冷链仓储",
            "evidence": "合成物流完成冷链仓储升级，不涉及芯片制造或半导体设备业务。",
            "claim": "合成物流完成冷链仓储升级",
            "entity_id": "合成物流",
            "source_entity": "合成物流",
            "targets": [("合成物流", "company", "high", "新闻主实体")],
            "is_irrelevant": True,
            "not_expected": ["北方华创", "中微公司", "中芯国际", "半导体设备"],
            "materiality": "low",
        },
        {
            "n": 40,
            "source_id": "gk-smic-news-asof2",
            "path": "sources/中芯国际/中芯国际_Q3后见报道.md",
            "source_kind": "original_news",
            "publisher": "合成科技媒体（fixture）",
            "entity_hints": ["中芯国际", "00981"],
            "published_at": "2025-09-15",
            "period": "2025Q3",
            "tags": ["as_of", "future_leakage", "original_news"],
            "title": "中芯国际 Q3 后见信息",
            "evidence": "中芯国际第三季度新增产能已在九月披露，不得用于六月末的 as_of 查询。",
            "claim": "九月披露的中芯国际Q3新增产能不得前视到六月末",
            "entity_id": "中芯国际",
            "source_entity": "中芯国际",
            "targets": [("中芯国际", "company", "high", "新闻主实体")],
        },
    ],
    "b": [
        {
            "n": 41,
            "source_id": "gk-zw-news-asof3",
            "path": "sources/中微公司/中微公司_Q4后见报道.md",
            "source_kind": "original_news",
            "publisher": "合成财经媒体（fixture）",
            "entity_hints": ["中微公司", "688012"],
            "published_at": "2025-10-20",
            "period": "2025Q4",
            "tags": ["as_of", "future_leakage", "original_news"],
            "title": "中微公司 Q4 后见信息",
            "evidence": "中微公司第四季度订单信息于十月公开，不得写入九月末之前的 as_of 答案。",
            "claim": "十月公开的中微公司Q4订单不得前视到九月末",
            "entity_id": "中微公司",
            "source_entity": "中微公司",
            "targets": [("中微公司", "company", "high", "新闻主实体")],
        },
        {
            "n": 42,
            "source_id": "gk-smic-ann-asof4",
            "path": "sources/中芯国际/中芯国际_十一月产能公告.md",
            "source_kind": "company_announcement",
            "publisher": "中芯国际",
            "entity_hints": ["中芯国际", "00981"],
            "published_at": "2025-11-05",
            "period": "2025-11",
            "tags": ["as_of", "future_leakage", "company_announcement"],
            "title": "中芯国际十一月产能公告",
            "evidence": "十一月公告确认新增产线投产，该事实不得进入十月三十一日以前的 as_of 答案。",
            "claim": "十一月确认的新增产线不得前视到十月底",
            "entity_id": "中芯国际",
            "source_entity": "中芯国际",
            "targets": [("中芯国际", "company", "high", "公告主实体")],
        },
        {
            "n": 43,
            "source_id": "gk-zw-correction2",
            "path": "sources/中微公司/中微公司_2023营收二次更正.md",
            "source_kind": "company_announcement",
            "publisher": "中微公司",
            "entity_hints": ["中微公司", "688012"],
            "published_at": "2025-01-15",
            "period": "2023年",
            "tags": ["correction", "restatement", "numeric"],
            "title": "中微公司 2023 年营收二次更正",
            "evidence": "公司将重述后的2023年营业收入由47.4亿元进一步更正为47.1亿元。",
            "claim": "中微公司二次更正2023年营业收入为47.1亿元",
            "entity_id": "中微公司",
            "source_entity": "中微公司",
            "targets": [("中微公司", "company", "high", "更正公告主实体")],
            "corrects": "C014",
            "numeric": {
                "metric": "营业收入",
                "value": 47.1,
                "unit": "亿元",
                "currency": "CNY",
                "period": "2023年",
                "scope": "合并",
                "restatement": True,
            },
        },
        {
            "n": 44,
            "source_id": "gk-smic-supersedes2",
            "path": "sources/中芯国际/中芯国际_Q1营收更新公告.md",
            "source_kind": "company_announcement",
            "publisher": "中芯国际",
            "entity_hints": ["中芯国际", "00981"],
            "published_at": "2025-05-20",
            "period": "2025Q1",
            "tags": ["supersedes", "numeric", "company_announcement"],
            "title": "中芯国际 Q1 营收更新公告",
            "evidence": "公司更新2025Q1营业收入为133.1亿元，该数据替代此前披露的132.5亿元。",
            "claim": "中芯国际更新2025Q1营业收入为133.1亿元",
            "entity_id": "中芯国际",
            "source_entity": "中芯国际",
            "targets": [("中芯国际", "company", "high", "更新公告主实体")],
            "supersedes": "C012",
            "numeric": {
                "metric": "营业收入",
                "value": 133.1,
                "unit": "亿元",
                "currency": "CNY",
                "period": "2025Q1",
                "scope": "合并",
                "restatement": True,
            },
        },
        {
            "n": 45,
            "source_id": "gk-smic-ir-control",
            "path": "sources/中芯国际/中芯国际_IR中性控制.md",
            "source_kind": "ir",
            "publisher": "中芯国际",
            "entity_hints": ["中芯国际", "00981"],
            "published_at": "2025-06-18",
            "period": "2025-06",
            "tags": ["neutral_control", "ir"],
            "title": "中芯国际 IR 中性控制样本",
            "evidence": "公司表示现有生产计划保持不变，本次沟通未披露新增财务指引。",
            "claim": "中芯国际现有生产计划保持不变",
            "entity_id": "中芯国际",
            "source_entity": "中芯国际",
            "targets": [("中芯国际", "company", "high", "IR主实体")],
            "materiality": "low",
        },
    ],
}


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, value: dict) -> None:
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


def source_document(case: dict) -> tuple[str, str]:
    hints = ", ".join(case["entity_hints"])
    extra = ""
    if case.get("corrects"):
        extra = "\ncorrection_of: gk-zw-2023-restated"
    frontmatter = f"""---
source_id: {case['source_id']}
source_kind: {case['source_kind']}
publisher: {case['publisher']}
published_at: {case['published_at']}
fetched_at: {case['published_at']}
entity_hints: [{hints}]
url: https://fixture.invalid/{case['source_id']}.html
synthetic: true
review_status: draft{extra}
---"""
    body = f"""
# {case['title']}（合成 fixture）

> RR-12.2d-3B 纯合成金标样本，不复制任何生产资料或真实受限文档。

{case['evidence']}

本样本仅用于覆盖与路由测试；所有名称、事件和数字均为虚构测试数据。
"""
    return frontmatter + body, body


def route_target(target: tuple[str, str, str, str]) -> dict:
    entity_id, entity_type, confidence, reason = target
    return {
        "entity_id": entity_id,
        "entity_type": entity_type,
        "confidence": confidence,
        "reason": reason,
    }


def apply_cohort(name: str) -> None:
    cases = CASES[name]
    manifest_path = CORPUS / "corpus_manifest.json"
    claims_path = CORPUS / "annotations" / "material_claims.json"
    spans_path = CORPUS / "annotations" / "evidence_spans.json"
    routes_path = CORPUS / "annotations" / "routing_targets.json"
    contradictions_path = CORPUS / "annotations" / "contradictions.json"

    manifest = load_json(manifest_path)
    claims_doc = load_json(claims_path)
    spans_doc = load_json(spans_path)
    routes_doc = load_json(routes_path)
    contradictions = load_json(contradictions_path)

    existing_sources = {item["source_id"] for item in manifest["revisions"]}
    existing_claims = {item["claim_id"] for item in claims_doc["claims"]}
    cohort_sources = {case["source_id"] for case in cases}
    cohort_claims = {f"C{case['n']:03d}" for case in cases}
    if cohort_sources & existing_sources or cohort_claims & existing_claims:
        raise SystemExit(f"cohort {name} already or partially applied")

    rendered: list[tuple[dict, Path, str, str]] = []
    for case in cases:
        path = CORPUS / case["path"]
        if path.exists():
            raise SystemExit(f"refusing to overwrite existing fixture: {path}")
        document, body = source_document(case)
        if body.count(case["evidence"]) != 1:
            raise SystemExit(f"evidence must occur exactly once: {case['source_id']}")
        rendered.append((case, path, document, body))

    for case, path, document, body in rendered:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(document, encoding="utf-8")
        claim_id = f"C{case['n']:03d}"
        span_id = f"S{case['n']:03d}"
        start = body.index(case["evidence"])
        end = start + len(case["evidence"])

        manifest["revisions"].append(
            {
                "source_id": case["source_id"],
                "revision_id": f"gkr-{case['source_id'][3:]}-v1",
                "logical_document_id": f"gkd-{case['source_id'][3:]}",
                "path": case["path"],
                "source_kind": case["source_kind"],
                "publisher": case["publisher"],
                "entity_hints": case["entity_hints"],
                "published_at": case["published_at"],
                "observed_at": case["published_at"],
                "effective_period": case["period"],
                "scenario_tags": case["tags"],
                "content_sha256": hashlib.sha256(body.encode("utf-8")).hexdigest(),
                "synthetic": True,
                "review_status": "draft",
            }
        )
        spans_doc["spans"][case["source_id"]] = [
            {
                "span_id": span_id,
                "start": start,
                "end": end,
                "text": case["evidence"],
                "claim_id": claim_id,
                "confidence": 1.0,
                "notes": ["rr-12.2d-3b", *case["tags"]],
            }
        ]
        claim = {
            "claim_id": claim_id,
            "source_id": case["source_id"],
            "claim_type": case.get("claim_type", "fact"),
            "text": case["claim"],
            "entity_id": case["entity_id"],
            "question_id": None,
            "published_at": case["published_at"],
            "effective_period": case["period"],
            "evidence_spans": [span_id],
            "materiality": case.get("materiality", "medium"),
            "numeric": case.get("numeric"),
        }
        if case.get("corrects"):
            claim["corrects"] = case["corrects"]
        if case.get("supersedes"):
            claim["supersedes"] = case["supersedes"]
        claims_doc["claims"].append(claim)

        route = {
            "source_id": case["source_id"],
            "source_entity": case["source_entity"],
            "content_summary": case["claim"],
            "expected_targets": [route_target(target) for target in case["targets"]],
            "has_ambiguity": case.get("has_ambiguity", False),
            "is_irrelevant": case.get("is_irrelevant", False),
        }
        if case.get("disambiguation"):
            route["disambiguation_needed"] = case["disambiguation"]
        if case.get("not_expected"):
            route["not_expected"] = case["not_expected"]
        routes_doc["routing"].append(route)

    if name == "b":
        contradictions["contradictions"].append(
            {
                "id": "CONTRADICT-002",
                "type": "restatement",
                "description": "二次更正2023年营收",
                "original_claim": {
                    "claim_id": "C014",
                    "source_id": "gk-zw-2023-restated",
                    "text": "中微公司重述后2023年营业收入47.4亿元",
                },
                "correcting_claim": {
                    "claim_id": "C043",
                    "source_id": "gk-zw-correction2",
                    "text": "中微公司二次更正2023年营业收入为47.1亿元",
                },
                "resolution": "以二次更正公告为准",
                "effective_date": "2025-01-15",
            }
        )
        contradictions["corrections"].append(
            {
                "id": "CORRECTION-002",
                "type": "numeric_restatement",
                "original_source": "gk-zw-2023-restated",
                "correcting_source": "gk-zw-correction2",
                "affected_claims": ["C014"],
                "field_changes": [
                    {
                        "field": "value",
                        "old": 47.4,
                        "new": 47.1,
                        "reason": "二次口径复核",
                    }
                ],
            }
        )
        contradictions["supersedes"].append(
            {
                "newer_claim": "C044",
                "supersedes": "C012",
                "reason": "更新Q1营收数据",
                "effective_date": "2025-05-20",
            }
        )

    manifest["revisions"].sort(key=lambda item: item["source_id"])
    claims_doc["claims"].sort(key=lambda item: int(item["claim_id"][1:]))
    spans_doc["spans"] = dict(sorted(spans_doc["spans"].items()))
    routes_doc["routing"].sort(key=lambda item: item["source_id"])

    write_json(manifest_path, manifest)
    write_json(claims_path, claims_doc)
    write_json(spans_path, spans_doc)
    write_json(routes_path, routes_doc)
    write_json(contradictions_path, contradictions)
    print(json.dumps({"cohort": name, "added": len(cases)}, ensure_ascii=False))


def repair_existing_cohort(name: str) -> None:
    """Re-render only this builder's already-added sources/hash/offset metadata."""
    cases = CASES[name]
    manifest_path = CORPUS / "corpus_manifest.json"
    spans_path = CORPUS / "annotations" / "evidence_spans.json"
    manifest = load_json(manifest_path)
    spans_doc = load_json(spans_path)
    revisions = {item["source_id"]: item for item in manifest["revisions"]}

    expected = {case["source_id"] for case in cases}
    if not expected <= revisions.keys() or not expected <= spans_doc["spans"].keys():
        raise SystemExit(f"cohort {name} is not fully present; refusing repair")

    for case in cases:
        document, body = source_document(case)
        path = CORPUS / case["path"]
        path.write_text(document, encoding="utf-8")
        revisions[case["source_id"]]["content_sha256"] = hashlib.sha256(
            body.encode("utf-8")
        ).hexdigest()
        span = spans_doc["spans"][case["source_id"]][0]
        start = body.index(case["evidence"])
        span["start"] = start
        span["end"] = start + len(case["evidence"])

    write_json(manifest_path, manifest)
    write_json(spans_path, spans_doc)
    print(json.dumps({"cohort": name, "repaired": len(cases)}, ensure_ascii=False))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--cohort", required=True, choices=sorted(CASES))
    parser.add_argument("--repair-existing", action="store_true")
    args = parser.parse_args()
    if args.repair_existing:
        repair_existing_cohort(args.cohort)
    else:
        apply_cohort(args.cohort)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
