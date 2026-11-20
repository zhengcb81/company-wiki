"""One finite tick. The host owns durable idempotency, repairs and consumer evidence."""

from __future__ import annotations

from collections.abc import Callable
import subprocess
import time

from .observations import Batch, digest


Host = Callable[[str, dict], dict]


class Deferred(Exception):
    def __init__(self, status: str, step: str):
        self.status = status
        self.step = step
        super().__init__(status, step)


def _text(value: dict, key: str, step: str) -> str:
    item = value.get(key)
    if not isinstance(item, str) or not item.strip():
        raise Deferred("unverified", step)
    return item


def _perform(host: Host, owner: str, kind: str, identity: list, payload: dict, *, lookup_only=False) -> dict:
    key = digest([kind, owner, *identity])
    request = {"schema_version": "feedback-action/1", "action_id": key, "owner": owner,
               "kind": kind, "payload": payload, "request_digest": digest([owner, kind, key, payload])}
    for method in ("lookup", "submit"):
        try:
            reply = host(owner, {**request, "method": method})
        except (OSError, subprocess.SubprocessError, ValueError, RecursionError):
            raise Deferred("unknown", kind) from None
        if (not isinstance(reply, dict) or reply.get("schema_version") != "feedback-action-result/1"
                or reply.get("action_id") != key or reply.get("request_digest") != request["request_digest"]):
            raise Deferred("unverified", kind)
        state = reply.get("state")
        if state == "absent" and method == "lookup":
            if lookup_only:
                raise Deferred("unknown", kind)
            continue
        if state == "done" and isinstance(reply.get("result"), dict):
            return reply["result"]
        if state in ("unknown", "pending", "failed"):
            raise Deferred(state, kind)
        raise Deferred("unverified", kind)
    raise AssertionError("submit must return an observed state")


def _triage(key: str, row: dict, host: Host) -> tuple[str, dict]:
    owner = row["owner"]
    visited = set()
    while owner not in visited:
        visited.add(owner)
        triage = _perform(host, owner, "triage", [key], {"occurrence_id": key, "observation": row})
        if triage.get("decision") != "refer":
            return owner, triage
        owner = _text(triage, "next_owner", "triage")
    raise Deferred("unverified", "triage_referral_cycle")


def _reconcile(key: str, row: dict, host: Host, observation: dict) -> dict:
    receipt = _perform(host, row["origin_owner"], "reconcile", [key], observation, lookup_only=True)
    state, original, cost = (receipt.get(k) for k in ("status", "job_status", "cost_state"))
    if row.get("evidence_ref") is not None and receipt.get("evidence_ref") != row["evidence_ref"]:
        raise Deferred("unverified", "reconcile")
    if original in ("succeeded", "failed", "cancelled", "interrupted", "unconfirmed"):
        known = state == "known" and cost in ("known", "not_applicable") and original != "unconfirmed"
        if known or (state == "cost_unknown" and cost == "unknown"):
            return {"status": "reconciled" if state == "known" else "unknown", "step": "reconcile",
                    "evidence_ref": _text(receipt, "evidence_ref", "reconcile"), "job_status": original, "cost_state": cost}
    if state == "known":
        return {"status": "awaiting_observation", "evidence_ref": _text(receipt, "evidence_ref", "reconcile")}
    return {"status": "unknown", "step": "reconcile"}


def _gate_review(triage: dict) -> dict:
    review = triage.get("gate_review")
    if (isinstance(review, dict)
            and review.get("decision") in ("remove", "narrow", "retain", "needs_evidence")
            and all(isinstance(review.get(key), str) and review[key].strip() for key in ("reason", "evidence_ref"))):
        return {key: review[key] for key in ("decision", "reason", "evidence_ref")}
    return {}


