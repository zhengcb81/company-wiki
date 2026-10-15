"""Apply the C-node independent review corrections as a recorded gold version.

The reviewer (blind to the freeze process, reading only originals + gold) found
four ``must_not_assert`` strings in du5-cn-proya-q1 that are actually TRUE of
the source (a poisoned negative control would penalise correct summaries) and
one mislabelled modality in du5-cn-gbits-call. Per INTERFACES — ``改错金标需
单独更正记录和版本，旧值仍可回放`` — the old values are recorded verbatim in
``gold_corrections.json.content_corrections`` and the manifest keeps the
freeze-time digests; gold anchors, importance and denominators never move, and
the corrections cannot wash the measured native baseline green (they only
affect claim-level checks, and the baseline emits no claims).

Run from the worktree root. Idempotent: re-running reports already-applied.
"""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(REPO))

from tools.document_understanding_benchmark.contamination import support_set_digest  # noqa: E402

PACKAGE = REPO / "tools" / "document_understanding_benchmark"
GOLD = PACKAGE / "gold"
MANIFEST = PACKAGE / "du5_manifest.json"
CORRECTIONS = PACKAGE / "gold_corrections.json"

# fact_id -> (field, new_value, reviewer_reason)
PROYA = {
    "q1-revenue-yoy-decline": (
        "must_not_assert",
        [
            "营业收入同比增长2.29%",
            "2,305,344,625.43元为2026年3月单月收入或2026年上半年累计收入",
            "营业收入23亿元",
            "营业收入2,305,344,625.4元",
        ],
        "旧负例含两个真命题（Q1 报告的『年初至报告期末』≡本报告期；23.05亿 是忠实四舍五入），"
        "会惩罚正确摘要；改为只有真正错误的期间与精度改写",
    ),
    "eps-basic-diluted-unit": (
        "must_not_assert",
        [
            "基本每股收益为0.93元/股，较上年增长6.06%",
            "每股收益0.93元为年化口径或2026年上半年累计口径",
            "稀释每股收益高于基本每股收益",
        ],
        "旧负例的『年初至报告期末累计』在 Q1 报告里为真（半真析取），删除后保留年化/半年度错误口径",
    ),
    "share-capital-and-buyback-holdings": (
        "must_not_assert",
        [
            "公司在报告期内增发了约100万股",
            "回购专户持股3,757,848股占总股本9.5%",
            "395,976,008.00为上年度末（2025年12月31日）的股本数",
        ],
        "旧负例『股本为金额（元）而非股数』与资产负债表原文（实收资本（或股本）单位：元）"
        "歧义甚至为真；改为明确错误的期间错置",
    ),
}
GBITS = {
    "yy-stabilize-target-uncertain": (
        "modality",
        "plan",
        "审阅判定：该句是带对冲的计划（希望…但目前也不太好判断），非 if-then 条件句；"
        "modality 由 conditional 更正为 plan",
    ),
}


def _apply(sample_id: str, edits: dict) -> list[dict]:
    path = GOLD / f"{sample_id}.json"
    raw = json.loads(path.read_text(encoding="utf8"))
    records = []
    for fact in raw["facts"]:
        if fact["id"] not in edits:
            continue
        field, new_value, reason = edits[fact["id"]]
        old_value = fact[field]
        if old_value == new_value:
            continue
        records.append(
            {
                "sample_id": sample_id,
                "fact_id": fact["id"],
                "field": field,
                "old_value": old_value,
                "new_value": new_value,
                "reason": reason,
            }
        )
        fact[field] = new_value
    if not records:
        return []
    raw["support_set_digest_at_freeze"] = raw.get(
        "support_set_digest_at_freeze", raw["support_set_digest"]
    )
    raw["support_set_digest"] = support_set_digest(raw)
    raw["notes"] = (
        raw.get("notes", "")
        + "（版本2，2026-10-15 C节点独审更正：仅负例字符串/一处 modality 标签，"
        "锚点与重要性、分母未动；旧值见 gold_corrections.json.content_corrections。）"
    )
    path.write_bytes((json.dumps(raw, ensure_ascii=False, indent=2) + "\n").encode("utf8"))
    return records


def main() -> int:
    corrections = json.loads(CORRECTIONS.read_text(encoding="utf8"))
    applied = corrections.setdefault("content_corrections", [])
    already = {(c["sample_id"], c["fact_id"], c["field"]) for c in applied}

    new_records = []
    for sample_id, edits in ((("du5-cn-proya-q1"), PROYA), ("du5-cn-gbits-call", GBITS)):
        for record in _apply(sample_id, edits):
            if (record["sample_id"], record["fact_id"], record["field"]) not in already:
                record["status"] = "applied"
                record["version"] = 2
                new_records.append(record)

    if not new_records:
        print("no new corrections to apply")
    applied.extend(new_records)
    corrections["content_corrections_note"] = (
        "改错金标：独立 reviewer 对照原件判定为真/歧义的负例与一处 modality 标签。"
        "旧值逐字段记录在 old_value，可与版本1字节（manifest.gold_sha256_at_freeze）"
        "一起回放。锚点、importance、target_kind、分母均未改动。"
    )
    CORRECTIONS.write_bytes(
        (json.dumps(corrections, ensure_ascii=False, indent=2) + "\n").encode("utf8")
    )

    manifest = json.loads(MANIFEST.read_text(encoding="utf8"))
    for row in manifest["samples"]:
        path = GOLD / f"{row['sample_id']}.json"
        raw = json.loads(path.read_text(encoding="utf8"))
        if row["sample_id"] in {r["sample_id"] for r in applied}:
            row["gold_sha256_at_freeze"] = row.get("gold_sha256_at_freeze", row["gold_sha256"])
            row["support_set_digest_at_freeze"] = row.get(
                "support_set_digest_at_freeze", row["support_set_digest"]
            )
            row["correction_version"] = 2
        row["gold_sha256"] = hashlib.sha256(
            path.read_bytes().replace(b"\r\n", b"\n")
        ).hexdigest()
        row["support_set_digest"] = raw["support_set_digest"]
    MANIFEST.write_bytes(
        (json.dumps(manifest, ensure_ascii=False, indent=2) + "\n").encode("utf8")
    )

    for record in new_records:
        print(f"applied v2: {record['sample_id']}/{record['fact_id']}.{record['field']}")
    print(f"content_corrections total: {len(applied)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
