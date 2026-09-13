"""R4 phase-B step B06 acceptance: separate "locally readable" from "formally
captured".

Design §B06 (with decision S-13 and the F-B01-7 acceptance item):

* the response envelope carries a **qualification** label - ``verified_input``
  (identity + period + source complete) vs ``preview`` (locally readable,
  provenance gaps: no URL, no capture trace) vs **``blocked``** (identity or
  period unknown, or a real field conflict);
* the response-level ``blocked`` lives HERE and not in ``outcome``: the
  consumer's own validator (filing-fetch ``validate_resolution_envelope``)
  requires ``outcome`` to be one of ITS eight values, which contain no
  ``blocked`` - putting it there would be an upstream error for filing-fetch;
* a preview licence is never inherited by a formal input, and a missing URL is
  never fabricated (no URL is invented, no network is touched);
* B06 only provides FACTS: the consumer's own permission gate
  (``revenue-forecast/scripts/company_wiki_source.py``) is not changed here.

Matrix items: L09, L10 (phase-B acceptance map, reverse-coverage
section; step B06 claims these, and the cases below are what exercises them).

Product code is NOT modified by this file (file-scope F10: new tests only).
"""

from __future__ import annotations

import hashlib
import json
import sys
from dataclasses import replace
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from company_wiki.source_catalog.models import RootSpec  # noqa: E402
from company_wiki.source_catalog.resolver import (  # noqa: E402
    QUALIFICATION_BLOCKED,
    QUALIFICATION_PREVIEW,
    QUALIFICATION_VERIFIED_INPUT,
    SourceRequest,
    SourceResolver,
    build_resolution_envelope,
)

BODY = b"%PDF-1.4 r4b06-qualification-payload"
DIGEST = hashlib.sha256(BODY).hexdigest()


def _sidecar(**overrides) -> dict:
    payload = {
        "schema_version": "1.0",
        "canonical_entity_id": "ent-acme",
        "display_name": "Acme",
        "market": "US",
        "security_id": "ACME",
        "source_title": "Acme 2025 Annual Report",
        "document_kind": "annual_report",
        "fiscal_year": 2025,
        "period_end": "2025-12-31",
        "filing_date": "2026-02-20",
        "form_type": "10-K",
        "provider": "sec",
        "provider_document_id": "doc-1",
        "source_url": "https://sec.gov/x/2025",
        "content_sha256": DIGEST,
        "retrieved_at": "2026-02-21T00:00:00Z",
        "collector_name": "sec_edgar",
        "collector_version": "1.0",
    }
    payload.update(overrides)
    return payload


def _write_copy(directory: Path, sidecar: dict, name: str = "2025.pdf") -> Path:
    directory.mkdir(parents=True, exist_ok=True)
    target = directory / name
    target.write_bytes(BODY)
    (directory / f"{name}.source.json").write_text(
        json.dumps(sidecar, ensure_ascii=False), encoding="utf-8"
    )
    return target


def _root(root_id: str, path: Path, kind: str, priority: int) -> RootSpec:
    return RootSpec(
        root_id,
        path,
        kind,
        priority=priority,
        adapter_id="company_raw_v1" if kind == "company_raw" else "sidecar_filing_v1",
        read_only=kind != "company_raw",
        reusable_for_filing=True,
        canonical_write_target="companies" if kind == "company_raw" else None,
    )


def _catalog(tmp_path: Path, roots: list[RootSpec]):
    from company_wiki.source_catalog import CatalogConfig, SourceCatalog

    catalog = SourceCatalog(
        CatalogConfig(
            project_root=tmp_path,
            catalog_dir=tmp_path / ".source_catalog",
            reusable_root_kinds=("company_raw", "directory"),
            roots=tuple(roots),
        )
    )
    catalog.scan()
    return catalog