def _advance_one(key: str, row: dict, host: Host, *, unfinished: bool) -> dict:
    observation = {"occurrence_id": key, "observation": row}
    bound = _perform(host, row["origin_owner"], "observe", [key], observation)
    if bound.get("recorded") is not True:
        raise Deferred("unverified", "observe")
    if unfinished or row["disposition"] == "unknown":
        return _reconcile(key, row, host, observation)
    expected = row["disposition"] == "expected"
    refusal = "refusal_code" in row
    if expected and not refusal:
        return {"status": "expected"}
    owner, triage = _triage(key, row, host)
    decision = triage.get("decision")
    review = _gate_review(triage)
    diagnostics = {"gate_review": review} if review else {}
    if refusal and not expected and review.get("decision", "needs_evidence") == "needs_evidence":
        return {"status": "needs_evidence", "step": "triage", **diagnostics}
    if decision in ("expected", "external", "needs_evidence"):
        return {"status": decision, "step": "triage", **diagnostics}
    if expected and review.get("decision") not in ("remove", "narrow"):
        # An expected refusal enters triage for review, even on a legacy port.
        # Its existing disposition holds until triage finds an actionable gate.
        return {"status": "expected", "step": "triage", **diagnostics}
    issue = _text(triage, "issue_ref", "triage")
    if decision == "repair":
        generation = _text(triage, "generation", "triage")
        repair = _perform(host, owner, "repair", [issue, generation], {"issue_ref": issue, "generation": generation})
        version = _text(repair, "fixed_version", "repair")
    elif decision == "fixed":
        version = _text(triage, "fixed_version", "triage")
    else:
        raise Deferred("unverified", "triage")
    scope = [key, owner, issue, version]
    original = row.get("original_occurrence_id", key)
    replay_input = {"issue_ref": issue, "issue_owner": owner, "fixed_version": version, "occurrence_id": key,
                    "original_occurrence_id": original, "observation": row, "acquisition": "reuse_only"}
    replay = _perform(host, row["origin_owner"], "replay", scope, replay_input)
    verdict = replay.get("verdict")
    if verdict == "unknown":
        raise Deferred("unknown", "replay")
    if verdict not in ("verified", "regressed") or replay.get("verified_version") != version:
        raise Deferred("unverified", "replay")
    evidence = _text(replay, "evidence_ref", "replay")
    report = {"occurrence_id": key, "original_occurrence_id": original, "origin_owner": row["origin_owner"], "issue_ref": issue,
              "fixed_version": version, "verdict": verdict, "evidence_ref": evidence}
    recorded = _perform(host, owner, "report", [*scope, verdict], report)
    if recorded.get("recorded") is not True:
        raise Deferred("unverified", "report")
    return {"status": verdict, "issue_ref": issue, "fixed_version": version, "evidence_ref": evidence, **diagnostics}


def advance(batch: Batch, host: Host, *, only: set[str] | None = None) -> dict:
    outcomes = []
    unfinished = batch.unfinished_occurrences()
    for key, row in batch.observations.items():
        if only is not None and key not in only:
            continue
        try:
            outcome = _advance_one(key, row, host, unfinished=key in unfinished)
        except Deferred as deferred:
            outcome = {"status": deferred.status, "step": deferred.step}
        outcomes.append({"occurrence_id": key, "disposition": row["disposition"], **outcome})
    return {"observations": outcomes, "diagnostics": batch.diagnostics}


def settle(batch: Batch, host: Host, wait_seconds: float = 0) -> dict:
    """Follow already-started actions to a finite deadline; never retry unknown outcomes."""
    deadline = time.monotonic() + wait_seconds
    result = advance(batch, host)
    while any(row["status"] == "pending" for row in result["observations"]):
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            break
        if remaining < 2:
            break
        time.sleep(2)
        pending = {row["occurrence_id"] for row in result["observations"] if row["status"] == "pending"}
        updates = advance(batch, host, only=pending)
        current = {row["occurrence_id"]: row for row in updates["observations"]}
        result["observations"] = [current.get(row["occurrence_id"], row) for row in result["observations"]]
    return result
