"""Explicit isolated Phase C runner. Default is loopback, never live POST."""

from __future__ import annotations

import argparse
from contextlib import closing
from dataclasses import asdict
from datetime import UTC, datetime
from decimal import Decimal
import gzip
import hashlib
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
import shutil
import sqlite3
import subprocess
import sys
import tempfile
from threading import Thread
import time
import uuid

ROOT = Path(__file__).resolve().parents[2]
# Existing paid preparations/ledger/receipts are explicit external inputs.
USAGE: Path | None = None
TOOLS = Path(__file__).resolve().parent
BOOTSTRAP = TOOLS / "phase_c_bootstrap"
sys.path[:0] = [str(ROOT), str(ROOT / "src"), str(ROOT / "scripts")]


def fingerprint(path: Path) -> dict:
    stat = path.stat()
    return {
        "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        "bytes": stat.st_size,
        "mtime_ns": stat.st_mtime_ns,
    }


def write_json(path: Path, value) -> None:
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf8"
    )


def read_rows(path: Path) -> list[dict]:
    return (
        [
            json.loads(line)
            for line in path.read_text(encoding="utf8").splitlines()
            if line
        ]
        if path.exists()
        else []
    )


def pre_reservation_refusal(
    *,
    code,
    receipt,
    native_usage,
    observer_path,
    observer_env_path,
    events_path,
    mode,
    source_sha256,
    run_id,
):
    """Return a named no-payment refusal only when no paid path began."""
    if code == 0 or receipt is None or native_usage or receipt.get("status") != "failed":
        return None
    try:
        observed_path = Path(observer_path).resolve(strict=True)
        configured_path = Path(observer_env_path).resolve(strict=True)
        event_path = Path(events_path).resolve(strict=True)
        observed = json.loads(observed_path.read_text(encoding="utf-8"))
        if (
            configured_path != observed_path
            or observed.get("schema_version") != "phase-c-observer/1"
            or observed.get("mode") != mode
            or observed.get("source_sha256") != source_sha256
            or Path(observed.get("events", "")).resolve() != event_path
        ):
            return None
        events = read_rows(event_path)
    except (OSError, TypeError, ValueError):
        return None
    budget = receipt.get("budget")
    if not isinstance(budget, dict) or any(
        isinstance(budget.get(field), bool)
        or not isinstance(budget.get(field), int)
        or budget.get(field) != 0
        for field in (
            "estimated_micro_usd",
            "tokens",
            "unknown_reservations",
            "unsettled_reservations",
        )
    ):
        return None
    refusals = [
        row for row in events
        if row.get("event") == "pre_reservation_refused"
        and row.get("run_id") == run_id
        and row.get("reserved") is False
        and isinstance(row.get("code"), str)
    ]
    posts = [
        row for row in events
        if row.get("event") == "http_post_attempt" and row.get("run_id") == run_id
    ]
    if len(refusals) != 1 or posts:
        return None
    refusal_code = refusals[0]["code"]
    document_errors = {
        error
        for document in receipt.get("documents", ())
        if isinstance(document, dict)
        for error in document.get("errors", ())
    }
    if refusal_code not in document_errors:
        return None
    return {
        "status": "PRE_RESERVATION_BLOCKED",
        "code": refusal_code,
        "reserved": False,
        "post_attempts": 0,
        "native_usage_rows": 0,
    }


def activation_recovery_precondition(*, code, receipt, native_usage, events, run_id):
    """Explain why a first run cannot safely resume a paid activation."""
    from company_wiki.automation.narrative_paid_response import (
        PaidResponseError,
        PaidResponsePin,
    )
    from company_wiki.automation.models import require_sha256

    if code != 2 or not isinstance(receipt, dict):
        return "initial_result_unavailable"
    documents = receipt.get("documents")
    if (
        not isinstance(documents, list)
        or len(documents) != 1
        or not isinstance(documents[0], dict)
    ):
        return "initial_document_receipt_unavailable"
    if documents[0].get("status") != "activation_pending":
        return "initial_document_not_activation_pending"
    if not isinstance(events, list) or not any(
        isinstance(row, dict)
        and row.get("event") == "activation_held"
        and row.get("run_id") == run_id
        for row in events
    ):
        return "activation_held_event_missing"
    if not isinstance(native_usage, list) or not native_usage:
        return "durable_paid_response_unavailable"
    for row in native_usage:
        if (
            not isinstance(row, dict)
            or row.get("usage_status") != "known"
        ):
            return "durable_paid_response_unavailable"
        try:
            require_sha256(row.get("response_sha256"), field_name="response_sha256")
        except (TypeError, ValueError):
            return "durable_paid_response_unavailable"
        try:
            pin = PaidResponsePin.from_json(row.get("paid_response_json"))
        except (PaidResponseError, TypeError, ValueError):
            return "durable_paid_response_unavailable"
        # The pin hashes the complete HTTP body; response_sha256 hashes the
        # adapter's decoded model response bytes. Bind both receipts through
        # the exact request instead of comparing hashes from different layers.
        if pin.request_sha256 != row.get("request_sha256"):
            return "durable_paid_response_unavailable"
    return None


def public_span_limits() -> dict[str, int]:
    """Expose the exact limits used by the production document router."""
    from company_wiki.source_catalog.narrative_routing import (
        DEFAULT_SELECTION_LIMIT,
        FINANCIAL_REPORT_SELECTION_LIMIT,
        PROSPECTUS_SELECTION_LIMIT,
    )

    return {
        "default": DEFAULT_SELECTION_LIMIT,
        "financial_reports": FINANCIAL_REPORT_SELECTION_LIMIT,
        "prospectus": PROSPECTUS_SELECTION_LIMIT,
    }


def mother_totals(metadata_path: str | Path, usage_path: str | Path, *,
                  budget_policy_path: str | Path | None = None) -> dict:
    from company_wiki.resource_budget import load_budget_policy

    meta = json.loads(Path(metadata_path).read_text(encoding="utf8"))
    baseline = meta["mother_budget"]
    policy = load_budget_policy(budget_policy_path)
    latest = {}
    for row in read_rows(Path(usage_path)):
        if row["kind"] != "native_model_charge" or row["mode"] != "live":
            continue
        latest[(row["database"], row["attempt_id"])] = row
    native = [row for row in latest.values() if not row.get("accounting_hold_for_run")]
    holds = [row for row in latest.values() if row.get("accounting_hold_for_run")]
    # A run-level fallback covers its already-persisted native attempts. Charge
    # the larger amount per dimension while accounting is unknown, not both.
    observed: dict[tuple[str, str], list[int]] = {}
    for row in native:
        amounts = observed.setdefault((row["database"], row.get("run_id", "")), [0, 0])
        amounts[0] += row["charged_tokens"]
        amounts[1] += row["charged_micro_usd"]
    extra_tokens = sum(max(0, row["charged_tokens"] - observed.get(
        (row["database"], row["accounting_hold_for_run"]), [0, 0])[0]) for row in holds)
    extra_usd = sum(max(0, row["charged_micro_usd"] - observed.get(
        (row["database"], row["accounting_hold_for_run"]), [0, 0])[1]) for row in holds)
    return {
        "charged_tokens": baseline["prior_charged_tokens"]
        + sum(row["charged_tokens"] for row in native) + extra_tokens,
        "charged_micro_usd": baseline["prior_charged_micro_usd"]
        + baseline["retained_fx_hold_micro_usd"]
        + sum(row["charged_micro_usd"] for row in native) + extra_usd,
        "new_unknown_count": sum(
            row["usage_status"] != "known" for row in latest.values()
        ),
        "token_limit": policy.cumulative_tokens,
        "micro_usd_limit": policy.cumulative_micro_usd,
        "prior_unknown7_retained": baseline[
            "old_unknown_hold_count_already_in_baseline"
        ],
    }


def mother_budget_fits(totals: dict, *, tokens_bound: int, micro_usd_bound: int) -> bool:
    """Unknown attempts already retain their full holds in charged totals.

    Keep those holds and the shared ceilings; unknown count is a diagnostic,
    not an additional global permission gate for unrelated bounded operations.
    """
    values = [totals[name] for name in (
        "charged_tokens", "charged_micro_usd", "token_limit", "micro_usd_limit")]
    if any(type(value) is not int or value < 0 for value in (*values, tokens_bound, micro_usd_bound)):
        raise ValueError("mother budget requires nonnegative integer accounting")
    return (totals["charged_tokens"] + tokens_bound <= totals["token_limit"]
            and totals["charged_micro_usd"] + micro_usd_bound <= totals["micro_usd_limit"])


def verify_preparation(meta: dict, *, mode: str) -> dict:
    before = {}
    for name, expected in meta["protected_fingerprints"].items():
        if mode == "loopback" and Path(name) not in {
            ROOT / "config.yaml",
            ROOT / "config/source_catalog.yaml",
        }:
            # Loopback uses only its own fake original/gold, and cannot consume
            # a newly revised real gold or charge the mother provider ledger.
            continue
        current = fingerprint(Path(name))
        if current != expected:
            raise ValueError("PREPARATION_FINGERPRINT_CHANGED: " + name)
        before[name] = current
    ocr = ROOT / "config/local_ocr.json"
    if ocr.exists():
        before[str(ocr)] = fingerprint(ocr)
    # Existing native attempts must agree with the prepared baseline. Read-only
    # SQLite plus file fingerprints prevents silently resetting historic usage.
    native = []
    for prior in meta["mother_budget"]["native_observations"] if mode == "live" else []:
        database = Path(prior["database"])
        if not database.exists():
            raise ValueError("MOTHER_NATIVE_DATABASE_MISSING")
        actual = fingerprint(database)
        if actual != prior["fingerprint"]:
            raise ValueError("MOTHER_NATIVE_DATABASE_CHANGED")
        with sqlite3.connect(database.as_uri() + "?mode=ro", uri=True) as connection:
            ids = [
                row[0]
                for row in connection.execute(
                    "SELECT attempt_id FROM narrative_model_reservations ORDER BY attempt_id"
                )
            ]
        if set(ids) != set(prior["current_attempt_ids"]):
            raise ValueError("MOTHER_NATIVE_ATTEMPTS_CHANGED")
        native.append(
            {
                "database": str(database),
                "attempts": len(ids),
                "unchanged": fingerprint(database) == actual,
            }
        )
    return {"protected": before, "native": native}