def _request() -> SourceRequest:
    return SourceRequest(
        entity="Acme",
        market="US",
        security_id="ACME",
        document_kind="annual_report",
        form_type="10-K",
        fiscal_year=2025,
        provider="sec",
        provider_document_id="doc-1",
        as_of_date="2026-08-10",
        mode="exact",
    )


def _qualified(tmp_path: Path, sidecar: dict):
    """One company_raw copy, resolved, then qualified through the envelope."""
    root = tmp_path / "companies"
    _write_copy(root / "Acme" / "raw" / "financial_reports" / "annual", sidecar)
    catalog = _catalog(tmp_path, [_root("company_raw", root, "company_raw", 10)])
    resolution = SourceResolver(catalog).resolve(_request())
    assert resolution.matches, resolution.debug_trace
    envelope = build_resolution_envelope(
        resolution, store=catalog.store, project_root=tmp_path
    )
    assert envelope.qualification is not None, envelope.to_dict()
    return resolution.matches[0], envelope


# ---------------------------------------------------------------------------
# The three labels
# ---------------------------------------------------------------------------


def test_r4b06_complete_handle_is_verified_input(tmp_path):
    handle, envelope = _qualified(tmp_path, _sidecar())
    qualification = envelope.qualification
    assert qualification["label"] == QUALIFICATION_VERIFIED_INPUT, qualification
    assert qualification["gaps"] == [], qualification
    assert qualification["reason"] == "", qualification
    # the facts the label rests on really are present
    assert handle.entity_ids and handle.fiscal_year == 2025
    assert handle.https_url and handle.content_sha256 == DIGEST


def test_r4b06_missing_url_is_refused_before_any_preview_label(tmp_path):
    """A local copy without a capture URL never reaches the envelope today.

    `resolve` refuses every non-capture-ready handle with
    ``capture_incomplete`` (a deliberate cross-repo rule: offering such a handle
    as reusable deadlocks filing-fetch's download path).  So the design's
    ``preview`` case is a RULE here, not a reachable outcome - recorded as such
    (see also `..._preview_is_not_inherited_by_a_formal_input`)."""
    root = tmp_path / "companies"
    _write_copy(
        root / "Acme" / "raw" / "financial_reports" / "annual",
        _sidecar(source_url=None),
    )
    catalog = _catalog(tmp_path, [_root("company_raw", root, "company_raw", 10)])
    resolution = SourceResolver(catalog).resolve(_request())
    assert not resolution.matches, resolution.debug_trace
    assert any("capture_incomplete" in item for item in resolution.debug_trace), (
        resolution.debug_trace
    )
    envelope = build_resolution_envelope(
        resolution, store=catalog.store, project_root=tmp_path
    )
    assert envelope.qualification is None, envelope.to_dict()


def test_r4b06_url_gap_rule_is_preview_and_invents_nothing(tmp_path):
    """The preview RULE itself, on a real handle with the gap added: the gap is
    named, the label is preview (not verified_input), and no URL is invented."""
    handle, _ = _qualified(tmp_path, _sidecar())
    from company_wiki.source_catalog.resolver import (
        _qualification_gaps,
        _qualification_label,
    )

    with_gap = replace(handle, https_url=None, missing_capture_fields=("https_url",))
    gaps = _qualification_gaps(with_gap)
    label, reason = _qualification_label(gaps, "")
    assert "url_missing" in gaps, gaps
    assert label == QUALIFICATION_PREVIEW, (label, gaps)
    assert reason, reason
    assert with_gap.https_url is None  # nothing invented


def test_r4b06_missing_capture_trace_is_preview(tmp_path):
    handle, _ = _qualified(tmp_path, _sidecar())
    from company_wiki.source_catalog.resolver import (
        _qualification_gaps,
        _qualification_label,
    )

    with_gap = replace(handle, missing_capture_fields=("capture_trace",))
    gaps = _qualification_gaps(with_gap)
    label, _ = _qualification_label(gaps, "")
    assert "capture_log_missing" in gaps, gaps
    assert label == QUALIFICATION_PREVIEW, (label, gaps)


