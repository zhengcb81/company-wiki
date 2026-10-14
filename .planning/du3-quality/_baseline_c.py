"""Node C: real baseline on the three fresh originals through the existing public entry.

Runs ``observer.observe_native`` (the existing parser/selector, read-only) on the
fresh A/H/US originals and evaluates each against its frozen fresh gold. It also
replays every gold quote against the real source text (citation replay) and
records source SHA/mtime/size before and after so raw-preservation is measured,
not assumed.

Semantics stay ``NOT_EVALUATED`` because no real model is called here: the card
is explicit that without a real model the benchmark must not emit a summary
fidelity PASS. This writes only a small summary into the owned planning dir; it
never copies originals and never writes production config.
"""

import hashlib
import json
import os
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path.cwd()))
from company_wiki.source_catalog import narrative_evidence as ne  # noqa: E402
from company_wiki.document_normalization import normalize_document  # noqa: E402
from tools.document_understanding_benchmark import evaluate  # noqa: E402
from tools.document_understanding_benchmark.observer import observe_native  # noqa: E402
from tools.document_understanding_benchmark.gold import load_gold_dir  # noqa: E402
from tools.document_understanding_benchmark.textutil import anchor_matches  # noqa: E402

FRESH = ["fresh-cn-smic-fy2025", "fresh-hk-anta-fy2025", "fresh-us-apple-10k"]
BIND = json.loads((Path.home() / ".du-bench" / "bindings.local.json").read_text(encoding="utf8"))
GOLDDIR = Path("tools/document_understanding_benchmark/gold")


def fingerprint(path: Path):
    st = path.stat()
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return {"sha256": h.hexdigest(), "mtime_ns": st.st_mtime_ns, "size": st.st_size}


def all_text(path: Path, sha: str):
    raw = path.read_bytes()
    if path.suffix.lower() == ".pdf":
        parsed = ne.parse_pdf_bytes(raw, source_id="x", source_sha256=sha, language="zh")
        return "\n".join((getattr(u, "raw_text", "") or "") for u in parsed.units)
    doc = normalize_document(raw, source_id="x", source_sha256=sha, mime_type="text/html")
    return "\n".join((getattr(u, "raw_text", "") or "") for u in doc.units)


rows = []
started = time.monotonic()
for sid in FRESH:
    gold = json.loads((GOLDDIR / f"{sid}.json").read_text(encoding="utf8"))
    path = Path(BIND[sid])
    before = fingerprint(path)
    text = all_text(path, before["sha256"])
    # citation replay: every gold quote must appear in the real source text
    quotes = [a["exact_quote"] for s in gold["facts"] for grp in s["any_support_sets"] for a in grp]
    replayed = sum(1 for q in quotes if anchor_matches(q, text))
    observed = observe_native(path, sha256=gold["source_sha256"], sample_id=sid)
    result = evaluate(observed, gold)
    after = fingerprint(path)
    m = result["metrics"]
    rows.append({
        "sample_id": sid,
        "company": gold.get("company"),
        "market": gold.get("market"),
        "carrier": path.suffix.lower(),
        "source_sha256": before["sha256"],
        "source_unchanged": before == after,
        "size_bytes": before["size"],
        "quote_replay": f"{replayed}/{len(quotes)}",
        "native_units": observed["metrics"].get("source_units"),
        "selected_spans": observed["metrics"].get("selected_spans"),
        "candidate_count": observed["metrics"].get("candidate_count"),
        "native_scan": observed["coverage"].get("native_scan"),
        "status": result["status"],
        "critical_recall": m.get("critical_fact_recall"),
        "critical_pass": m.get("critical_fact_recall_denominator_declared") and round(
            (m.get("critical_fact_recall") or 0) * (m.get("critical_fact_recall_denominator") or 0)
        ),
        "critical_denominator": m.get("critical_fact_recall_denominator"),
        "critical_declared": m.get("critical_fact_recall_denominator_declared"),
        "narrative_recall": m.get("narrative_fact_recall"),
        "semantics_entailment": "NOT_EVALUATED (no real model called)",
    })

elapsed = round(time.monotonic() - started, 3)
report = {
    "schema_version": "du3-quality-baseline/1",
    "generated": "2026-10-14",
    "entry_point": "company_wiki.source_catalog.narrative_evidence (existing public parser/selector)",
    "model_calls": 0,
    "paid_calls": 0,
    "network_calls": 0,
    "elapsed_seconds": elapsed,
    "semantics": "NOT_EVALUATED — no real model; ROOT wires G2/G4/G5 window later",
    "rows": rows,
}
out = Path(".planning/du3-quality/baseline_c.json")
out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf8")
print(json.dumps(report, ensure_ascii=False, indent=2))
print("\nRAW PRESERVED:", all(r["source_unchanged"] for r in rows))
print("wrote", out)