def _cli(
    root: Path,
    output: Path,
    label: str,
    command: list[str],
    env: dict,
    payload: dict | None = None,
    timeout: float = 420,
    compact_stdout: bool = False,
    parse_json: bool = True,
):
    started = time.perf_counter()
    process = subprocess.Popen(
        command,
        cwd=root,
        env=env,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if os.name == "nt" else 0,
    )
    try:
        stdout, stderr = process.communicate(
            None
            if payload is None
            else json.dumps(payload, ensure_ascii=False).encode(),
            timeout=timeout,
        )
    except subprocess.TimeoutExpired:
        if os.name == "nt":
            subprocess.run(
                ["taskkill", "/PID", str(process.pid), "/T", "/F"],
                capture_output=True,
                check=False,
            )
        else:
            process.kill()
        stdout, stderr = process.communicate(timeout=15)
        (output / (label + ".stderr.log")).write_bytes(stderr)
        write_json(
            output / (label + ".command.json"),
            {
                "command": command,
                "exit": 124,
                "seconds": round(time.perf_counter() - started, 3),
                "owned_pid": process.pid,
            },
        )
        raise TimeoutError("PHASE_C_OWNED_CLI_TIMEOUT") from None
    (output / (label + ".stderr.log")).write_bytes(stderr)
    if not compact_stdout:
        (output / (label + ".stdout.json")).write_bytes(stdout)
    write_json(
        output / (label + ".command.json"),
        {
            "command": command,
            "exit": process.returncode,
            "seconds": round(time.perf_counter() - started, 3),
            "stdout_sha256": hashlib.sha256(stdout).hexdigest(),
            "stdout_bytes": len(stdout),
        },
    )
    value = json.loads(stdout) if stdout and parse_json else None
    return process.returncode, value, stderr, stdout


def append_native(database: Path, run_id: str, output: Path, mode: str) -> list[dict]:
    from company_wiki.automation.narrative_run_store import NarrativeRunStore

    if not database.exists():
        return []
    store = NarrativeRunStore(database)
    records = []
    for item in store.reservations_for_run(run_id):
        row = {
            "kind": "native_model_charge",
            "mode": mode,
            "database": str(database),
            **asdict(item),
            "charged_tokens": item.charged_tokens,
            "charged_micro_usd": item.charged_micro_usd,
            "cost_kind": "budget_proxy_or_unknown_hold_not_invoice",
        }
        records.append(row)
    write_json(output / (run_id + ".native-usage.json"), records)
    # Capture production's safe failure rule and bounded result before the
    # isolated database is removed. Do not copy accepted selections or the DB.
    with closing(sqlite3.connect(database.as_uri() + "?mode=ro", uri=True)) as connection:
        connection.row_factory = sqlite3.Row
        failures = [dict(row) for row in connection.execute(
            "SELECT a.attempt_id,a.job_id,a.outcome,a.error_code,a.error_detail,a.result_json "
            "FROM attempts a JOIN narrative_run_jobs r ON r.job_id=a.job_id "
            "WHERE r.run_id=? AND a.error_code IS NOT NULL ORDER BY a.attempt_id",
            (run_id,),
        )]
    write_json(output / (run_id + ".native-failures.json"), failures)
    if mode == "live":
        _append_native_rows(database, run_id, records,
                            journal_sha256=fingerprint(output / (run_id + ".native-usage.json"))["sha256"])
    if failures:
        # A test-review snapshot must never prevent native charge persistence
        # or the owner's finally cleanup. Its failure remains explicit.
        try:
            from tools.document_understanding_benchmark.phase_c_failure_review_material import preserve_failure_review_material

            review = preserve_failure_review_material(
                database, run_id, output / (run_id + ".failure-review.json.gz")
            )
        except Exception as exc:
            review = {"status": "FAIL", "error_type": type(exc).__name__}
        if review is not None:
            write_json(output / (run_id + ".failure-review-index.json"), review)
    return records


def _accounting_hold(database, run_id, mode, *, tokens, micro_usd, reconciled=False):
    return {"kind": "native_model_charge", "mode": mode, "database": str(database),
            "attempt_id": run_id + ":accounting-unknown", "run_id": run_id,
            "accounting_hold_for_run": run_id,
            "usage_status": "known" if reconciled else "unknown",
            "charged_tokens": tokens, "charged_micro_usd": micro_usd,
            "cost_kind": "accounting_fallback_hold_not_provider_invoice"}


def _append_native_rows(database, run_id, records, *, journal_sha256=None):
    if USAGE is None:
        raise ValueError("live native usage needs the explicit existing mother ledger")
    previous = read_rows(USAGE)
    existing = {json.dumps(row, sort_keys=True, ensure_ascii=False) for row in previous}
    to_append = list(records)
    held = next((row for row in reversed(previous)
                 if row.get("accounting_hold_for_run") == run_id
                 and row.get("database") == str(database)), None)
    if held is not None:
        release = _accounting_hold(database, run_id, "live", tokens=0, micro_usd=0,
                                   reconciled=True)
        binding = journal_sha256 or held.get("native_usage_journal_sha256")
        if binding:
            release["native_usage_journal_sha256"] = binding
        to_append.append(release)
    with USAGE.open("a", encoding="utf-8") as stream:
        for row in to_append:
            encoded = json.dumps(row, sort_keys=True, ensure_ascii=False)
            if encoded not in existing:
                stream.write(encoded + "\n")
                existing.add(encoded)
        stream.flush()
        os.fsync(stream.fileno())


def _preserve_accounting_hold(database, run_id, output, mode, limits):
    row = _accounting_hold(database, run_id, mode, tokens=limits["max_tokens"],
        micro_usd=int(Decimal(str(limits["max_cost_usd"])) * 1_000_000))
    journal = output / (run_id + ".native-usage.json")
    try:
        row["native_usage_journal_sha256"] = fingerprint(journal)["sha256"]
    except OSError:
        # Keep the full hold when native usage never became durable. A later
        # file cannot retroactively establish what the failed run recorded.
        pass
    saved = {"ledger_saved": False, "sidecar_saved": False}
    ledger_error = None
    if mode == "live":
        try:
            if USAGE is None:
                raise ValueError("accounting fallback requires the existing mother ledger")
            with USAGE.open("a", encoding="utf-8") as stream:
                stream.write(json.dumps(row, sort_keys=True, ensure_ascii=False) + "\n")
                stream.flush()
                os.fsync(stream.fileno())
            saved["ledger_saved"] = True
        except Exception as exc:
            ledger_error = exc
    try:
        write_json(output / (run_id + ".accounting-hold.json"), row)
        saved["sidecar_saved"] = True
    except Exception:
        if not saved["ledger_saved"]:
            raise
    if ledger_error is not None:
        raise ledger_error
    return saved


def reconcile_native_usage(output: Path, run_id: str) -> dict:
    """Replay exact durable usage after the owned AUTO DB was removed; no POST."""
    if USAGE is None:
        raise ValueError("native reconciliation requires the existing mother ledger")
    if not run_id or Path(run_id).name != run_id or run_id in {".", ".."}:
        raise ValueError("run ID must be a single filename component")
    journal = output / (run_id + ".native-usage.json")
    journal_bytes = journal.read_bytes()
    journal_sha256 = hashlib.sha256(journal_bytes).hexdigest()
    holds = {row["database"]: row for row in read_rows(USAGE)
             if row.get("accounting_hold_for_run") == run_id}
    fallback = output / (run_id + ".accounting-hold.json")
    if not holds and fallback.exists():
        held = json.loads(fallback.read_text(encoding="utf-8"))
        if held.get("accounting_hold_for_run") == run_id:
            holds[held["database"]] = held
    if not holds or any(not held.get("native_usage_journal_sha256") for held in holds.values()):
        raise ValueError("native usage journal has no bound accounting snapshot; retain unknown hold")
    if any(held["native_usage_journal_sha256"] != journal_sha256 for held in holds.values()):
        raise ValueError("native usage journal changed; retain unknown hold")
    rows = json.loads(journal_bytes)
    if not isinstance(rows, list):
        raise ValueError("native usage journal must contain reservation rows")
    for row in rows:
        if (not isinstance(row, dict) or row.get("kind") != "native_model_charge"
                or row.get("mode") != "live" or row.get("run_id") != run_id
                or not isinstance(row.get("database"), str) or not row["database"]
                or not isinstance(row.get("usage_status"), str) or not row["usage_status"]
                or any(type(row.get(k)) is not int or row[k] < 0
                       for k in ("charged_tokens", "charged_micro_usd"))
                or not isinstance(row.get("attempt_id"), str) or not row["attempt_id"]):
            raise ValueError("native usage journal is not this run's accounting")
    databases = {row["database"] for row in rows}
    if not rows:
        if any(row.get("event") == "http_post_attempt" and row.get("run_id") == run_id
               for row in read_rows(output / "events.jsonl")):
            raise ValueError("empty native usage after recorded POST; retain unknown hold")
        databases = set(holds)
    if len(databases) != 1 or databases != set(holds):
        raise ValueError("native usage journal has ambiguous database ownership")
    _append_native_rows(databases.pop(), run_id, rows, journal_sha256=journal_sha256)
    result = {"status": "RECONCILED", "run_id": run_id, "native_rows": len(rows),
              "journal_sha256": journal_sha256, "model_post_attempts": 0,
              "AUTO_database_opened": False}
    write_json(output / (run_id + ".accounting-reconciled.json"), result)
    return result


def source_descriptor(sample: dict) -> dict:
    observation = sample["source_metadata_observation"]
    primary = sample.get("verified_official_descriptor") or {}
    # Identity/language are prepared source facts, never sample-ID semantics.
    # Legacy preparations lack display names: their explicit security ID is
    # still a valid resolver query; do not invent a company or a language.
    descriptor = {
        key: primary.get(key, observation.get(key))
        for key in (
            "entity", "publisher", "market", "security_id", "fiscal_year",
            "fiscal_period", "period_end", "published_date", "filing_date",
            "source_url", "form_type", "title", "document_kind", "language",
        )
    }
    entity = descriptor["entity"] or descriptor["security_id"]
    if not isinstance(entity, str) or not entity.strip():
        raise ValueError("prepared source identity requires entity or security_id")
    descriptor["entity"] = entity
    descriptor["publisher"] = descriptor["publisher"] or entity
    if descriptor["published_date"] is None and descriptor["filing_date"] is not None:
        # The observed filing date is the public availability date. File mtime
        # and the local capture time cannot establish historic availability.
        descriptor["published_date"] = descriptor["filing_date"]
    return descriptor


