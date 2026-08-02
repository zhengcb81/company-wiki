"""AUTO-3 HandlerRegistry: frozen handler specifications for known job types.

This module depends only on the Python standard library and ``models``.  It
does not import the legacy scheduler, network, LLM or configuration modules.
New job types must be registered here together with their schema, retry and
error policy — a weak model must not add unregistered handlers.
"""

from __future__ import annotations

from dataclasses import dataclass


class UnknownJobTypeError(KeyError):
    """Raised when a job_type has no registered handler spec."""


@dataclass(frozen=True)
class HandlerSpec:
    """Frozen specification for a single handler type (AUTO-F)."""

    job_type: str
    handler_version: str
    input_schema: str
    result_schema: str
    effect_class: str  # "artifact_only", "knowledge_write", "external_side_effect"
    allowed_paths: tuple[str, ...]
    network: bool
    llm: bool
    default_max_attempts: int
    retryable_errors: tuple[str, ...]
    human_errors: tuple[str, ...]
    terminal_errors: tuple[str, ...]


class HandlerRegistry:
    """Mapping from ``job_type`` to its frozen ``HandlerSpec``."""

    def __init__(self) -> None:
        self._specs: dict[str, HandlerSpec] = {}

    def register(self, spec: HandlerSpec) -> None:
        self._specs[spec.job_type] = spec

    def get(self, job_type: str) -> HandlerSpec:
        try:
            return self._specs[job_type]
        except KeyError:
            raise UnknownJobTypeError(
                f"no handler registered for job_type: {job_type}"
            ) from None

    def known_job_types(self) -> tuple[str, ...]:
        return tuple(sorted(self._specs))


# --------------------------------------------------------------------------- #
# Pre-registered handler specs for the first supported event types (AUTO-F).
# --------------------------------------------------------------------------- #
_KNOWN_SPECS: tuple[HandlerSpec, ...] = (
    HandlerSpec(
        job_type="source.normalize",
        handler_version="1.0.0",
        input_schema="SourceNormalizeInput.v1",
        result_schema="SourceNormalizeResult.v1",
        effect_class="artifact_only",
        allowed_paths=("companies/*/raw/**", "sectors/*/raw/**"),
        network=False,
        llm=False,
        default_max_attempts=2,
        retryable_errors=("IO_TRANSIENT",),
        human_errors=(),
        terminal_errors=("SCHEMA_INVALID", "HASH_MISMATCH"),
    ),
    HandlerSpec(
        job_type="source.analyze",
        handler_version="1.0.0",
        input_schema="SourceAnalyzeInput.v1",
        result_schema="SourceAnalyzeResult.v1",
        effect_class="artifact_only",
        allowed_paths=("artifacts/proposals/**",),
        network=False,
        llm=True,
        default_max_attempts=3,
        retryable_errors=("IO_TRANSIENT", "LEASE_LOST"),
        human_errors=("REVIEW_PENDING",),
        terminal_errors=("SCHEMA_INVALID", "POLICY_DENIED"),
    ),
    HandlerSpec(
        job_type="gold.validate_receipt",
        handler_version="1.0.0",
        input_schema="GoldValidateInput.v1",
        result_schema="GoldValidateResult.v1",
        effect_class="artifact_only",
        allowed_paths=("artifacts/gates/**",),
        network=False,
        llm=False,
        default_max_attempts=2,
        retryable_errors=("IO_TRANSIENT", "LEASE_LOST"),
        human_errors=("REVIEW_PENDING", "REVIEW_NEEDS_CHANGES"),
        terminal_errors=("PACKET_CORPUS_MISMATCH", "SCHEMA_INVALID"),
    ),
    HandlerSpec(
        job_type="gold.refresh_packet",
        handler_version="1.0.0",
        input_schema="GoldRefreshInput.v1",
        result_schema="GoldRefreshResult.v1",
        effect_class="artifact_only",
        allowed_paths=("artifacts/gates/**",),
        network=False,
        llm=False,
        default_max_attempts=2,
        retryable_errors=("IO_TRANSIENT",),
        human_errors=(),
        terminal_errors=("SCHEMA_INVALID",),
    ),
    HandlerSpec(
        job_type="gold.promote_reviewed",
        handler_version="1.0.0",
        input_schema="GoldPromoteInput.v1",
        result_schema="GoldPromoteResult.v1",
        effect_class="knowledge_write",
        allowed_paths=("tests/fixtures/gold_corpus/**",),
        network=False,
        llm=False,
        default_max_attempts=1,
        retryable_errors=(),
        human_errors=("REVIEW_PENDING",),
        terminal_errors=("PACKET_CORPUS_MISMATCH", "SCHEMA_INVALID", "HASH_MISMATCH"),
    ),
    HandlerSpec(
        job_type="timer.execute_step",
        handler_version="1.0.0",
        input_schema="TimerStepInput.v1",
        result_schema="TimerStepResult.v1",
        effect_class="artifact_only",
        allowed_paths=("artifacts/**",),
        network=False,
        llm=False,
        default_max_attempts=2,
        retryable_errors=("IO_TRANSIENT",),
        human_errors=(),
        terminal_errors=("SCHEMA_INVALID",),
    ),
    HandlerSpec(
        job_type="analysis.validate",
        handler_version="1.0.0",
        input_schema="AnalysisValidateInput.v1",
        result_schema="AnalysisValidateResult.v1",
        effect_class="artifact_only",
        allowed_paths=("artifacts/proposals/**",),
        network=False,
        llm=False,
        default_max_attempts=2,
        retryable_errors=("IO_TRANSIENT",),
        human_errors=(),
        terminal_errors=("SCHEMA_INVALID", "HASH_MISMATCH"),
    ),
    HandlerSpec(
        job_type="analysis.review",
        handler_version="1.0.0",
        input_schema="AnalysisReviewInput.v1",
        result_schema="AnalysisReviewResult.v1",
        effect_class="artifact_only",
        allowed_paths=("artifacts/proposals/**", "artifacts/gates/**"),
        network=False,
        llm=False,
        default_max_attempts=2,
        retryable_errors=("IO_TRANSIENT", "LEASE_LOST"),
        human_errors=("REVIEW_PENDING", "REVIEW_NEEDS_CHANGES"),
        terminal_errors=("SCHEMA_INVALID",),
    ),
)


def create_default_registry() -> HandlerRegistry:
    """Return a registry pre-loaded with all known handler specs."""
    registry = HandlerRegistry()
    for spec in _KNOWN_SPECS:
        registry.register(spec)
    return registry


__all__ = [
    "HandlerSpec",
    "HandlerRegistry",
    "UnknownJobTypeError",
    "create_default_registry",
]
