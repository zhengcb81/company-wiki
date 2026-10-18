"""RED: shell-shape rules of `identity-audit-receipt/1`.

The receipt shell is frozen by INTERFACES section 7 (six fields) plus the
card's ``sources`` array.  An extra key anywhere in that shell is a contract
violation, and every check must carry its own status vocabulary.
"""

from __future__ import annotations

import json

from fixtures import sidecar_catalog
from harness import audit_core, run_module, write_json

AUDIT_MODULE = "tools.identity_audit"

SHELL_FIELDS = {
    "schema_version",
    "status",
    "generated_at",
    "inputs",
    "counts",
    "limitations",
    "sources",
}
COUNT_FIELDS = {"checked", "passed", "failed", "not_applicable", "not_evaluated"}
TOP_LEVEL_STATUSES = {"ok", "partial", "fail", "blocked", "unavailable"}
# Card section 5.3 fixes each check's shape: identity/period carry `observed`
# and `expected`, unit carries `tokens`; every check has `status` and
# `detail`, and refusals add `error_code`/`reason`.  The frozen part of this
# test is the status vocabulary below, not the absence of payload fields.
CHECK_FIELDS = {
    "status",
    "detail",
    "error_code",
    "reason",
    "observed",
    "expected",
    "tokens",
}


def _receipt(plain) -> dict:
    return audit_core().audit(
        config_path=plain.config_path,
        request=sidecar_catalog.request_payload(refs=[plain.ref_payload()]),
    )


def test_the_receipt_shell_has_exactly_the_frozen_fields(plain):
    receipt = _receipt(plain)
    assert set(receipt) == SHELL_FIELDS, sorted(set(receipt) ^ SHELL_FIELDS)
    assert receipt["schema_version"] == "identity-audit-receipt/1"
    assert set(receipt["counts"]) == COUNT_FIELDS, receipt["counts"]


def test_generated_at_is_a_utc_second_precision_stamp(plain):
    receipt = _receipt(plain)
    stamp = receipt["generated_at"]
    assert isinstance(stamp, str) and stamp.endswith("Z"), stamp
    assert len(stamp) == len("2026-10-18T08:00:00Z"), stamp
    assert stamp[10] == "T" and stamp[4] == "-" and stamp[7] == "-"


def test_inputs_bind_the_config_and_the_request_bytes(plain):
    receipt = _receipt(plain)
    inputs = receipt["inputs"]
    config_key = str(plain.config_path)
    assert config_key in inputs, sorted(inputs)
    binding = inputs[config_key]
    assert set(binding) == {"sha256", "bytes"}, binding
    assert binding["bytes"] == plain.config_path.stat().st_size
    assert binding["sha256"] == sidecar_catalog.sha256_bytes(
        plain.config_path.read_bytes()
    )


def test_limitations_are_declared(plain):
    receipt = _receipt(plain)
    limitations = receipt["limitations"]
    assert isinstance(limitations, list) and limitations, limitations
    assert all(isinstance(item, str) and item.strip() for item in limitations)


def test_every_check_uses_the_frozen_status_vocabulary(plain):
    receipt = _receipt(plain)
    checks = receipt["sources"][0]["checks"]
    assert receipt["status"] in TOP_LEVEL_STATUSES, receipt["status"]
    assert set(checks) == {
        "ref",
        "bytes",
        "identity",
        "period",
        "availability",
        "spans",
        "unit",
    }, sorted(checks)
    # The card names one extra availability-only status:
    # `source_availability_unknown` (section 5.3).  Nothing else may invent a
    # status outside the shared vocabulary.
    for name in ("ref", "bytes", "identity", "period", "availability", "unit"):
        entry = checks[name]
        assert isinstance(entry, dict), (name, entry)
        assert set(entry) <= CHECK_FIELDS, (name, sorted(entry))
        allowed = {"pass", "fail", "not_applicable", "not_evaluated"}
        if name == "availability":
            allowed.add("source_availability_unknown")
        assert entry["status"] in allowed, (name, entry)
        if entry["status"] in {"not_applicable", "not_evaluated"}:
            assert entry.get("reason"), (name, entry)
        assert entry["status"] not in {"ok", "partial", "blocked", "unavailable"}, (
            name,
            entry,
        )


def test_counts_reconcile_with_the_per_source_checks(plain):
    receipt = _receipt(plain)
    counts = receipt["counts"]
    checks = receipt["sources"][0]["checks"]
    entries = [
        checks[name]
        for name in ("ref", "bytes", "identity", "period", "availability", "unit")
    ]
    entries.extend(checks["spans"])
    assert counts["checked"] == len(entries), (counts, len(entries))
    assert counts["passed"] == sum(1 for e in entries if e["status"] == "pass"), counts
    assert counts["failed"] == sum(1 for e in entries if e["status"] == "fail"), counts
    assert counts["not_applicable"] == sum(
        1 for e in entries if e["status"] == "not_applicable"
    ), counts


def test_a_source_with_a_failure_reports_fail_at_both_levels(plain):
    receipt = audit_core().audit(
        config_path=plain.config_path,
        request=sidecar_catalog.request_payload(
            refs=[plain.ref_payload(byte_size=plain.ref.byte_size + 1)]
        ),
    )
    assert receipt["status"] == "fail", receipt
    assert receipt["sources"][0]["status"] == "fail", receipt["sources"][0]


def test_an_unreadable_catalog_is_unavailable_not_a_pass(plain):
    missing = plain.root / "config" / "absent.yaml"
    assert not missing.exists()
    receipt = audit_core().audit(
        config_path=missing,
        request=sidecar_catalog.request_payload(refs=[plain.ref_payload()]),
    )
    assert receipt["status"] == "unavailable", receipt
    assert receipt.get("reason") == "dependency_unavailable", receipt
    assert receipt["counts"]["passed"] == 0, receipt["counts"]


def test_the_single_line_json_is_canonical(plain):
    request_path = write_json(
        plain.root / "canonical-request.json",
        sidecar_catalog.request_payload(refs=[plain.ref_payload()]),
    )
    code, stdout, stderr = run_module(
        AUDIT_MODULE,
        ["--config", str(plain.config_path), "--request", str(request_path)],
        stdin_path=request_path,
        out_dir=plain.root / "canonical",
    )
    assert code == 0, (code, stdout[:400], stderr[:400])
    body = stdout.decode("utf-8").rstrip("\n")
    assert stdout.decode("utf-8") == body + "\n"
    assert body == json.dumps(
        json.loads(body), ensure_ascii=True, sort_keys=True, separators=(",", ":")
    )
    assert all(ord(char) < 128 for char in body), "canonical JSON is ASCII-escaped"
