"""Card section 5.5.4: an unknown upstream availability stays unknown.

When the read receipt carries ``availability_evidence: null`` the consumer must
report ``source_availability_unknown`` with a null evidence block.  Reporting
``observed`` instead is the loss P4 exists to catch (section 6).
"""

from __future__ import annotations

from .support import checks, cwp, observations
from .support import constants as C


def _spans(p4_manifest: dict, item: dict) -> list[dict]:
    return [s for s in p4_manifest["spans"] if s["source_id"] == item["source_id"]]


def test_p4_unknown_availability_preserved(
    p4_case, p4_sources, p4_manifest, p4_reads
) -> None:
    """A null upstream evidence is mirrored as source_availability_unknown."""
    case = p4_case()
    item = p4_sources[0]
    read = p4_reads[item["relative_path"]]
    evidence = read.receipt.get("availability_evidence")
    assert evidence is None, (
        "the synthetic sidecar fixture must carry no availability evidence; "
        f"got {evidence!r}"
    )
    obs = observations.observation_from_manifest(
        consumer="ff",
        manifest=cwp.manifest_for(p4_manifest["bundle"], item["source_id"]),
        receipt=read.receipt,
        spans=_spans(p4_manifest, item),
    )
    assert obs["availability"] == {
        "status": C.AVAILABILITY_UNKNOWN, "evidence": None,
    }, f"the derived availability must stay unknown; got {obs['availability']!r}"

    outcomes = checks.check_unknown_availability(
        cwp_availability_evidence=evidence, availability=obs["availability"],
    )
    failing = [o.name for o in outcomes if not o.ok]
    case.check("unknown_availability_preserved", "fail" if failing else "pass",
               {"failing": failing})
    assert not failing, f"availability checks failed -> {failing}"
    case.settle("pass")


def test_p4_observed_availability_fails(
    p4_case, p4_sources, p4_manifest, p4_reads
) -> None:
    """Claiming ``observed`` over a null upstream must fail, with the code."""
    case = p4_case()
    item = p4_sources[0]
    read = p4_reads[item["relative_path"]]
    base = observations.observation_from_manifest(
        consumer="ff",
        manifest=cwp.manifest_for(p4_manifest["bundle"], item["source_id"]),
        receipt=read.receipt,
        spans=_spans(p4_manifest, item),
    )
    obs = observations.mutate_availability_observed(base)
    assert obs["availability"]["status"] == C.AVAILABILITY_OBSERVED, (
        f"the mutation must flip the status to observed; got {obs['availability']!r}"
    )

    outcomes = checks.check_unknown_availability(
        cwp_availability_evidence=None, availability=obs["availability"],
    )
    failing = {o.name: o for o in outcomes if not o.ok}
    assert "unknown_preserved" in failing, (
        "an observed claim over a null upstream must fail unknown_preserved; "
        f"observed {sorted(failing)}"
    )
    assert "unknown_evidence_null" in failing, (
        "the fabricated evidence block must fail unknown_evidence_null; "
        f"observed {sorted(failing)}"
    )
    assert C.CODE_AVAILABILITY_LOST in {o.code for o in outcomes if not o.ok}, (
        f"the failures must carry {C.CODE_AVAILABILITY_LOST}"
    )
    case.check("fabricated_observed_detected", "pass", {
        "code": C.CODE_AVAILABILITY_LOST,
        "consumer_status": obs["availability"]["status"],
    })
    case.settle("pass")
