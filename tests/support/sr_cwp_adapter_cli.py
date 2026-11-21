"""Fixture ``json_command_v1`` adapter CLI for public-discovery tests.

Wire: ``<command...> discover`` with one JSON request on stdin; one JSON
response on stdout.  This is the same external-process contract the
production adapters use (``JsonCommandAdapter``), exercised through a real
child process — no network, no SDK, no downloads.
"""

from __future__ import annotations

import argparse
import json
import sys


def _candidate(provider_document_id: str, *, filing_date: str, kind: str,
               amended: bool = False, fiscal_period: str | None = "FY",
               market: str = "CN", security_id: str = "600001"):
    return {
        "candidate_id": "fixture:" + provider_document_id,
        "provider": "fixture", "provider_document_id": provider_document_id,
        "market": market, "title": "Acme filing", "entity": "Acme",
        "source_url": "https://provider.invalid/" + provider_document_id,
        "document_kind": kind, "filing_date": filing_date,
        "fiscal_year": 2026, "fiscal_period": fiscal_period,
        "amended": amended, "security_id": security_id,
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--name", required=True)
    parser.add_argument("--version", required=True)
    parser.add_argument("action", choices=("discover", "fetch"))
    args = parser.parse_args(argv)
    payload = json.load(sys.stdin)
    request = payload.get("request", payload)
    if args.action != "discover":
        print(json.dumps({
            "schema_version": "1.0", "status": "failed",
            "adapter": {"name": args.name, "version": args.version},
            "error": {"code": "fetch_not_supported", "type": "ValueError",
                      "message": "discovery fixture never fetches"},
        }, ensure_ascii=False), file=sys.stderr)
        return 1
    response = {
        "schema_version": "1.0", "status": "ok",
        "adapter": {"name": args.name, "version": args.version},
        "candidates": [
            # The first accession is the locally registered original; the
            # revised one stays missing so the caller must fetch it.
            _candidate("annual-report.pdf", filing_date="2026-05-01",
                       kind=request.get("document_kind", "annual_report")),
            _candidate("annual-report-revised.pdf", filing_date="2026-05-01",
                       kind=request.get("document_kind", "annual_report"),
                       amended=True),
        ],
        "coverage": "complete",
        "covered_from": "2026-01-01",
        "covered_to": request.get("as_of_date", "2026-05-31"),
        # Bounded adapters must account the exchange they actually made.
        "acquisition_usage": {
            "schema_version": "1.0",
            "response_bytes": len(json.dumps(request).encode("utf-8")),
            "cost_usd": "0",
        },
    }
    print(json.dumps(response, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