def prepared_live_input(metadata: dict, sample_id: str) -> tuple[dict, dict]:
    """Select one explicit source/provider pair before creating any run IO."""
    samples = [row for row in metadata.get("samples", ())
               if isinstance(row, dict) and row.get("sample_id") == sample_id]
    if len(samples) != 1:
        raise ValueError("expected unique prepared sample: " + str(sample_id))
    sample = samples[0]
    provider_name = sample.get("provider")
    providers = [row for row in metadata.get("providers", ())
                 if isinstance(row, dict) and row.get("provider") == provider_name]
    if not isinstance(provider_name, str) or not provider_name or len(providers) != 1:
        raise ValueError("expected unique prepared provider: " + str(provider_name))
    source_descriptor(sample)
    return sample, providers[0]


def seed_identity(root: Path, mode: str, descriptor: dict, *, source_catalog_config: Path | None = None) -> dict:
    from company_wiki.source_catalog.config import load_catalog_config
    from company_wiki.source_catalog.security_identity import (
        SecurityMasterStore,
        SecurityRecord,
        load_identity_master,
    )

    destination = SecurityMasterStore(root / "catalog/security_master")
    market = descriptor["market"]
    if mode == "loopback":
        record = SecurityRecord(
            canonical_name="Acme",
            market="US",
            exchange="NASDAQ",
            ticker="ACME",
            security_id="ACME",
            aliases=(),
            active=True,
            source_name="loopback-only-fixture",
            source_url="https://fixture.company-wiki.test/acme/fixture-security-list",
            source_record_id="fixture-ACME",
            identifiers={},
        )
        destination.write_market(
            market,
            [record],
            retrieved_at="2026-08-26T00:00:00Z",
            sources=(record.source_url,),
        )
        return {"kind": "explicit_fake_security_fixture_not_official_company_proof"}
    # Code checkout and data lake may live in different directories. Resolve
    # existing snapshots through the selected source owner's config, exactly as
    # registered-readonly originals do; never guess a sibling data location.
    production = load_catalog_config(
        Path(source_catalog_config) if source_catalog_config is not None
        else ROOT / "config/source_catalog.yaml"
    )
    existing = SecurityMasterStore(production.catalog_dir / "security_master")
    load_identity_master(existing, market=market)
    source = existing.path_for(market)
    before = fingerprint(source)
    target = destination.path_for(market)
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, target)
    assert fingerprint(source) == fingerprint(target) == before
    load_identity_master(destination, market=market)
    return {
        "kind": "byte_exact_existing_official_security_snapshot_no_refresh",
        "original": str(source),
        "fingerprint": before,
    }


def _public_read_expectation(descriptor, selection):
    fields = ('canonical_entity_id', 'market', 'security_id', 'document_kind', 'fiscal_year', 'fiscal_period')
    if selection is None or selection == {
        'mode': 'qualified_source_request', 'filing_identity_period_asof_qualification': 'REQUEST_APPLIED'
    }:
        return {key: descriptor.get(key) for key in fields}
    if selection == {
        'mode': 'exact_source_version', 'filing_identity_period_asof_qualification': 'NOT_EVALUATED'
    }:
        # These labels were observed, not independently qualified as filing
        # filters. The exact public Ref, source bytes and artifact SHA remain
        # mandatory; this is not a claim of issuer/period/as-of eligibility.
        return dict.fromkeys(fields)
    raise ValueError('unsupported or contradictory public read selection')


def public_bundle(root, output, env, config, imported, descriptor, label, *, source_selection=None):
    from company_wiki.automation.narrative_contracts import NarrativeBundle

    expected = _public_read_expectation(descriptor, source_selection)

    command = [
        sys.executable,
        "-B",
        "-X",
        "utf8",
        "-m",
        "company_wiki.source_catalog.narrative_transport_cli",
        "--config",
        str(config),
    ]
    code, reference, _, _ = _cli(
        root,
        output,
        label + "-reference",
        command + ["--operation", "reference"],
        env,
        {
            "schema_version": "narrative-reference-request/1",
            "source_ref": imported["source_ref"],
        },
    )
    assert code == 0 and reference is not None
    request = {
        "schema_version": "narrative-read-request/1",
        "narrative_ref": reference,
        "as_of_date": (None if source_selection is not None
                       and source_selection['mode'] == 'exact_source_version'
                       else datetime.now(UTC).date().isoformat()),
        "expected_source": expected,
    }
    write_json(output / (label + ".read-request.json"), request)
    write_json(output / (label + ".read-selection.json"), {
        'selection': source_selection or {'mode': 'legacy_qualified_request'},
        'expected_source_basis': 'qualified_request' if source_selection is None
            or source_selection['mode'] == 'qualified_source_request' else 'exact_content_pin_no_filing_qualification',
    })
    code, wire, stderr, raw = _cli(
        root,
        output,
        label + "-read",
        command + ["--operation", "read"],
        env,
        request,
        compact_stdout=True,
    )
    assert code == 0 and wire is not None
    receipt = json.loads(stderr)
    assert receipt["replay_status"] == "verified"
    assert receipt["narrative_ref"] == reference
    assert reference["artifact_sha256"] == hashlib.sha256(raw).hexdigest()
    bundle = NarrativeBundle.from_dict(wire)
    assert bundle.source_ref.to_dict() == imported["source_ref"]
    with gzip.open(output / (label + ".bundle.json.gz"), "wb") as stream:
        stream.write(raw)
    return reference, bundle, request, receipt


def consumers(root, output, env, catalog_config, descriptor, narrative_request, expected_bundle, *, projects):
    ff = projects / "filing-fetch"
    rf = projects / "revenue-forecast"
    connection = root / "company-wiki-connection.json"
    write_json(connection, {"schema_version": "1.0", "company_wiki_root": str(root)})
    request = {
        "schema_version": "2.0",
        "company_query": descriptor["security_id"],
        "market": descriptor["market"],
        "document_kind": descriptor["document_kind"],
        "fiscal_year": descriptor["fiscal_year"],
        "as_of_date": datetime.now(UTC).date().isoformat(),
        "filing_intent": "reuse_only",
    }
    if descriptor.get("fiscal_period") is not None:
        request["fiscal_period"] = descriptor["fiscal_period"]
    filing_request = root / "consumer-filing-request.json"
    narrative_file = root / "consumer-narrative-request.json"
    write_json(filing_request, request)
    write_json(narrative_file, narrative_request)
    offline = {**env, "CWP_PHASE_C_NO_NETWORK": "1"}
    results = []
    if descriptor["fiscal_year"] is None:
        # The caller already holds the exact registered SourceRef. Unknown
        # fiscal periods are not "latest" and need no provider discovery.
        ref = narrative_request["narrative_ref"]["source_ref"]
        candidate = {key: descriptor.get(key) for key in
                     ("document_kind", "fiscal_year", "fiscal_period")}
        candidate.update(status="source_candidate", source_ref=ref,
                         byte_verification="pending_verified_open",
                         resolution_outcome="reused_existing", download_events=0)
        script = (
            "import json,sys; from pathlib import Path; "
            "sys.path.insert(0,sys.argv[1]); "
            "from source_preparation import prepare_registered_source_result; "
            "r=json.load(sys.stdin); "
            "v=prepare_registered_source_result(r['candidate'],as_of_date=r['as_of_date'],"
            "company_wiki_catalog_config=Path(r['config']),source_reader_receipt_version='2.2'); "
            "print(json.dumps(v,ensure_ascii=False))"
        )
        code, value, stderr, _ = _cli(
            root, output, "rf-registered-source",
            [sys.executable, "-B", "-X", "utf8", "-c", script, str(rf / "scripts")],
            offline, {"candidate": candidate, "as_of_date": request["as_of_date"],
                      "config": str(catalog_config)}, timeout=90,
        )
        results.append({"consumer": "filing-fetch", "status": "NOT_REQUESTED_ALREADY_REGISTERED",
                        "reason": "exact SourceRef read; no fiscal/latest discovery requested", "downloads": 0})
        results.append({"consumer": "RF-registered-source", "exit": code, "receipt": value})
        assert code == 0 and value["filing_fetch"] is None
    else:
        code, value, stderr, _ = _cli(
            root,
            output,
            "ff-reuse",
            [
                sys.executable,
                "-B",
                "-X",
                "utf8",
                str(ff / "scripts/fetch_filing.py"),
                "--config",
                str(connection),
                "--request-file",
                str(filing_request),
                "--source-ref-v2",
            ],
            offline,
            timeout=90,
        )
        results.append({"consumer": "filing-fetch", "exit": code, "receipt": value})
        assert code == 0 and value["downloads"] == 0
        code, value, stderr, _ = _cli(
            root,
            output,
            "rf-source",
            [
                sys.executable,
                "-B",
                "-X",
                "utf8",
                str(rf / "scripts/source_preparation.py"),
                "--request-file",
                str(filing_request),
                "--company-wiki-config",
                str(connection),
                "--company-wiki-catalog-config",
                str(catalog_config),
                "--filing-fetch-root",
                str(ff),
                "--result-envelope",
                "--narrative-request-file",
                str(narrative_file),
                "--timeout-seconds",
                "90",
            ],
            offline,
            timeout=100,
        )
        results.append({"consumer": "RF-source+narrative", "exit": code, "receipt": value})
        if code != 0:
            ref = narrative_request["narrative_ref"]["source_ref"]
            reader_code, _, reader_stderr, reader_body = _cli(
                root,
                output,
                "rf-source-failure-public-reader",
                [
                    sys.executable,
                    "-B",
                    "-X",
                    "utf8",
                    "-m",
                    "company_wiki.source_catalog.source_reader_cli",
                    "--config",
                    str(catalog_config),
                    "--document-id",
                    ref["document_id"],
                    "--source-id",
                    ref["source_id"],
                    "--content-sha256",
                    ref["content_sha256"],
                    "--purpose",
                    "filing_reuse",
                ],
                offline,
                timeout=90,
                compact_stdout=True,
                parse_json=False,
            )
            write_json(
                output / "rf-source-failure-diagnostic.json",
                {
                    "public_reader_exit": reader_code,
                    "public_reader_receipt": json.loads(reader_stderr),
                    "body_sha256": hashlib.sha256(reader_body).hexdigest(),
                    "body_bytes": len(reader_body),
                },
            )
        assert code == 0 and value["filing_fetch"]["downloads"] == 0
        assert value["narrative"]["narrative_ref"] == narrative_request["narrative_ref"]
    code, value, stderr, _ = _cli(
        root,
        output,
        "rf-narrative",
        [
            sys.executable,
            "-B",
            "-X",
            "utf8",
            str(rf / "scripts/narrative_source_preparation.py"),
            "--company-wiki-catalog-config",
            str(catalog_config),
            "--operation",
            "read",
            "--timeout-seconds",
            "90",
        ],
        offline,
        narrative_request,
        timeout=100,
    )
    results.append({"consumer": "RF-narrative", "exit": code, "receipt": value})
    assert code == 0
    assert value["narrative_ref"] == narrative_request["narrative_ref"]
    assert value["source_ref"] == expected_bundle["source_ref"]
    assert value["reading_context"] == expected_bundle["reading_context"]
    assert value["evidence_spans"] == expected_bundle["evidence_spans"]
    assert value["summary"] == expected_bundle["summary"]
    if "summary_assessment" in expected_bundle:
        assert "summary_assessment" in value
        assert value["summary_assessment"] == expected_bundle["summary_assessment"]
        results[-1]["summary_assessment_preserved"] = True
    assert value["read_receipt"]["replay_status"] == "verified"
    results[-1]["historical_exact_ref_full_context_verified"] = True
    return results


