"""RED: the six frozen checks of `identity-audit-receipt/1`.

Every case here is written against the card's decision rules (P3-IDENTITY-AUDIT
section 5.4).  A case that cannot reach a verdict must show up as
``not_applicable``/``not_evaluated``/``null`` -- never as a pass.
"""

from __future__ import annotations

import json
from pathlib import Path


from fixtures import sidecar_catalog
from fixtures.sidecar_catalog import make_span
from harness import (
    audit_core,
    checks_of,
    run_export_v2,
    run_module,
    sole_source,
    write_json,
)

AUDIT_MODULE = "tools.identity_audit"


def audit(fixture, *, spans=(), expect=None, ref_overrides=None):
    """Call the lane core once and return the receipt dict."""
    core = audit_core()
    return core.audit(
        config_path=fixture.config_path,
        request=sidecar_catalog.request_payload(
            refs=[fixture.ref_payload(**(ref_overrides or {}))],
            spans=spans,
            expect=expect,
        ),
    )


# --------------------------------------------------------------------------
# ref
# --------------------------------------------------------------------------


def test_ref_mismatch_is_reported_not_raised(plain):
    """A wrong byte_size must come back as `ref.fail`, not as an exception."""
    receipt = audit(plain, ref_overrides={"byte_size": plain.ref.byte_size + 1})
    ref = checks_of(receipt)["ref"]
    assert ref["status"] == "fail", ref
    assert ref.get("error_code") == "p3_ref_mismatch", ref
    assert ref["detail"]["byte_size"] == plain.ref.byte_size + 1
    assert ref["detail"]["observed_byte_size"] == plain.ref.byte_size


def test_ref_mime_type_mismatch_is_reported(plain):
    receipt = audit(plain, ref_overrides={"mime_type": "application/pdf"})
    ref = checks_of(receipt)["ref"]
    assert ref["status"] == "fail", ref
    assert ref.get("error_code") == "p3_ref_mismatch", ref


def test_ref_passes_when_the_request_matches_the_catalog(plain):
    receipt = audit(plain)
    assert checks_of(receipt)["ref"]["status"] == "pass"


# --------------------------------------------------------------------------
# bytes
# --------------------------------------------------------------------------


def test_replaced_bytes_of_the_same_length_fail_the_bytes_check(plain):
    """Read-only proof: flip one byte, keep the length, and bytes must fail."""
    before = sidecar_catalog.snapshot_tree(plain.root)
    original = plain.raw_path.read_bytes()
    mutated = bytes([original[0] ^ 0x01]) + original[1:]
    assert len(mutated) == len(original)
    plain.raw_path.write_bytes(mutated)
    try:
        receipt = audit(plain)
        checks = checks_of(receipt)
        assert checks["bytes"]["status"] == "fail", checks["bytes"]
        assert checks.get("error_code") == "p3_bytes_mismatch", checks
    finally:
        plain.raw_path.write_bytes(original)
    assert plain.raw_path.read_bytes() == original
    after = sidecar_catalog.snapshot_tree(plain.root)
    catalog_files = {
        key: value
        for key, value in after.items()
        if key.startswith("catalog/")
    }
    assert catalog_files, after.keys()
    for key, value in catalog_files.items():
        assert before[key] == value, (key, before[key], value)


def test_bytes_pass_when_the_original_matches_the_requested_digest(plain):
    receipt = audit(plain)
    bytes_check = checks_of(receipt)["bytes"]
    assert bytes_check["status"] == "pass", bytes_check
    assert bytes_check["detail"]["sha256"] == plain.sha256
    assert bytes_check["detail"]["bytes"] == len(plain.body)


# --------------------------------------------------------------------------
# identity
# --------------------------------------------------------------------------


def test_security_id_width_drift_fails_identity(plain):
    """`9896` observed where the manifest itself declares a CN 6-digit code."""
    plain.catalog.record_source_facts(
        ref=plain.ref,
        facts={"security_id": "9896"},
        evidence={"security_id": {"value": "9896", "locator": "fixture:width-drift"}},
    )
    receipt = audit(plain)
    identity = checks_of(receipt)["identity"]
    assert identity["status"] == "fail", identity
    assert identity.get("error_code") == "p3_identity_conflict", identity
    assert identity["observed"]["security_id"] == "9896"
    assert identity["observed"]["market"] == "CN"
    assert identity["detail"]["canonical_security_id"] == "009896"


