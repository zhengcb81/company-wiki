"""C-node: replay over a read-only snapshot of the real catalog.

The card asks for an independent snapshot replay: build an explicit scope/candidate
inventory from the catalog that is actually installed in this tree, then run the
relevant/irrelevant change matrix against it for real, and leave a small receipt.

What this node proves and what it does not:

* It proves the component's *identity* and *difference* behaviour against real catalog
  identities -- real component ids, real versions, real content and matcher digests -- and
  it proves a change confined to one source's decision domain does not invalidate an
  unrelated one.
* It does **not** prove production reuse. The ``0POST``/CAS/recovery ordering belongs to
  ROOT's B node, and a green ``compare`` here is not a certification of it. Nothing in
  this node reads a company original, calls a model, or writes outside the owned ledger.

The scope and candidate membership are synthetic: the catalog records *which* policies
exist and what they contain, but not which ones a particular source's router actually
inspected. That instrumentation is ROOT's. The boundary is recorded in the receipt.
"""

from __future__ import annotations

import copy
import json
import os
import pathlib

import pytest
from fixtures.document_understanding_decision_dependencies import catalog_snapshot as cs

from .wire_contract import (
    assert_comparison_shape,
    assert_frozen_shape,
    import_decision_module,
)


def _freeze(trace_value, **limits):
    frozen = import_decision_module().freeze_decision_dependencies(
        trace_value, limits=limits or None
    )
    assert_frozen_shape(frozen)
    return frozen


def _compare(frozen, current, **limits):
    result = import_decision_module().compare_decision_dependencies(
        frozen, current, limits=limits or None
    )
    assert_comparison_shape(result)
    return result


def _canonical(value) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)


@pytest.fixture(scope="module")
def replay():
    """Load the real catalog once, read-only, and build the replay inputs."""
    catalog, digest_before = cs.load_catalog()
    snapshot = cs.build_snapshot(catalog, digest_before)
    _, digest_after = cs.load_catalog()
    return {
        "catalog": catalog,
        "snapshot": snapshot,
        "digest_before": digest_before,
        "digest_after": digest_after,
    }


# --- 0. raw preservation and the snapshot boundary -------------------------------------


def test_the_real_catalog_is_read_only_and_unmodified(replay):
    assert replay["digest_before"] == replay["digest_after"], "the installed catalog moved"
    assert cs.CATALOG_PATH.is_file()


def test_the_snapshot_carries_real_catalog_identities(replay):
    snapshot = replay["snapshot"]
    assert snapshot["catalog_sha256"] == replay["digest_before"]
    assert snapshot["schema_version"] == "du-reading-catalog/1"
    assert len(snapshot["families"]) == 24
    assert len(snapshot["facets"]) == 14
    assert len(snapshot["bindings"]) == 15
    for item in snapshot["families"] + snapshot["facets"]:
        assert len(item["content_digest"]) == 64
        assert len(item["matcher_digest"]) == 64
        assert item["version"], item["component_id"]


def test_the_snapshot_stores_identity_not_policy_bodies(replay):
    """The snapshot is ids and digests; the policy text stays in the catalog."""
    payload = _canonical(replay["snapshot"])
    phrase = cs.distinctive_phrase(replay["catalog"])
    assert phrase not in payload
    assert "reading_questions" not in payload
    assert "aliases" not in payload


# --- 1. a source-local domain freezes complete ------------------------------------------


def test_a_source_local_decision_domain_freezes_complete(replay):
    frozen = _freeze(cs.source_domain(replay["snapshot"], profile_id="cn_annual"))
    assert frozen["status"] == "complete", frozen["diagnostics"]
    assert frozen["scopes"]
    assert frozen["components"]
    assert frozen["candidates"]
    assert frozen["decision_digest"]


