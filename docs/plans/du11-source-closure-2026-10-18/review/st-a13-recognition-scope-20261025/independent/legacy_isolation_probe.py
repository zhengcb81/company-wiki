"""Compare real selector artifacts with the same fixture and new relation disabled."""
from pathlib import Path
from hashlib import sha256
from unittest.mock import patch
import json
import sys
from company_wiki.source_catalog import narrative_business_policy as policy
from company_wiki.source_catalog.narrative_document import DocumentStructure
from company_wiki.source_catalog.narrative_evidence import _make_unit, select_narrative_evidence
from company_wiki.source_contract import EvidenceCoordinates, source_id_for_sha256

HERE = Path(__file__).resolve().parent
ROOT = next(p for p in HERE.parents if (p / "pyproject.toml").exists())

def main():
    if len(sys.argv) != 2 or not sys.argv[1].replace("-", "").isalnum():
        raise SystemExit("usage: legacy_isolation_probe.py NEW-REPORT-STEM")
    output = HERE / (sys.argv[1] + ".json")
    if output.exists():
        raise FileExistsError(output)
    text = "本公司的仪器维护服务属于在某一时段内履行的履约义务。"
    digest = sha256(b"independent-legacy-isolation").hexdigest()
    source = source_id_for_sha256(digest)
    unit = _make_unit(source_id=source, parser_version="1.0.0", coordinates=EvidenceCoordinates(paragraph_index=0),
                      raw_text=text, unit_kind="html_paragraph", source_role="company_filing", language="zh",
                      metadata={"source_locator": "cwp-html-dom/1|n=0.0"})
    parsed = DocumentStructure(source, digest, "zh", (unit,), line_count=1, mime_type="text/html")
    rows = []
    for version in ("0.6.0", "0.7.0", "0.7.1", "0.8.0", "0.9.0"):
        actual = select_narrative_evidence(parsed, title="Annual report", existing_kind="annual_report", selector_version=version, max_selected=6)
        with patch.object(policy, "named_recognition_scope", lambda _: False):
            baseline = select_narrative_evidence(parsed, title="Annual report", existing_kind="annual_report", selector_version=version, max_selected=6)
        current = [e.to_dict() for e in actual.evidence_spans]
        old = [e.to_dict() for e in baseline.evidence_spans]
        rows.append({"selector_version": version, "actual_span_ids": [e["span_id"] for e in current],
                     "baseline_span_ids": [e["span_id"] for e in old], "actual_topics": [e["structured_value"]["topics"] for e in current],
                     "byte_equivalent_artifact_dict": current == old,
                     "pass": current != old if version == "0.9.0" else current == old})
    result = {"schema_version": "recognition-scope-independent-real-legacy-isolation/1", "rows": rows,
              "pass": all(x["pass"] for x in rows), "neutral_fixture_text": text,
              "baseline": "Only the new scope detector is disabled in memory; source, old classifiers, and file bytes stay identical.",
              "source_sha256": {p: sha256((ROOT/p).read_bytes()).hexdigest() for p in (
                  "src/company_wiki/source_catalog/narrative_business_policy.py", "src/company_wiki/source_catalog/narrative_recognition_scope.py",
                  "src/company_wiki/source_catalog/narrative_evidence.py", "src/company_wiki/source_catalog/narrative_business_meaning.py")},
              "external_calls": 0, "downloads": 0}
    with output.open("x", encoding="utf8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
        f.write("\n")
    print(json.dumps({"pass": result["pass"], "rows": rows}, ensure_ascii=False))
    return 0 if result["pass"] else 1

if __name__ == "__main__":
    raise SystemExit(main())