def selector_versions(value: str | None) -> tuple[str, ...]:
    """The historical pair is the default; one new selector is explicit."""
    if value is None:
        return ("0.9.0", "0.8.0")
    if value == "0.9.0":
        return ("0.9.0",)
    if value == "0.9.0,0.8.0":
        return ("0.9.0", "0.8.0")
    raise ValueError("selector versions must be 0.9.0 or the historical 0.9.0,0.8.0 pair")



def reading_projection_for(selector_version: str, requested: str | None) -> str | None:
    """One runner boundary: legacy v4 default; registered recipes are explicit."""
    from company_wiki.automation.narrative_model_extractive import EXTRACTIVE_MODEL_PROJECTION_VERSION
    from company_wiki.automation.narrative_model_scoped import SCOPED_MODEL_PROJECTION_VERSION
    from company_wiki.automation.narrative_summary_protocols import SCOPED_PROJECTIONS

    if requested not in (SCOPED_PROJECTIONS | {None, EXTRACTIVE_MODEL_PROJECTION_VERSION}):
        raise ValueError("unsupported phase C reading model projection")
    return (requested or SCOPED_MODEL_PROJECTION_VERSION) if selector_version == "0.9.0" else None


def successful_model_observation(receipt, native, events, materials: Path, run_id: str, *, reading_model_projection):
    """Observe existing AUTO diagnostics and captured paid bytes; never save prose.

    This is fixture/receipt assembly, not semantic truth or live-quality acceptance.
    The original protocol report remains in the native receipt, not a second cache.
    """
    from collections import Counter
    from company_wiki.automation.models import canonical_json_hash
    from company_wiki.automation.narrative_model import MODEL_RESPONSE_MAX_BYTES
    from company_wiki.automation.narrative_summary_execution import extract_summary_execution
    from company_wiki.automation.narrative_model_extractive import EXTRACTIVE_MODEL_PROJECTION_VERSION
    from company_wiki.automation.narrative_summary_assessment import ASSESSMENT_SCHEMA
    from company_wiki.automation.narrative_summary_protocols import scoped_protocol_for_projection

    executions = [extract_summary_execution({"schema_version": "narrative-terminal-receipt/1.0", "execution": item["execution"]})
                  for document in receipt.get("documents", [])
                  for item in document.get("model_diagnostics", []) if "execution" in item]
    if reading_model_projection == EXTRACTIVE_MODEL_PROJECTION_VERSION and not executions:
        raise ValueError("PHASE_C_EXTRACTIVE_EXECUTION_NOT_OBSERVED")
    protocol = scoped_protocol_for_projection(reading_model_projection)
    fidelity = protocol is not None and protocol.assess_fidelity
    if fidelity and (not executions or any(
        report["schema_version"] != ASSESSMENT_SCHEMA or report["validator"]["version"] != protocol.assessor_version for report in executions
    )):
        raise ValueError("PHASE_C_FIDELITY_ASSESSMENT_NOT_OBSERVED")
    assessment = executions[-1] if fidelity else None
    execution = executions[-1] if executions and not fidelity else None
    audit = None if execution is None else {
        "schema_version": execution["schema_version"], "plan_sha256": execution["plan_sha256"],
        "report_sha256": canonical_json_hash(execution), "task_count": len(execution["tasks"]),
        "source_dispositions": dict(Counter(row["source_disposition"] for row in execution["tasks"])),
        "model_dispositions": dict(Counter(row["model_disposition"] for row in execution["tasks"])),
        "source_coverage_complete": execution["source_coverage_complete"],
        "model_coverage_complete": execution["model_coverage_complete"],
        "model_diagnostic": execution["model_diagnostic"],
        "admitted_claim_ids": [row["claim_id"] for row in execution["tasks"] if row["source_disposition"] == "admitted"],
        "report_origin": "native_batch_receipt.model_diagnostics.execution",
        "semantic_truth": "not_evaluated", "human_permission": "not_required",
    }
    captures = []
    for record in native:
        expected = record.get("response_sha256")
        if expected is None:
            captures.append({"attempt_id": record["attempt_id"], "status": "NO_RETURNED_FINAL",
                             "usage_status": record["usage_status"]})
            continue
        filename = run_id + "." + record["attempt_id"] + ".response.json.gz"
        path = materials / filename
        if path.parent.resolve() != materials.resolve():
            raise ValueError("PHASE_C_CAPTURE_PATH_INVALID")
        try:
            with gzip.open(path, "rb") as stream:
                raw = stream.read(MODEL_RESPONSE_MAX_BYTES + 1)
        except (OSError, EOFError) as exc:
            raise ValueError("PHASE_C_CAPTURE_UNAVAILABLE") from exc
        sha = hashlib.sha256(raw).hexdigest()
        observations = [row for row in events if row.get("event") == "model_final_observed"
                        and row.get("run_id") == run_id and row.get("attempt_id") == record["attempt_id"]]
        if (len(raw) > MODEL_RESPONSE_MAX_BYTES or sha != expected or not observations
                or any(row.get("final_sha256") != sha or row.get("final_bytes") != len(raw)
                       for row in observations)):
            raise ValueError("PHASE_C_CAPTURE_IDENTITY_DIFFERS")
        captures.append({"attempt_id": record["attempt_id"], "status": "CAPTURED_AND_NATIVE_HASH_MATCHED",
                         "sha256": sha, "bytes": len(raw), "usage_status": record["usage_status"]})
    result = {"source_card_execution": audit, "paid_response_capture": captures}
    if assessment is not None:
        # This is program-owned emission/diagnostic metadata, not the old
        # extractive source-card report and never a semantic-quality verdict.
        result["summary_assessment_observation"] = {
            key: assessment[key] for key in (
                "schema_version", "source_plan_sha256", "claims_sha256",
                "source_admitted_task_keys", "requested_task_keys", "emitted_task_keys",
                "missing_requested_task_keys", "budget_deferred_task_keys",
                "requested_emission_complete", "admitted_emission_complete",
                "diagnostic_count", "diagnostics_limited", "diagnostic_claim_ids",
                "semantic_status", "subfact_coverage_status",
            )
        }
        result["summary_assessment_observation"].update(
            report_sha256=canonical_json_hash(assessment),
            assessor_version=assessment["validator"]["version"],
            validator_implementation_sha256=assessment["validator"]["implementation_sha256"],
            report_origin="native_batch_receipt.model_diagnostics.execution",
        )
    return result

def run_pair(
    sample,
    provider,
    metadata,
    *,
    mode,
    output,
    preparation_path=None,
    fixture_endpoint=None,
    missing_gold=False,
    split_groups=False,
    reading_model_projection=None,
    consumer_projects=None,
    source_mode="isolated-copy",
    source_catalog_config=None,
    selected_versions=None,
    activation_recovery=False,
):
    """Own the whole temporary-lake lifetime, including preparation failures."""
    versions = selector_versions(selected_versions)
    projections = {version: reading_projection_for(version, reading_model_projection) for version in versions}
    if source_mode not in {"isolated-copy", "registered_readonly"}:
        raise ValueError("unsupported phase C source mode")
    if source_mode == "registered_readonly":
        if source_catalog_config is None:
            raise ValueError("registered_readonly requires explicit source_catalog_config")
        if mode != "live":
            raise ValueError("registered_readonly requires explicitly prepared source metadata")
        source_catalog_config = Path(source_catalog_config).resolve(strict=True)
        if not source_catalog_config.is_file():
            raise ValueError("source_catalog_config must be a file")
    descriptor = source_descriptor(sample) if mode == "live" else None
    temp_parent = Path(tempfile.gettempdir()).resolve()
    outcome = None
    root = None
    try:
        with tempfile.TemporaryDirectory(prefix="cwplC-", dir=temp_parent) as directory:
            root = Path(directory).resolve()
            if (root.parent != temp_parent or not root.name.startswith("cwplC-")
                    or root == ROOT or root in ROOT.parents):
                raise RuntimeError("unsafe phase C temporary root")
            outcome = _run_pair_in_owned_root(
                sample, provider, metadata, root=root, mode=mode, output=output,
                descriptor=descriptor, versions=versions, projections=projections,
                preparation_path=preparation_path, fixture_endpoint=fixture_endpoint,
                missing_gold=missing_gold, split_groups=split_groups,
                consumer_projects=consumer_projects, source_mode=source_mode,
                source_catalog_config=source_catalog_config, activation_recovery=activation_recovery,
            )
    except OSError as exc:
        if outcome is None:
            raise
        outcome.update(status="FAIL", cleanup_error=type(exc).__name__, remaining_owned_temp=str(root))
    assert root is not None and outcome is not None
    outcome["temporary_lake_removed"] = not root.exists()
    if (outcome.get("protected_unchanged") is not True
            or outcome.get("sentinel_unchanged") is not True
            or not outcome["temporary_lake_removed"]):
        outcome["status"] = "FAIL"
    write_json(output / "receipt.json", outcome)
    return outcome