def test_the_manifest_holds_no_policy_text_only_identity(replay):
    domain = cs.source_domain(replay["snapshot"], profile_id="cn_annual")
    frozen = _freeze(domain)
    payload = _canonical(frozen)
    phrase = cs.distinctive_phrase(replay["catalog"])
    assert phrase not in payload, "a policy body leaked into the manifest"
    for row in domain["components"]:
        assert row["content_digest"] in payload, row["component_id"]
        assert row["matcher_digest"] in payload, row["component_id"]
        assert row["component_id"] in payload, row["component_id"]


# --- 2. relevant changes move the decision ----------------------------------------------


def _component_mutate(snapshot, component_id, *, field, value):
    def mutate(trace_value):
        rows = [
            {**row, field: value} if row["component_id"] == component_id else row
            for row in trace_value["components"]
        ]
        trace_value["components"] = rows
        return trace_value

    return mutate


def test_a_policy_content_edit_in_this_domain_changes_the_decision(replay):
    snapshot = replay["snapshot"]
    domain = cs.source_domain(snapshot, profile_id="cn_annual")
    target = next(row["component_id"] for row in domain["components"]
                  if row["component_id"].startswith("family:"))
    mutated = _component_mutate(snapshot, target, field="content_digest", value="0" * 64)(
        copy.deepcopy(domain)
    )
    result = _compare(_freeze(domain), mutated)
    assert result["status"] == "changed"
    assert result["changed_component_ids"] == [target]


def test_a_matcher_signal_edit_in_this_domain_changes_the_decision(replay):
    snapshot = replay["snapshot"]
    domain = cs.source_domain(snapshot, profile_id="cn_annual")
    target = next(row["component_id"] for row in domain["components"]
                  if row["component_id"].startswith("facet:"))
    mutated = _component_mutate(snapshot, target, field="matcher_digest", value="1" * 64)(
        copy.deepcopy(domain)
    )
    result = _compare(_freeze(domain), mutated)
    assert result["status"] == "changed"
    assert result["changed_component_ids"] == [target]


def test_a_losing_candidate_its_own_membership_edit_changes_the_decision(replay):
    """A candidate that never won is still part of the decision."""
    snapshot = replay["snapshot"]
    domain = cs.source_domain(snapshot, profile_id="cn_annual")
    losers = [row["candidate_id"] for row in domain["candidates"] if not row["eligible"]]
    assert losers, "the replay must include losing candidates"
    loser = losers[0]
    mutated = copy.deepcopy(domain)
    for row in mutated["candidates"]:
        if row["candidate_id"] == loser:
            row["eligible"] = True
    result = _compare(_freeze(domain), mutated)
    assert result["status"] == "changed"
    codes = {item["code"] for item in result["diagnostics"]}
    assert "CANDIDATE_MEMBERSHIP_CHANGED" in codes


def test_a_losing_candidate_component_edit_changes_the_decision(replay):
    snapshot = replay["snapshot"]
    domain = cs.source_domain(snapshot, profile_id="cn_annual")
    losers = [row for row in domain["candidates"] if not row["eligible"]]
    assert losers, "the replay must include losing candidates"
    loser = losers[0]
    assert loser["component_ids"], loser["candidate_id"]
    mutated = copy.deepcopy(domain)
    for row in mutated["candidates"]:
        if row["candidate_id"] == loser["candidate_id"]:
            dropped = row["component_ids"][-1]
            row["component_ids"] = [cid for cid in row["component_ids"] if cid != dropped]
    assert len(mutated["candidates"]) == len(domain["candidates"])
    result = _compare(_freeze(domain), mutated)
    assert result["status"] == "changed"
    codes = {item["code"] for item in result["diagnostics"]}
    assert "CANDIDATE_MEMBERSHIP_CHANGED" in codes


