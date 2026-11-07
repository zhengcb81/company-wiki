"""Contract for the public canonical issuer bridge (G-CWP-CANONICAL-01).

Every case runs the real fixed CLI as a subprocess against an isolated CWP
engine fixture (scan + recorded verified source facts through the real
engines) and, for the StockWiki side, a transport stand-in that frames the
frozen ``stockwiki.dashboard_issuer_proof/1`` seam around the REAL StockWiki
identity engine (build_identity_request / IdentityReceiptStore /
QuickScanStore / MarketRegistryStore at the pinned checkout).  The stand-in
exists only because the owner proof CLI itself (G-SW-ISSUER-PROOF-READ-01)
is not delivered yet; all identity semantics come from the pinned real
engine — this is seam framing, never a trust callback.

Covered here:

- same-issuer positive through the real engines, with complete SourceRef,
  issuer pin, exact total and association_scope=issuer_only;
- precise zero-write: exact file-set SHA/size around a query;
- negatives: wrong issuer, bare-ticker-only, foreign listing, missing
  evidence, multi-listing ambiguity, revoked receipt, provisional owner,
  wrong market, old source version, tampered receipt hash, offline proof
  CLI, future envelope schema, foreign binding namespace, query-echo
  mismatch, analysis subject, non-UTC as_of, malformed/duplicate/oversized
  request JSON, incomplete operator configuration;
- pagination pinned to the proof snapshot with honest stale on owner
  identity revision bump or proven-set change, never mixing revisions.
"""

from __future__ import annotations

import base64
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from company_wiki.source_catalog import CatalogConfig, RootSpec, SourceCatalog  # noqa: E402
from company_wiki.source_catalog.public_canonical_browser import (  # noqa: E402
    REQUEST_SCHEMA,
    RESPONSE_SCHEMA,
    SW_ENVELOPE_SCHEMA_VERSION,
)
from company_wiki.source_catalog.source_reader import SourceRef  # noqa: E402


# The pinned StockWiki checkout supplies the REAL identity engine for the
# fixture stand-in (read-only import in a subprocess).  Computed, never a
# literal host path; override with CWP_SW_CHECKOUT when the checkout lives
# elsewhere.  A missing checkout fails the engine tests by name (it is the
# named prerequisite) — the positive is never skipped.
SW_CHECKOUT = Path(os.environ.get("CWP_SW_CHECKOUT")
                   or (Path.home() / "Projects" / "StockWiki"))
SW_REGISTRY_FIXTURE = (SW_CHECKOUT / "tests" / "fixtures" / "market_registry"
                       / "iso10383_sample.csv")

ENT_ACME = "ENT_3f2a9c81-1111-4c01-9a01-00000000ac01"
ENT_BETA = "ENT_3f2a9c81-2222-4c02-9a02-00000000be02"
AS_OF = "2026-10-30T00:00:00Z"

CIK_ACME = "87654321"
CIK_BETA = "87654322"
TEN_K_TITLE = "ACME Corp Form 10-K 2025"
BETA_TITLE = "BETA Corp Form 10-K 2025"

ACME_BODY = (
    "<html><head><title>" + TEN_K_TITLE + "</title></head><body>"
    '<script type="application/json" id="primary-dei">'
    "{\"EntityCentralIndexKey\": \"000087654321\","
    "\"DocumentFiscalYearFocus\": \"2025\","
    "\"DocumentFiscalPeriodFocus\": \"FY\","
    "\"DocumentType\": \"10-K\","
    "\"DocumentPeriodEndDate\": \"2025-12-31\"}"
    "</script><p>ACME CORP annual report.</p></body></html>"
).encode("utf-8")
ACME_AMENDED_BODY = (
    "<html><head><title>" + TEN_K_TITLE + " (Amended)</title></head>"
    "<body><p>ACME CORP amended annual report.</p></body></html>"
).encode("utf-8")
ACME_TICKER_ONLY_BODY = (
    "<html><head><title>ACME press note</title></head>"
    "<body><p>ACME ticker mentioned, nothing verified.</p></body></html>"
).encode("utf-8")
ACME_CN_BODY = b"%PDF-1.4 acme cn annual"
BETA_BODY = (
    "<html><head><title>" + BETA_TITLE + "</title></head><body>"
    '<script type="application/json" id="primary-dei">'
    "{\"EntityCentralIndexKey\": \"000087654322\","
    "\"DocumentFiscalYearFocus\": \"2025\","
    "\"DocumentFiscalPeriodFocus\": \"FY\","
    "\"DocumentType\": \"10-K\","
    "\"DocumentPeriodEndDate\": \"2025-12-31\"}"
    "</script><p>BETA CORP annual report.</p></body></html>"
).encode("utf-8")

ACME_URN = "urn:company-wiki:source:sha256:" + hashlib.sha256(
    ACME_BODY).hexdigest()
ACME_AMENDED_URN = "urn:company-wiki:source:sha256:" + hashlib.sha256(
    ACME_AMENDED_BODY).hexdigest()
ACME_TICKER_ONLY_URN = "urn:company-wiki:source:sha256:" + hashlib.sha256(
    ACME_TICKER_ONLY_BODY).hexdigest()
ACME_CN_URN = "urn:company-wiki:source:sha256:" + hashlib.sha256(
    ACME_CN_BODY).hexdigest()
BETA_URN = "urn:company-wiki:source:sha256:" + hashlib.sha256(
    BETA_BODY).hexdigest()


# --- CWP engine fixture -------------------------------------------------------


def _sha(body: bytes) -> str:
    return hashlib.sha256(body).hexdigest()


def _source_urn(body: bytes) -> str:
    return "urn:company-wiki:source:sha256:" + _sha(body)


def _document_urn(body: bytes) -> str:
    return "urn:company-wiki:document:sha256:" + _sha(body)


def _write_doc(directory: Path, name: str, body: bytes, sidecar: dict) -> None:
    directory.mkdir(parents=True, exist_ok=True)
    (directory / name).write_bytes(body)
    (directory / f"{name}.source.json").write_text(
        json.dumps(sidecar, ensure_ascii=False), encoding="utf-8",
    )


def _us_sidecar(entity: str, display: str, security: str, provider: str,
                title: str) -> dict:
    return {
        "schema_version": "1.0",
        "canonical_entity_id": entity,
        "display_name": display,
        "market": "US",
        "security_id": security,
        "document_kind": "annual_report",
        "filing_date": "2026-02-27",
        "form_type": "10-K",
        "provider": "test",
        "provider_document_id": provider,
        "language": "en",
        "fiscal_year": 2025,
        "period_end": "2025-12-31",
        "title": title,
    }


def _dei_facts_evidence(sha: str, entity: str, market: str, security: str,
                        cik: str, title: str) -> tuple[dict, dict]:
    facts = {
        "entity": entity, "market": market, "security_id": security,
        "document_kind": "annual_report", "fiscal_year": 2025,
        "fiscal_period": "FY", "form_type": "10-K",
        "period_end": "2025-12-31", "title": title,
    }
    method = "sec-primary-dei/1"
    issuer_base = {"content_sha256": sha, "extraction_method": method,
                   "primary_cik": cik, "issuer_record_id": "US:" + cik}
    evidence = {
        "document_kind": {"content_sha256": sha, "extraction_method": method,
                          "locator": "primary-dei:/DocumentType",
                          "value": "annual_report"},
        "entity": {**issuer_base,
                   "locator": "primary-dei:/EntityCentralIndexKey",
                   "value": entity},
        "market": {**issuer_base,
                   "locator": "primary-dei:/EntityCentralIndexKey",
                   "value": market},
        "security_id": {**issuer_base,
                        "locator": "primary-dei:/EntityCentralIndexKey",
                        "value": security},
        "fiscal_year": {"content_sha256": sha, "extraction_method": method,
                        "locator": "primary-dei:/DocumentFiscalYearFocus",
                        "value": 2025},
        "fiscal_period": {"content_sha256": sha, "extraction_method": method,
                          "locator": "primary-dei:/DocumentFiscalPeriodFocus",
                          "value": "FY"},
        "form_type": {"content_sha256": sha, "extraction_method": method,
                      "locator": "primary-dei:/DocumentType", "value": "10-K"},
        "period_end": {"content_sha256": sha, "extraction_method": method,
                       "locator": "primary-dei:/DocumentPeriodEndDate",
                       "value": "2025-12-31"},
        "title": {"content_sha256": sha, "extraction_method": method,
                  "locator": "html:/html/head/title", "value": title},
    }
    return facts, evidence