def _run_pair_in_owned_root(
    sample,
    provider,
    metadata,
    *,
    root,
    mode,
    output,
    descriptor,
    versions,
    projections,
    preparation_path=None,
    fixture_endpoint=None,
    missing_gold=False,
    split_groups=False,
    consumer_projects=None,
    source_mode="isolated-copy",
    source_catalog_config=None,
    activation_recovery=False,
):
    from company_wiki.source_catalog.official_source_flow import (
        prepare_official_narrative_request,
    )
    from company_wiki.automation.narrative_run_store import NarrativeRunStore
    from company_wiki.automation.models import canonical_json_hash
    from company_wiki.automation.narrative_selection_generation import (
        reading_material_sha256,
    )
    from company_wiki.automation.narrative_contracts import NarrativeBundle

    (root / "config").mkdir()
    sentinel = root / "SENTINEL"
    sentinel.write_bytes(b"own-isolated-phase-C-lake\n")
    sentinel_before = fingerprint(sentinel)
    config = root / "config/source_catalog.yaml"
    write_json(
        config,
        {
            "schema_version": "1.0",
            "catalog_dir": str(root / "catalog"),
            "roots": [
                {
                    "root_id": "live_raw",
                    "kind": "company_raw",
                    "path": str(root / "companies"),
                }
            ],
        },
    )
    options = dict(provider["options"])
    env = {
        **os.environ,
        "PYTHONDONTWRITEBYTECODE": "1",
        "PYTHONPATH": os.pathsep.join(
            [str(BOOTSTRAP), str(ROOT), str(ROOT / "src"), str(ROOT / "scripts")]
        ),
    }
    events = output / "events.jsonl"
    materials = output / "materials"
    materials.mkdir(exist_ok=True)
    if mode == "loopback":
        body = b"<html><h1>Company business update</h1><p>We launched cloud services for customers and expanded overseas operations.</p></html>"
        if missing_gold:
            body += b"<!-- independent failed-gold source -->"
        if split_groups:
            body = b"<html><h1>Company business update</h1><h2>Product development</h2><p>We launched cloud services for customers.</p><h2>Overseas operations</h2><p>We opened twelve overseas stores in new markets.</p></html>"
        original = root / "fixture-original.html"
        original.write_bytes(body)
        sha = hashlib.sha256(body).hexdigest()
        descriptor = {
            "entity": "Acme",
            "publisher": "Acme",
            "market": "US",
            "security_id": "ACME",
            "document_kind": "investor_relations",
            "title": "Acme business update",
            "source_url": "https://fixture.company-wiki.test/acme/update",
            "published_date": "2026-08-26",
            "fiscal_year": 2026,
            "fiscal_period": None,
            "language": "en",
        }
        gold = root / "fixture-gold.json"
        quote = (
            "Nonexistent operating statement must stop payment."
            if missing_gold
            else "We launched cloud services for customers and expanded overseas operations."
        )
        write_json(
            gold,
            {
                "source_sha256": sha,
                "facts": [
                    {
                        "id": "fixture-business-fact",
                        "importance": "critical",
                        "target_kind": "required_business",
                        "any_support_sets": [
                            [
                                {"location_kind": "document", "exact_quote": text}
                                for text in (
                                    [
                                        "We launched cloud services for customers.",
                                        "We opened twelve overseas stores in new markets.",
                                    ]
                                    if split_groups
                                    else [quote]
                                )
                            ]
                        ],
                    }
                ],
            },
        )
        mime = "text/html"
        options["endpoint"] = fixture_endpoint
        options["allow_local_http"] = True
        llm = root / "loopback-llm.json"
        write_json(
            llm,
            {
                "llm": {
                    "provider": "deepseek",
                    "model": options["model_id"],
                    "base_url": fixture_endpoint.removesuffix("/chat/completions"),
                    "max_tokens": options["max_output_tokens"],
                    "temperature": options["temperature"],
                    "generation_policy": {"deepseek": {"narrative": {
                        key: options[key] for key in ("thinking", "reasoning_effort")
                        if key in options
                    }}},
                }
            },
        )
        env.update(
            DEEPSEEK_API_KEY="loopback-fixture-not-a-real-key",
            CWP_PHASE_C_NO_NETWORK="1",
        )
    else:
        original = Path(sample["original"])
        sha = sample["fingerprint"]["sha256"]
        gold = Path(sample["gold"])
        mime = sample["mime_type"]
        llm = None
    protected = {
        str(path): fingerprint(path) for path in (
            (original, gold, sentinel, Path(source_catalog_config))
            if source_mode == "registered_readonly" else (original, gold, config, sentinel))
    }
    ocr = ROOT / "config/local_ocr.json"
    if ocr.exists():
        shutil.copyfile(ocr, root / "config/local_ocr.json")
    observer = root / "observer.json"
    observer_config = {
        "schema_version": "phase-c-observer/1",
        "mode": mode,
        "source_sha256": sha,
        "gold": str(gold),
        "gold_sha256": fingerprint(gold)["sha256"],
        "model_options": options,
        "events": str(events),
        "materials": str(materials),
        "metadata": str(preparation_path) if preparation_path is not None else None,
        "usage_ledger": str(USAGE),
        "forbid_post": False,
    }
    write_json(observer, observer_config)
    env["CWP_PHASE_C_OBSERVER"] = str(observer)
    database = root / "AUTO.sqlite"
    states = []
    pinned_read = None
    current_run = None
    outcome = {
        "mode": mode,
        "sample": sample["sample_id"],
        "source_mode": source_mode,
        "selector_versions": list(versions),
        "reading_model_projections": projections,
        "comparison_scope": "paired" if len(versions) == 2 else "single_selector_no_paired_improvement_claim",

        "scope": "development regression, not holdout",
        "states": states,
        "internal_algorithm_caps": {
            "0.8.0": "No internal 48000-char cap",
            "0.9.0": 48000,
        },
        "public_span_limits": public_span_limits(),
        "activation_recovery_requested": activation_recovery,
        "model_settings": options,
        "capture_origin": "existing local bytes; descriptor URL does not prove remote or historical download SHA",
    }
    if mode == "live":
        observation = sample["source_metadata_observation"]
        primary = sample.get("verified_official_descriptor") or {}
        date_field = (
            "published_date"
            if primary.get("published_date", observation.get("published_date")) is not None
            else "filing_date"
        )
        date_owner = "verified_official_descriptor" if date_field in primary else "source_metadata_observation"
        outcome["availability_date_provenance"] = {
            "observed_published_date": observation.get("published_date"),
            "observed_filing_date": observation.get("filing_date"),
            "registered_published_date": descriptor["published_date"],
            "method": date_owner + "." + date_field
            if descriptor["published_date"] is not None
            else "unknown_public_availability",
            "mtime_used": False,
        }
        outcome["language_provenance"] = {
            "registered_language": descriptor["language"],
            "gold_language_label": json.loads(gold.read_text(encoding="utf8")).get(
                "language"
            ),
            "basis": "prepared_source_descriptor"
            if descriptor["language"] is not None
            else "unspecified_source_language_normalization_owner_decides",
            "translation": False,
        }
    try:
        identity_proof = (seed_identity(root, mode, descriptor, source_catalog_config=source_catalog_config)
                          if source_mode != "registered_readonly" or consumer_projects is not None
                          else {"kind": "not_requested_no_consumer_identity_clone"})
        outcome["identity_snapshot"] = identity_proof
        if "original" in identity_proof:
            protected[identity_proof["original"]] = identity_proof["fingerprint"]
        if source_mode == "registered_readonly":
            from tools.document_understanding_benchmark.phase_c_readonly_source import prepare_registered_source
            from company_wiki.source_catalog.source_reader import SourceRef

            mounted = prepare_registered_source(source_config=Path(source_catalog_config),
                owned_root=root, original=original, expected_sha256=sha,
                descriptor=descriptor, as_of_date=datetime.now(UTC).date().isoformat(),
                source_facts=sample.get("registered_source_facts"),
                expected_ref=SourceRef(**sample["source_ref"]) if sample.get("source_ref") is not None else None)
            config = Path(mounted["catalog_config"])
            # This is an existing registered SourceRef, not an HTTP/import receipt.
            imported = {"source_ref": mounted["source_ref"]}
            outcome["source_registration"] = mounted
            protected[str(config)] = fingerprint(config)
            write_json(output / "registered-source.json", mounted)
        else:
            request = root / "import.json"
            write_json(
                request,
                {
                    "schema_version": "official-source-import-request/1",
                    "request_id": "phaseC-" + uuid.uuid4().hex,
                    "source": descriptor,
                    "content_sha256": sha,
                    "mime_type": mime,
                    "max_bytes": fingerprint(original)["bytes"],
                    "capture_receipt": {
                        "capture_method": "local_document",
                        "tool_name": "phase-C-existing-local-reuse",
                        "tool_call_id": uuid.uuid4().hex,
                        "captured_at": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
                        "response_bytes": fingerprint(original)["bytes"],
                        "content_sha256": sha,
                    },
                },
            )
            code, imported, _, _ = _cli(
                root,
                output,
                "import",
                [
                    sys.executable,
                    "-B",
                    "-X",
                    "utf8",
                    "-m",
                    "company_wiki.source_catalog.official_source_cli",
                    "--config",
                    str(config),
                    "--project-root",
                    str(root),
                    "--operation",
                    "import",
                    "--request",
                    str(request),
                    "--input-file",
                    str(original),
                ],
                env,
                timeout=60,
            )
            assert code == 0
        outcome["source_ref"] = imported["source_ref"]
        limits = metadata["candidate_per_paid_request_limits"]
        for version in (
            ["0.9.0"] if (missing_gold or split_groups) else versions
        ):
            current_run = (
                "phaseC-" + version.replace(".", "") + "-" + uuid.uuid4().hex[:12]
            )
            template = {
                "schema_version": "narrative-batch-request/1",
                "run_id": current_run,
                "profile": "P2",
                "selector_version": version,
                "max_seconds": limits["max_seconds"],
                "max_tokens": limits["max_tokens"],
                "max_cost_usd": limits["max_cost_usd"],
                "max_final_bytes": limits["max_final_bytes"],
                "max_persistent_bytes": limits["max_persistent_bytes"],
                "max_scratch_bytes": limits["max_scratch_bytes"],
                "model": {**options, **limits["model_transport_only"]},
                "pricing": {
                    key: value
                    for key, value in provider["price_proxy"].items()
                    if key
                    in {
                        "version",
                        "input_micro_usd_per_million_tokens",
                        "output_micro_usd_per_million_tokens",
                    }
                },
            }
            if projections[version] is not None:
                template["reading_model_projection"] = projections[version]
            batch_request = prepare_official_narrative_request(
                [imported], batch_template=template
            )
            request_path = root / (current_run + ".json")
            write_json(request_path, batch_request.to_dict())
            command = [
                sys.executable,
                "-B",
                "-X",
                "utf8",
                str(TOOLS / "phase_c_launcher.py"),
                "--llm-provider",
                provider["provider"],
                "--project-root",
                str(root),
                "--catalog-config",
                str(config),
                "--automation-db",
                str(database),
                "--work-dir",
                str(root / current_run),
                "--request",
                str(request_path),
            ]
            if mode == "loopback":
                command += ["--llm-config", str(llm), "--allow-local-model-http"]
            observer_config.update(hold_activation=activation_recovery,
                                   activation_run_id=current_run,
                                   prepared_payload_max_bytes=limits['max_final_bytes'])
            write_json(observer, observer_config)
            code, receipt, _, _ = _cli(root, output, current_run, command, env)
            # Persist native charges before resuming any paid output. A fresh
            # run, request, work directory or model call is never a substitute.
            native = append_native(database, current_run, output, mode)
            state = {
                "version": version,
                "run_id": current_run,
                "exit": code,
                "receipt": receipt,
                "native_usage": native,
            }
            states.append(state)
            if missing_gold or split_groups:
                assert code != 0 and not native
                assert not any(
                    row["event"] == "http_post_attempt" for row in read_rows(events)
                )
                assert any(
                    row.get("code") == "PHASE_C_GOLD_SUPPORT_MISSING"
                    for row in read_rows(events)
                )
                if split_groups:
                    observation = next(
                        row["gold"]
                        for row in read_rows(events)
                        if row["event"] == "pre_reservation_material"
                    )
                    assert observation["groups"] >= 2
                    assert all(
                        fact["all_anchors_individually_present"]
                        and not fact["supported"]
                        for fact in observation["facts"]
                    )
                    state["actual_groups_separate_with_all_anchors_present"] = True
                state["expected_refusal_zero_reservation_zero_POST"] = True
                break
            refusal = pre_reservation_refusal(
                code=code,
                receipt=receipt,
                native_usage=native,
                observer_path=observer,
                observer_env_path=env.get("CWP_PHASE_C_OBSERVER"),
                events_path=events,
                mode=mode,
                source_sha256=sha,
                run_id=current_run,
            )
            if activation_recovery and refusal is not None:
                state["activation_recovery"] = refusal
                state["expected_refusal_zero_reservation_zero_POST"] = True
                outcome["status"] = "PRE_RESERVATION_BLOCKED"
                break
            if activation_recovery:
                initial_events = read_rows(events)
                recovery_issue = activation_recovery_precondition(
                    code=code,
                    receipt=receipt,
                    native_usage=native,
                    events=initial_events,
                    run_id=current_run,
                )
                if recovery_issue is not None:
                    documents = receipt.get("documents", []) if receipt else []
                    if not isinstance(documents, list):
                        documents = []
                    state["activation_recovery"] = {
                        "status": "NOT_RECOVERABLE",
                        "reason": recovery_issue,
                        "initial_exit": code,
                        "document_statuses": [
                            row.get("status") for row in documents
                            if isinstance(row, dict)
                        ],
                        "document_errors": [
                            error for row in documents if isinstance(row, dict)
                            for error in row.get("errors", [])
                            if isinstance(error, str)
                        ],
                        "native_usage_statuses": [
                            row.get("usage_status") for row in native
                        ],
                        "response_hashes_present": all(
                            bool(row.get("response_sha256")) for row in native
                        ),
                    }
                    raise RuntimeError("ACTIVATION_RECOVERY_NOT_AVAILABLE")
                runs = NarrativeRunStore(database)
                generation_before = runs.final_generations(current_run)
                posts_before_recovery = sum(row["event"] == "http_post_attempt"
                                            for row in read_rows(events))
                observer_config.update(hold_activation=False, forbid_post=True)
                write_json(observer, observer_config)
                code, receipt, _, _ = _cli(root, output, current_run + "-activation-resume",
                                           command, env)
                after = append_native(database, current_run, output, mode)
                stable_fields = ("attempt_id", "request_sha256", "response_sha256", "usage_status",
                                 "input_tokens", "output_tokens", "estimated_micro_usd",
                                 "charged_tokens", "charged_micro_usd")
                identity_before = [{key: row[key] for key in stable_fields} for row in native]
                identity_after = [{key: row[key] for key in stable_fields} for row in after]
                posts_after_recovery = sum(row["event"] == "http_post_attempt"
                                           for row in read_rows(events))
                assert code == 0 and receipt is not None
                assert identity_before == identity_after
                assert runs.final_generations(current_run) == generation_before
                assert posts_before_recovery == posts_after_recovery
                state["activation_recovery"] = {
                    "status": "PASS", "held_status": "activation_pending",
                    "same_run_id": current_run,
                    "native_attempts_before": len(native), "native_attempts_after": len(after),
                    "charged_tokens_before": sum(row["charged_tokens"] for row in native),
                    "charged_tokens_after": sum(row["charged_tokens"] for row in after),
                    "charged_micro_usd_before": sum(row["charged_micro_usd"] for row in native),
                    "charged_micro_usd_after": sum(row["charged_micro_usd"] for row in after),
                    "POSTs_before": posts_before_recovery, "POSTs_after": posts_after_recovery,
                    "paid_generation_unchanged": True, "response_identity_unchanged": True,
                }
                native = after
                state.update(exit=code, receipt=receipt, native_usage=native)
                observer_config["forbid_post"] = False
                write_json(observer, observer_config)
            if code != 0:
                raise ValueError("INITIAL_BATCH_FAILED_NO_BLIND_RESEND")
            state.update(successful_model_observation(
                receipt, native, read_rows(events), materials, current_run,
                reading_model_projection=projections[version]))
            reference, bundle, read_request, replay = public_bundle(
                root, output, env, config, imported, descriptor, current_run,
                source_selection=outcome.get('source_registration', {}).get('selection'),
            )
            runs = NarrativeRunStore(database)
            final = runs.final_generations(current_run).get(
                imported["source_ref"]["document_id"]
            )
            if version == "0.9.0":
                assert (
                    final is not None
                    and final["reading_dependencies"]["status"] == "complete"
                )
                assert final["selection_generation"][
                    "material_sha256"
                ] == reading_material_sha256(bundle)
                from company_wiki.source_catalog.config import load_catalog_config

                catalog_db = load_catalog_config(
                    config, project_root=root
                ).database_path
                with closing(
                    sqlite3.connect(catalog_db.as_uri() + "?mode=ro", uri=True)
                ) as connection:
                    row = connection.execute(
                        "SELECT metadata_json FROM narrative_artifact_versions WHERE artifact_version_id=?",
                        (reference["artifact_version_id"],),
                    ).fetchone()
                artifact_metadata = json.loads(row[0])
                assert artifact_metadata["generation_manifest"] == final
                assert artifact_metadata["generation_sha256"] == canonical_json_hash(
                    final
                )
                state["final_generation"] = final
                pinned_read = (state, read_request, bundle)
            state["public_replay"] = replay
            state["artifact_ref"] = reference
            posts_before = sum(
                row["event"] == "http_post_attempt" for row in read_rows(events)
            )
            observer_config["forbid_post"] = True
            write_json(observer, observer_config)
            code, resumed, _, _ = _cli(
                root, output, current_run + "-restart", command, env
            )
            assert (
                code == 0
                and append_native(database, current_run, output, mode) == native
            )
            assert (
                sum(row["event"] == "http_post_attempt" for row in read_rows(events))
                == posts_before
            )
            template["run_id"] = current_run + "-cache"
            write_json(
                request_path,
                prepare_official_narrative_request(
                    [imported], batch_template=template
                ).to_dict(),
            )
            cache_command = list(command)
            cache_command[cache_command.index("--work-dir") + 1] = str(
                root / template["run_id"]
            )
            observer_config['activation_run_id'] = template['run_id']
            write_json(observer, observer_config)
            code, cached, _, _ = _cli(
                root, output, current_run + "-cross-run", cache_command, env
            )
            assert code == 0 and cached["budget"]["tokens"] == 0
            assert not append_native(database, template["run_id"], output, mode)
            assert (
                sum(row["event"] == "http_post_attempt" for row in read_rows(events))
                == posts_before
            )
            state.update(same_run_zero_POST=True, cross_run_zero_POST=True)
            observer_config["forbid_post"] = False
            write_json(observer, observer_config)
        if outcome.get("status") != "PRE_RESERVATION_BLOCKED" and not (missing_gold or split_groups):
            # Paired mode leaves the older baseline LATEST. Single mode keeps
            # the current Ref LATEST. Both consumers pin the exact saved 0.9 Ref.
            state, exact_request, previous_bundle = pinned_read
            command = [
                sys.executable,
                "-B",
                "-X",
                "utf8",
                "-m",
                "company_wiki.source_catalog.narrative_transport_cli",
                "--config",
                str(config),
            ]
            code, latest, _, _ = _cli(
                root,
                output,
                "latest-after-legacy" if len(versions) == 2 else "latest-single-090",
                command + ["--operation", "reference"],
                env,
                {
                    "schema_version": "narrative-reference-request/1",
                    "source_ref": imported["source_ref"],
                },
            )
            assert code == 0
            if len(versions) == 2:
                assert latest == next(row["artifact_ref"] for row in states if row["version"] == "0.8.0")
                assert latest != exact_request["narrative_ref"]
            else:
                assert latest == exact_request["narrative_ref"]
            code, wire, stderr, raw = _cli(
                root,
                output,
                "exact-090-after-legacy" if len(versions) == 2 else "exact-single-090",
                command + ["--operation", "read"],
                env,
                exact_request,
                compact_stdout=True,
            )
            exact_receipt = json.loads(stderr)
            assert (
                code == 0
                and exact_receipt["narrative_ref"] == exact_request["narrative_ref"]
            )
            assert (
                hashlib.sha256(raw).hexdigest()
                == exact_request["narrative_ref"]["artifact_sha256"]
            )
            exact_bundle = NarrativeBundle.from_dict(wire)
            assert exact_bundle.to_dict() == previous_bundle.to_dict()
            assert (
                wire["reading_context"] == previous_bundle.to_dict()["reading_context"]
            )
            assert (
                reading_material_sha256(exact_bundle)
                == state["final_generation"]["selection_generation"]["material_sha256"]
            )
            exact_proof_key = ("historical_exact_ref_after_legacy_LATEST" if len(versions) == 2
                               else "current_exact_ref_single_selector")
            state[exact_proof_key] = {
                "status": "PASS",
                ("legacy_latest_ref" if len(versions) == 2 else "latest_ref"): latest,
                "pinned_090_ref": exact_request["narrative_ref"],
                "reading_context_not_trimmed": True,
                "duplicate_bundle_saved": False,
            }
            observer_config["forbid_post"] = True
            write_json(observer, observer_config)
            state["consumers"] = (consumers(
                root, output, env, config, descriptor, exact_request, exact_bundle.to_dict(),
                projects=consumer_projects,
            ) if consumer_projects is not None else {
                "status": "NOT_RUN", "reason": "explicit consumer checkout root not supplied"})
            if len(versions) == 1 and isinstance(state["consumers"], list):
                for item in state["consumers"]:
                    if item.pop("historical_exact_ref_full_context_verified", False):
                        item["current_exact_ref_full_context_verified"] = True
        if outcome.get("status") != "PRE_RESERVATION_BLOCKED":
            outcome["status"] = "PASS"
    except Exception as exc:
        from tools.document_understanding_benchmark.phase_c_readonly_source import ReadonlySourceGap

        if isinstance(exc, ReadonlySourceGap):
            outcome.update(source_gap={"reason": exc.reason, "detail": exc.detail}, status="NOT_RUN")
        trace = exc.__traceback__
        while trace is not None and trace.tb_next is not None:
            trace = trace.tb_next
        outcome.update(
            status="NOT_RUN" if isinstance(exc, ReadonlySourceGap) else "FAIL",
            error=f"{type(exc).__name__}: {exc}",
            error_file=Path(trace.tb_frame.f_code.co_filename).name if trace else None,
            error_line=trace.tb_lineno if trace else None,
        )
    finally:
        try:
            try:
                if current_run is not None and database.exists():
                    append_native(database, current_run, output, mode)
            except Exception as exc:
                # The native usage journal is written before the mother ledger.
                # An accounting failure is never success or zero-cost evidence;
                # retain the failed run identity for reconciliation, but do not
                # strand an entire test lake merely because persistence failed.
                outcome.update(status="FAIL", finalization_error=type(exc).__name__,
                               native_usage_reconciliation_required=True,
                               native_usage_run_id=current_run)
                try:
                    saved = _preserve_accounting_hold(database, current_run, output, mode,
                                                     metadata["candidate_per_paid_request_limits"])
                    outcome["native_usage_hold_saved"] = saved["ledger_saved" if mode == "live" else "sidecar_saved"]
                    outcome["native_usage_hold_sidecar_saved"] = saved["sidecar_saved"]
                except Exception as hold_error:
                    outcome.update(native_usage_hold_saved=False,
                                   accounting_hold_error=type(hold_error).__name__)
            outcome["model_post_attempts"] = sum(
                row["event"] == "http_post_attempt" for row in read_rows(events)
            )
            outcome["protected_unchanged"] = all(
                fingerprint(Path(path)) == before for path, before in protected.items()
            )
            outcome["sentinel_unchanged"] = fingerprint(sentinel) == sentinel_before
        except Exception as exc:
            outcome.update(status="FAIL", finalization_observation_error=type(exc).__name__)
    return outcome