def test_market_is_never_borrowed_across_markets(plain):
    """A CN request must not accept an HK-declared code that merely equals it."""
    plain.catalog.record_source_facts(
        ref=plain.ref,
        facts={"market": "HK"},
        evidence={"market": {"value": "HK", "locator": "fixture:market-drift"}},
    )
    receipt = audit(plain, expect={"market": "CN", "security_id": "688012"})
    identity = checks_of(receipt)["identity"]
    assert identity["status"] == "fail", identity
    assert identity.get("error_code") == "p3_identity_conflict", identity
    assert identity["observed"]["market"] == "HK"
    assert identity["expected"]["market"] == "CN"


def test_expect_null_requires_an_actual_null_observation(plain):
    """An explicit `null` expectation is "unknown", not "no constraint"."""
    receipt = audit(plain, expect={"market": None})
    identity = checks_of(receipt)["identity"]
    assert identity["status"] == "fail", identity
    assert identity.get("error_code") == "p3_identity_conflict", identity


def test_expect_null_passes_when_both_sides_are_unknown(build):
    fixture = build(facts={"form_type": None, "language": None})
    receipt = audit(fixture, expect={"form_type": None, "language": None})
    identity = checks_of(receipt)["identity"]
    assert identity["status"] == "pass", identity
    assert identity["observed"]["form_type"] is None
    assert identity["observed"]["language"] is None
    assert identity["expected"] == {"form_type": None, "language": None}


def test_identity_is_not_applicable_when_the_manifest_has_no_identity(build):
    """Missing identity must not be converted into a pass."""
    fixture = build()
    fixture.catalog.record_source_facts(
        ref=fixture.ref,
        facts={"market": None, "security_id": None},
        evidence={
            "market": {"value": None, "locator": "fixture:no-market"},
            "security_id": {"value": None, "locator": "fixture:no-security-id"},
        },
    )
    receipt = audit(fixture)
    identity = checks_of(receipt)["identity"]
    assert identity["status"] == "not_applicable", identity
    assert identity.get("reason"), identity
    assert identity["observed"]["security_id"] is None


# --------------------------------------------------------------------------
# period
# --------------------------------------------------------------------------


def test_expect_period_against_a_null_manifest_period_fails(plain):
    """`expect.fiscal_period` given while the manifest is null is a conflict."""
    plain.catalog.record_source_facts(
        ref=plain.ref,
        facts={"fiscal_period": None},
        evidence={"fiscal_period": {"value": None, "locator": "fixture:period-null"}},
    )
    receipt = audit(plain, expect={"fiscal_period": "H1"})
    period = checks_of(receipt)["period"]
    assert period["status"] == "fail", period
    assert period.get("error_code") == "p3_period_conflict", period
    assert period["observed"]["fiscal_period"] is None
    assert period["observed"]["unknown_source"] == "nullable_manifest"


def test_fabricated_date_without_evidence_conflicts_with_an_unknown_expectation(
    build,
):
    """A date written with no capture proof must not be waved through."""
    fixture = build(facts={"published_date": "2026-08-01"})
    receipt = audit(fixture, expect={"published_date": None})
    period = checks_of(receipt)["period"]
    assert period["status"] == "fail", period
    assert period.get("error_code") == "p3_period_conflict", period
    assert period["observed"]["published_date"] == "2026-08-01"
    assert period["observed"]["date_provenance"] == "unverified"


def test_unknown_publication_date_stays_unknown_and_is_marked_unverified(plain):
    """`published_date=null` with no availability evidence is honest, not fake."""
    plain.catalog.record_source_facts(
        ref=plain.ref,
        facts={"published_date": None},
        evidence={"published_date": {"value": None, "locator": "fixture:no-date"}},
    )
    receipt = audit(plain)
    checks = checks_of(receipt)
    assert checks["availability"]["status"] == "source_availability_unknown", checks
    assert checks["availability"]["detail"]["evidence"] is None
    assert checks["period"]["observed"]["published_date"] is None
    assert checks["period"]["observed"]["date_provenance"] == "unverified"
    assert checks["period"]["status"] in {"pass", "not_applicable"}, checks["period"]
    assert receipt["status"] in {"ok", "partial"}, receipt["status"]


def test_a_non_iso_publication_date_fails_the_period_check(build):
    """A manifest date outside YYYY-MM-DD is a conflict, never a normal form."""
    # `record_source_facts` enforces strict ISO dates itself, so the malformed
    # value has to enter through the sidecar before indexing.
    fixture = build(facts={"period_end": "2026/06/30"})
    receipt = audit(fixture)
    period = checks_of(receipt)["period"]
    assert period["status"] == "fail", period
    assert period.get("error_code") == "p3_period_conflict", period
    assert period["observed"]["period_end"] == "2026/06/30", period