def _record_facts(catalog: SourceCatalog, body: bytes, mime: str,
                  facts: dict, evidence: dict) -> None:
    from company_wiki.source_catalog.assertion_service import record_source_facts

    ref = SourceRef(
        document_id=_document_urn(body),
        source_id=_source_urn(body),
        content_sha256=_sha(body),
        byte_size=len(body),
        mime_type=mime,
        schema_version="2.0",
    )
    result = record_source_facts(catalog, ref=ref, facts=facts,
                                 evidence=evidence)
    assert result["status"] == "recorded", result


def _scan_config(tmp_path: Path) -> CatalogConfig:
    return CatalogConfig(
        project_root=tmp_path,
        catalog_dir=tmp_path / ".source_catalog",
        roots=(
            RootSpec("company_raw", tmp_path / "companies", "company_raw",
                     priority=10, adapter_id="company_raw_v1", read_only=False,
                     reusable_for_filing=True,
                     canonical_write_target="companies"),
        ),
        reusable_root_kinds=("company_raw",),
    )


def _build_cwp(tmp_path: Path) -> SourceCatalog:
    companies = tmp_path / "companies"
    _write_doc(companies / "ACME" / "raw" / "annual", "acme_10k_2025.html",
               ACME_BODY, _us_sidecar(ENT_ACME, "ACME CORP", "ACME",
                                      "acme-10k-25", TEN_K_TITLE))
    _write_doc(companies / "ACME" / "raw" / "annual",
               "acme_10k_2025_amended.html", ACME_AMENDED_BODY,
               _us_sidecar(ENT_ACME, "ACME CORP", "ACME", "acme-10k-25-am",
                           TEN_K_TITLE + " (Amended)"))
    _write_doc(companies / "ACME" / "raw" / "notes", "acme_ticker_note.html",
               ACME_TICKER_ONLY_BODY,
               _us_sidecar(ENT_ACME, "ACME CORP", "ACME", "acme-note",
                           "ACME press note"))
    _write_doc(companies / "ACME" / "raw" / "cn", "acme_cn_annual.pdf",
               ACME_CN_BODY, {
                   "schema_version": "1.0",
                   "canonical_entity_id": ENT_ACME,
                   "display_name": "ACME CORP",
                   "market": "CN",
                   "security_id": "600000",
                   "document_kind": "annual_report",
                   "filing_date": "2026-03-30",
                   "form_type": "FY",
                   "provider": "test",
                   "provider_document_id": "acme-cn-25",
                   "language": "zh",
                   "fiscal_year": 2025,
                   "period_end": "2025-12-31",
               })
    _write_doc(companies / "BETA" / "raw" / "annual", "beta_10k_2025.html",
               BETA_BODY, _us_sidecar(ENT_BETA, "BETA CORP", "BETA",
                                      "beta-10k-25", BETA_TITLE))
    catalog = SourceCatalog(_scan_config(tmp_path))
    catalog.scan()

    facts, evidence = _dei_facts_evidence(
        _sha(ACME_BODY), "ACME CORP", "US", "ACME", CIK_ACME, TEN_K_TITLE)
    _record_facts(catalog, ACME_BODY, "text/html", facts, evidence)
    facts, evidence = _dei_facts_evidence(
        _sha(BETA_BODY), "BETA CORP", "US", "BETA", CIK_BETA, BETA_TITLE)
    _record_facts(catalog, BETA_BODY, "text/html", facts, evidence)
    cn_facts = {
        "entity": "ACME CORP", "market": "CN", "security_id": "600000",
        "document_kind": "annual_report", "fiscal_year": 2025,
        "period_end": "2025-12-31",
    }
    cn_evidence = {
        key: {"locator": "sidecar:" + key, "value": value}
        for key, value in cn_facts.items()
    }
    _record_facts(catalog, ACME_CN_BODY, "application/pdf", cn_facts,
                  cn_evidence)
    return catalog


def _config_path(tmp_path: Path) -> Path:
    config_path = tmp_path / "source_catalog.yaml"
    config_path.write_text(json.dumps({
        "schema_version": "1.0",
        "catalog_dir": str(tmp_path / ".source_catalog"),
        "reusable_root_kinds": ["company_raw"],
        "roots": [{
            "root_id": "company_raw", "kind": "company_raw",
            "path": str(tmp_path / "companies"), "priority": 10,
        }],
    }), encoding="utf-8")
    return config_path


# --- StockWiki real-engine transport stand-in ---------------------------------