def loopback_draft(material, *, invalid_summary=False):
    """Synthetic source copy; protocol/failed-output transport, never quality proof."""
    if material["schema_version"] == "narrative-model-request/6":
        # Ranking-only v5 never copies body, numbers, prose or source aliases.
        return {"decisions": [{"task": task["key"],
            "priority": "invalid" if invalid_summary else "normal",
            "disposition": "consider"} for task in material["material"]["tasks"]]}
    from company_wiki.automation.narrative_summary_protocols import scoped_protocol_for_request
    if scoped_protocol_for_request(material['schema_version']) is not None:
        view = material["material"]
        task = view["tasks"][0]
        support = task.get("support_parts", view["task_defaults"]["support_parts"])
        key = task["parts"][0]["key"] if support == "all_parts" else support[0]
        part = next(part for part in task["parts"] if part["key"] == key)
        if "shared_ref" in part:
            source_key = part["shared_ref"]
            part = next(row for row in view["shared_fragments"] if row["source_key"] == source_key)
        return {"drafts_by_task": {task["key"]: [{"text": "" if invalid_summary else part["text"][:180],
                "basis_parts": [key], "modality": "actual"}]}}
    alias, text = material["evidence"][0][:2]
    source = material["source"]
    unit_citations = material["schema_version"] == "narrative-model-request/4"
    source_owned = unit_citations or material["schema_version"] == "narrative-model-request/3"
    result = {
        "draft": {
            "claims": [
                {
                    "claim_id": "fixture-claim",
                    "text": text[:180],
                    "evidence_ids": [alias],
                    "evidence_group_ids": [],
                    "claim_type": "company_statement",
                    "modality": "actual",
                }
            ],
        }
    }
    if unit_citations:
        unit = next(row[0] for row in material["citation_units"] if alias in row[2])
        result = {"claims": [{"claim_id": "fixture-claim", "text": text[:180],
            "citation_unit_ids": [unit], "claim_type": "company_statement", "modality": "actual"}]}
    if not source_owned:
        result["draft"].update(source_id=source["source_id"],
            source_sha256=source["source_sha256"], language=source["language"])
    if invalid_summary:
        if unit_citations:
            result["claims"][0]["text"] = ""
        else:
            del result["draft"]["claims" if source_owned else "source_sha256"]
    return result