# ---------------------------------------------------------------------------
# What BLOCKS the formal contract (S-13: the response-level verdict)
# ---------------------------------------------------------------------------


def test_r4b06_unknown_identity_blocks_the_formal_contract(tmp_path):
    """Identity unknown => blocked, not preview.

    ``resolve`` matches BY identity, so a served handle always has entity ids;
    the rule is therefore exercised on a real handle whose identity facts are
    removed - the point is what the QUALIFICATION rule does with them."""
    handle, _ = _qualified(tmp_path, _sidecar())
    catalog_handle = replace(handle, entity_ids=())
    from company_wiki.source_catalog.resolver import (
        _qualification_gaps,
        _qualification_label,
    )

    gaps = _qualification_gaps(catalog_handle)
    label, reason = _qualification_label(gaps, "")
    assert "identity_missing" in gaps, gaps
    assert label == QUALIFICATION_BLOCKED, (label, gaps)
    assert reason, reason


def test_r4b06_unknown_period_blocks_the_formal_contract(tmp_path):
    """B-VR06-01: the PERIOD is a period fact, not a filing date.

    A `published_date` says when the filing was PUBLISHED, so a handle carrying
    only that is period-unknown and the formal contract is blocked - which is
    what the plan always said and what the first version of the code got wrong
    (it accepted the date as the period, which made `period_missing`
    unreachable).  `fiscal_period` is a period fact in its own right."""
    handle, _ = _qualified(tmp_path, _sidecar())
    from company_wiki.source_catalog.resolver import (
        _qualification_gaps,
        _qualification_label,
    )

    date_only = replace(handle, fiscal_year=None, published_date="2026-02-20")
    gaps = _qualification_gaps(date_only)
    assert "period_missing" in gaps, gaps
    assert _qualification_label(gaps, "")[0] == QUALIFICATION_BLOCKED, gaps

    period_only = replace(handle, fiscal_year=None, fiscal_period="H1")
    assert "period_missing" not in _qualification_gaps(period_only)

    assert "period_missing" not in _qualification_gaps(handle)


def test_r4b06_missing_source_identity_blocks_the_formal_contract(tmp_path):
    """No source id / no bytes hash: the copy cannot be a formal input (the
    design's preview case requires a local import hash)."""
    handle, _ = _qualified(tmp_path, _sidecar())
    from company_wiki.source_catalog.resolver import (
        _qualification_gaps,
        _qualification_label,
    )

    candidate = replace(handle, missing_capture_fields=("snapshot_sha256",))
    gaps = _qualification_gaps(candidate)
    label, reason = _qualification_label(gaps, "")
    assert "source_missing" in gaps, gaps
    assert label == QUALIFICATION_BLOCKED, (label, gaps)
    assert reason, reason


def test_r4b06_field_conflict_blocks_the_formal_contract(tmp_path):
    """S-13 wiring: a REAL metadata conflict (B05's reserved key) is the same
    fact the read side calls ``metadata_status="blocked"`` - the envelope must
    report it as a response-level ``blocked``, not as a weaker preview."""
    root = tmp_path / "companies"
    dropbox = tmp_path / "Dropbox" / "Stock"
    _write_copy(
        root / "Acme" / "raw" / "financial_reports" / "annual",
        _sidecar(source_title="Acme 2025 Annual Report"),
    )
    # EQUAL priorities on purpose: the scanner only merges captures whose root
    # priority is not lower than the stored one (scanner.py's branch), so a
    # numerically higher priority root would never reach the merge/provenance
    # path at all.
    catalog = _catalog(
        tmp_path,
        [_root("company_raw", root, "company_raw", 10),
         _root("dropbox_stock", dropbox, "directory", 10)],
    )
    # a second capture of the SAME bytes declaring a DIFFERENT title
    _write_copy(dropbox, _sidecar(source_title="Acme 2025 Annual Report (restated)"))
    catalog.scan()

    resolution = SourceResolver(catalog).resolve(_request())
    assert resolution.matches, resolution.debug_trace
    envelope = build_resolution_envelope(
        resolution, store=catalog.store, project_root=tmp_path
    )
    qualification = envelope.qualification
    assert qualification is not None, envelope.to_dict()
    assert qualification["label"] == QUALIFICATION_BLOCKED, qualification
    assert "title" in qualification["reason"], qualification


