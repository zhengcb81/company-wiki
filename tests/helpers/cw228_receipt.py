"""CW-2.28 receipt contract helpers (task_plan §12.2).

Shared by ``tests/contract/test_cw_228_receipt.py`` and by later phases that need
to validate the attempt receipts they write. These helpers encode the
machine-decidable PASS/FAIL rules from §12.1 and the receipt format from §12.2,
including the negative cases listed in §12.2.9.

The per-receipt JSON Schema lives at
``docs/contracts/cw-2.28-receipt.schema.json`` and validates *shape*. The
``validate_receipt_rules`` and ``validate_chain`` functions add the cross-field
and cross-receipt rules a declarative schema cannot express (status↔exit-code,
phase ordering, previous-PASS gate, index↔file SHA integrity, legacy
impersonation, secret scan).
"""

from __future__ import annotations

import hashlib
import json
import pathlib
import re
from typing import Any

import jsonschema

ALL_STATUSES = {
    "PASS",
    "FAIL",
    "PARTIAL",
    "BLOCKED_AUTHORIZATION",
    "BLOCKED_UPSTREAM",
    "INVALIDATED_CONCURRENT_CHANGE",
    "NOT_RUN",
}
# Only PASS unlocks the next phase. Everything else is a soft terminal for the
# chain (it does not advance). This is the §12.2.5 override of the old §6 rule.
UNLOCKING_STATUSES = {"PASS"}

SCHEMA_PATH = (
    pathlib.Path(__file__).resolve().parents[2]
    / "docs"
    / "contracts"
    / "cw-2.28-receipt.schema.json"
)

ATTEMPT_FILENAME = re.compile(r"^phase-(\d+)-attempt-(\d+)\.json$")
LEGACY_FILENAME = re.compile(r"^phase-\d+-receipt\.json$")

# High-confidence *active* secret patterns. These match real credential blobs,
# not field names, so legitimate metadata like "secret_scan_result" does not trip.
_SECRET_PATTERNS = [
    re.compile(r"AKIA[0-9A-Z]{16}"),  # AWS access key id
    re.compile(r"-----BEGIN (?:RSA |EC |DSA |OPENSSH |)PRIVATE KEY-----"),
    re.compile(r"gh[pousr]_[A-Za-z0-9]{36,}"),  # GitHub token
    re.compile(r"sk-ant-[A-Za-z0-9_\-]{20,}"),  # Anthropic key
    re.compile(r"sk-proj-[A-Za-z0-9_\-]{20,}"),  # OpenAI project key
    re.compile(r"xox[baprs]-[A-Za-z0-9-]{10,}"),  # Slack token
    re.compile(r"Bearer [A-Za-z0-9._\-]{20,}", re.IGNORECASE),
]


def load_schema() -> dict[str, Any]:
    """Load and parse the receipt JSON Schema."""
    return json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))


def schema_validator() -> jsonschema.Draft202012Validator:
    return jsonschema.Draft202012Validator(load_schema())


def validate_receipt_shape(receipt: dict[str, Any]) -> list[str]:
    """Validate a single receipt against the JSON Schema. Returns error strings."""
    errors: list[str] = []
    validator = schema_validator()
    for err in sorted(validator.iter_errors(receipt), key=lambda e: list(e.path)):
        loc = ".".join(str(p) for p in err.path) or "<root>"
        errors.append(f"schema:{loc}: {err.message}")
    return errors


def validate_receipt_rules(receipt: dict[str, Any]) -> list[str]:
    """Cross-field rules for a single receipt (independent of the JSON Schema).

    Enforces §12.2.9 cases 3 and 4: a PASS receipt must have every command at
    exit_code 0 with no failed/skipped/xfailed tests. A command flagged
    ``red_contract=True`` is a declared RED probe (§12.1.2/§12.4.2) — its nonzero
    exit and failed/xfailed tests ARE the success criterion, so it is exempt from
    the exit-code and failed/xfailed checks, but it still may not have skips, and
    the receipt must carry an invariant attesting the RED failed for the right
    reason (not an import/fixture/path error).
    """
    errors: list[str] = []
    status = receipt.get("status")
    commands = receipt.get("command_results", []) or []
    invariants = receipt.get("invariant_results", []) or []
    red_attested = any(
        isinstance(inv, dict)
        and inv.get("name") == "red_fails_for_right_reason"
        and inv.get("passed") is True
        for inv in invariants
    )
    if status == "PASS":
        for cmd in commands:
            if not isinstance(cmd, dict):
                errors.append("rule:command_results entry is not an object")
                continue
            cid = cmd.get("command_id", "<no-id>")
            is_red = bool(cmd.get("red_contract"))
            if is_red:
                if not red_attested:
                    errors.append(
                        f"rule:red_contract command '{cid}' lacks invariant "
                        "'red_fails_for_right_reason'=passed"
                    )
                if cmd.get("skipped_tests"):
                    errors.append(
                        f"rule:status=PASS but red_contract command '{cid}' has "
                        f"skipped_tests={cmd.get('skipped_tests')}"
                    )
                continue
            if cmd.get("exit_code", 0) != 0:
                errors.append(
                    f"rule:status=PASS but command '{cid}' exit_code={cmd.get('exit_code')}"
                )
            for key in ("failed_tests", "skipped_tests", "xfailed_tests"):
                if cmd.get(key):
                    errors.append(
                        f"rule:status=PASS but command '{cid}' has {key}={cmd.get(key)}"
                    )
    return errors


