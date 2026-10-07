"""Refresh provenance of the synthetic transport golden via the real reader.

Run: python -B tests/support/refresh_narrative_transport_golden.py
Refuses changes to source bytes, spans or summary semantics. All model work
uses the existing local Replay fixture, never an external provider.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sys
import tempfile

REPO = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(REPO / "src"), str(REPO / "tests"), str(REPO / "tests/contract")]

from company_wiki.automation.models import canonical_json  # noqa: E402
from support.narrative_transport_fixture import published_fixture  # noqa: E402
from test_narrative_transport_cli import _cli, _reference  # noqa: E402


def main() -> None:
    directory = REPO / "tests/fixtures/narrative_transport_v1"
    with tempfile.TemporaryDirectory(prefix="cw-golden-") as scratch:
        with published_fixture(Path(scratch)) as fixture:
            reference = _reference(fixture)
            result = _cli(fixture, "read", {
                "schema_version": "narrative-read-request/1", "narrative_ref": reference,
                "as_of_date": "2026-09-01", "expected_source": fixture.expected_source,
            })
            assert result.returncode == 0, result.stderr
            bundle = json.loads(result.stdout)
            bundle["expected_read_policy_sha256"] = "f" * 64
            prior = json.loads((directory / "bundle.json").read_bytes())
            prior["versions"] = bundle["versions"]
            # Span parser_version is provenance too. Keep its identity, hash,
            # locator, source text and all structured semantics exact.
            for old_span, span in zip(prior["evidence_spans"], bundle["evidence_spans"], strict=True):
                old_span["parser_version"] = span["parser_version"]
            for field in ("prompt_version", "response_sha256"):
                prior["summary"]["model"][field] = bundle["summary"]["model"][field]
            assert prior == bundle, "source/span/summary semantics changed; inspect before updating golden"
            content = canonical_json(bundle).encode("utf-8")
            reference.update(artifact_version_id="narrative-golden-txt-v1",
                             artifact_sha256=hashlib.sha256(content).hexdigest(), byte_size=len(content))
            receipt = json.loads(result.stderr)
            receipt.update(narrative_ref=reference, source_read_policy_sha256="f" * 64,
                           read_at="2026-10-03T00:00:00Z")
            request = json.loads((directory / "read_request.json").read_bytes())
            request["narrative_ref"] = reference
            for name, value in (("bundle.json", bundle), ("reference.json", reference),
                                ("read_receipt.json", receipt), ("read_request.json", request)):
                (directory / name).write_bytes(canonical_json(value).encode("utf-8"))
            metadata = json.loads((directory / "metadata.json").read_bytes())
            for name in metadata["file_sha256"]:
                metadata["file_sha256"][name] = hashlib.sha256((directory / name).read_bytes()).hexdigest()
            (directory / "metadata.json").write_bytes(canonical_json(metadata).encode("utf-8"))
            print(canonical_json({"status": "refreshed", "versions": bundle["versions"],
                                  "source_spans_summary_unchanged": True, "external_model_calls": 0}))


if __name__ == "__main__":
    main()