# ---------------------------------------------------------------------------
# The licence boundary and the honest default
# ---------------------------------------------------------------------------


def test_r4b06_preview_is_not_inherited_by_a_formal_input(tmp_path):
    """L10: the preview licence is not inheritable.

    The preview OUTCOME is refused by `resolve` today (see the case above), so
    the licence boundary is asserted where it can be observed: the label is a
    function of the handle's CURRENT facts, and completing them moves the label
    from preview to verified_input - the weaker label is never carried forward
    and never assumed by the stronger one."""
    handle, envelope = _qualified(tmp_path, _sidecar())
    assert envelope.qualification["label"] == QUALIFICATION_VERIFIED_INPUT, (
        envelope.qualification
    )

    from company_wiki.source_catalog.resolver import (
        _qualification_gaps,
        _qualification_label,
    )

    preview_handle = replace(handle, https_url=None, missing_capture_fields=("https_url",))
    label, _ = _qualification_label(_qualification_gaps(preview_handle), "")
    assert label == QUALIFICATION_PREVIEW, label
    label_after, gaps_after = _qualification_label(_qualification_gaps(handle), "")
    assert label_after == QUALIFICATION_VERIFIED_INPUT and gaps_after == "", (
        label_after,
        gaps_after,
    )
    assert label != label_after


def test_r4b06_an_unanswered_request_carries_no_qualification(tmp_path):
    """Nothing served, nothing qualified: the field stays None instead of
    guessing a label for a MISSING answer."""
    root = tmp_path / "companies"
    _write_copy(root / "Acme" / "raw" / "financial_reports" / "annual", _sidecar())
    catalog = _catalog(tmp_path, [_root("company_raw", root, "company_raw", 10)])
    other = SourceRequest(
        entity="Acme",
        market="US",
        security_id="ACME",
        document_kind="annual_report",
        fiscal_year=2019,  # no such version
        as_of_date="2026-08-10",
        mode="exact",
    )
    resolution = SourceResolver(catalog).resolve(other)
    assert not resolution.matches, resolution.debug_trace
    envelope = build_resolution_envelope(
        resolution, store=catalog.store, project_root=tmp_path
    )
    assert envelope.qualification is None, envelope.to_dict()


def test_r4b06_malformed_shared_metadata_is_not_a_crash(tmp_path):
    """The `metadata_json` column is SHARED: several modules write it, so its
    shape cannot be assumed.  A non-object payload (or a non-object reserved
    key) means "no readable conflict evidence" - the envelope still builds."""
    from company_wiki.source_catalog.resolver import _metadata_conflict_reason

    class _Store:
        def __init__(self, payload: str):
            self._payload = payload

        def fetchone(self, sql, params=()):  # noqa: ANN001
            return {"metadata_json": self._payload}

    for payload in (
        "[]",
        '"a string"',
        "null",
        "{not json",
        '{"r4_provenance": "not an object"}',
        '{"r4_provenance": {"fields": []}}',
        '{"r4_provenance": {"fields": {"title": "not a record"}}}',
    ):
        assert _metadata_conflict_reason(_Store(payload), "doc-1") == "", payload

    real = (
        '{"r4_provenance": {"schema_version": "1.0", "fields": '
        '{"title": {"value": "x", "conflicts": [{"value": "y"}]}}}}'
    )
    reason = _metadata_conflict_reason(_Store(real), "doc-1")
    assert "title" in reason, reason