def test_period_passes_when_the_manifest_agrees_with_expect(plain):
    receipt = audit(
        plain,
        expect={
            "fiscal_year": 2026,
            "fiscal_period": "H1",
            "period_end": "2026-06-30",
        },
    )
    period = checks_of(receipt)["period"]
    assert period["status"] == "pass", period
    assert period["observed"]["fiscal_year"] == 2026


# --------------------------------------------------------------------------
# availability
# --------------------------------------------------------------------------


def test_unknown_availability_is_never_reported_as_a_pass(plain):
    receipt = audit(plain)
    availability = checks_of(receipt)["availability"]
    assert availability["status"] == "source_availability_unknown", availability
    assert availability["detail"]["evidence"] is None
    assert availability["detail"]["reason"] == "no_verified_capture_evidence"


def test_verified_capture_evidence_is_passed_through_verbatim(captured):
    receipt = audit(captured)
    availability = checks_of(receipt)["availability"]
    assert availability["status"] == "pass", availability
    evidence = availability["detail"]["evidence"]
    assert evidence["schema_version"] == "source-availability-evidence/1"
    assert evidence["basis"] == "prior_verified_capture"
    assert evidence["source_sha256"] == captured.sha256
    assert evidence["available_by"] == "2026-08-02"


# --------------------------------------------------------------------------
# span
# --------------------------------------------------------------------------


def test_span_text_off_by_one_character_fails_grounding(plain):
    text = plain.text()
    start, end = 0, 12
    wrong = text[start:end - 1] + "X"
    assert len(wrong) == end - start and wrong != text[start:end]
    receipt = audit(
        plain,
        spans=[make_span(plain.source_id, char_start=start, char_end=end, raw_text=wrong)],
    )
    span = checks_of(receipt)["spans"][0]
    assert span["status"] == "fail", span
    assert span.get("error_code") == "p3_span_ungrounded", span


def test_span_with_a_page_coordinate_is_not_applicable(plain):
    text = plain.text()
    receipt = audit(
        plain,
        spans=[
            make_span(
                plain.source_id,
                page_number=1,
                char_start=0,
                char_end=12,
                raw_text=text[0:12],
            )
        ],
    )
    span = checks_of(receipt)["spans"][0]
    assert span["status"] == "not_applicable", span
    assert span["reason"] == "not_groundable_shape", span


def test_grounded_span_passes_and_reports_its_offsets(plain):
    text = plain.text()
    receipt = audit(
        plain,
        spans=[
            make_span(plain.source_id, char_start=0, char_end=12, raw_text=text[0:12])
        ],
    )
    span = checks_of(receipt)["spans"][0]
    assert span["status"] == "pass", span
    assert span["detail"]["char_start"] == 0
    assert span["detail"]["char_end"] == 12


# --------------------------------------------------------------------------
# unit
# --------------------------------------------------------------------------


def test_a_unit_token_absent_from_the_original_fails_the_unit_check(plain):
    """The span text claims `单位：百万元`; those characters are not at that offset."""
    shifted = "单位：百万元" + plain.text()[7:19]
    receipt = audit(
        plain,
        spans=[
            make_span(plain.source_id, char_start=0, char_end=12, raw_text=shifted)
        ],
    )
    checks = checks_of(receipt)
    assert checks["spans"][0]["status"] == "fail", checks["spans"]
    unit = checks["unit"]
    assert unit["status"] == "fail", unit
    assert unit.get("error_code") == "p3_unit_mismatch", unit


def test_the_real_unit_marker_is_reported_with_its_offsets(plain):
    text = plain.text()
    start, end = 0, len(text)
    receipt = audit(
        plain,
        spans=[
            make_span(plain.source_id, char_start=start, char_end=end, raw_text=text)
        ],
    )
    unit = checks_of(receipt)["unit"]
    assert unit["status"] == "pass", unit
    tokens = unit["tokens"]
    assert tokens, unit
    assert any("百万元" in token["text"] for token in tokens), tokens
    for token in tokens:
        assert text[token["char_start"]:token["char_end"]] == token["text"], token


def test_no_unit_token_is_not_applicable_with_an_explicit_reason(unmarked):
    text = unmarked.text()
    receipt = audit(
        unmarked,
        spans=[
            make_span(
                unmarked.source_id, char_start=0, char_end=len(text), raw_text=text
            )
        ],
    )
    unit = checks_of(receipt)["unit"]
    assert unit["status"] == "not_applicable", unit
    assert unit["reason"] == "no_unit_token_in_span", unit
    assert unit["tokens"] == []


