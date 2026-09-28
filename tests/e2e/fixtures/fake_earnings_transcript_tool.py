"""Offline subprocess fixture for the earnings-transcripts JSON boundary.

The fixture deliberately has no company-wiki imports.  It behaves like a
provider process: discovery returns metadata only and candidate fetch returns
one bounded ``earnings-transcript-result/2`` object.
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
import sys
import time


DISCOVERY_SCHEMA = "earnings-transcript-discovery-result/1"
FETCH_SCHEMA = "earnings-transcript-result/2"


def _body(kind: str) -> tuple[bytes, str, str]:
    lines = (
        "Full Conference Call Transcript",
        "CEO: We launched a new product and expanded overseas capacity.",
        "Questions & Answers",
        "Analyst: Is the new product ready for commercial launch?",
        "CEO: It is too early to speculate on commercial launch, though customer validation continues.",
    )
    canonical = "\n".join(lines) + "\n"
    if kind == "txt":
        return canonical.encode("utf-8"), canonical, "text/plain"
    html = (
        "<html><body><main>"
        f"<h1>{lines[0]}</h1>"
        f"<p>{lines[1]}</p>"
        "<h2>Questions &amp; Answers</h2>"
        f"<p>{lines[3]}</p>"
        f"<p>{lines[4]}</p>"
        "</main></body></html>"
    )
    return html.encode("utf-8"), canonical, "text/html"


def _increment(state_dir: Path, operation: str) -> None:
    state_dir.mkdir(parents=True, exist_ok=True)
    path = state_dir / f"{operation}-count.txt"
    count = int(path.read_text(encoding="ascii")) if path.exists() else 0
    path.write_text(str(count + 1), encoding="ascii")


def _load_request() -> dict:
    value = json.loads(sys.stdin.buffer.read().decode("utf-8"))
    if not isinstance(value, dict):
        raise ValueError("request must be an object")
    return value


def _candidate(request: dict, kind: str) -> dict:
    suffix = "txt" if kind == "txt" else "html"
    return {
        "provider": "fixture_provider",
        "ticker": request["ticker"],
        "exchange": request["exchange"],
        "fiscal_period": f"{request['fiscal_year']}-Q{request['fiscal_quarter']}",
        "provider_document_id": f"acme-2026-q2-{suffix}",
        "source_url": f"https://fixtures.invalid/transcripts/acme-2026-q2.{suffix}",
        "published_date": "2026-06-30",
    }


def _discover(request: dict, kind: str) -> dict:
    candidate = _candidate(request, kind)
    return {
        "schema_version": DISCOVERY_SCHEMA,
        "request_id": request["request_id"],
        "status": "discovered",
        "provider": "fixture_provider",
        "ticker": request["ticker"],
        "fiscal_period": candidate["fiscal_period"],
        "as_of_date": request["as_of_date"],
        "candidate_count": 1,
        "candidates": [candidate],
    }


def _fetch(request: dict, kind: str, fault: str) -> dict:
    body, canonical, mime_type = _body(kind)
    candidate = request["candidate"]
    effective_url = candidate["source_url"]
    if fault == "redirect":
        effective_url = "https://redirect.invalid/transcripts/acme-2026-q2.html"
    return {
        "schema_version": FETCH_SCHEMA,
        "request_id": request["request_id"],
        "status": "fetched",
        "provider": "fixture_provider",
        "ticker": request["ticker"],
        "exchange": request["exchange"],
        "fiscal_period": f"{request['fiscal_year']}-Q{request['fiscal_quarter']}",
        "as_of_date": request["as_of_date"],
        "title": "Acme 2026 Q2 Earnings Call Transcript",
        "source_url": candidate["source_url"],
        "provider_document_id": candidate["provider_document_id"],
        "published_date": candidate["published_date"],
        "extraction_version": "fixture-provider-text/1",
        "provider_payload_sha256": hashlib.sha256(body).hexdigest(),
        "canonical_content_sha256": hashlib.sha256(canonical.encode("utf-8")).hexdigest(),
        "content_bytes": len(canonical.encode("utf-8")),
        "provider_payload_encoding": "base64",
        "provider_payload_base64": base64.b64encode(body).decode("ascii"),
        "provider_payload_mime_type": mime_type,
        "effective_url": effective_url,
        "http_status": 200,
        "retrieved_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "adapter_name": "fake-earnings-transcript-tool",
        "adapter_version": "1.0.0",
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--operation", choices=("discover", "fetch-candidate"), required=True)
    parser.add_argument("--state-dir", type=Path, required=True)
    parser.add_argument("--fixture", choices=("html", "txt"), default="html")
    parser.add_argument(
        "--fault", choices=("ok", "timeout", "bad-json", "oversized", "redirect"),
        default="ok",
    )
    args = parser.parse_args()
    request = _load_request()
    _increment(args.state_dir, args.operation)
    if args.operation == "fetch-candidate" and args.fault == "timeout":
        time.sleep(10)
    if args.operation == "fetch-candidate" and args.fault == "bad-json":
        sys.stdout.write("{bad-json")
        return 0
    if args.operation == "fetch-candidate" and args.fault == "oversized":
        sys.stdout.write("x" * (512 * 1024))
        return 0
    result = (
        _discover(request, args.fixture)
        if args.operation == "discover"
        else _fetch(request, args.fixture, args.fault)
    )
    sys.stdout.write(json.dumps(result, ensure_ascii=False, separators=(",", ":")) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