DRIVER_SOURCE = r'''
"""Frozen-seam framing around the REAL StockWiki identity engine.

Stand-in for the not-yet-delivered G-SW-ISSUER-PROOF-READ-01 CLI.  All
identity semantics (entity store, receipts, market registry, G2b envelope)
come from the pinned StockWiki checkout; this wrapper only implements the
frozen framing: bounds, negative mapping, listing selection and the
receipt_sha256 rule.  It is NOT authority: the CWP side revalidates
everything it consumes.
"""

import hashlib
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, r"%(sw)s")

from stockwiki.identity_g2b import IdentityRequestError, build_identity_request
from stockwiki.identity_receipts import (
    IdentityReceiptStore,
    binding_projection,
)
from stockwiki.identity_snapshot import listing_v21_for_security
from stockwiki.market_registry import MarketRegistryStore
from stockwiki.paths import WorkspacePaths
from stockwiki.quick_scan_store import QuickScanStore

SCHEMA_VERSION = "%(schema)s"
LIBRARY_REVISION = "not_provided_no_global_revision"
MAX_STDIN = 65536
MAX_STDOUT = 1048576

NEGATIVE_MAP = {
    "entity_not_found": ("not_found", ["canonical_entity_not_found"]),
    "market_not_registered": ("unavailable", ["market_not_registered"]),
    "mic_unresolved": ("unavailable", ["mic_unresolved"]),
    "mic_not_registered": ("unavailable", ["mic_not_registered"]),
}


def _canon(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True,
                      separators=(",", ":"), allow_nan=False)


def _receipt(envelope):
    body = {k: v for k, v in envelope.items() if k != "receipt_sha256"}
    return hashlib.sha256(_canon(body).encode("utf-8")).hexdigest()


def _listing(security, entity_id):
    return listing_v21_for_security(security, entity_id)


def _stores(root):
    paths = WorkspacePaths.from_root(root)
    qss = QuickScanStore(paths)
    receipts = IdentityReceiptStore(paths)
    registry = MarketRegistryStore(paths)
    missing = [store.database_path.name
               for store in (qss, receipts, registry)
               if not store.database_path.exists()]
    if missing:
        return None, ("unavailable", ["receipt_store_missing"] + missing)
    return (qss, receipts, registry), None


def _negative_state(code):
    if code in NEGATIVE_MAP:
        return NEGATIVE_MAP[code]
    if code.startswith("receipt_"):
        return ("unavailable", [code])
    if code.startswith("binding_") or code.startswith("envelope_"):
        return ("incompatible", [code])
    return ("unavailable", [code])


def _select_listing(payload, requested):
    listings = payload["listings"]
    active = [item for item in listings if item["listing_status"] == "active"]
    if requested is not None:
        if requested not in [item["listing_id"] for item in listings]:
            return None, ("not_found", ["listing_not_found_in_owner_package"])
        for item in active:
            if item["listing_id"] == requested:
                return item, None
        return None, ("unavailable", ["selected_listing_not_active"])
    if not active:
        return None, ("not_found", ["no_active_listing"])
    if len(active) > 1:
        return None, ("ambiguous", ["multiple_active_listings"])
    return active[0], None


def _provisional_receipt(entity, qss):
    security = entity["securities"][0]
    listing = _listing(security, entity["entity_id"])
    binding = binding_projection(qss, security["source_binding_ref"])
    return {
        "receipt_id": entity["scope_attestation_id"],
        "kind": "provisional_scope",
        "scope": "listed_operating_company",
        "basis": "official_equity_category",
        "negative_scope_flag": False,
        "entity_id": entity["entity_id"],
        "identity_revision": entity["identity_revision"],
        "security_id": security["security_id"],
        "listing_id": listing["listing_id"],
        "source_binding_ref": security["source_binding_ref"],
        "source_listing": {
            "listing_id": listing["listing_id"],
            "security_id": listing["security_id"],
            "market": listing["market"],
            "exchange_raw": listing["exchange_raw"],
            "exchange_mic": listing["exchange_mic"],
            "ticker_raw": listing["ticker_raw"],
            "ticker": listing["ticker"],
            "valid_from": listing["valid_from"],
            "valid_to": listing["valid_to"],
            "canonical_name": binding["source_canonical_name"],
        },
        "source_namespace": binding["source_namespace"],
        "source_record_id": binding["source_record_id"],
        "known_attributes": {
            "incorporation_country": entity["incorporation_country"],
            "security_type": security.get("security_type"),
            "share_class": None,
            "currency": listing["currency"],
            "listing_status": listing["listing_status"],
        },
        "evidence_ref": "https://example.invalid/fixture/equity-category",
        "recorded_at": "2026-10-30T00:00:00Z",
        "status": "active",
    }


def _verified_receipt(entity, qss):
    securities = entity["securities"]
    listings = [_listing(security, entity["entity_id"])
                for security in securities]
    return {
        "receipt_id": entity["verified_issuer_receipt_id"],
        "kind": "verified_issuer",
        "entity_id": entity["entity_id"],
        "identity_revision": entity["identity_revision"],
        "recorded_at": "2026-10-30T00:00:00Z",
        "same_legal_issuer": True,
        "security_ids": [s["security_id"] for s in securities],
        "listing_ids": [listing["listing_id"] for listing in listings],
        "incorporation_country": entity["incorporation_country"],
        "canonical_name": entity["canonical_name"],
        "evidence_ref": "https://example.invalid/issuer-evidence",
        "security_attributes": {
            s["security_id"]: {
                "security_type": s.get("security_type"),
                "share_class": None,
                "adr_ratio": s.get("adr_ratio"),
                "ordinary_security_ref": s.get("ordinary_security_ref"),
            } for s in securities
        },
        "listing_attributes": {
            listing["listing_id"]: {
                **{k: listing[k] for k in (
                    "security_id", "market", "exchange_raw", "exchange_mic",
                    "ticker_raw", "ticker", "currency", "listing_status",
                    "source_binding_ref", "valid_from", "valid_to")},
                **{k: binding_projection(qss, s["source_binding_ref"])[k]
                   for k in ("source_namespace", "source_record_id",
                             "source_canonical_name")},
            }
            for s, listing in zip(securities, listings)
        },
        "verified_adr_ratios": {},
    }


def cmd_setup(root, spec_path):
    with open(spec_path, "r", encoding="utf-8") as handle:
        spec = json.load(handle)
    paths = WorkspacePaths.from_root(root)
    qss = QuickScanStore(paths)
    qss.migrate()
    receipts = IdentityReceiptStore(paths)
    receipts.migrate()
    registry = MarketRegistryStore(paths)
    with open(spec["registry_csv"], "rb") as handle:
        registry.import_official_csv(
            handle.read(),
            source_url="https://example.invalid/mic.csv",
            fetched_at=spec["recorded_at"],
        )
    for scenario in spec["entities"]:
        entity = scenario["entity"]
        bindings = scenario["bindings"]
        if scenario.get("revision_bump"):
            entity["identity_revision"] += 1
        qss.save_entity(entity, source_bindings=bindings)
        if scenario.get("kind") == "verified_issuer":
            receipt = _verified_receipt(entity, qss)
            receipts.record_receipt(receipt, identity_store=qss)
            if scenario.get("revoke"):
                receipts.revoke(receipt["receipt_id"],
                                reason="revoked in fixture",
                                recorded_at=spec["recorded_at"])
        elif scenario.get("kind") == "provisional":
            receipts.record_receipt(_provisional_receipt(entity, qss),
                                    identity_store=qss)
    sys.stdout.write(json.dumps({"setup": "ok"}) + "\n")
    return 0


def cmd_read(root):
    raw = sys.stdin.buffer.read(MAX_STDIN + 1)
    if len(raw) > MAX_STDIN:
        sys.stderr.write("request too large\n")
        return 2
    try:
        query = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        sys.stderr.write("bad request\n")
        return 2
    if os.environ.get("CWP_FIXTURE_CRASH"):
        sys.stderr.write("crash on purpose\n")
        return 7
    entity_id = query["entity_id"]
    listing_id = query.get("listing_id")
    as_of = query["as_of"]
    stores, failure = _stores(root)
    if failure is not None:
        state, reasons = failure
        payload = None
        selected = None
        revision = None
    else:
        qss, receipts, registry = stores
        try:
            built = build_identity_request(
                qss, receipts, registry, entity_id=entity_id, as_of=as_of)
        except IdentityRequestError as exc:
            state, reasons = _negative_state(exc.error_code)
            payload = None
            selected = None
            revision = None
        else:
            if built["payload"]["identity_state"] != "verified":
                state, reasons = ("unverified",
                                  ["owner_identity_not_verified"])
                payload = None
                selected = None
                revision = None
            else:
                listing, failure = _select_listing(built["payload"],
                                                   listing_id)
                if failure is not None:
                    state, reasons = failure
                    payload = None
                    selected = None
                    revision = None
                else:
                    state = "available"
                    reasons = []
                    payload = built
                    selected = listing["listing_id"]
                    revision = built["payload"]["identity_revision"]
    envelope = {
        "schema_version": SCHEMA_VERSION,
        "authority": "stockwiki",
        "state": state,
        "reason_codes": reasons,
        "query": {"entity_id": entity_id, "listing_id": listing_id,
                  "as_of": as_of},
        "selected_listing_id": selected,
        "identity_revision": revision,
        "library_revision": LIBRARY_REVISION,
        "owner_package": payload if state == "available" else None,
        "receipt_sha256": "0" * 64,
    }
    if os.environ.get("CWP_FIXTURE_FUTURE_SCHEMA"):
        envelope["schema_version"] = "stockwiki.dashboard_issuer_proof/2"
    if os.environ.get("CWP_FIXTURE_AS_OF_SHIFT"):
        envelope["query"]["as_of"] = "2020-01-01T00:00:00Z"
    if os.environ.get("CWP_FIXTURE_SELECTED_LISTING"):
        envelope["selected_listing_id"] = os.environ[
            "CWP_FIXTURE_SELECTED_LISTING"]
    if os.environ.get("CWP_FIXTURE_RECEIPT_REF_MISMATCH") \
            and envelope["owner_package"]:
        envelope["owner_package"]["payload"][
            "verified_issuer_receipt_id"] = "IVR_fixture_missing"
    if os.environ.get("CWP_FIXTURE_NAMESPACE") and envelope["owner_package"]:
        for binding in envelope["owner_package"]["trusted_context"][
                "source_bindings"].values():
            binding["source_namespace"] = os.environ["CWP_FIXTURE_NAMESPACE"]
    envelope["receipt_sha256"] = _receipt(envelope)
    if os.environ.get("CWP_FIXTURE_TAMPER_RECEIPT"):
        envelope["receipt_sha256"] = "f" + envelope["receipt_sha256"][1:]
    out = (_canon(envelope) + "\n").encode("utf-8")
    if len(out) > MAX_STDOUT:
        sys.stderr.write("envelope too large\n")
        return 2
    if os.environ.get("CWP_FIXTURE_OVERSIZED_STDOUT"):
        stream = getattr(sys.stdout, "buffer", sys.stdout)
        stream.write(b"x" * (MAX_STDOUT + 1))
        stream.flush()
        return 0
    if os.environ.get("CWP_FIXTURE_OVERSIZED_STDERR"):
        stream = getattr(sys.stderr, "buffer", sys.stderr)
        stream.write(b"x" * (MAX_STDOUT + 1))
        stream.flush()
        return 2
    if os.environ.get("CWP_FIXTURE_NONZERO_AVAILABLE"):
        stream = getattr(sys.stderr, "buffer", sys.stderr)
        stream.write(out)
        stream.flush()
        return 2
    stream = getattr(sys.stdout, "buffer", sys.stdout)
    stream.write(out)
    stream.flush()
    return 0


def main():
    args = sys.argv[1:]
    if not args:
        return 2
    if args[0] == "setup":
        return cmd_setup(Path(args[args.index("--root") + 1]),
                         args[args.index("--spec") + 1])
    if args[0] == "read":
        return cmd_read(Path(args[args.index("--root") + 1]))
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
''' % {"sw": str(SW_CHECKOUT), "schema": SW_ENVELOPE_SCHEMA_VERSION}


def _write_driver(tmp_path: Path) -> Path:
    driver = tmp_path / "sw" / "dashboard_issuer_proof_fixture_cli.py"
    driver.parent.mkdir(parents=True, exist_ok=True)
    driver.write_text(DRIVER_SOURCE, encoding="utf-8", newline="\n")
    return driver


