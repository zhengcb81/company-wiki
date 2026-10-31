"""Post-review delivery enrichment (self-audit gaps): join frozen sample
manifest identity onto every page record so comparison.json carries per-page
source/page/image_SHA per the card's output interface.  Data join only — no
engine output is touched."""
import json
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
DELIVERY = REPO / "delivery" / "w23-xiaomi-ocr"
PLAN = REPO / "docs" / "plans" / "w23-xiaomi-ocr-2026-10-30"

manifest = json.loads((PLAN / "sample_manifest.json").read_text(encoding="utf-8"))
identity = {
    p["page_id"]: {
        "source_id": manifest["documents"][p["doc"]]["source_id"],
        "document_id": manifest["documents"][p["doc"]]["document_id"],
        "content_sha256": manifest["documents"][p["doc"]]["content_sha256"],
        "pdf_page_index": p["pdf_page_index"],
        "page_image_sha256": p["png_sha256"],
        "market": manifest["documents"][p["doc"]]["market"],
        "language": manifest["documents"][p["doc"]]["language"],
        "genre": manifest["documents"][p["doc"]]["genre"],
    }
    for p in manifest["pages"]
}

for arm_file in ("raw_r0.json", "raw_n0.json", "raw_x1.json", "raw_x2.json"):
    path = DELIVERY / arm_file
    payload = json.loads(path.read_text(encoding="utf-8"))
    for record in payload["records"]:
        record["page_identity"] = identity.get(record["page_id"])
    payload["page_identity_provenance"] = (
        "joined from docs/plans/w23-xiaomi-ocr-2026-10-30/sample_manifest.json "
        "(frozen, commit 0d24c943) in the post-review enrichment step; engine fields untouched"
    )
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=1), encoding="utf-8")

comparison_path = DELIVERY / "comparison.json"
comparison = json.loads(comparison_path.read_text(encoding="utf-8"))
for arm, entry in comparison["arms"].items():
    for split in ("eval", "holdout"):
        for per_page in entry["evaluation"][split]["per_page"]:
            per_page["page_identity"] = identity.get(per_page["page_id"])
comparison["page_identity_provenance"] = (
    "per-page source/page/image SHA joined from the frozen sample_manifest.json "
    "in the post-review enrichment step (self-audit gap); no engine output changed"
)
comparison_path.write_text(json.dumps(comparison, ensure_ascii=False, indent=1), encoding="utf-8")

# verify
check = json.loads(comparison_path.read_text(encoding="utf-8"))
sample = check["arms"]["R0"]["evaluation"]["eval"]["per_page"][0]
print("enriched per_page keys:", sorted(sample.keys()))
print("identity sample:", {k: str(v)[:24] for k, v in sample["page_identity"].items()})
wer = {
    split: [(p["page_id"], p.get("wer")) for p in check["arms"]["R0"]["evaluation"][split]["per_page"] if "wer" in p]
    for split in ("eval", "holdout")
}
print("WER per split:", wer)