def test_r4b06_an_envelope_labels_a_handle_that_carries_gaps(tmp_path):
    """B-VR06-02/03 (kills the reviewer's surviving mutant M6): the GAP RULE must
    actually reach the envelope.  Nothing in the pipeline-produced fixtures
    carries a URL/capture gap (such a handle is refused by `capture_incomplete`),
    so the wiring is exercised with a hand-built resolution whose handle carries
    one - an envelope that ignores the rule answers `verified_input` here."""
    from dataclasses import replace as dataclass_replace

    from company_wiki.source_catalog.resolver import (
        ResolutionResult,
        ResolutionStatus,
    )

    _, envelope = _qualified(tmp_path, _sidecar())
    assert envelope.qualification["label"] == QUALIFICATION_VERIFIED_INPUT

    handle, _ = _qualified(tmp_path, _sidecar())
    gapped = dataclass_replace(handle, https_url=None, missing_capture_fields=("https_url",))
    resolution = ResolutionResult(
        schema_version="1.0",
        request_id="urn:test:gapped",
        status=ResolutionStatus.REUSED_EXACT,
        reason="r",
        download_required=False,
        download_allowed=False,
        matches=(gapped,),
        debug_trace=(),
    )
    built = build_resolution_envelope(resolution)
    qualification = built.qualification
    assert qualification is not None, built.to_dict()
    assert qualification["label"] == QUALIFICATION_PREVIEW, qualification
    assert "url_missing" in qualification["gaps"], qualification
    # and the conflict check says whether it could run at all
    assert qualification["conflict_check"] == "not_available", qualification


def test_r4b06_the_conflict_check_reports_that_it_ran(tmp_path):
    """B-VR06-02: with a store the envelope consulted B05's reserved key; the
    qualification says so instead of implying the check happened either way."""
    _, envelope = _qualified(tmp_path, _sidecar())
    assert envelope.qualification["conflict_check"] == "store", envelope.qualification


def test_r4b06_a_served_document_without_a_period_is_blocked(tmp_path):
    """B-VR06-01 end to end: `latest_as_of` really serves a document whose source
    carries no fiscal year (measured), so the period gap is reachable through the
    pipeline - not only through the rule."""
    from company_wiki.source_catalog.resolver import SourceRequest

    root = tmp_path / "companies"
    # the title must not carry a year either: the resolver DERIVES a fiscal year
    # from the title/file name, so "Acme 2025 Report" would yield fiscal_year=2025
    # and the case would quietly stop testing the gap
    _write_copy(root / "Acme" / "raw" / "financial_reports" / "annual",
                _sidecar(fiscal_year=None, source_title="Acme report"))
    catalog = _catalog(tmp_path, [_root("company_raw", root, "company_raw", 10)])
    resolution = SourceResolver(catalog).resolve(SourceRequest(
        entity="Acme", market="US", security_id="ACME", document_kind="annual_report",
        provider="sec", provider_document_id="doc-1", as_of_date="2026-08-10",
        mode="latest_as_of"))
    assert resolution.matches, resolution.debug_trace
    assert resolution.matches[0].fiscal_year is None, resolution.matches[0].fiscal_year
    envelope = build_resolution_envelope(resolution, store=catalog.store,
                                         project_root=tmp_path)
    qualification = envelope.qualification
    assert qualification["label"] == QUALIFICATION_BLOCKED, qualification
    assert "period_missing" in qualification["gaps"], qualification


def test_r4b06_qualification_is_additive_for_pre_b06_consumers(tmp_path):
    """The consumer's validator tolerates unknown keys and keeps the schema
    version, so the new field must not move either."""
    _, envelope = _qualified(tmp_path, _sidecar())
    payload = envelope.to_dict()
    assert payload["envelope_schema_version"] == "1.0", payload["envelope_schema_version"]
    assert "qualification" in payload
    assert set(payload["qualification"]) == {"label", "gaps", "reason", "conflict_check"}