def _sw_entity(entity_id: str, state: str, name: str, ticker: str,
               source_urn: str, receipt_id: str | None, market: str = "US",
               exchange: str = "NASDAQ", mic: str = "XNAS",
               security_suffix: str = "0001") -> tuple[dict, list[dict]]:
    security_id = f"SEC_2c3b5e4f-0000-4b2c-9d3e-00000000{security_suffix}"
    entity = {
        "entity_id": entity_id,
        "identity_schema_version": "2.1.0",
        "identity_state": state,
        "identity_revision": 1,
        "canonical_name": name,
        "incorporation_country": "US" if market == "US" else market,
        "scope_attestation_id": "ATT_fixture_scope_" + security_suffix,
        "verified_issuer_receipt_id": receipt_id,
        "company_wiki_ref": None,
        "formal_stockwiki_profile": None,
        "securities": [{
            "security_id": security_id,
            "entity_id": entity_id,
            "market": market,
            "exchange_raw": exchange,
            "exchange": mic,
            "ticker": ticker,
            "currency": "USD" if market == "US" else "CNY",
            "security_type": "ordinary",
            "listing_status": "active",
            "source_binding_ref": "BND_fixture_" + security_suffix,
            "adr_ratio": None,
            "ordinary_security_ref": None,
        }],
        "segments": [],
    }
    bindings = [{
        "binding_ref": "BND_fixture_" + security_suffix,
        "source_namespace": "cwp_source_export_v2",
        "source_record_id": source_urn,
        "source_canonical_name": name.upper(),
        "security_id": security_id,
        "entity_id": entity_id,
        "market": market,
        "exchange_raw": exchange,
        "exchange_mic": mic,
        "ticker": ticker,
        "status": "active",
    }]
    return entity, bindings


def _build_sw_workspace(tmp_path: Path, scenarios: list[dict]) -> Path:
    driver = _write_driver(tmp_path)
    root = tmp_path / "sw" / "workspace"
    root.mkdir(parents=True)
    spec = {
        "registry_csv": str(SW_REGISTRY_FIXTURE),
        "recorded_at": "2026-10-30T00:00:00Z",
        "entities": scenarios,
    }
    spec_path = tmp_path / "sw" / "spec.json"
    spec_path.write_text(json.dumps(spec, ensure_ascii=False),
                         encoding="utf-8")
    completed = subprocess.run(
        [sys.executable, "-B", str(driver), "setup", "--root", str(root),
         "--spec", str(spec_path)],
        capture_output=True,
    )
    assert completed.returncode == 0, completed.stderr.decode("utf-8")
    return root


# --- CLI harness ---------------------------------------------------------------


def _request(**overrides) -> dict:
    request = {
        "schema_version": REQUEST_SCHEMA,
        "canonical_entity_id": ENT_ACME,
        "listing_id": None,
        "analysis_subject_id": None,
        "as_of": AS_OF,
        "document_kinds": None,
        "fiscal_years": None,
        "language": None,
        "limit": None,
        "cursor": None,
        "proof_snapshot_id": None,
    }
    request.update(overrides)
    return request


def _file_set(root: Path) -> dict[str, tuple[str, int]]:
    """Exact file inventory.  ``*-shm`` files are SQLite's ephemeral shared
    memory index, recreated by every reader open; they carry no business
    state.  Everything else — the database itself, its WAL, source bytes and
    the SW workspace — is compared byte-exact."""
    result: dict[str, tuple[str, int]] = {}
    for path in sorted(root.rglob("*")):
        if path.is_file() and not path.name.endswith("-shm"):
            body = path.read_bytes()
            result[str(path)] = (hashlib.sha256(body).hexdigest(), len(body))
    return result


def _run_cli(tmp_path: Path, config_path: Path, sw_root: Path | None,
             payload: dict | str, *, sw_python: str | None = None,
             sw_cli: Path | None = None, env: dict | None = None) \
        -> subprocess.CompletedProcess:
    run_env = dict(os.environ)
    run_env["PYTHONPATH"] = str(
        Path(__file__).resolve().parents[2] / "src")
    if env:
        run_env.update(env)
    args = [sys.executable, "-B", "-m",
            "company_wiki.source_catalog.public_canonical_browser_cli",
            "--config", str(config_path)]
    if sw_root is not None:
        args += ["--sw-python", sw_python or sys.executable,
                 "--sw-cli", str(sw_cli or
                                 tmp_path / "sw" /
                                 "dashboard_issuer_proof_fixture_cli.py"),
                 "--sw-root", str(sw_root)]
    return subprocess.run(
        args,
        input=(json.dumps(payload) if isinstance(payload, dict)
               else payload).encode("utf-8"),
        capture_output=True, cwd=str(tmp_path), env=run_env,
    )


def _stdout_json(completed: subprocess.CompletedProcess) -> dict:
    return json.loads(completed.stdout.decode("utf-8"))


def _stderr_json(completed: subprocess.CompletedProcess) -> dict:
    return json.loads(completed.stderr.decode("utf-8").splitlines()[-1])


def _assert_no_path_leak(payload: str, tmp_path: Path) -> None:
    for marker in (
        str(tmp_path), str(tmp_path).replace("\\", "/"),
        "source_catalog.yaml", ".source_catalog",
        "dashboard_issuer_proof", str(SW_CHECKOUT), "companies",
    ):
        assert marker not in payload, marker


def _acme_scenario(source_urn: str, *, revoked: bool = False,
                   revision_bump: bool = False) -> dict:
    entity, bindings = _sw_entity(
        ENT_ACME, "verified", "ACME Corporation", "ACME", source_urn,
        "IVR_fixture_acme_1")
    return {"kind": "verified_issuer", "entity": entity, "bindings": bindings,
            "revoke": revoked, "revision_bump": revision_bump}


def _beta_scenario(source_urn: str) -> dict:
    entity, bindings = _sw_entity(
        ENT_BETA, "verified", "BETA Corporation", "BETA", source_urn,
        "IVR_fixture_beta_1", security_suffix="0002")
    return {"kind": "verified_issuer", "entity": entity,
            "bindings": bindings}


def _dual_scenario(source_urn: str) -> dict:
    entity, bindings = _sw_entity(
        ENT_ACME, "verified", "ACME Corporation", "ACME", source_urn,
        "IVR_fixture_acme_1", security_suffix="0001")
    security2 = dict(entity["securities"][0])
    security2["security_id"] = "SEC_2c3b5e4f-0000-4b2c-9d3e-000000000003"
    security2["exchange_raw"] = "NYSE"
    security2["exchange"] = "XNYS"
    security2["source_binding_ref"] = "BND_fixture_0003"
    entity["securities"].append(security2)
    bindings.append({
        "binding_ref": "BND_fixture_0003",
        "source_namespace": "cwp_source_export_v2",
        # One owner binding per source record: the second share class binds
        # the company's other CWP source record (the amended filing).
        "source_record_id": ACME_AMENDED_URN,
        "source_canonical_name": "ACME CORPORATION",
        "security_id": security2["security_id"],
        "entity_id": ENT_ACME,
        "market": "US",
        "exchange_raw": "NYSE",
        "exchange_mic": "XNYS",
        "ticker": "ACME",
        "status": "active",
    })
    return {"kind": "verified_issuer", "entity": entity, "bindings": bindings}


@pytest.fixture()
def workspace(tmp_path):
    catalog = _build_cwp(tmp_path)
    config_path = _config_path(tmp_path)
    yield tmp_path, catalog, config_path
    catalog.close()


# --- positive -------------------------------------------------------------------


def test_same_issuer_positive_through_real_engines(workspace):
    tmp_path, catalog, config_path = workspace
    sw_root = _build_sw_workspace(tmp_path, [_acme_scenario(ACME_URN)])
    before = _file_set(tmp_path)
    completed = _run_cli(tmp_path, config_path, sw_root, _request())
    after = _file_set(tmp_path)
    assert completed.returncode == 0, completed.stderr.decode("utf-8")
    assert before == after, "query must be zero-write"
    result = _stdout_json(completed)
    assert result["schema_version"] == RESPONSE_SCHEMA
    assert result["state"] == "available"
    assert result["binding"]["status"] == "verified"
    assert result["binding"]["reason_codes"] == ["same_issuer_proven"]
    assert result["binding"]["association_scope"] == "issuer_only"
    issuer = result["binding"]["issuer"]
    assert issuer == {
        "namespace": "sec.cik", "value": CIK_ACME,
        "verifier": "sec-primary-dei/1",
        "assertion_id": issuer["assertion_id"],
        "source_id": ACME_URN,
        "content_sha256": _sha(ACME_BODY),
    }
    sw_view = result["binding"]["stockwiki"]
    assert sw_view["entity_id"] == ENT_ACME
    assert sw_view["identity_revision"] == 1
    assert sw_view["envelope_state"] == "available"
    assert sw_view["library_revision"] == "not_provided_no_global_revision"
    assert sw_view["selected_listing_id"] \
        == result["binding"]["stockwiki"]["selected_listing_id"]
    assert len(sw_view["receipt_sha256"]) == 64
    # Only the proven same-issuer document version is an item; the amended
    # bytes, the bare-ticker note and the CN report stay unverified.
    assert {item["source_ref"]["source_id"]
            for item in result["items"]} == {ACME_URN}
    item = result["items"][0]
    assert item["document_version_id"].startswith("cwpdv1-")
    assert item["source_ref"] == {
        "document_id": _document_urn(ACME_BODY),
        "source_id": ACME_URN,
        "content_sha256": _sha(ACME_BODY),
        "byte_size": len(ACME_BODY),
        "mime_type": "text/html",
        "schema_version": "2.0",
    }
    assert result["page"]["total_status"] == "exact"
    assert result["page"]["total"] == 1
    assert result["page"]["proof_snapshot_id"]
    assert result["catalog_revision"]
    candidates = result["unverified_candidates"]
    assert len(candidates) >= 3
    assert all("source_ref" not in entry for entry in candidates)
    assert {entry["reason_code"] for entry in candidates} \
        == {"issuer_proof_missing"}
    _assert_no_path_leak(json.dumps(result), tmp_path)


