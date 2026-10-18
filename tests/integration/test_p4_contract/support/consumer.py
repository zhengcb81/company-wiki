"""Read-only consumer execution driven strictly by the ROOT command manifest.

Card 5.2: only the manifest's ``argv`` is executed, with the four declared
placeholders substituted.  No subcommand is guessed, no ``--help`` probe is run,
and the lane never writes into the consumer repository.  ``HEAD`` and
``git status --porcelain`` are captured before and after to prove read-only.
"""

from __future__ import annotations

import os
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from . import constants as C
from .jsonio import JsonRejected, loads_strict, sha256_bytes

PLACEHOLDERS = ("{catalog}", "{document_id}", "{source_id}", "{content_sha256}")
_REQUIRED_FIELDS = frozenset({"argv", "cwd", "timeout_s"})


class ManifestRejected(ValueError):
    """The ROOT command manifest is unusable; the lane reports ``not_evaluated``."""

    def __init__(self, reason: str, detail: str = ""):
        self.reason = reason
        self.detail = detail
        super().__init__(reason + (f": {detail}" if detail else ""))


@dataclass(frozen=True)
class ConsumerSpec:
    """One consumer entry from ``p4-consumer-commands/1``."""

    consumer: str
    argv: tuple[str, ...]
    cwd: Path
    timeout_s: int

    def render(self, *, catalog: Path, document_id: str, source_id: str,
               content_sha256: str) -> list[str]:
        values = {
            "{catalog}": str(catalog),
            "{document_id}": document_id,
            "{source_id}": source_id,
            "{content_sha256}": content_sha256,
        }
        rendered: list[str] = []
        for token in self.argv:
            for placeholder, value in values.items():
                token = token.replace(placeholder, value)
            rendered.append(token)
        return rendered


@dataclass(frozen=True)
class ConsumerRun:
    """One consumer invocation and its raw stdout."""

    consumer: str
    argv: tuple[str, ...]
    returncode: int
    stdout: bytes
    stderr_tail: str

    @property
    def stdout_sha256(self) -> str:
        return sha256_bytes(self.stdout)

    @property
    def stdout_prefix(self) -> str:
        chunk = self.stdout[: C.CONSUMER_STDOUT_PREFIX_BYTES]
        return chunk.decode("utf-8", "replace")


@dataclass(frozen=True)
class ParsedObservation:
    """A parsed observation, or an explicit unmapped refusal (card 5.3)."""

    observation: dict[str, Any] | None
    reason: str | None
    stdout_sha256: str
    stdout_prefix: str


def load_manifest(path: Path) -> dict[str, ConsumerSpec]:
    """Parse ``p4-consumer-commands/1``; unknown or malformed entries are refused."""
    try:
        raw = path.read_bytes()
    except OSError as exc:
        raise ManifestRejected("not_configured", f"cannot read manifest: {exc}") from exc
    try:
        payload = loads_strict(raw, label="consumer manifest")
    except JsonRejected as exc:
        raise ManifestRejected(exc.reason, exc.detail) from exc
    if not isinstance(payload, dict):
        raise ManifestRejected(C.CODE_INVALID_JSON, "manifest is not an object")
    if payload.get("schema_version") != C.P4_COMMANDS_SCHEMA:
        raise ManifestRejected(
            C.CODE_INVALID_ARGUMENT,
            f"manifest schema_version must be {C.P4_COMMANDS_SCHEMA}",
        )
    specs: dict[str, ConsumerSpec] = {}
    for consumer in C.CONSUMERS:
        entry = payload.get(consumer)
        if entry is None:
            continue
        if not isinstance(entry, dict) or not _REQUIRED_FIELDS <= set(entry):
            raise ManifestRejected(
                C.CODE_INVALID_ARGUMENT,
                f"{consumer} entry must carry argv/cwd/timeout_s",
            )
        argv = entry["argv"]
        if not isinstance(argv, list) or not argv or not all(
            isinstance(token, str) and token for token in argv
        ):
            raise ManifestRejected(
                C.CODE_INVALID_ARGUMENT, f"{consumer}.argv must be non-empty strings"
            )
        timeout_s = entry["timeout_s"]
        if not isinstance(timeout_s, int) or isinstance(timeout_s, bool) or timeout_s <= 0:
            raise ManifestRejected(
                C.CODE_INVALID_ARGUMENT, f"{consumer}.timeout_s must be a positive int"
            )
        if timeout_s > C.MAX_COMMAND_TIMEOUT_S:
            raise ManifestRejected(
                C.CODE_LIMIT_EXCEEDED,
                f"{consumer}.timeout_s {timeout_s} exceeds {C.MAX_COMMAND_TIMEOUT_S}",
            )
        cwd = Path(str(entry["cwd"]))
        if not cwd.is_dir():
            raise ManifestRejected(
                C.CODE_DEPENDENCY_UNAVAILABLE, f"{consumer}.cwd is not a directory"
            )
        specs[consumer] = ConsumerSpec(
            consumer=consumer, argv=tuple(argv), cwd=cwd, timeout_s=timeout_s
        )
    if not specs:
        raise ManifestRejected(
            C.CODE_NOT_CONFIGURED, "manifest declares neither ff nor rf"
        )
    return specs