class Loopback:
    def __init__(self, *, invalid_summary=False):
        self.requests = []
        self.invalid_summary = invalid_summary
        owner = self

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *args):
                pass

            def do_POST(self):
                raw = self.rfile.read(int(self.headers["Content-Length"]))
                body = json.loads(raw)
                owner.requests.append(
                    {"body_sha256": hashlib.sha256(raw).hexdigest(), "bytes": len(raw)}
                )
                material = json.loads(body["messages"][1]["content"])
                result = loopback_draft(material, invalid_summary=owner.invalid_summary)
                wire = json.dumps(
                    {
                        "model": body["model"],
                        "choices": [
                            {
                                "finish_reason": "stop",
                                "message": {"content": json.dumps(result)},
                            }
                        ],
                        "usage": {"prompt_tokens": 50, "completion_tokens": 30},
                    }
                ).encode()
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(wire)))
                self.end_headers()
                self.wfile.write(wire)

        self.server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.thread = Thread(target=self.server.serve_forever, daemon=True)
        self.endpoint = f"http://127.0.0.1:{self.server.server_port}/chat/completions"

    def __enter__(self):
        self.thread.start()
        return self

    def __exit__(self, *args):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=5)


def loopback_preparation():
    """Synthetic controls for the existing loopback, with no paid history/config."""
    return {"protected_fingerprints": {}, "providers": [{
        "provider": "deepseek", "options": {"model_id": "stub-model",
            "endpoint": "http://127.0.0.1:1/chat/completions", "api_key_env": "DEEPSEEK_API_KEY",
            "max_output_tokens": 8192, "temperature": 1.0, "thinking": "disabled",
            "output_token_field": "max_tokens"},
        "price_proxy": {"version": "loopback-only/1",
            "input_micro_usd_per_million_tokens": 1000000,
            "output_micro_usd_per_million_tokens": 2000000}}],
        "candidate_per_paid_request_limits": {"max_seconds": 300, "max_tokens": 200000,
            "max_cost_usd": "1", "max_final_bytes": 2097152,
            "max_persistent_bytes": 67108864, "max_scratch_bytes": 33554432,
            "model_transport_only": {"timeout_seconds": 120, "max_request_bytes": 262144,
                                     "max_response_bytes": 262144}}}


def argument_parser() -> argparse.ArgumentParser:
    from company_wiki.automation.narrative_model_runtime import DURABLE_PAID_RESPONSE_PROJECTIONS
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=("loopback", "live"), default="loopback")
    parser.add_argument("--sample", help="exact sample_id from the explicit preparation metadata")
    parser.add_argument("--metadata", type=Path,
                        help="Explicit live preparation revision; loopback does not need paid history.")
    parser.add_argument("--usage-ledger", type=Path,
                        help="Existing cumulative live mother ledger, never reset for a Temp run.")
    parser.add_argument("--output", type=Path, required=True,
                        help="New owned receipt directory; existing outputs are never replaced.")
    parser.add_argument("--consumer-projects", type=Path,
                        help="Explicit sibling FF/RF checkout root; omission records consumers NOT_RUN.")
    parser.add_argument("--reading-model-projection", choices=tuple(sorted(DURABLE_PAID_RESPONSE_PROJECTIONS)),
                        default="reading-model-input/4",
                        help="Selector 0.9 defaults to legacy v4; other registered durable protocols are explicit.")
    parser.add_argument("--source-mode", choices=("isolated-copy", "registered_readonly"), default="isolated-copy",
                        help="Keep the historical local import, or register existing roots without copying raw bytes.")
    parser.add_argument("--source-catalog-config", type=Path,
                        help="Current source-owner roots for registered_readonly; only the owned catalog is written.")
    parser.add_argument("--selector-versions", choices=("0.9.0", "0.9.0,0.8.0"),
                        help="Omission retains the historical pair; 0.9.0 is single-selector acceptance.")
    parser.add_argument("--activation-recovery", action="store_true",
                        help="Test paid outbox activation_pending then resume the same run with zero new POST.")
    parser.add_argument("--reconcile-run-id", help="Replay an existing native usage journal into --usage-ledger; no model or AUTO DB.")
    return parser