def test_zero_write_across_the_whole_fixture_root(workspace):
    tmp_path, catalog, config_path = workspace
    sw_root = _build_sw_workspace(tmp_path, [_acme_scenario(ACME_URN)])
    before = _file_set(tmp_path)
    _run_cli(tmp_path, config_path, sw_root, _request())
    after = _file_set(tmp_path)
    # No new file, no removed file, no changed byte anywhere in the isolated
    # fixture root: catalog, source roots and the SW workspace included.
    assert set(before) == set(after)
    for path in before:
        assert before[path] == after[path], path


# --- negatives: cross-owner identity ---------------------------------------------


def test_wrong_issuer_documents_are_not_attributed(workspace):
    tmp_path, catalog, config_path = workspace
    sw_root = _build_sw_workspace(tmp_path, [
        _acme_scenario(ACME_URN), _beta_scenario(BETA_URN)])
    result = _stdout_json(_run_cli(
        tmp_path, config_path, sw_root,
        _request(canonical_entity_id=ENT_BETA)))
    assert result["binding"]["status"] == "verified"
    assert result["binding"]["issuer"]["value"] == CIK_BETA
    assert {item["source_ref"]["source_id"]
            for item in result["items"]} == {BETA_URN}
    assert ACME_URN not in {item["source_ref"]["source_id"]
                            for item in result["items"]}


def test_same_bare_ticker_is_never_an_item(workspace):
    tmp_path, catalog, config_path = workspace
    sw_root = _build_sw_workspace(tmp_path, [_acme_scenario(ACME_URN)])
    result = _stdout_json(_run_cli(tmp_path, config_path, sw_root, _request()))
    # The bare-ticker note shares ticker and entity key but has no verified
    # issuer proof: candidate diagnostics only, never an item.
    assert ACME_TICKER_ONLY_URN not in {
        item["source_ref"]["source_id"] for item in result["items"]}
    assert any(entry["reason_code"] == "issuer_proof_missing"
               for entry in result["unverified_candidates"])


def test_binding_without_cwp_facts_is_unknown_not_empty(workspace):
    tmp_path, catalog, config_path = workspace
    sw_root = _build_sw_workspace(
        tmp_path, [_acme_scenario(ACME_TICKER_ONLY_URN)])
    result = _stdout_json(_run_cli(tmp_path, config_path, sw_root, _request()))
    assert result["binding"]["status"] == "unknown"
    assert "resolved_source_unverified_facts" \
        in result["binding"]["reason_codes"]
    assert result["binding"]["issuer"] is None
    assert result["items"] == []
    # Insufficient proof is never faked into an exact zero.
    assert result["page"]["total"] is None
    assert result["page"]["total_status"] == "unknown"


def test_foreign_listing_is_refused(workspace):
    tmp_path, catalog, config_path = workspace
    sw_root = _build_sw_workspace(tmp_path, [_acme_scenario(ACME_URN)])
    result = _stdout_json(_run_cli(
        tmp_path, config_path, sw_root,
        _request(listing_id="LST_ffffffff-ffff-4fff-8fff-ffffffffffff")))
    assert result["binding"]["status"] == "unknown"
    assert "listing_not_found_in_owner_package" \
        in result["binding"]["reason_codes"]
    assert result["binding"]["stockwiki"]["envelope_state"] == "not_found"
    assert result["items"] == []
    assert result["page"]["total_status"] == "unknown"


def test_multi_listing_without_selection_is_ambiguous(workspace):
    tmp_path, catalog, config_path = workspace
    sw_root = _build_sw_workspace(tmp_path, [_dual_scenario(ACME_URN)])
    result = _stdout_json(_run_cli(tmp_path, config_path, sw_root, _request()))
    assert result["binding"]["status"] == "ambiguous"
    assert "multiple_active_listings" in result["binding"]["reason_codes"]
    assert result["binding"]["issuer"] is None
    assert result["items"] == []
    assert result["page"]["total_status"] == "unknown"


def test_multi_listing_with_explicit_selection_verifies(workspace):
    tmp_path, catalog, config_path = workspace
    sw_root = _build_sw_workspace(tmp_path, [_dual_scenario(ACME_URN)])
    import sqlite3
    con = sqlite3.connect(str(tmp_path / "sw" / "workspace" / "data" /
                              "quick_scan" / "identity_receipts.sqlite"))
    receipt = json.loads(con.execute(
        "SELECT receipt_json FROM identity_receipt").fetchone()[0])
    con.close()
    listing_id = receipt["listing_ids"][0]
    result = _stdout_json(_run_cli(
        tmp_path, config_path, sw_root, _request(listing_id=listing_id)))
    assert result["binding"]["status"] == "verified"
    assert result["binding"]["stockwiki"]["selected_listing_id"] == listing_id
    assert result["binding"]["association_scope"] == "issuer_only"
    assert {item["source_ref"]["source_id"]
            for item in result["items"]} == {ACME_URN}


def test_revoked_receipt_is_unavailable(workspace):
    tmp_path, catalog, config_path = workspace
    sw_root = _build_sw_workspace(
        tmp_path, [_acme_scenario(ACME_URN, revoked=True)])
    result = _stdout_json(_run_cli(tmp_path, config_path, sw_root, _request()))
    assert result["binding"]["status"] == "unavailable"
    assert "receipt_not_active" in result["binding"]["reason_codes"]
    assert result["binding"]["issuer"] is None
    assert result["items"] == []
    assert result["page"]["total_status"] == "unknown"


def test_provisional_owner_is_not_a_verified_binding(workspace):
    tmp_path, catalog, config_path = workspace
    entity, bindings = _sw_entity(
        ENT_ACME, "provisional", "ACME Corporation", "ACME", ACME_URN, None)
    sw_root = _build_sw_workspace(
        tmp_path, [{"kind": "provisional", "entity": entity,
                    "bindings": bindings}])
    result = _stdout_json(_run_cli(tmp_path, config_path, sw_root, _request()))
    assert result["binding"]["status"] == "unknown"
    assert "owner_identity_not_verified" in result["binding"]["reason_codes"]
    assert result["binding"]["issuer"] is None
    assert result["items"] == []


def test_wrong_market_entity_never_binds(workspace):
    tmp_path, catalog, config_path = workspace
    # A listing in a market the owner registry does not know is refused by
    # the owner engine itself; the bridge reports the named unavailability.
    entity, bindings = _sw_entity(
        ENT_ACME, "verified", "ACME Corporation", "ACME", ACME_URN,
        "IVR_fixture_acme_1", market="ZZ", exchange="FAKE", mic="ZZZZ",
        security_suffix="0004")
    sw_root = _build_sw_workspace(
        tmp_path, [{"kind": "verified_issuer", "entity": entity,
                    "bindings": bindings}])
    result = _stdout_json(_run_cli(tmp_path, config_path, sw_root, _request()))
    assert result["binding"]["status"] == "unavailable"
    assert "market_not_registered" in result["binding"]["reason_codes"]
    assert result["binding"]["issuer"] is None
    assert result["items"] == []


