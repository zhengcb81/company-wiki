"""CLI entry: ``python -m company_wiki.source_catalog.financial_statements.cli``.

Reads one ``financial-statements-request/1`` JSON on stdin, writes one
``financial-statements-response/1`` JSON on stdout. Exit codes: 0 = a valid
response envelope (complete/partial/not_found/unavailable), 2 = request or
config error (error envelope on stdout), 1 = unexpected failure.

``--fixture-root`` enables offline replay of frozen real responses (gzip
fixtures plus manifest) through the same bounded transport — useful for
hermetic end-to-end runs and normalization replay without network access.
"""

from __future__ import annotations

import argparse
import gzip
import json
from pathlib import Path
import sys
from typing import Any, Sequence

from ..config import CatalogConfigError, load_catalog_config
from ..service import SourceCatalog
from ..canonical_writer import CanonicalSourceWriter
from .contracts import (
    STATEMENTS_RESPONSE_SCHEMA_VERSION,
    RequestValidationError,
    StatementsRequest,
)
from .repository import query_financial_statements_readonly
from .service import FinancialStatementsService
from .sina_provider import SinaStatementsProvider

FIXTURE_MANIFEST_VERSION = "financial-statements-fixture-replay/1"


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="company-wiki-financial-statements",
        description="A-share historical financial statements via company-wiki.",
    )
    parser.add_argument(
        "--wiki-root",
        type=Path,
        required=True,
        help="company-wiki connection root containing config/source_catalog.yaml",
    )
    parser.add_argument(
        "--fixture-root",
        type=Path,
        default=None,
        help="offline replay root (manifest.json + *.json.gz fixtures); no network",
    )
    return parser


class FixtureFileTransport:
    """Serves frozen gzip responses by exact URL for offline replay."""

    def __init__(self, fixture_root: Path):
        self.fixture_root = fixture_root
        manifest_path = fixture_root / "manifest.json"
        if not manifest_path.is_file():
            raise FileNotFoundError(f"fixture manifest missing: {manifest_path.name}")
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        self.by_url: dict[str, bytes] = {}
        for entry in manifest.get("fixtures", []):
            url = entry["url"]
            payload = gzip.decompress((fixture_root / entry["file"]).read_bytes())
            self.by_url[url] = payload

    def __call__(self, request):  # httpx handler protocol
        import httpx

        url = str(request.url)
        if url not in self.by_url:
            return httpx.Response(
                404, json={"error": "fixture_not_found", "url": url.split("?")[0]}
            )
        return httpx.Response(
            200,
            content=self.by_url[url],
            headers={"content-type": "application/json; charset=utf-8"},
        )


def _provider(fixture_root: Path | None) -> SinaStatementsProvider:
    if fixture_root is None:
        return SinaStatementsProvider()
    fixture = FixtureFileTransport(fixture_root)

    def factory(budget):
        import httpx

        from ..bounded_http import BudgetedHTTPTransport

        return httpx.Client(
            transport=BudgetedHTTPTransport(
                httpx.MockTransport(fixture), budget
            )
        )

    return SinaStatementsProvider(http_client_factory=factory)


def _error_envelope(status: str, message: str, **extra: Any) -> dict[str, Any]:
    payload = {
        "schema_version": STATEMENTS_RESPONSE_SCHEMA_VERSION,
        "status": status,
        "error": message,
    }
    payload.update(extra)
    return payload


def main(argv: Sequence[str] | None = None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    args = _parser().parse_args(argv)
    try:
        request_payload = json.loads(sys.stdin.read())
    except json.JSONDecodeError as exc:
        json.dump(_error_envelope("request_error", f"invalid request JSON: {exc}"), sys.stdout)
        sys.stdout.write("\n")
        return 2
    try:
        request = StatementsRequest.from_payload(request_payload)
    except RequestValidationError as exc:
        json.dump(_error_envelope(exc.code, str(exc)), sys.stdout)
        sys.stdout.write("\n")
        return 2

    root = args.wiki_root.expanduser().resolve(strict=True)
    config_path = root / "config" / "source_catalog.yaml"
    if not config_path.is_file():
        json.dump(
            _error_envelope("config_error", "wiki root lacks config/source_catalog.yaml"),
            sys.stdout,
        )
        sys.stdout.write("\n")
        return 2
    try:
        config = load_catalog_config(config_path, project_root=root)
    except (CatalogConfigError, OSError) as exc:
        json.dump(_error_envelope("config_error", f"invalid source catalog config: {exc}"), sys.stdout)
        sys.stdout.write("\n")
        return 2

    # Read-only requests never open the writable store: no database is
    # created or migrated on a reuse-only path.
    if request.intent == "reuse_only":
        from .service import handle_reuse_only_request

        response = handle_reuse_only_request(request, config)
        json.dump(response, sys.stdout, ensure_ascii=False, indent=1)
        sys.stdout.write("\n")
        return 0
    catalog = SourceCatalog(config)
    try:
        provider = _provider(args.fixture_root)
    except (FileNotFoundError, OSError, json.JSONDecodeError):
        # A broken fixture root must not break pure-reuse runs; any actual
        # fetch attempt then reports provider_unavailable honestly.
        provider = None
    service = FinancialStatementsService(
        catalog=catalog,
        writer=CanonicalSourceWriter(catalog),
        provider=provider,
    )
    try:
        response = service.handle_request(request)
    except Exception as exc:  # noqa: BLE001 - surfaced as an honest envelope
        json.dump(_error_envelope("fatal", f"{type(exc).__name__}: {exc}"), sys.stdout)
        sys.stdout.write("\n")
        return 1
    json.dump(response, sys.stdout, ensure_ascii=False, indent=1)
    sys.stdout.write("\n")
    return 0


__all__ = ["FIXTURE_MANIFEST_VERSION", "FixtureFileTransport", "main"]


if __name__ == "__main__":
    raise SystemExit(main())