# --------------------------------------------------------------------------
# request validation and limits
# --------------------------------------------------------------------------


def test_an_empty_source_refs_array_is_blocked_not_passed(plain):
    core = audit_core()
    receipt = core.audit(
        config_path=plain.config_path,
        request=sidecar_catalog.request_payload(refs=[]),
    )
    assert receipt["status"] == "blocked", receipt
    assert receipt.get("reason") == "invalid_argument", receipt
    assert receipt["sources"] == []
    assert receipt["counts"]["checked"] == 0


def test_a_wrong_request_schema_version_is_blocked(plain):
    core = audit_core()
    receipt = core.audit(
        config_path=plain.config_path,
        request=sidecar_catalog.request_payload(
            refs=[plain.ref_payload()], schema_version="identity-audit-request/9"
        ),
    )
    assert receipt["status"] == "blocked", receipt
    assert receipt.get("reason") == "invalid_argument", receipt


def test_ref_extra_field_is_rejected(plain):
    core = audit_core()
    payload = plain.ref_payload()
    payload["unexpected_field"] = "x"
    receipt = core.audit(
        config_path=plain.config_path,
        request=sidecar_catalog.request_payload(refs=[payload]),
    )
    assert receipt["status"] == "blocked", receipt
    assert receipt.get("reason") == "invalid_argument", receipt


def test_duplicate_json_keys_are_blocked(plain):
    request_path = sidecar_catalog.write_raw_request(
        plain.root,
        '{"schema_version":"identity-audit-request/1",'
        '"source_refs":[],"source_refs":[]}',
    )
    code, stdout, stderr = run_module(
        AUDIT_MODULE,
        ["--config", str(plain.config_path), "--request", str(request_path)],
        stdin_path=request_path,
        out_dir=plain.root / "dup-keys",
    )
    assert code == 3, (code, stdout[:400], stderr[:400])
    receipt = json.loads(stdout.decode("utf-8"))
    assert receipt["status"] == "blocked", receipt
    assert receipt.get("reason") in {"invalid_json", "invalid_argument"}, receipt


def test_too_many_source_refs_is_blocked_by_the_limit(plain):
    core = audit_core()
    refs = [plain.ref_payload() for _ in range(core.MAX_SOURCE_REFS + 1)]
    receipt = core.audit(
        config_path=plain.config_path,
        request=sidecar_catalog.request_payload(refs=refs),
    )
    assert receipt["status"] == "blocked", receipt
    assert receipt.get("reason") == "limit_exceeded", receipt


# --------------------------------------------------------------------------
# read-only proof and CLI behaviour
# --------------------------------------------------------------------------


def test_the_audit_never_writes_anything_but_the_out_file(plain):
    request_path = _request(plain)
    before = sidecar_catalog.snapshot_tree(plain.root)
    out_dir = plain.root / "out"
    out_path = out_dir / "receipt.json"
    code, stdout, stderr = run_module(
        AUDIT_MODULE,
        ["--config", str(plain.config_path), "--request", str(request_path)],
        stdin_path=request_path,
        out_dir=out_dir,
    )
    assert code == 0, (code, stdout[:400], stderr[:400])
    after = sidecar_catalog.snapshot_tree(plain.root)
    changed = {
        key
        for key in set(before) | set(after)
        if before.get(key) != after.get(key) and not key.startswith("out/")
    }
    assert changed == set(), changed
    assert not out_path.exists(), "stdout-only run must not create the out file"


def _request(fixture) -> Path:
    return write_json(
        fixture.root / "request.json",
        sidecar_catalog.request_payload(refs=[fixture.ref_payload()]),
    )


def test_out_file_changes_nothing_but_the_out_file(plain):
    request_path = _request(plain)
    before = sidecar_catalog.snapshot_tree(plain.root)
    out_path = plain.root / "receipt-out.json"
    code, stdout, stderr = run_module(
        AUDIT_MODULE,
        [
            "--config",
            str(plain.config_path),
            "--request",
            str(request_path),
            "--out",
            str(out_path),
        ],
        stdin_path=request_path,
        out_dir=plain.root / "out-run",
    )
    assert code == 0, (code, stdout[:400], stderr[:400])
    assert out_path.is_file(), "the documented --out file must be written"
    assert json.loads(out_path.read_text(encoding="utf-8")) == json.loads(stdout)
    after = sidecar_catalog.snapshot_tree(plain.root)
    changed = {
        key
        for key in set(before) | set(after)
        if before.get(key) != after.get(key)
        and not key.startswith("receipt-out.json")
        and not key.startswith("out-run/")
        and key != "request.json"
    }
    assert changed == set(), changed