def run_consumer(
    spec: ConsumerSpec,
    *,
    catalog: Path,
    document_id: str,
    source_id: str,
    content_sha256: str,
) -> ConsumerRun:
    """Execute exactly the manifest argv in the manifest cwd."""
    argv = spec.render(
        catalog=catalog,
        document_id=document_id,
        source_id=source_id,
        content_sha256=content_sha256,
    )
    env = dict(os.environ)
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    env["COMPANY_WIKI_NETWORK"] = "blocked"
    env["COMPANY_WIKI_REAL_LLM"] = "0"
    for secret in (
        "OPENAI_API_KEY", "DEEPSEEK_API_KEY", "MINIMAX_API_KEY",
        "MIMO_API_KEY", "TAVILY_API_KEY", "ANTHROPIC_API_KEY",
    ):
        env.pop(secret, None)
    try:
        proc = subprocess.run(
            argv,
            cwd=str(spec.cwd),
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
            timeout=spec.timeout_s,
        )
    except subprocess.TimeoutExpired as exc:
        raise ManifestRejected(
            "limit_exceeded", f"{spec.consumer} exceeded timeout_s {spec.timeout_s}"
        ) from exc
    except OSError as exc:
        raise ManifestRejected(
            C.CODE_DEPENDENCY_UNAVAILABLE, f"{spec.consumer} failed to start: {exc}"
        ) from exc
    stdout = proc.stdout[: C.MAX_CONSUMER_STDOUT_BYTES]
    return ConsumerRun(
        consumer=spec.consumer,
        argv=tuple(argv),
        returncode=proc.returncode,
        stdout=stdout,
        stderr_tail=proc.stderr.decode("utf-8", "replace")[-2000:],
    )


def parse_observation(run: ConsumerRun) -> ParsedObservation:
    """Map stdout onto ``p4-consumer-observation/1`` without guessing fields.

    The shape must match exactly; anything else is ``not_evaluated`` with
    ``reason="unmapped_consumer_output"`` and only the stdout digest plus a 2 KiB
    prefix are retained.
    """
    digest = run.stdout_sha256
    prefix = run.stdout_prefix
    if run.returncode != 0:
        return ParsedObservation(None, "consumer_nonzero_exit", digest, prefix)
    try:
        payload = loads_strict(run.stdout, label="consumer stdout")
    except JsonRejected:
        return ParsedObservation(
            None, C.UNMAPPED_CONSUMER_OUTPUT, digest, prefix
        )
    if not isinstance(payload, dict) or set(payload) != C.OBSERVATION_KEYS:
        return ParsedObservation(None, C.UNMAPPED_CONSUMER_OUTPUT, digest, prefix)
    if payload.get("schema_version") != C.P4_OBSERVATION_SCHEMA:
        return ParsedObservation(None, C.UNMAPPED_CONSUMER_OUTPUT, digest, prefix)
    if payload.get("consumer") not in C.CONSUMERS:
        return ParsedObservation(None, C.UNMAPPED_CONSUMER_OUTPUT, digest, prefix)
    source_ref = payload.get("source_ref")
    if not isinstance(source_ref, dict) or set(source_ref) != C.SOURCE_REF_KEYS:
        return ParsedObservation(None, C.UNMAPPED_CONSUMER_OUTPUT, digest, prefix)
    if source_ref.get("schema_version") != C.SOURCE_REF_SCHEMA_VERSION:
        return ParsedObservation(None, C.UNMAPPED_CONSUMER_OUTPUT, digest, prefix)
    facts = payload.get("facts")
    if not isinstance(facts, dict) or set(facts) != C.FACT_KEY_SET:
        return ParsedObservation(None, C.UNMAPPED_CONSUMER_OUTPUT, digest, prefix)
    availability = payload.get("availability")
    if not isinstance(availability, dict) or set(availability) != C.AVAILABILITY_KEYS:
        return ParsedObservation(None, C.UNMAPPED_CONSUMER_OUTPUT, digest, prefix)
    quotes = payload.get("quotes")
    if not isinstance(quotes, list):
        return ParsedObservation(None, C.UNMAPPED_CONSUMER_OUTPUT, digest, prefix)
    for quote in quotes:
        if not isinstance(quote, dict) or set(quote) != C.QUOTE_KEYS:
            return ParsedObservation(None, C.UNMAPPED_CONSUMER_OUTPUT, digest, prefix)
        tokens = quote.get("unit_tokens")
        if not isinstance(tokens, list) or any(
            not isinstance(token, dict) or set(token) != C.UNIT_TOKEN_KEYS
            for token in tokens
        ):
            return ParsedObservation(None, C.UNMAPPED_CONSUMER_OUTPUT, digest, prefix)
    for key in ("downloads", "model_calls"):
        block = payload.get(key)
        if not isinstance(block, dict) or set(block) != C.COUNT_KEYS:
            return ParsedObservation(None, C.UNMAPPED_CONSUMER_OUTPUT, digest, prefix)
        if not isinstance(block.get("count"), int) or isinstance(block.get("count"), bool):
            return ParsedObservation(None, C.UNMAPPED_CONSUMER_OUTPUT, digest, prefix)
    return ParsedObservation(payload, None, digest, prefix)


def git_state(root: Path) -> dict[str, Any]:
    """``HEAD`` plus porcelain status, for the cross-repo read-only proof."""

    def _git(*args: str) -> str:
        try:
            proc = subprocess.run(
                ["git", "-C", str(root), *args],
                stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                check=False, timeout=60,
            )
        except (OSError, subprocess.TimeoutExpired) as exc:
            raise ManifestRejected(
                C.CODE_DEPENDENCY_UNAVAILABLE, f"git unavailable for {root}: {exc}"
            ) from exc
        if proc.returncode != 0:
            raise ManifestRejected(
                C.CODE_DEPENDENCY_UNAVAILABLE,
                f"git {' '.join(args)} failed in {root}",
            )
        return proc.stdout.decode("utf-8", "replace")

    return {
        "root": str(root),
        "head": _git("rev-parse", "HEAD").strip(),
        "status": _git("status", "--porcelain"),
    }


def python_executable() -> str:
    return sys.executable
