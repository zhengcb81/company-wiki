"""Card section 5.5.3: unit tokens must stay grounded in the source text.

A quote may keep only unit tokens that literally appear inside it, and a quote
whose magnitude was converted (``120,000,000元`` rewritten as ``1.2亿元``) is a
``p4_consumer_unit_rescaled`` failure - section 6 requires both paths.
"""

from __future__ import annotations

from .support import checks, cwp, observations
from .support import constants as C


def _spans(p4_manifest: dict, item: dict) -> list[dict]:
    return [s for s in p4_manifest["spans"] if s["source_id"] == item["source_id"]]


def _spanned_source(p4_sources: list[dict]) -> dict:
    item = next((i for i in p4_sources if i["spans"]), None)
    assert item is not None, "the fixture set must contain a source with spans"
    return item


def test_p4_unit_tokens_are_substrings(
    p4_case, p4_sources, p4_manifest, p4_reads
) -> None:
    """A derived observation keeps every unit token inside its own quote."""
    case = p4_case()
    item = _spanned_source(p4_sources)
    read = p4_reads[item["relative_path"]]
    spans = _spans(p4_manifest, item)
    obs = observations.observation_from_manifest(
        consumer="ff",
        manifest=cwp.manifest_for(p4_manifest["bundle"], item["source_id"]),
        receipt=read.receipt,
        spans=spans,
    )
    decoded = read.data.decode("utf-8")
    outcomes = checks.check_unit_grounding(
        decoded_text=decoded, cwp_spans=spans, quotes=obs["quotes"],
    )
    failing = [o.name for o in outcomes if not o.ok]
    case.check("unit_tokens_grounded", "fail" if failing else "pass",
               {"failing": failing})
    assert not failing, f"unit grounding checks failed -> {failing}"
    assert obs["quotes"], "the spanned fixture must yield at least one quote"
    case.settle("pass")


def test_p4_quote_missing_unit_token_fails(
    p4_case, p4_sources, p4_manifest, p4_reads
) -> None:
    """Dropping a token the CWP span carries is a rescale, not a simplification."""
    case = p4_case()
    item = _spanned_source(p4_sources)
    read = p4_reads[item["relative_path"]]
    spans = _spans(p4_manifest, item)
    base = observations.observation_from_manifest(
        consumer="ff",
        manifest=cwp.manifest_for(p4_manifest["bundle"], item["source_id"]),
        receipt=read.receipt,
        spans=spans,
    )
    obs = observations.mutate_drop_unit_token(base, index=0)
    assert obs["quotes"][0]["unit_tokens"] != base["quotes"][0]["unit_tokens"], (
        "the mutation must actually drop a unit token before the check runs"
    )

    outcomes = checks.check_unit_grounding(
        decoded_text=read.data.decode("utf-8"), cwp_spans=spans, quotes=obs["quotes"],
    )
    failing = {o.name: o for o in outcomes if not o.ok}
    assert "quote[0]_unit_tokens_preserved" in failing, (
        "a dropped unit token must fail quote[0]_unit_tokens_preserved; "
        f"observed {sorted(failing)}"
    )
    assert failing["quote[0]_unit_tokens_preserved"].code == C.CODE_UNIT_RESCALED, (
        f"expected {C.CODE_UNIT_RESCALED}; "
        f"got {failing['quote[0]_unit_tokens_preserved'].code}"
    )
    case.check("missing_unit_token_detected", "pass", {
        "code": C.CODE_UNIT_RESCALED,
        "lost": failing["quote[0]_unit_tokens_preserved"].detail["lost_tokens"],
    })
    case.settle("pass")


def test_p4_quote_rescaled_fails(
    p4_case, p4_sources, p4_manifest, p4_reads
) -> None:
    """A converted magnitude must fail: the text no longer exists in the source."""
    case = p4_case()
    item = _spanned_source(p4_sources)
    read = p4_reads[item["relative_path"]]
    spans = _spans(p4_manifest, item)
    base = observations.observation_from_manifest(
        consumer="ff",
        manifest=cwp.manifest_for(p4_manifest["bundle"], item["source_id"]),
        receipt=read.receipt,
        spans=spans,
    )
    obs = observations.mutate_rescale_quote(base, index=0)
    assert obs["quotes"][0]["text"] == "1.2亿元", (
        f"the rescale mutation must produce 1.2亿元; got {obs['quotes'][0]['text']!r}"
    )

    outcomes = checks.check_unit_grounding(
        decoded_text=read.data.decode("utf-8"), cwp_spans=spans, quotes=obs["quotes"],
    )
    failing = {o.name: o for o in outcomes if not o.ok}
    assert "quote[0]_text_present_in_source" in failing, (
        "a converted quote must fail quote[0]_text_present_in_source; "
        f"observed {sorted(failing)}"
    )
    assert failing["quote[0]_text_present_in_source"].code == C.CODE_UNIT_RESCALED, (
        f"expected {C.CODE_UNIT_RESCALED}; "
        f"got {failing['quote[0]_text_present_in_source'].code}"
    )
    case.check("rescaled_quote_detected", "pass", {
        "code": C.CODE_UNIT_RESCALED,
        "quote": obs["quotes"][0]["text"],
    })
    case.settle("pass")
