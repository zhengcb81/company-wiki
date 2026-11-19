"""Publish only assertions that the native Phase C receipt actually exercised."""

import argparse
import json
import os
from pathlib import Path
import tempfile


def _bool_outcome(value):
    if value is True:
        return "zero-post"
    if value is False:
        return "extra-post"
    return "unknown"


def observations(receipt, env, version):
    # The loopback runner also exercises deliberate refusals separately. Only the
    # normal scenario has these positive recovery expectations.
    normal = receipt.get("normal", receipt) if isinstance(receipt, dict) else None
    if not isinstance(normal, dict) or not isinstance(normal.get("states"), list):
        return
    for state in normal["states"]:
        if not isinstance(state, dict) or not isinstance(state.get("run_id"), str) or not state["run_id"]:
            continue
        native_id = state["run_id"]
        replay = state.get("public_replay")
        marker = replay.get("replay_status") if isinstance(replay, dict) else None
        if (not marker and state.get("public_read_exit") == 2 and isinstance(replay, dict)
                and replay.get("schema_version") == "narrative-read-receipt/1"
                and isinstance(replay.get("reason"), str) and replay["reason"]):
            marker = "read-refused"
        checks = [
            ("locator-replay", "verified", marker if isinstance(marker, str) and marker.strip() else "unknown"),
            ("same-run-cache", "zero-post", _bool_outcome(state.get("same_run_zero_POST"))),
            ("cross-run-cache", "zero-post", _bool_outcome(state.get("cross_run_zero_POST"))),
        ]
        refusal_codes = {"locator-replay": state.get("refusal_code")}
        for kind in ("same_run", "cross_run"):
            binding = state.get(kind + "_cache_binding")
            if isinstance(binding, str) and binding:
                checks.append((kind.replace("_", "-") + "-cache-binding", "verified", binding))
        cache_read = state.get("cache_public_observation")
        if isinstance(cache_read, dict):
            cache_receipt = cache_read.get("public_replay")
            outcome = cache_receipt.get("replay_status") if isinstance(cache_receipt, dict) else None
            if not outcome and cache_read.get("public_read_exit") == 2 and isinstance(cache_receipt, dict) and cache_receipt.get("reason"):
                outcome = "read-refused"
            checks.append(("cache-locator-replay", "verified", outcome or "unknown"))
            refusal_codes["cache-locator-replay"] = cache_read.get("refusal_code")
        for check, expected, actual in checks:
            row = {"schema_version": "feedback-observation/1", "owner": "company-wiki",
                   "run_id": env.get("RESEARCH_FEEDBACK_RUN_ID") or native_id,
                   "attempt_id": env.get("RESEARCH_FEEDBACK_ATTEMPT_ID") or native_id, "step_id": native_id,
                   "check_id": check, "expected": expected, "actual": actual,
                   "evidence_ref": f"phase-c/{native_id}/{check}"}
            if version:
                row["version"] = version
            if actual == "unknown":
                row["disposition"] = "unknown"
            code = refusal_codes.get(check)
            if actual == "read-refused" and isinstance(code, str):
                row["refusal_code"] = code
            yield row


def resolve(receipt, reference, version):
    """Resolve a public occurrence reference in the native receipt supplied by its owner."""
    rows = [r for r in observations(receipt, {}, version) if r["evidence_ref"] == reference]
    if len(rows) != 1:
        return {"status": "reference_unresolved"}
    row = rows[0]
    normal = receipt.get("normal", receipt)
    state = next(s for s in normal["states"] if isinstance(s, dict) and s.get("run_id") == row["step_id"])
    artifact = state.get("artifact_ref")
    return {"status": "resolved", "observation": row, "mode": receipt.get("mode"),
            "selector_version": state.get("version"),
            "artifact_sha256": artifact.get("artifact_sha256") if isinstance(artifact, dict) else None}


def publish(receipt, env, version):
    destination = env.get("RESEARCH_FEEDBACK_OUT")
    if not destination:
        return None
    path = Path(destination)
    data = b"".join((json.dumps(r, ensure_ascii=True, sort_keys=True) + "\n").encode("ascii")
                    for r in observations(receipt, env, version))
    if not data:
        return {"status": "no_native_states"}
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(dir=path.parent, delete=False) as output:
            temporary = Path(output.name)
            output.write(data)
        try:
            # Publish a complete file without overwriting an unrelated existing
            # destination or racing a second import of the same native receipt.
            if os.name == "nt":
                # Windows rename refuses existing targets. Hard links are not
                # available in every sandbox or on every Windows filesystem.
                os.rename(temporary, path)
                temporary = None
            else:
                os.link(temporary, path)
        except FileExistsError:
            if path.stat().st_size == len(data) and path.read_bytes() == data:
                result = {"status": "reused"}
            else:
                result = {"status": "output_conflict"}
        else:
            result = {"status": "published"}
    except OSError as exc:
        result = {"status": "write_failed", "error_type": type(exc).__name__}
    if temporary is not None:
        try:
            temporary.unlink(missing_ok=True)
        except OSError as exc:
            result["temporary_cleanup_error"] = type(exc).__name__
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description="Offline projection or resolution from a recorded Phase C outcome")
    parser.add_argument("receipt", type=Path)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--out", type=Path)
    group.add_argument("--ref")
    args = parser.parse_args(argv)
    receipt = json.loads(args.receipt.read_text(encoding="utf-8"))
    fingerprint = args.receipt.parent / "harness-fingerprint.json"
    version = json.loads(fingerprint.read_text(encoding="utf-8")).get("repository_head") if fingerprint.is_file() else None
    if args.ref is not None:
        result = resolve(receipt, args.ref, version)
    else:
        result = publish(receipt, {**os.environ, "RESEARCH_FEEDBACK_OUT": str(args.out)}, version)
    print(json.dumps(result, ensure_ascii=True))
    return 0 if result["status"] in {"reused", "published", "resolved"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
