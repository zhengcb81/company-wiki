"""Fail-closed stage policy for the live source-catalog worker."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any


SOURCE_ONLY_SCHEDULER_POLICY_SCHEMA_VERSION = "1.0.0"

_FORBIDDEN_DISPATCH_TOKENS = (
    "assessment",
    "buy",
    "research",
    "rating",
    "sell",
    "sotp",
    "stockwiki",
    "target_price",
    "valuation",
    "wiki_writer",
)


class SourceOnlySchedulerPolicyError(ValueError):
    """Raised before a non-source or mismatched stage can be dispatched."""


class SourceOnlyStage(str, Enum):
    """Stable activity names emitted by the live source-catalog worker."""

    SCANNING = "scanning"
    NORMALIZING = "normalizing"
    SUMMARIZING = "summarizing"
    EXPORTING = "exporting"


@dataclass(frozen=True)
class SourceOnlyStageContract:
    stage: SourceOnlyStage
    catalog_method: str

    def to_dict(self) -> dict[str, str]:
        return {
            "stage": self.stage.value,
            "catalog_method": self.catalog_method,
        }


_STAGE_CONTRACTS = (
    SourceOnlyStageContract(SourceOnlyStage.SCANNING, "scan"),
    SourceOnlyStageContract(SourceOnlyStage.NORMALIZING, "normalize"),
    SourceOnlyStageContract(
        SourceOnlyStage.SUMMARIZING,
        "summarize_with_llm",
    ),
    SourceOnlyStageContract(SourceOnlyStage.EXPORTING, "export_indexes"),
)
_METHOD_BY_STAGE = {item.stage: item.catalog_method for item in _STAGE_CONTRACTS}


@dataclass(frozen=True)
class SourceOnlySchedulerPolicy:
    """Immutable allowlist; config files cannot add or rename worker stages."""

    schema_version: str = SOURCE_ONLY_SCHEDULER_POLICY_SCHEMA_VERSION

    def __post_init__(self) -> None:
        if self.schema_version != SOURCE_ONLY_SCHEDULER_POLICY_SCHEMA_VERSION:
            raise SourceOnlySchedulerPolicyError(
                "scheduler policy schema_version is unsupported"
            )

    @property
    def stages(self) -> tuple[SourceOnlyStageContract, ...]:
        return _STAGE_CONTRACTS

    def require_dispatch(
        self,
        stage: SourceOnlyStage | str,
        catalog_method: str,
    ) -> SourceOnlyStage:
        if not isinstance(catalog_method, str) or catalog_method != catalog_method.strip():
            raise SourceOnlySchedulerPolicyError("catalog method must be exact text")
        try:
            resolved_stage = SourceOnlyStage(stage)
        except (TypeError, ValueError) as exc:
            raise SourceOnlySchedulerPolicyError(
                "stage is outside the source-only allowlist"
            ) from exc
        candidate = f"{resolved_stage.value} {catalog_method}".casefold()
        if any(token in candidate for token in _FORBIDDEN_DISPATCH_TOKENS):
            raise SourceOnlySchedulerPolicyError(
                "dispatch contains a forbidden research or investment token"
            )
        expected_method = _METHOD_BY_STAGE[resolved_stage]
        if catalog_method != expected_method:
            raise SourceOnlySchedulerPolicyError(
                "stage and catalog method do not match the source-only contract"
            )
        return resolved_stage

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "stages": [item.to_dict() for item in self.stages],
        }


__all__ = [
    "SOURCE_ONLY_SCHEDULER_POLICY_SCHEMA_VERSION",
    "SourceOnlySchedulerPolicy",
    "SourceOnlySchedulerPolicyError",
    "SourceOnlyStage",
    "SourceOnlyStageContract",
]
