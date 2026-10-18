"""Card section 5.5.2: identity and period facts must mirror the manifest.

A consumer may never fill a field the upstream left ``null``, and may never
rewrite an identity value - including the silent ``security_id`` re-padding
that section 6 calls out.
"""

from __future__ import annotations

from .support import checks, cwp, observations
from .support import constants as C


def _observation(item: dict, bundle: dict, read, spans: list[dict]) -> dict:
    return observations.observation_from_manifest(
        consumer="ff",
        manifest=cwp.manifest_for(bundle, item["source_id"]),
        receipt=read.receipt,
        spans=spans,
    )


def _text_source(p4_sources: list[dict]) -> dict:
    item = next((i for i in p4_sources if i["mime_type"] == "text/plain"), None)
    assert item is not None, "the fixture set must contain a text/plain source"
    return item


def test_p4_identity_matches_manifest(
    p4_case, p4_sources, p4_manifest, p4_reads
) -> None:
    """A derived observation reproduces every manifest fact exactly."""
    case = p4_case()
    for item in p4_sources:
        read = p4_reads[item["relative_path"]]
        spans = _spans(p4_manifest, item)
        obs = _observation(item, p4_manifest["bundle"], read, spans)
        manifest = cwp.manifest_for(p4_manifest["bundle"], item["source_id"])
        outcomes = checks.check_identity_period(manifest=manifest, facts=obs["facts"])
        failing = [o.name for o in outcomes if not o.ok]
        case.check(f"identity::{item['relative_path']}",
                   "fail" if failing else "pass", {"failing": failing})
        assert not failing, (
            f"{item['relative_path']}: identity checks failed -> {failing}"
        )
    case.settle("pass")


def _spans(p4_manifest: dict, item: dict) -> list[dict]:
    return [s for s in p4_manifest["spans"] if s["source_id"] == item["source_id"]]


def test_p4_security_id_width_mismatch_fails(
    p4_case, p4_sources, p4_manifest, p4_reads
) -> None:
    """A zero-padded ``security_id`` is a rewrite, not a formatting choice."""
    case = p4_case()
    item = _text_source(p4_sources)
    read = p4_reads[item["relative_path"]]
    base = _observation(item, p4_manifest["bundle"], read, _spans(p4_manifest, item))
    obs = observations.mutate_security_id_width(base, width=8)
    manifest = cwp.manifest_for(p4_manifest["bundle"], item["source_id"])

    outcomes = checks.check_identity_period(manifest=manifest, facts=obs["facts"])
    failing = {o.name: o for o in outcomes if not o.ok}
    assert "facts_values_match_manifest" in failing, (
        "a zero-padded security_id must fail facts_values_match_manifest; "
        f"observed {sorted(failing)}"
    )
    assert failing["facts_values_match_manifest"].code == C.CODE_FIELD_MISSING, (
        f"expected {C.CODE_FIELD_MISSING}; "
        f"got {failing['facts_values_match_manifest'].code}"
    )
    case.check("security_id_width_detected", "pass", {
        "code": C.CODE_FIELD_MISSING,
        "mismatched": failing["facts_values_match_manifest"].detail["mismatched_fields"],
        "upstream": manifest.get("security_id"),
        "consumer": obs["facts"].get("security_id"),
    })
    case.settle("pass")


def test_p4_published_date_filled_fails(
    p4_case, p4_sources, p4_manifest, p4_reads
) -> None:
    """A date the consumer invented where upstream is ``null`` must fail."""
    case = p4_case()
    item = _text_source(p4_sources)
    read = p4_reads[item["relative_path"]]
    base = _observation(item, p4_manifest["bundle"], read, _spans(p4_manifest, item))
    assert base["facts"]["published_date"] is None, (
        "the text fixture must carry a null published_date for this case; got "
        f"{base['facts']['published_date']!r}"
    )
    obs = observations.mutate_fill_published_date(base, "2026-03-01")
    manifest = cwp.manifest_for(p4_manifest["bundle"], item["source_id"])

    outcomes = checks.check_identity_period(manifest=manifest, facts=obs["facts"])
    failing = {o.name: o for o in outcomes if not o.ok}
    assert "published_date_unknown_preserved" in failing, (
        "filling a null published_date must fail published_date_unknown_preserved; "
        f"observed {sorted(failing)}"
    )
    assert "facts_unknown_not_filled" in failing, (
        "the same fill must also fail facts_unknown_not_filled; "
        f"observed {sorted(failing)}"
    )
    assert C.CODE_FIELD_MISSING in {o.code for o in outcomes if not o.ok}, (
        "the failures must carry the p4_consumer_field_missing code"
    )
    case.check("published_date_fill_detected", "pass", {
        "code": C.CODE_FIELD_MISSING,
        "consumer": obs["facts"]["published_date"],
        "upstream": manifest.get("published_date"),
    })
    case.settle("pass")