def test_unsupported_binding_namespace_is_not_converted(workspace):
    tmp_path, catalog, config_path = workspace
    sw_root = _build_sw_workspace(tmp_path, [_acme_scenario(ACME_URN)])
    result = _stdout_json(_run_cli(
        tmp_path, config_path, sw_root, _request(),
        env={"CWP_FIXTURE_NAMESPACE": "sec.cik"}))
    assert result["binding"]["status"] == "unknown"
    assert "unsupported_source_namespace" in result["binding"]["reason_codes"]
    # The StockWiki proof itself was verified; only the CWP resolution is
    # refused — the honest half-proof is recorded, never converted.
    assert result["binding"]["stockwiki"]["envelope_state"] == "available"
    assert result["items"] == []
    assert result["page"]["total_status"] == "unknown"


def test_analysis_subject_is_unsupported(workspace):
    tmp_path, catalog, config_path = workspace
    sw_root = _build_sw_workspace(tmp_path, [_acme_scenario(ACME_URN)])
    result = _stdout_json(_run_cli(
        tmp_path, config_path, sw_root,
        _request(analysis_subject_id="ASJ_fixture_1")))
    assert result["state"] == "unsupported"
    assert "analysis_subject_unsupported" in result["reason_codes"]
    assert result["binding"]["status"] == "unavailable"
    assert result["items"] == []
    assert result["page"]["total_status"] == "unknown"


# --- negatives: seam integrity ----------------------------------------------------


def test_tampered_receipt_hash_is_refused(workspace):
    tmp_path, catalog, config_path = workspace
    sw_root = _build_sw_workspace(tmp_path, [_acme_scenario(ACME_URN)])
    result = _stdout_json(_run_cli(
        tmp_path, config_path, sw_root, _request(),
        env={"CWP_FIXTURE_TAMPER_RECEIPT": "1"}))
    assert result["binding"]["status"] == "unavailable"
    assert "stockwiki_proof_receipt_mismatch" \
        in result["binding"]["reason_codes"]
    assert result["binding"]["stockwiki"] is None
    assert result["items"] == []


def test_query_echo_mismatch_is_refused(workspace):
    tmp_path, catalog, config_path = workspace
    sw_root = _build_sw_workspace(tmp_path, [_acme_scenario(ACME_URN)])
    result = _stdout_json(_run_cli(
        tmp_path, config_path, sw_root, _request(),
        env={"CWP_FIXTURE_AS_OF_SHIFT": "1"}))
    assert result["binding"]["status"] == "unavailable"
    assert "stockwiki_proof_query_echo_mismatch" \
        in result["binding"]["reason_codes"]
    assert result["items"] == []


def test_owner_package_must_name_the_receipt_it_supplies(workspace):
    tmp_path, catalog, config_path = workspace
    sw_root = _build_sw_workspace(tmp_path, [_acme_scenario(ACME_URN)])
    result = _stdout_json(_run_cli(
        tmp_path, config_path, sw_root, _request(),
        env={"CWP_FIXTURE_RECEIPT_REF_MISMATCH": "1"},
    ))
    assert result["binding"]["status"] == "incompatible"
    assert "verified_issuer_receipt_mismatch" \
        in result["binding"]["reason_codes"]
    assert result["items"] == []
    assert result["page"]["total_status"] == "unknown"


def test_explicit_listing_cannot_be_replaced_by_another_proven_listing(workspace):
    tmp_path, catalog, config_path = workspace
    sw_root = _build_sw_workspace(tmp_path, [_dual_scenario(ACME_URN)])
    receipt_path = (sw_root / "data" / "quick_scan" /
                    "identity_receipts.sqlite")
    import sqlite3
    con = sqlite3.connect(str(receipt_path))
    receipt = json.loads(con.execute(
        "SELECT receipt_json FROM identity_receipt").fetchone()[0])
    con.close()
    requested, returned = receipt["listing_ids"]
    assert requested != returned

    result = _stdout_json(_run_cli(
        tmp_path, config_path, sw_root,
        _request(listing_id=requested),
        env={"CWP_FIXTURE_SELECTED_LISTING": returned},
    ))
    assert result["binding"]["status"] == "unavailable"
    assert "stockwiki_proof_selected_listing_mismatch" \
        in result["binding"]["reason_codes"]
    assert result["items"] == []
    assert result["page"]["total_status"] == "unknown"


def test_public_candidate_helpers_are_query_bounded(workspace):
    from company_wiki.source_catalog.public_document_browser import (
        PublicDocumentBrowser,
    )

    _, catalog, _ = workspace
    browser = PublicDocumentBrowser(catalog)
    documents, truncated, rows_read = browser._entity_documents_with_limit(
        ENT_ACME, limit=1)
    assert len(documents) == 1
    assert truncated and rows_read == 2
    versions, version_truncated, version_rows_read = \
        browser._document_versions_with_limit(documents[0], limit=1)
    assert len(versions) <= 1
    assert version_rows_read <= 4
    assert isinstance(version_truncated, bool)


def test_assertion_scan_is_sql_limited_before_rows_are_materialized():
    from types import SimpleNamespace
    from company_wiki.source_catalog.public_canonical_browser import (
        _MAX_ASSERTION_SCAN, PublicCanonicalBrowser,
    )
    from company_wiki.source_catalog.source_reader import SourceReadError

    class Reader:
        def fetchall(self, sql, params):
            assert "LIMIT ?" in sql
            assert "evidence_json" not in sql
            assert params == (_MAX_ASSERTION_SCAN + 1,)
            return [{"assertion_id": str(index)}
                    for index in range(_MAX_ASSERTION_SCAN + 1)]

    browser = PublicCanonicalBrowser.__new__(PublicCanonicalBrowser)
    browser.catalog = SimpleNamespace(reader=Reader())
    with pytest.raises(SourceReadError, match="issuer_scan_budget_exceeded"):
        browser._verified_assertions()


def test_proven_versions_require_an_exact_proof_for_each_source_ref():
    from types import SimpleNamespace
    from company_wiki.source_catalog.public_canonical_browser import (
        Binding, IssuerKey, PublicCanonicalBrowser, ResolvedIssuer,
    )

    document_id = "controlled-document"
    wanted = ResolvedIssuer(
        IssuerKey("sec.cik", CIK_ACME), "sec-primary-dei/1",
        "assertion-good", "source-good", "a" * 64,
    )
    foreign = ResolvedIssuer(
        IssuerKey("sec.cik", CIK_BETA), "sec-primary-dei/1",
        "assertion-foreign", "source-foreign", "b" * 64,
    )
    rows = [
        SimpleNamespace(document_id=document_id, source_id="source-good",
                        sort_key=lambda: (1, "source-good")),
        SimpleNamespace(document_id=document_id, source_id="source-foreign",
                        sort_key=lambda: (2, "source-foreign")),
        SimpleNamespace(document_id=document_id, source_id="source-unproven",
                        sort_key=lambda: (3, "source-unproven")),
    ]
    browser = PublicCanonicalBrowser.__new__(PublicCanonicalBrowser)
    browser._verified_assertions = lambda: [{
        "source_id": "source-good", "document_id": document_id,
    }]
    issuer_by_source = {
        "source-good": wanted,
        "source-foreign": foreign,
        "source-unproven": None,
    }
    browser._issuer_for_source = lambda source_id, memo: issuer_by_source[
        source_id]
    document = object()
    fallback = SimpleNamespace(
        _document=lambda requested: document if requested == document_id else None,
        _document_versions_with_limit=lambda _, limit: (
            rows[:limit], False, min(len(rows), limit)),
    )
    browser._fallback_browser = lambda: fallback

    versions = browser._proven_versions(Binding(
        status="verified", reason_codes=[], issuer_pin=wanted.pin(),
    ))
    assert [row.source_id for row in versions] == ["source-good"]


@pytest.mark.parametrize("output_stream", ["stdout", "stderr"])
def test_stockwiki_proof_output_is_bounded(workspace, output_stream):
    tmp_path, catalog, config_path = workspace
    sw_root = _build_sw_workspace(tmp_path, [_acme_scenario(ACME_URN)])
    result = _stdout_json(_run_cli(
        tmp_path, config_path, sw_root, _request(),
        env={f"CWP_FIXTURE_OVERSIZED_{output_stream.upper()}": "1"},
    ))
    assert result["binding"]["status"] == "unavailable"
    assert "stockwiki_proof_output_limit" \
        in result["binding"]["reason_codes"]
    assert result["items"] == []
    assert result["page"]["total_status"] == "unknown"


def test_nonzero_proof_exit_cannot_authorize_available_state(workspace):
    tmp_path, catalog, config_path = workspace
    sw_root = _build_sw_workspace(tmp_path, [_acme_scenario(ACME_URN)])
    result = _stdout_json(_run_cli(
        tmp_path, config_path, sw_root, _request(),
        env={"CWP_FIXTURE_NONZERO_AVAILABLE": "1"},
    ))
    assert result["binding"]["status"] == "unavailable"
    assert "stockwiki_proof_cli_failed" \
        in result["binding"]["reason_codes"]
    assert result["items"] == []
    assert result["page"]["total_status"] == "unknown"