def validate_receipt(receipt: dict[str, Any]) -> list[str]:
    """Full single-receipt validation: shape + cross-field rules + secrets."""
    errors = validate_receipt_shape(receipt) + validate_receipt_rules(receipt)
    errors.extend(_secret_rule_errors(receipt))
    return errors


def scan_secrets(receipt: dict[str, Any]) -> list[str]:
    """Return high-confidence active-secret hits found in the serialized receipt."""
    text = json.dumps(receipt, ensure_ascii=False)
    hits: list[str] = []
    for pattern in _SECRET_PATTERNS:
        for match in pattern.findall(text):
            hits.append(match if isinstance(match, str) else match[0])
    return hits


def _secret_rule_errors(receipt: dict[str, Any]) -> list[str]:
    hits = scan_secrets(receipt)
    return [f"secret:high-confidence active secret in receipt: {h[:8]}…" for h in hits]


def _load_index(index_path: pathlib.Path) -> tuple[dict[str, Any], list[str]]:
    """Load receipt-index.json. Returns (entries_dict, errors)."""
    errors: list[str] = []
    if not index_path.exists():
        return {}, ["chain:receipt-index.json missing"]
    try:
        raw = json.loads(index_path.read_text(encoding="utf-8"))
    except Exception as exc:  # noqa: BLE001 - surface any parse failure to the caller
        return {}, [f"chain:receipt-index.json not parseable: {exc}"]
    entries: dict[str, Any] = {}
    if isinstance(raw, dict):
        # Accept either {"phases": {...}} or a flat {key: {path, sha256}} map.
        candidates = raw.get("phases", raw) if isinstance(raw.get("phases"), dict) else raw
        for key, value in candidates.items():
            if isinstance(value, dict) and "path" in value:
                entries[str(key)] = value
    return entries, errors


def validate_chain(receipts_dir: pathlib.Path) -> list[str]:
    """Validate a directory of attempt receipts + receipt-index.json.

    Enforces the chain-level §12.2.9 cases: phase ordering / previous-PASS gate
    (cases 5 and 6), index→file existence and SHA integrity (cases 7 and 8), and
    legacy-receipt impersonation (case 9).
    """
    receipts_dir = pathlib.Path(receipts_dir)
    errors: list[str] = []

    attempt_files: dict[int, list[pathlib.Path]] = {}
    for path in sorted(receipts_dir.glob("phase-*-attempt-*.json")):
        match = ATTEMPT_FILENAME.match(path.name)
        if not match:
            errors.append(f"chain:attempt filename malformed: {path.name}")
            continue
        attempt_files.setdefault(int(match.group(1)), []).append(path)

    # Validate every attempt receipt and record which phases have a PASS.
    pass_phases: set[int] = set()
    for phase, files in sorted(attempt_files.items()):
        for path in files:
            try:
                receipt = json.loads(path.read_text(encoding="utf-8"))
            except Exception as exc:  # noqa: BLE001
                errors.append(f"chain:{path.name} not parseable: {exc}")
                continue
            for err in validate_receipt(receipt):
                errors.append(f"chain:{path.name}: {err}")
            if receipt.get("status") == "PASS":
                pass_phases.add(phase)

    # Previous-PASS gate: phase N PASS requires phase N-1 PASS (N>0).
    for phase in sorted(pass_phases):
        if phase > 0 and (phase - 1) not in pass_phases:
            errors.append(
                f"chain:phase {phase} marked PASS but phase {phase - 1} has no PASS attempt"
            )

    # Index integrity.
    entries, index_errors = _load_index(receipts_dir / "receipt-index.json")
    errors.extend(index_errors)
    index_blob = json.dumps(entries, ensure_ascii=False)
    for key, entry in entries.items():
        rel = entry.get("path")
        if not rel:
            errors.append(f"chain:index entry '{key}' missing 'path'")
            continue
        target = (receipts_dir / rel).resolve()
        if not ATTEMPT_FILENAME.match(target.name):
            errors.append(
                f"chain:index entry '{key}' points at non-attempt file {target.name}"
            )
            continue
        if not target.exists():
            errors.append(f"chain:index entry '{key}' -> {rel} does not exist")
            continue
        actual = hashlib.sha256(target.read_bytes()).hexdigest()
        recorded = entry.get("sha256")
        if recorded and recorded != actual:
            errors.append(
                f"chain:index entry '{key}' sha256 mismatch "
                f"(file={actual[:12]}… index={str(recorded)[:12]}…)"
            )

    # Legacy receipts must remain on disk as evidence but never be indexed.
    for path in receipts_dir.glob("phase-*-receipt.json"):
        if LEGACY_FILENAME.match(path.name) and path.name in index_blob:
            errors.append(
                f"chain:legacy {path.name} referenced by receipt-index (legacy impersonation)"
            )

    return errors


def sha256_file(path: pathlib.Path) -> str:
    return hashlib.sha256(pathlib.Path(path).read_bytes()).hexdigest()


__all__ = [
    "ALL_STATUSES",
    "ATTEMPT_FILENAME",
    "LEGACY_FILENAME",
    "UNLOCKING_STATUSES",
    "load_schema",
    "schema_validator",
    "sha256_file",
    "validate_chain",
    "validate_receipt",
    "validate_receipt_rules",
    "validate_receipt_shape",
    "scan_secrets",
]
