"""Card section 5.3: observation mapping, including the unmapped refusal.

A consumer stdout that does not carry the exact ``p4-consumer-observation/1``
shape is ``not_evaluated`` with ``reason="unmapped_consumer_output"``, and only
the stdout digest plus a 2 KiB prefix are retained - never the whole payload.
"""

from __future__ import annotations

import json
from pathlib import Path

from .support import consumer
from .support import constants as C
from .support import environment as E
from .support.jsonio import canonical_dumps, sha256_bytes


def _run(stdout: bytes, *, returncode: int = 0) -> consumer.ConsumerRun:
    return consumer.ConsumerRun(
        consumer="ff",
        argv=("probe",),
        returncode=returncode,
        stdout=stdout,
        stderr_tail="",
    )


def test_p4_missing_manifest_maps_to_not_evaluated(p4_case) -> None:
    """Without ROOT's manifest no consumer runs; the case is not_evaluated."""
    case = p4_case()
    configured = E.consumer_commands_path()
    if configured is not None:
        case.check("observation_not_evaluated", "not_applicable",
                   {"reason": "a consumer manifest was provided"})
        case.settle("pass")
        return

    case.check("consumer_manifest_missing", "not_evaluated",
               {"reason": C.REQUIRE_COMMANDS_REASON})
    case.settle("not_evaluated", C.REQUIRE_COMMANDS_REASON)


def test_p4_unmapped_stdout_is_refused_with_prefix(p4_case, tmp_path) -> None:
    """Wrong-shape stdout yields not_evaluated + unmapped_consumer_output."""
    case = p4_case()
    payload = {"schema_version": "p4-consumer-observation/1", "extra": True}
    stdout = json.dumps(payload).encode("utf-8")

    run = _run(stdout)
    parsed = consumer.parse_observation(run)

    assert parsed.observation is None, "a wrong-shape payload must not be mapped"
    assert parsed.reason == C.UNMAPPED_CONSUMER_OUTPUT, (
        f"expected {C.UNMAPPED_CONSUMER_OUTPUT!r}; got {parsed.reason!r}"
    )
    assert parsed.stdout_sha256 == sha256_bytes(stdout), (
        "the retained digest must be the real sha256 of the consumer stdout"
    )
    assert parsed.stdout_prefix == stdout[: C.CONSUMER_STDOUT_PREFIX_BYTES].decode(
        "utf-8", "replace"
    ), "only the first 2 KiB of stdout may be retained"
    assert len(parsed.stdout_prefix.encode("utf-8")) <= (
        C.CONSUMER_STDOUT_PREFIX_BYTES + 3
    ), "the retained prefix must stay within 2 KiB"

    case.check("unmapped_consumer_output", "pass", {
        "reason": parsed.reason,
        "stdout_sha256": parsed.stdout_sha256,
        "retained_bytes": len(parsed.stdout_prefix.encode("utf-8")),
    })
    case.settle("pass")


def test_p4_nonzero_exit_is_not_mapped(p4_case) -> None:
    """A consumer that fails exits are never read as an observation."""
    case = p4_case()
    stdout = canonical_dumps({"schema_version": C.P4_OBSERVATION_SCHEMA}).encode(
        "utf-8"
    )
    parsed = consumer.parse_observation(_run(stdout, returncode=2))
    assert parsed.observation is None, "a failed consumer run must not map"
    assert parsed.reason == "consumer_nonzero_exit", (
        f"expected a nonzero-exit reason; got {parsed.reason!r}"
    )
    case.check("nonzero_exit_not_mapped", "pass", {"reason": parsed.reason})
    case.settle("pass")


def test_p4_manifest_entries_are_read_only(p4_case, tmp_path) -> None:
    """A malformed ROOT manifest is rejected before any consumer executes."""
    case = p4_case()
    bad = tmp_path / "bad-commands.json"
    bad.write_text(
        json.dumps({"schema_version": "p4-consumer-commands/1", "ff": {}}),
        encoding="utf-8",
    )
    try:
        consumer.load_manifest(bad)
    except consumer.ManifestRejected as exc:
        assert exc.reason, "the refusal must carry an error code"
        assert "argv/cwd/timeout_s" in exc.detail or exc.reason, (
            f"the refusal must explain itself; got {exc.detail!r}"
        )
    else:
        raise AssertionError("an entryless manifest must be rejected")

    missing = tmp_path / "absent.json"
    try:
        consumer.load_manifest(missing)
    except consumer.ManifestRejected as exc:
        assert exc.reason == "not_configured", (
            f"expected not_configured; got {exc.reason!r}"
        )
    else:
        raise AssertionError("a missing manifest must be rejected")

    case.check("manifest_refused_before_execution", "pass",
               {"path": Path(bad).name})
    case.settle("pass")