def test_future_envelope_schema_is_incompatible(workspace):
    tmp_path, catalog, config_path = workspace
    sw_root = _build_sw_workspace(tmp_path, [_acme_scenario(ACME_URN)])
    result = _stdout_json(_run_cli(
        tmp_path, config_path, sw_root, _request(),
        env={"CWP_FIXTURE_FUTURE_SCHEMA": "1"}))
    assert result["binding"]["status"] == "unavailable"
    assert "stockwiki_proof_envelope_version_unsupported" \
        in result["binding"]["reason_codes"]
    assert result["items"] == []


def test_offline_proof_cli_is_unavailable_not_zero(workspace):
    tmp_path, catalog, config_path = workspace
    sw_root = _build_sw_workspace(tmp_path, [_acme_scenario(ACME_URN)])
    # 1) proof CLI crashes without a named envelope
    result = _stdout_json(_run_cli(
        tmp_path, config_path, sw_root, _request(),
        env={"CWP_FIXTURE_CRASH": "1"}))
    assert result["state"] == "empty"
    assert result["binding"]["status"] == "unavailable"
    assert "stockwiki_proof_cli_failed" in result["binding"]["reason_codes"]
    assert result["page"]["total_status"] == "unknown"
    assert result["items"] == []
    # 2) interpreter path does not exist
    result = _stdout_json(_run_cli(
        tmp_path, config_path, sw_root, _request(),
        sw_python=str(tmp_path / "missing" / "python.exe")))
    assert result["binding"]["status"] == "unavailable"
    assert "stockwiki_proof_not_configured" \
        in result["binding"]["reason_codes"]
    # 3) no proof configuration at all
    completed = _run_cli(tmp_path, config_path, None, _request())
    assert completed.returncode == 0
    result = _stdout_json(completed)
    assert result["binding"]["status"] == "unavailable"
    assert "stockwiki_proof_not_configured" \
        in result["binding"]["reason_codes"]
    assert result["page"]["total_status"] == "unknown"


# --- old source version & pagination -----------------------------------------------


def test_old_source_version_stays_out_of_items(workspace):
    tmp_path, catalog, config_path = workspace
    sw_root = _build_sw_workspace(tmp_path, [_acme_scenario(ACME_URN)])
    result = _stdout_json(_run_cli(tmp_path, config_path, sw_root, _request()))
    assert ACME_AMENDED_URN not in {
        item["source_ref"]["source_id"] for item in result["items"]}
    amended = [entry for entry in result["unverified_candidates"]
               if entry["document_id"] == _document_urn(ACME_AMENDED_BODY)]
    assert amended and amended[0]["reason_code"] == "issuer_proof_missing"


def _browse_one_page(tmp_path, config_path, sw_root, *, limit=1, cursor=None,
                     snapshot=None):
    completed = _run_cli(
        tmp_path, config_path, sw_root,
        _request(limit=limit, cursor=cursor, proof_snapshot_id=snapshot))
    assert completed.returncode == 0, completed.stderr.decode("utf-8")
    return _stdout_json(completed)


def test_proof_assertion_replacement_stales_existing_snapshot(workspace):
    tmp_path, catalog, config_path = workspace
    sw_root = _build_sw_workspace(tmp_path, [_acme_scenario(ACME_URN)])
    new_body = ACME_BODY.replace(b"annual report", b"annual report rev2")
    _write_doc(tmp_path / "companies" / "ACME" / "raw" / "annual",
               "acme_10k_2025_rev2.html", new_body,
               _us_sidecar(ENT_ACME, "ACME CORP", "ACME", "acme-10k-25-r2",
                           TEN_K_TITLE))
    catalog.scan()
    facts, evidence = _dei_facts_evidence(
        _sha(new_body), "ACME CORP", "US", "ACME", CIK_ACME, TEN_K_TITLE)
    _record_facts(catalog, new_body, "text/html", facts, evidence)
    first = _browse_one_page(tmp_path, config_path, sw_root, limit=None)
    assert first["page"]["total"] == 2
    snapshot = first["page"]["proof_snapshot_id"]

    corrected_facts, corrected_evidence = _dei_facts_evidence(
        _sha(new_body), "ACME CORPORATION", "US", "ACME", CIK_ACME,
        TEN_K_TITLE)
    corrected_evidence["entity"]["value"] = "ACME CORPORATION"
    _record_facts(catalog, new_body, "text/html", corrected_facts,
                  corrected_evidence)
    changed = _browse_one_page(
        tmp_path, config_path, sw_root, limit=None, snapshot=snapshot)
    assert changed["state"] == "stale"
    assert changed["items"] == []
    assert changed["page"]["total_status"] == "unknown"
    assert changed["page"]["proof_snapshot_id"] != snapshot


def test_pagination_is_pinned_and_stale_on_revision_change(workspace):
    tmp_path, catalog, config_path = workspace
    sw_root = _build_sw_workspace(tmp_path, [
        _acme_scenario(ACME_URN), _beta_scenario(BETA_URN)])
    page1 = _browse_one_page(tmp_path, config_path, sw_root)
    assert page1["state"] == "available"
    assert page1["page"]["total"] == 1
    snapshot = page1["page"]["proof_snapshot_id"]

    again = _browse_one_page(tmp_path, config_path, sw_root, snapshot=snapshot)
    assert again["state"] == "available"

    # Owner identity revision bump: any pinned page must go stale.
    bump_root = tmp_path / "bump"
    sw_root2 = _build_sw_workspace(
        bump_root, [_acme_scenario(ACME_URN, revision_bump=True)])
    result = _browse_one_page(tmp_path, config_path, sw_root2,
                              snapshot=snapshot)
    assert result["state"] == "stale"
    assert result["page"]["total"] is None
    assert result["page"]["total_status"] == "unknown"
    assert result["items"] == []
    assert result["page"]["proof_snapshot_id"] != snapshot

    # A newly PROVEN version behind the pinned snapshot is stale too —
    # pages never mix revisions of the proven set.

    new_body = ACME_BODY.replace(b"annual report", b"annual report rev2")
    _write_doc(tmp_path / "companies" / "ACME" / "raw" / "annual",
               "acme_10k_2025_rev2.html", new_body,
               _us_sidecar(ENT_ACME, "ACME CORP", "ACME", "acme-10k-25-r2",
                           TEN_K_TITLE))
    catalog.scan()
    facts, evidence = _dei_facts_evidence(
        _sha(new_body), "ACME CORP", "US", "ACME", CIK_ACME, TEN_K_TITLE)
    _record_facts(catalog, new_body, "text/html", facts, evidence)
    result = _browse_one_page(tmp_path, config_path, sw_root,
                              snapshot=snapshot)
    assert result["state"] == "stale"
    assert result["page"]["proof_snapshot_id"] != snapshot

    # A fresh page on the new revision serves both proven versions.
    fresh = _browse_one_page(tmp_path, config_path, sw_root, limit=None)
    assert fresh["state"] == "available"
    assert fresh["page"]["total"] == 2
    assert {item["source_ref"]["source_id"] for item in fresh["items"]} == {
        ACME_URN, _source_urn(new_body)}


# --- request validation -------------------------------------------------------------


@pytest.mark.parametrize("payload,reason", [
    (_request(canonical_entity_id="中微公司"), "invalid_canonical_entity_id"),
    (_request(canonical_entity_id="ENT_notauuid"),
     "invalid_canonical_entity_id"),
    (_request(listing_id="LST_short"), "invalid_listing_id"),
    (_request(as_of="2026-10-30"), "invalid_as_of"),
    (_request(as_of="2026-10-30T00:00:00+08:00"), "invalid_as_of"),
    (_request(limit=0), "invalid_limit"),
    (_request(limit=True), "invalid_limit"),
    (_request(limit=501), "invalid_limit"),
    (_request(document_kinds=["bad kind!"]), "invalid_document_kinds"),
    (_request(fiscal_years=["2025"]), "invalid_fiscal_years"),
    (_request(proof_snapshot_id="../etc/passwd"), "invalid_proof_snapshot_id"),
    (_request(cursor="../../../../etc/passwd"), "invalid_cursor"),
    (dict(_request(), source_url="https://example.invalid/x"),
     "request_fields_not_exact"),
])
def test_malformed_requests_are_blocked(workspace, payload, reason):
    tmp_path, catalog, config_path = workspace
    completed = _run_cli(tmp_path, config_path, None, payload)
    assert completed.returncode == 2
    error = _stderr_json(completed)
    assert error["state"] == "blocked"
    assert error["reason"] == reason
    assert error["schema_version"] == RESPONSE_SCHEMA