def test_a_child_scope_edit_changes_the_decision(replay):
    snapshot = replay["snapshot"]
    domain = cs.source_domain(snapshot, profile_id="cn_annual", include_child_scope=True)
    child = next(row["scope_id"] for row in domain["scopes"] if row["purpose"] == "business_review")
    mutated = copy.deepcopy(domain)
    mutated["scopes"] = [
        {**row, "purpose": "project_review"} if row["scope_id"] == child else row
        for row in mutated["scopes"]
    ]
    result = _compare(_freeze(domain), mutated)
    assert result["status"] == "changed"
    codes = {item["code"] for item in result["diagnostics"]}
    assert "SCOPE_CHANGED" in codes


def test_an_algorithm_version_edit_changes_the_decision(replay):
    snapshot = replay["snapshot"]
    domain = cs.source_domain(snapshot, profile_id="cn_annual")
    mutated = copy.deepcopy(domain)
    mutated["versions"] = {**mutated["versions"], "selector": "1.1.0"}
    assert _compare(_freeze(domain), mutated)["status"] == "changed"


def test_a_candidate_removed_from_the_inventory_changes_the_decision(replay):
    snapshot = replay["snapshot"]
    domain = cs.source_domain(snapshot, profile_id="cn_annual")
    dropped = domain["candidates"][0]["candidate_id"]
    mutated = copy.deepcopy(domain)
    mutated["candidates"] = [
        row for row in mutated["candidates"] if row["candidate_id"] != dropped
    ]
    result = _compare(_freeze(domain), mutated)
    assert result["status"] == "changed"
    assert result["removed_candidate_ids"] == [dropped]


# --- 3. irrelevant changes do NOT move this decision ------------------------------------


def test_an_unrelated_catalog_policy_edit_does_not_touch_this_domain(replay):
    """The card's core requirement: no whole-catalog invalidation.

    A policy that this source never had to inspect lives outside its decision domain. Its
    body is not in the trace, and its digest is not in the manifest, so editing it cannot
    change this decision.
    """
    snapshot = replay["snapshot"]
    domain = cs.source_domain(snapshot, profile_id="cn_annual")
    domain_ids = {row["component_id"] for row in domain["components"]}
    outsider = next(
        item for item in snapshot["families"] if item["component_id"] not in domain_ids
    )
    assert outsider["component_id"] not in domain_ids

    frozen = _freeze(domain)
    digest_before = frozen["decision_digest"]
    assert outsider["component_id"] not in _canonical(frozen)
    assert outsider["content_digest"] not in _canonical(frozen)

    # Simulate the edit on the catalog side and rebuild the *same* source's domain.
    edited = copy.deepcopy(snapshot)
    for item in edited["families"]:
        if item["component_id"] == outsider["component_id"]:
            item["content_digest"] = "2" * 64
            item["matcher_digest"] = "3" * 64
    rebuilt = cs.source_domain(edited, profile_id="cn_annual")

    assert _freeze(rebuilt)["decision_digest"] == digest_before
    assert _compare(frozen, rebuilt)["status"] == "same"


def test_a_whole_catalog_edit_far_away_leaves_the_domain_untouched(replay):
    snapshot = replay["snapshot"]
    domain = cs.source_domain(snapshot, profile_id="cn_annual")
    frozen = _freeze(domain)
    edited = copy.deepcopy(snapshot)
    for item in edited["families"] + edited["facets"]:
        if item["component_id"] not in {row["component_id"] for row in domain["components"]}:
            item["content_digest"] = "4" * 64
            item["matcher_digest"] = "5" * 64
            item["version"] = "9.9.9"
    rebuilt = cs.source_domain(edited, profile_id="cn_annual")
    assert _compare(frozen, rebuilt)["status"] == "same"


