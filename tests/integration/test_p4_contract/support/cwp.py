"""Drivers for the published CWP read/export interfaces (card 2 / 5.5.1).

Only ``company-wiki-source-read`` and ``company-wiki-source-export-v2`` are
invoked, through ``sys.executable -B -m`` with the lane's ``src`` on
``PYTHONPATH``.  The catalog is opened read-only and is never scanned or written.
"""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from . import constants as C
from .jsonio import JsonRejected, loads_strict


READ_MODULE = "company_wiki.source_catalog.source_reader_cli"
EXPORT_MODULE = "company_wiki.source_catalog.source_export_v2_cli"
CATALOG_CLI_MODULE = "company_wiki.source_catalog.cli"


class CwpUnavailable(RuntimeError):
    """A published CWP entry point refused to run; the lane reports, never repairs."""


@dataclass(frozen=True)
class ReadResult:
    """One successful read: raw bytes plus the parsed stderr receipt."""

    data: bytes
    receipt: dict[str, Any]
    argv: tuple[str, ...]


@dataclass(frozen=True)
class ExportResult:
    """One successful export: the parsed v2 bundle."""

    bundle: dict[str, Any]
    argv: tuple[str, ...]


def _environment() -> dict[str, str]:
    env = dict(os.environ)
    env["PYTHONPATH"] = str(C.REPO_ROOT / "src")
    env["PYTHONIOENCODING"] = "utf-8"
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    # The lane is hermetic: never let a CWP subprocess reach the network.
    env["COMPANY_WIKI_NETWORK"] = "blocked"
    env["COMPANY_WIKI_REAL_LLM"] = "0"
    env["PYTHON_DOTENV_DISABLED"] = "1"
    for secret in (
        "OPENAI_API_KEY", "DEEPSEEK_API_KEY", "MINIMAX_API_KEY",
        "MIMO_API_KEY", "TAVILY_API_KEY", "ANTHROPIC_API_KEY",
    ):
        env.pop(secret, None)
    return env