@pytest.mark.parametrize("field", ["cursor", "proof_snapshot_id"])
def test_deep_page_tokens_are_blocked_without_traceback(workspace, field):
    tmp_path, catalog, config_path = workspace
    sw_root = _build_sw_workspace(tmp_path, [_acme_scenario(ACME_URN)])
    raw = b"[" * 3_000 + b"0" + b"]" * 3_000
    token = base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")
    assert len(token) <= 8192
    completed = _run_cli(
        tmp_path, config_path, sw_root, _request(**{field: token}),
    )
    assert completed.returncode == 2
    error = _stderr_json(completed)
    assert error["state"] == "blocked"
    assert error["reason"] in {f"invalid_{field}", f"unsupported_{field}"}
    assert str(tmp_path) not in completed.stderr.decode("utf-8")



def test_token_decoder_converts_parser_recursion_to_named_refusal(monkeypatch):
    import company_wiki.source_catalog.public_canonical_browser as browser
    from company_wiki.source_catalog.public_canonical_browser import (
        CanonicalBrowseError, _decode_token,
    )

    def raise_recursion_error(*args, **kwargs):
        raise RecursionError("nested JSON")

    monkeypatch.setattr(browser.json, "loads", raise_recursion_error)
    token = base64.urlsafe_b64encode(b'{"v":1}').decode("ascii").rstrip("=")
    with pytest.raises(CanonicalBrowseError, match="^invalid_cursor$"):
        _decode_token(token, "cursor")

def test_duplicate_and_oversized_requests_are_blocked(workspace):
    tmp_path, catalog, config_path = workspace
    good = json.dumps(_request())
    completed = _run_cli(tmp_path, config_path, None,
                         good[:-1] + ',"limit":3}')
    assert completed.returncode == 2
    assert _stderr_json(completed)["state"] == "blocked"
    completed = _run_cli(tmp_path, config_path, None, "x" * 70_000)
    assert completed.returncode == 2
    assert _stderr_json(completed)["state"] == "blocked"


def test_source_read_budget_refusal_is_named_and_pathless(
        workspace, monkeypatch, capsys):
    import io
    from types import SimpleNamespace
    import company_wiki.source_catalog.public_canonical_browser_cli as cli
    from company_wiki.source_catalog.public_canonical_browser import (
        PublicCanonicalBrowser,
    )
    from company_wiki.source_catalog.source_reader import SourceReadError

    tmp_path, catalog, config_path = workspace
    payload = json.dumps(_request()).encode("utf-8")
    monkeypatch.setattr(cli.sys, "stdin", SimpleNamespace(
        buffer=io.BytesIO(payload)))

    def over_budget(self, request):
        raise SourceReadError("unavailable", "issuer_scan_budget_exceeded")

    monkeypatch.setattr(PublicCanonicalBrowser, "browse", over_budget)
    code = cli.main(["--config", str(config_path)])
    captured = capsys.readouterr()
    error = json.loads(captured.err)
    assert code == 2
    assert error["state"] == "unavailable"
    assert error["reason"] == "issuer_scan_budget_exceeded"
    assert str(tmp_path) not in captured.err
    assert "Traceback" not in captured.err


def test_incomplete_proof_configuration_is_blocked(workspace):
    tmp_path, catalog, config_path = workspace
    sw_cli = tmp_path / "sw" / "dashboard_issuer_proof_fixture_cli.py"
    run_env = dict(os.environ)
    run_env["PYTHONPATH"] = str(Path(__file__).resolve().parents[2] / "src")
    completed = subprocess.run(
        [sys.executable, "-B", "-m",
         "company_wiki.source_catalog.public_canonical_browser_cli",
         "--config", str(config_path), "--sw-cli", str(sw_cli)],
        input=json.dumps(_request()).encode("utf-8"), capture_output=True,
        cwd=str(tmp_path), env=run_env,
    )
    assert completed.returncode == 2
    error = _stderr_json(completed)
    assert error["state"] == "blocked"
    assert error["reason"] == "invalid_request"


def test_missing_catalog_is_unavailable_via_cli(tmp_path):
    config_path = tmp_path / "source_catalog.yaml"
    config_path.write_text(json.dumps({
        "schema_version": "1.0",
        "catalog_dir": str(tmp_path / ".missing"),
        "reusable_root_kinds": ["company_raw"],
        "roots": [{"root_id": "company_raw", "kind": "company_raw",
                   "path": str(tmp_path / "none"), "priority": 10}],
    }), encoding="utf-8")
    (tmp_path / "none").mkdir()
    completed = _run_cli(tmp_path, config_path, None, _request())
    assert completed.returncode == 2
    assert _stderr_json(completed)["state"] == "unavailable"


# --- request bounds: nonfinite & depth (card: UTF8/duplicate/nonfinite/depth) ----


def test_nonfinite_and_deep_requests_are_blocked(workspace):
    tmp_path, catalog, config_path = workspace
    # NaN/Infinity literals are refused outright, not parsed as floats.
    good = json.dumps(_request())
    for literal in ('NaN', 'Infinity', '-Infinity'):
        payload = good[:-1] + ',"language":' + literal + '}'
        completed = _run_cli(tmp_path, config_path, None, payload)
        assert completed.returncode == 2, literal
        assert _stderr_json(completed)["state"] == "blocked"
    # Deeply nested unknown fields are a bounded refusal, never a traceback.
    deep = good[:-1] + ',"x":' + '[' * 20000 + ']' * 20000 + '}'
    completed = _run_cli(tmp_path, config_path, None, deep)
    assert completed.returncode == 2
    error = _stderr_json(completed)
    assert error["state"] == "blocked"


# --- reopen interop: canonical tokens reopen through the EXISTING reader -------


def test_canonical_item_reopens_through_existing_public_cli(workspace):
    tmp_path, catalog, config_path = workspace
    sw_root = _build_sw_workspace(tmp_path, [_acme_scenario(ACME_URN)])
    result = _stdout_json(_run_cli(tmp_path, config_path, sw_root, _request()))
    item = result["items"][0]
    # The exact version reopen is the EXISTING public CLI (untouched); the
    # canonical bridge only hands out tokens that reader accepts verbatim.
    reopen_request = {
        "schema_version": "company-wiki-public-document-version-request/1",
        "document_version_id": item["document_version_id"],
    }
    completed = subprocess.run(
        [sys.executable, "-B", "-m",
         "company_wiki.source_catalog.public_document_browser_cli",
         "--config", str(config_path)],
        input=json.dumps(reopen_request).encode("utf-8"),
        capture_output=True, cwd=str(tmp_path),
        env={**os.environ,
             "PYTHONPATH": str(Path(__file__).resolve().parents[2] / "src")},
    )
    assert completed.returncode == 0, completed.stderr.decode("utf-8")
    reopened = json.loads(completed.stdout.decode("utf-8"))
    assert reopened["state"] == "available"
    assert reopened["document"]["source_ref"] == item["source_ref"]
    assert reopened["document"]["storage_state"] == "resolvable"


def test_incomplete_us_dei_evidence_is_missing_evidence_not_guess(workspace):
    tmp_path, catalog, config_path = workspace
    # The amended US annual gets plain sidecar facts (no original-DEI
    # observations): the issuer channel demands the original read, which
    # browse never performs, and the security master cache is absent —
    # named missing-evidence, never a guess from name/ticker.
    plain_facts = {
        "entity": "ACME CORP", "market": "US", "security_id": "ACME",
        "document_kind": "annual_report", "fiscal_year": 2025,
        "period_end": "2025-12-31",
    }
    plain_evidence = {
        key: {"locator": "sidecar:" + key, "value": value}
        for key, value in plain_facts.items()
    }
    _record_facts(catalog, ACME_AMENDED_BODY, "text/html", plain_facts,
                  plain_evidence)
    sw_root = _build_sw_workspace(tmp_path, [_acme_scenario(ACME_URN)])
    result = _stdout_json(_run_cli(tmp_path, config_path, sw_root, _request()))
    assert result["binding"]["status"] == "verified"
    assert {item["source_ref"]["source_id"]
            for item in result["items"]} == {ACME_URN}
    amended = [entry for entry in result["unverified_candidates"]
               if entry["document_id"] == _document_urn(ACME_AMENDED_BODY)]
    assert amended and amended[0]["reason_code"] == "issuer_proof_missing"
    # And the proven binding still pins the complete-DEI source only.
    assert result["binding"]["issuer"]["source_id"] == ACME_URN