def test_two_different_sources_have_independent_identities(replay):
    """Editing one source's deciding policy must not move a different source's decision."""
    snapshot = replay["snapshot"]
    left = _freeze(cs.source_domain(snapshot, profile_id="cn_annual"))
    right = _freeze(cs.source_domain(snapshot, profile_id="sec_10k"))
    assert left["decision_digest"] != right["decision_digest"]

    edited = copy.deepcopy(snapshot)
    for item in edited["families"]:
        if item["component_id"] == "family:cn_annual_report":
            item["content_digest"] = "6" * 64
            item["matcher_digest"] = "7" * 64
    left_after = _freeze(cs.source_domain(edited, profile_id="cn_annual"))
    right_after = _freeze(cs.source_domain(edited, profile_id="sec_10k"))
    assert left_after["decision_digest"] != left["decision_digest"]
    assert right_after["decision_digest"] == right["decision_digest"]


def test_reordering_the_catalog_snapshot_is_not_a_change(replay):
    snapshot = replay["snapshot"]
    domain = cs.source_domain(snapshot, profile_id="cn_annual")
    shuffled = copy.deepcopy(snapshot)
    shuffled["families"] = list(reversed(shuffled["families"]))
    shuffled["facets"] = list(reversed(shuffled["facets"]))
    shuffled["bindings"] = list(reversed(shuffled["bindings"]))
    assert (
        _freeze(cs.source_domain(shuffled, profile_id="cn_annual"))["decision_digest"]
        == _freeze(domain)["decision_digest"]
    )


# --- 4. the whole catalog is not a legal dependency unit ---------------------------------


def test_the_whole_catalog_is_not_a_usable_decision_domain(replay):
    """Real finding, not a synthetic one: 78 derived scopes exceed the 64 default.

    A caller that hands this component the entire catalog as one domain cannot get a
    ``complete`` freeze out of it -- which is exactly why the dependency unit has to be
    the source-local decision domain, and why a whole-catalog hash would be both too
    strict (every unrelated edit invalidates everything) and too weak here (it stops).
    """
    whole = cs.whole_catalog_domain(replay["snapshot"])
    assert len(whole["scopes"]) > 64, len(whole["scopes"])
    frozen = _freeze(whole)
    assert frozen["status"] == "partial"
    codes = {item["code"] for item in frozen["diagnostics"]}
    assert "SCOPES_LIMIT_REACHED" in codes
    assert _compare(frozen, whole)["status"] != "same"


# --- 5. the small receipt ----------------------------------------------------------------