def test_a_failing_check_exits_two_and_a_clean_audit_exits_zero(plain):
    clean_request = _request(plain)
    code, stdout, stderr = run_module(
        AUDIT_MODULE,
        ["--config", str(plain.config_path), "--request", str(clean_request)],
        stdin_path=clean_request,
        out_dir=plain.root / "clean",
    )
    assert code == 0, (code, stdout[:400], stderr[:400])
    assert json.loads(stdout.decode("utf-8"))["status"] in {"ok", "partial"}

    bad_request = write_json(
        plain.root / "request-bad.json",
        sidecar_catalog.request_payload(
            refs=[plain.ref_payload(byte_size=plain.ref.byte_size + 5)]
        ),
    )
    code, stdout, stderr = run_module(
        AUDIT_MODULE,
        ["--config", str(plain.config_path), "--request", str(bad_request)],
        stdin_path=bad_request,
        out_dir=plain.root / "bad",
    )
    assert code == 2, (code, stdout[:400], stderr[:400])
    receipt = json.loads(stdout.decode("utf-8"))
    assert receipt["status"] == "fail", receipt
    assert receipt["counts"]["failed"] >= 1, receipt["counts"]


def test_invalid_arguments_are_blocked_and_never_print_usage_to_stdout(plain):
    code, stdout, stderr = run_module(
        AUDIT_MODULE,
        ["--config", str(plain.config_path)],
        stdin_path=_request(plain),
        out_dir=plain.root / "badargs",
    )
    assert code == 3, (code, stdout[:400], stderr[:400])
    receipt = json.loads(stdout.decode("utf-8"))
    assert receipt["status"] == "blocked", receipt
    assert receipt.get("reason") == "invalid_argument", receipt
    assert b"usage:" not in stdout.lower()


def test_out_is_refused_when_it_names_a_directory(plain):
    request_path = _request(plain)
    target = plain.root / "out-dir"
    target.mkdir(exist_ok=True)
    code, stdout, stderr = run_module(
        AUDIT_MODULE,
        [
            "--config",
            str(plain.config_path),
            "--request",
            str(request_path),
            "--out",
            str(target),
        ],
        stdin_path=request_path,
        out_dir=plain.root / "out-dir-run",
    )
    assert code == 3, (code, stdout[:400], stderr[:400])
    receipt = json.loads(stdout.decode("utf-8"))
    assert receipt["status"] == "blocked", receipt
    assert receipt.get("reason") == "invalid_argument", receipt


def test_pretty_out_is_content_equivalent_to_the_single_line_receipt(plain):
    request_path = _request(plain)
    code, stdout, stderr = run_module(
        AUDIT_MODULE,
        ["--config", str(plain.config_path), "--request", str(request_path), "--pretty"],
        stdin_path=request_path,
        out_dir=plain.root / "pretty",
    )
    assert code == 0, (code, stdout[:400], stderr[:400])
    assert stdout.count(b"\n") == 1, stdout[:200]
    assert json.loads(stdout.decode("utf-8"))["schema_version"] == (
        "identity-audit-receipt/1"
    )


# --------------------------------------------------------------------------
# equivalence with the frozen export v2 CLI
# --------------------------------------------------------------------------


def test_manifest_matches_the_export_v2_cli_field_by_field(plain):
    request_path = write_json(
        plain.root / "export-request.json",
        {
            "schema_version": "2.0",
            "source_refs": [plain.ref_payload()],
            "evidence_spans": [],
        },
    )
    bundle = run_export_v2(plain.config_path, request_path, plain.root / "export-run")
    exported = bundle["manifests"][0]
    receipt = audit(plain)
    observed = sole_source(receipt)["checks"]["identity"]["observed"]
    assert observed["document_kind"] == exported["document_kind"]
    assert observed["canonical_entity_id"] == exported["canonical_entity_id"]
    assert observed["market"] == exported["market"]
    assert observed["security_id"] == exported["security_id"]
    assert observed["form_type"] == exported["form_type"]
    assert observed["title"] == exported["title"]
    assert observed["language"] == exported["language"]
    period = sole_source(receipt)["checks"]["period"]["observed"]
    assert period["fiscal_year"] == exported["fiscal_year"]
    assert period["fiscal_period"] == exported["fiscal_period"]
    assert period["period_end"] == exported["period_end"]
    assert period["published_date"] == exported["published_date"]
