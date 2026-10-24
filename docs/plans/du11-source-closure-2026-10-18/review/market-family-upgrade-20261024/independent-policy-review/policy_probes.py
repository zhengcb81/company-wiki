"""Read-only strategy probes and bounded source checks; no acquisition/models."""
from hashlib import sha256
import json
from pathlib import Path
import re

from bs4 import BeautifulSoup
from company_wiki.document_understanding import strategy_binding


ROOT = next(parent for parent in Path(__file__).resolve().parents if (parent / "pyproject.toml").is_file())
OUT = Path(__file__).resolve().parent
catalog_path = ROOT / "src/company_wiki/document_understanding/profiles/reading_catalog.json"
catalog = json.loads(catalog_path.read_text(encoding="utf-8"))
families = {entry["id"]: entry for entry in catalog["families"]}
cases = (
    ("20f_risk_key_information", "sec_20f", "20-F", ["Item 3. Key Information", "D. Risk Factors"]),
    ("20f_business_actual", "sec_20f", "20-F", ["Item 4. Information on the Company", "B. Business Overview"]),
    ("20f_notes17_variant", "sec_20f", "20-F", ["Item 17. Financial Statements", "Notes to Financial Statements"]),
    ("20f_notes18_control", "sec_20f", "20-F", ["Item 18. Financial Statements", "Notes to Financial Statements"]),
    ("20f_item7_not_mda", "sec_20f", "20-F", ["Item 7. Major Shareholders and Related Party Transactions"]),
    ("10k_item7_mda", "sec_10k", "10-K", ["Item 7. Management's Discussion and Analysis"]),
    ("hk_postperiod_english", "hk_interim_report", "unknown", ["RECENT DEVELOPMENTS AFTER THE REPORTING PERIOD"]),
    ("hk_postperiod_chinese", "hk_interim_report", "unknown", ["報告期後的近期發展"]),
)
result = {"scope": "Direct current production section matcher using installed family rules; not a full selector or summary evaluation.",
          "catalog_sha256": sha256(catalog_path.read_bytes()).hexdigest(), "matcher_cases": [], "source_reads": []}
for label, family, form, headings in cases:
    keys = ["s" + str(index) for index in range(len(headings))]
    parents = dict(zip(keys, [None, *keys[:-1]]))
    diagnostics = []
    matched = strategy_binding._match_rule(keys[-1], {"section_rules": families[family]["sections"], "form_type": form},
        parents, dict(zip(keys, headings)), diagnostics)
    result["matcher_cases"].append({"case": label, "family": family, "headings": headings,
        "matched_role": matched.get("role") if matched else None,
        "matched_priority": matched.get("priority") if matched else None, "diagnostics": diagnostics})

manifest_path = ROOT / "docs/plans/document-understanding-2026-10-13/sample_manifest.json"
manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
for sample_id in ("us-20f", "us-txt"):
    entry = next(entry for entry in manifest["samples"] if entry["id"] == sample_id)
    path = Path(entry["path"])
    path = path if path.is_absolute() else ROOT / path
    raw = path.read_bytes()
    assert sha256(raw).hexdigest() == entry["sha256"]
    record = {"sample_id": sample_id, "sha256": entry["sha256"], "bytes": len(raw), "read_scope": "bounded original heading/turn checks"}
    if sample_id == "us-20f":
        soup = BeautifulSoup(raw, "html.parser")
        headings = []
        for node in soup.find_all(("p", "div", "h1", "h2", "h3", "td")):
            text = " ".join(node.get_text(" ", strip=True).split())
            if len(text) <= 180 and re.match(r"^(?:Item\s*[34578](?:\.|\s)|[BCD]\.\s*(?:Risk Factors|Business Overview|Organizational Structure))", text, re.I):
                if text not in headings:
                    headings.append(text)
        record["short_native_headings"] = headings
    else:
        lines = raw.decode("utf-8").splitlines()
        record["opening_lines"] = [{"line": index + 1, "text": text} for index, text in enumerate(lines[:45]) if text.strip()]
        record["qualification_excerpt"] = [{"line": index + 1, "text": text[:1800]} for index, text in enumerate(lines) if 127 <= index <= 133 and text.strip()]
        record["qa_excerpt"] = [{"line": index + 1, "text": text[:600]} for index, text in enumerate(lines) if 233 <= index <= 244 and text.strip()]
        record["tail_roles"] = [{"line": index + 1, "text": text[:800]} for index, text in enumerate(lines) if index >= 325 and text.strip()]
    record["original_unchanged"] = sha256(path.read_bytes()).hexdigest() == entry["sha256"]
    result["source_reads"].append(record)

(OUT / "probes.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(json.dumps(result, ensure_ascii=False, indent=2))