def main() -> int:
    parser = argument_parser()
    args = parser.parse_args()
    global USAGE
    if args.reconcile_run_id is not None:
        if args.usage_ledger is None or args.mode != "live":
            parser.error("native reconciliation requires live mode and the existing usage ledger")
        USAGE = args.usage_ledger.resolve()
        print(json.dumps(reconcile_native_usage(args.output.resolve(strict=True), args.reconcile_run_id)))
        return 0
    if args.source_mode == "registered_readonly" and args.source_catalog_config is None:
        parser.error("registered_readonly requires --source-catalog-config")
    if args.source_mode == "registered_readonly" and args.mode != "live":
        parser.error("registered_readonly uses explicit prepared originals; loopback retains its own synthetic source")
    if args.mode == "live" and (args.metadata is None or args.usage_ledger is None):
        parser.error("live mode requires explicit --metadata and --usage-ledger")
    if args.mode == "live" and args.sample is None:
        parser.error("choose one explicit prepared sample for each live operation")
    preparation_path = args.metadata.resolve() if args.metadata is not None else None
    metadata = (json.loads(preparation_path.read_text(encoding="utf8"))
                if preparation_path is not None else loopback_preparation())
    live_input = prepared_live_input(metadata, args.sample) if args.mode == "live" else None
    preparation = verify_preparation(metadata, mode=args.mode)
    destination = args.output.resolve()
    destination.mkdir(parents=True, exist_ok=False)
    USAGE = (args.usage_ledger.resolve() if args.usage_ledger is not None
             else destination / "loopback-never-written-usage.jsonl")
    ledger_before = fingerprint(USAGE) if USAGE.exists() else None
    write_json(destination / "preparation.json", preparation)
    git_head = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT,
                              capture_output=True, text=True, check=False)
    head = git_head.stdout.strip() if git_head.returncode == 0 else None
    write_json(destination / "harness-fingerprint.json", {
        "files": {name: fingerprint(TOOLS / name) for name in (
            "phase_c_runner.py", "phase_c_observer.py", "phase_c_launcher.py",
            "phase_c_failure_review_material.py", "phase_c_bootstrap/sitecustomize.py")},
        "repository_head": head,
        "tracked_source_dirty": (subprocess.run(["git", "diff", "--quiet", "--", "src"], cwd=ROOT).returncode != 0
                                 if head is not None else None),
        "purpose": "reproducibility observation only; not permission or source acceptance",
    })
    if args.mode == "live":
        assert live_input is not None
        sample, provider = live_input
        from config import Config
        from company_wiki.automation.narrative_http_model import (
            model_options_from_config,
        )

        actual = model_options_from_config(
            Config.load(llm_provider=provider["provider"], validation_scope="llm").llm,
            purpose="narrative"
        )
        if actual != provider["options"]:
            raise ValueError("ACTUAL_CONFIGURED_MODEL_DRIFT")
        outcome = run_pair(sample, provider, metadata, mode="live", output=destination,
                           preparation_path=preparation_path,
                           reading_model_projection=args.reading_model_projection,
                           consumer_projects=args.consumer_projects,
                           source_mode=args.source_mode, source_catalog_config=args.source_catalog_config,
                           selected_versions=args.selector_versions,
                           activation_recovery=args.activation_recovery)
        write_json(destination / "mother-after.json", mother_totals(preparation_path, USAGE))
    else:
        provider = next(
            row for row in metadata["providers"] if row["provider"] == "deepseek"
        )
        sample = {"sample_id": "loopback-fixture"}
        with Loopback() as server:
            success = destination / "success"
            failure = destination / "missing-gold"
            separated = destination / "split-groups"
            success.mkdir()
            failure.mkdir()
            separated.mkdir()
            normal = run_pair(
                sample,
                provider,
                metadata,
                mode="loopback",
                output=success,
                preparation_path=preparation_path,
                reading_model_projection=args.reading_model_projection,
                consumer_projects=args.consumer_projects,
                fixture_endpoint=server.endpoint,
                selected_versions=args.selector_versions,
                activation_recovery=args.activation_recovery,
            )
            count = len(server.requests)
            denied = run_pair(
                sample,
                provider,
                metadata,
                mode="loopback",
                output=failure,
                preparation_path=preparation_path,
                reading_model_projection=args.reading_model_projection,
                consumer_projects=args.consumer_projects,
                fixture_endpoint=server.endpoint,
                missing_gold=True,
            )
            split_denied = run_pair(
                sample,
                provider,
                metadata,
                mode="loopback",
                output=separated,
                preparation_path=preparation_path,
                reading_model_projection=args.reading_model_projection,
                consumer_projects=args.consumer_projects,
                fixture_endpoint=server.endpoint,
                split_groups=True,
            )
            outcome = {
                "status": "PASS"
                if normal["status"]
                == denied["status"]
                == split_denied["status"]
                == "PASS"
                and count == len(selector_versions(args.selector_versions))
                and len(server.requests) == len(selector_versions(args.selector_versions))
                else "FAIL",
                "mode": "loopback",
                "normal": normal,
                "denied": denied,
                "split_groups_denied": split_denied,
                "loopback_POSTs": len(server.requests),
                "external_POSTs": 0,
                "mother_ledger_changed": (
                    fingerprint(USAGE) if USAGE.exists() else None
                )
                != ledger_before,
                "fixture_not_model_quality": True,
            }
            if outcome["mother_ledger_changed"]:
                outcome["status"] = "FAIL"
        malformed = destination / "invalid-summary"
        malformed.mkdir()
        with Loopback(invalid_summary=True) as server:
            rejected = run_pair(sample, provider, metadata, mode="loopback", output=malformed,
                                reading_model_projection="reading-model-input/4",
                                consumer_projects=args.consumer_projects,
                                fixture_endpoint=server.endpoint,
                                preparation_path=preparation_path)
            observed = [row for row in read_rows(malformed/'events.jsonl')
                        if row.get('event') == 'model_final_observed']
            failed_records = [item for path in malformed.glob('*.native-failures.json')
                              for item in json.loads(path.read_text(encoding='utf8'))
                              if item['error_code'] == 'SUMMARY_INVALID']
            finals = list((malformed/'materials').glob('*.response.json.gz'))
            diagnostic = None
            if len(failed_records) == 1:
                diagnostic = json.loads(failed_records[0]['result_json'])['result'].get('failed_final')
            exact_final = gzip.decompress(finals[0].read_bytes()) if len(finals) == 1 else None
            failed_usage = [item for path in malformed.glob('*.native-usage.json')
                            for item in json.loads(path.read_text(encoding='utf8'))]
            failed_output_settled = (len(failed_usage) == 1
                and failed_usage[0]['output_bytes'] == 0
                and failed_usage[0]['output_sha256'] is None
                and failed_usage[0]['output_settled_at'] is not None
                and failed_usage[0]['charged_tokens'] == 80
                and failed_usage[0]['usage_status'] == 'known')
            review_files = list(malformed.glob('*.failure-review.json.gz'))
            review_indexes = list(malformed.glob('*.failure-review-index.json'))
            native_review_preserved = False
            if len(review_files) == len(review_indexes) == 1:
                from company_wiki.automation.narrative_contracts import NarrativeSelectResult
                from company_wiki.automation.narrative_selection_generation import reading_material_sha256

                review_bytes = review_files[0].read_bytes()
                index = json.loads(review_indexes[0].read_text(encoding='utf8'))
                material = json.loads(gzip.decompress(review_bytes))
                item = material['items'][0]
                selected = NarrativeSelectResult.from_dict(item['select_result'])
                native_review_preserved = (
                    material['schema_version'] == 'native-failure-review/1'
                    and len(material['items']) == 1
                    and index['sha256'] == hashlib.sha256(review_bytes).hexdigest()
                    and index['bytes'] == len(review_bytes)
                    and selected.source_ref.content_sha256 == rejected['source_ref']['content_sha256']
                    and item['final_generation']['selection_generation']['material_sha256']
                    == reading_material_sha256(selected)
                    and failed_records[0]['attempt_id'] in item['failed_summary_attempt_ids']
                    and bool(selected.evidence_spans)
                )
            passed = (rejected['status'] == 'FAIL' and len(server.requests) == 1
                      and len(observed) == 1 and len(failed_records) == 1 and diagnostic is not None
                      and exact_final is not None
                      and failed_output_settled
                      and native_review_preserved
                      and diagnostic['final_content_sha256'] == hashlib.sha256(exact_final).hexdigest()
                      and rejected['temporary_lake_removed'] and rejected['protected_unchanged']
                      and rejected['sentinel_unchanged'])
            outcome['paid_transport_invalid_summary_negative'] = {
                'reading_model_projection':'reading-model-input/4',
                'scope':'legacy_prose_contract_negative_not_v5_rank_quality',
                'status':'PASS' if passed else 'FAIL', 'local_POSTs':len(server.requests),
                'production_rejected':rejected['status']=='FAIL',
                'complete_final_captured_before_decode':len(finals)==1,
                'production_failure_rule_preserved':len(failed_records)==1,
                'bounded_diagnostic_matches_final':passed,
                'failed_output_slot_settled_zero_without_usage_refund':failed_output_settled,
                'native_failure_material_preserved_before_cleanup':native_review_preserved,
                'temporary_lake_removed':rejected['temporary_lake_removed'],
                'external_POSTs':0,
            }
            if not passed or (fingerprint(USAGE) if USAGE.exists() else None) != ledger_before:
                outcome['status'] = 'FAIL'
    outcome["all_prepared_protected_unchanged"] = all(
        fingerprint(Path(path)) == before
        for path, before in preparation["protected"].items()
    )
    if not outcome["all_prepared_protected_unchanged"]:
        outcome["status"] = "FAIL"
    write_json(destination / "overall.json", outcome)
    print(
        json.dumps(
            {
                "status": outcome["status"],
                "mode": args.mode,
                "receipt": str(destination / "overall.json"),
            },
            ensure_ascii=False,
        )
    )
    return 0 if outcome["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