def test_the_replay_leaves_a_small_receipt(replay, tmp_path):
    """A receipt of the matrix, not a copy of the catalog or of any document text."""
    snapshot = replay["snapshot"]
    domain = cs.source_domain(snapshot, profile_id="cn_annual")
    frozen = _freeze(domain)

    outsider = next(
        item for item in snapshot["families"]
        if item["component_id"] not in {row["component_id"] for row in domain["components"]}
    )
    edited = copy.deepcopy(snapshot)
    for item in edited["families"]:
        if item["component_id"] == outsider["component_id"]:
            item["content_digest"] = "2" * 64
            item["matcher_digest"] = "3" * 64
    irrelevant = _compare(frozen, cs.source_domain(edited, profile_id="cn_annual"))["status"]

    target = next(row["component_id"] for row in domain["components"]
                  if row["component_id"].startswith("family:"))
    relevant = _compare(
        frozen,
        _component_mutate(snapshot, target, field="content_digest", value="0" * 64)(
            copy.deepcopy(domain)
        ),
    )

    whole = cs.whole_catalog_domain(snapshot)
    whole_frozen = _freeze(whole)

    losers = [row for row in domain["candidates"] if not row["eligible"]]
    assert losers, "the receipt must cover a losing participant"
    loser_mutated = copy.deepcopy(domain)
    for row in loser_mutated["candidates"]:
        if row["candidate_id"] == losers[0]["candidate_id"]:
            row["eligible"] = True
    losing = _compare(frozen, loser_mutated)

    matrix = {
        "relevant_policy_content_edit": relevant["status"],
        "relevant_component_ids": relevant["changed_component_ids"],
        "losing_participant_membership_edit": losing["status"],
        "losing_participant_ids": [losers[0]["candidate_id"]],
        "irrelevant_out_of_domain_edit": irrelevant,
        "array_order_irrelevant": _compare(frozen, _freeze(_shuffled(domain)))["status"],
        "whole_catalog_domain": whole_frozen["status"],
        "whole_catalog_scope_count": len(whole["scopes"]),
        "whole_catalog_component_count": len(whole["components"]),
        "whole_catalog_diagnostic_codes": sorted(
            {item["code"] for item in whole_frozen["diagnostics"]}
        ),
    }
    receipt = {
        "receipt_schema": "du3-dependencies-c-receipt/1",
        "lane": "dependencies",
        "certifies_production_reuse": False,
        "limits_used": "frozen DU3/1 defaults: 64 scopes / 512 components / 4096 candidates / "
                       "2 MiB input / 200000 work units",
        "catalog_snapshot": {
            "catalog_file": snapshot["catalog_file"],
            "catalog_sha256": snapshot["catalog_sha256"],
            "schema_version": snapshot["schema_version"],
            "families": len(snapshot["families"]),
            "facets": len(snapshot["facets"]),
            "bindings": len(snapshot["bindings"]),
        },
        "boundary": {
            "real": [
                "installed reading_catalog.json identities: component id, version, "
                "content digest, matcher digest, applies-to tuples",
            ],
            "synthetic": [
                "the decision scope ids, the inspected-component set and the candidate "
                "membership are constructed here: the catalog does not record which "
                "policies a given source's router actually inspected",
            ],
            "not_certified": [
                "production 0POST/CAS reuse and recovery belong to ROOT's B node; a green "
                "compare here is not a certification of them",
            ],
        },
        "source_local_domain": {
            "profile_id": "cn_annual",
            "scopes": len(domain["scopes"]),
            "components": len(domain["components"]),
            "candidates": len(domain["candidates"]),
            "status": frozen["status"],
            "decision_digest": frozen["decision_digest"],
        },
        "matrix": matrix,
        "catalog_unchanged_during_replay": replay["digest_before"] == replay["digest_after"],
    }
    out = os.environ.get("DU3_DEP_RECEIPT") or str(tmp_path / "c_replay_receipt.json")
    with open(out, "w", encoding="utf-8") as handle:
        json.dump(receipt, handle, ensure_ascii=False, sort_keys=True, indent=1)
    print("DU3-DEP-RECEIPT " + json.dumps({"path": out, "matrix": matrix}, sort_keys=True))

    assert matrix["relevant_policy_content_edit"] == "changed"
    assert matrix["losing_participant_membership_edit"] == "changed"
    assert matrix["irrelevant_out_of_domain_edit"] == "same"
    assert matrix["array_order_irrelevant"] == "same"
    assert matrix["whole_catalog_domain"] == "partial"
    assert matrix["whole_catalog_scope_count"] > 64
    assert receipt["catalog_unchanged_during_replay"] is True
    assert receipt["certifies_production_reuse"] is False


def _shuffled(domain):
    shuffled = copy.deepcopy(domain)
    shuffled["scopes"] = list(reversed(shuffled["scopes"]))
    shuffled["components"] = list(reversed(shuffled["components"]))
    shuffled["candidates"] = list(reversed(shuffled["candidates"]))
    return shuffled


def test_the_component_never_certifies_production_reuse():
    """Explicitly out of scope, per the card: ROOT owns 0POST/CAS/recovery."""
    package = pathlib.Path(import_decision_module().__file__).resolve().parent
    sources = sorted(package.glob("*.py"))
    assert sources
    for source in sources:
        text = source.read_text(encoding="utf-8")
        for forbidden in ("CACHE_HIT", "cache_hit", "0POST", "post_count", "reuse_allowed",
                          "reuse_granted", "may_reuse"):
            assert forbidden not in text, f"{source.name} claims {forbidden}"