def _run(argv: list[str], *, timeout: int, stdin: bytes | None = None):
    try:
        return subprocess.run(
            argv,
            input=stdin,
            cwd=str(C.REPO_ROOT),
            env=_environment(),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired as exc:
        raise CwpUnavailable(f"published CWP command timed out: {argv[2]}") from exc
    except OSError as exc:
        raise CwpUnavailable(f"published CWP command failed to start: {exc}") from exc


def read_source(
    config_path: Path,
    *,
    document_id: str,
    source_id: str,
    content_sha256: str,
    include_availability_evidence: bool = True,
    timeout: int = C.MAX_COMMAND_TIMEOUT_S,
) -> ReadResult:
    """Read exact source bytes through ``company-wiki-source-read``."""
    argv = [
        sys.executable, "-B", "-m", READ_MODULE,
        "--config", str(config_path),
        "--document-id", document_id,
        "--source-id", source_id,
        "--content-sha256", content_sha256,
        "--purpose", "filing_reuse",
    ]
    if include_availability_evidence:
        argv.append("--include-availability-evidence")
    proc = _run(argv, timeout=timeout)
    if proc.returncode != 0:
        raise CwpUnavailable(
            f"source read refused ({proc.returncode}): "
            f"{proc.stderr.decode('utf-8', 'replace')[:400]}"
        )
    try:
        receipt = loads_strict(proc.stderr, label="read receipt")
    except JsonRejected as exc:
        raise CwpUnavailable(f"read receipt is not strict JSON: {exc}") from exc
    if not isinstance(receipt, dict):
        raise CwpUnavailable("read receipt is not an object")
    return ReadResult(data=proc.stdout, receipt=receipt, argv=tuple(argv))


def export_sources(
    config_path: Path,
    *,
    source_refs: list[dict[str, Any]],
    evidence_spans: list[dict[str, Any]] | None = None,
    timeout: int = C.MAX_COMMAND_TIMEOUT_S,
) -> ExportResult:
    """Publish a pathless v2 bundle through ``company-wiki-source-export-v2``."""
    argv = [
        sys.executable, "-B", "-m", EXPORT_MODULE,
        "--config", str(config_path),
    ]
    request = {
        "schema_version": C.SOURCE_REF_SCHEMA_VERSION,
        "source_refs": source_refs,
        "evidence_spans": list(evidence_spans or []),
    }
    stdin = json.dumps(request, ensure_ascii=False).encode("utf-8")
    proc = _run(argv, timeout=timeout, stdin=stdin)
    if proc.returncode != 0:
        raise CwpUnavailable(
            f"source export refused ({proc.returncode}): "
            f"{proc.stderr.decode('utf-8', 'replace')[:400]}"
        )
    try:
        bundle = loads_strict(proc.stdout, label="export bundle")
    except JsonRejected as exc:
        raise CwpUnavailable(f"export bundle is not strict JSON: {exc}") from exc
    if not isinstance(bundle, dict):
        raise CwpUnavailable("export bundle is not an object")
    return ExportResult(bundle=bundle, argv=tuple(argv))


def build_wire_span(*, source_id: str, span: dict[str, Any]) -> dict[str, Any]:
    """A wire-shaped ``EvidenceSpan`` dict built by CWP's own value object.

    ``span_id``/``output_sha256``/``locator`` are derived quantities, and the
    export CLI refuses any dict that is not exactly the 12 published fields, so
    the lane must not hand-roll them.  Building through ``EvidenceSpan.create``
    keeps the request valid and the digests identical to what CWP publishes.
    """
    from company_wiki.source_contract.evidence_span import (
        EvidenceCoordinates,
        EvidenceSpan,
    )

    coordinates = EvidenceCoordinates(
        page_number=None,
        paragraph_index=None,
        table_index=None,
        row_index=None,
        column_index=None,
        char_start=span["char_start"],
        char_end=span["char_end"],
    )
    return EvidenceSpan.create(
        source_id=source_id,
        coordinates=coordinates,
        raw_text=span["raw_text"],
        structured_value=None,
        parser_name="p4-fixture-parser",
        parser_version="1.0.0",
        parse_status="parsed",
        quality_flags=[],
    ).to_dict()


def wire_spans(sources: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Every fixture span, shaped for ``company-wiki-source-export-v2``."""
    return [
        build_wire_span(source_id=item["source_id"], span=span)
        for item in sources
        for span in item["spans"]
    ]


def ensure_catalog_state(config_path: Path, *, timeout: int = C.MAX_COMMAND_TIMEOUT_S) -> None:
    """Materialize ``catalog/state`` so the read-only CLIs can open the catalog.

    Neither published CLI scans, and ``ReadOnlyCatalogReader`` refuses to create
    a missing database, so a fixture that ships only source files is unreadable
    until ``company-wiki-source-catalog scan`` has run once (probe: export
    ``catalog_unavailable`` before, rc 0 after).  A catalog that already has
    state is left untouched, so a ROOT-provided read-only catalog is never
    rewritten.  ``--config`` is a *global* flag and must precede ``scan``.
    """
    from company_wiki.source_catalog.config import load_catalog_config

    try:
        database = Path(load_catalog_config(config_path).database_path)
    except Exception as exc:  # noqa: BLE001 - config refusal becomes a lane skip
        raise CwpUnavailable(f"catalog config unreadable: {exc}") from exc
    if database.is_file():
        return
    argv = [
        sys.executable, "-B", "-m", CATALOG_CLI_MODULE,
        "--config", str(config_path), "scan",
    ]
    proc = _run(argv, timeout=timeout)
    if proc.returncode != 0:
        raise CwpUnavailable(
            f"catalog scan refused ({proc.returncode}): "
            f"{proc.stderr.decode('utf-8', 'replace')[:400]}"
        )
    if not database.is_file():
        raise CwpUnavailable(f"catalog scan left no state database: {database}")


def load_expected() -> dict[str, Any]:
    """Read ``fixtures/expected.json``; the single source of fixture truth."""
    payload = json.loads(
        (C.FIXTURES_DIR / "expected.json").read_text(encoding="utf-8")
    )
    if payload.get("schema_version") != C.P4_FIXTURE_SCHEMA:
        raise CwpUnavailable("fixtures/expected.json has an unexpected schema_version")
    return payload


def expected_sources() -> list[dict[str, Any]]:
    return list(load_expected()["sources"])


def expected_config_sha256() -> str:
    return str(load_expected()["catalog_config"]["sha256"])


def manifest_for(bundle: dict[str, Any], source_id: str) -> dict[str, Any]:
    """Pick one manifest out of a v2 bundle by ``source_id``."""
    manifests = bundle.get("manifests")
    if not isinstance(manifests, list):
        raise CwpUnavailable("export bundle has no manifests array")
    for item in manifests:
        if isinstance(item, dict) and item.get("source_id") == source_id:
            return item
    raise CwpUnavailable(f"bundle does not carry manifest for {source_id}")


def recompute_bundle_sha256(bundle: dict[str, Any]) -> str:
    """Recount ``bundle_sha256`` the way CWP's export contract counts it.

    The export contract canonicalizes with ``ensure_ascii=False`` (see
    ``source_export_v2._canonical_json``), which differs from the
    ``ensure_ascii=True`` form INTERFACES.md section 1 mandates for this lane's
    own artifacts.  Reproducing the *producer's* form is what makes the
    recomputation comparable to the declared digest; the lane's receipts and
    handoff still use the section-1 form.  Verified against the published CLI:
    the fixture bundle digest matches only under ``ensure_ascii=False``.
    """
    payload = {
        key: value for key, value in bundle.items()
        if key not in {"bundle_sha256", "export_id"}
    }
    blob = json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")
    return hashlib.sha256(blob).hexdigest()


def export_id_for(bundle_sha256: str) -> str:
    """The export contract's deterministic ``export_id`` for a bundle digest."""
    return "urn:company-wiki:source-export:sha256:" + bundle_sha256
