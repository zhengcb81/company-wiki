"""Read-only W05 real-source replay. No provider, paid model or source writes."""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import sys

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--repo", type=Path, required=True)
parser.add_argument("--original", type=Path, required=True)
parser.add_argument("--receipt", type=Path, required=True)
args = parser.parse_args()
sys.path.insert(0, str(args.repo.resolve() / "src"))
from company_wiki.source_catalog.transcript_text_extract import extract_transcript_material
from company_wiki.source_catalog.narrative_evidence import (
    parse_transcript_text, select_narrative_evidence, verify_transcript_evidence_spans,
)

original = args.original.resolve(strict=True)
before = original.stat()
body = original.read_bytes()
sha = hashlib.sha256(body).hexdigest()
assert sha == "bdc90bf78dbf55ec3f1d789f1f76ebd2e97c7aab51dcc24a262f5d512fb47656"
material = extract_transcript_material(body, mime_type="text/html")
material.verify(body)
parsed = parse_transcript_text(material.text_utf8, source_id=material.original_source_id,
                              source_sha256=sha)
assert parsed.units and not parsed.errors
selected = select_narrative_evidence(parsed, title="Microsoft Q4 FY2026 earnings call",
                                     existing_kind="investor_call_transcript")
verified, failed = verify_transcript_evidence_spans(
    material.text_utf8, source_id=material.original_source_id, source_sha256=sha,
    evidence_spans=selected.evidence_spans,
)
assert selected.evidence_spans and len(verified) == len(selected.evidence_spans) and not failed
start = min(unit.metadata["line_start"] for unit in parsed.units)
end = max(unit.metadata["line_end"] for unit in parsed.units)
assert (start, end) == (90, 414), (start, end)
assert all("This is the Trace Id" not in unit.raw_text for unit in parsed.units)
roles = Counter(unit.source_role for unit in parsed.units)
assert roles["management"] and roles["analyst"] and roles["operator"]
after = original.stat()
assert (before.st_size, before.st_mtime_ns) == (after.st_size, after.st_mtime_ns)
assert hashlib.sha256(original.read_bytes()).hexdigest() == sha
receipt = {
    "schema_version": "w05-main-real-replay/1", "original_sha256": sha,
    "bytes": len(body), "line_count": len(material.text_utf8.splitlines()),
    "body_start_line": start, "body_end_line": end, "parsed_units": len(parsed.units),
    "parser_version": selected.evidence_spans[0].parser_version,
    "roles": dict(roles), "selected": len(selected.evidence_spans), "replayed": len(verified),
    "failures": len(failed), "original_sha_mtime_unchanged": True,
    "provider_calls": 0, "paid_calls": 0, "research_acceptance": "NOT_RUN",
    "actual_source_repo": str(args.repo.resolve()),
}
args.receipt.parent.mkdir(parents=True, exist_ok=True)
assert not args.receipt.exists(), "do not replace an older acceptance receipt"
args.receipt.write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
print(json.dumps(receipt))
