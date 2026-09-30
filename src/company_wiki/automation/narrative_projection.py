"""Durable publication and pathless reading of verified narrative bundles."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import json
import sqlite3
import uuid

from company_wiki.source_catalog.lock import (
    CatalogOperationLockedError,
    CatalogOperationLock,
)
from company_wiki.source_catalog.narrative_artifact_store import (
    NarrativeArtifactDraft,
    NarrativeArtifactError,
    NarrativeArtifactStore,
    NarrativeArtifactVersion,
    NarrativeSourceNotCurrentError,
)

from .models import (
    Effect,
    EffectStatus,
    HandlerOutcome,
    RuntimeState,
    canonical_json,
    canonical_json_hash,
    require_canonical_json,
    require_utc_timestamp,
)
from .narrative_contracts import NarrativeBundle, NarrativeContractError
from .narrative_verify import EFFECT_TYPE
from .store import (
    AutomationStore,
    AutomationStoreError,
    IntegrityViolationError,
    LeaseLostError,
    RecordNotFoundError,
)


MAX_OUTBOX_ATTEMPTS = 5
OUTBOX_LEASE_SECONDS = 120
RETRY_MAX_SECONDS = 300


@dataclass(frozen=True)
class NarrativeProjectionReceipt:
    effect_id: str | None
    status: str
    artifact_version_id: str | None = None


@dataclass(frozen=True)
class NarrativeArtifactRead:
    artifact: NarrativeArtifactVersion
    bundle: NarrativeBundle


class NarrativeProjectionError(ValueError):
    """A leased effect does not describe one valid, replayed narrative bundle."""


class NarrativeBundleReader:
    """Return only hash-checked visible bundles bound to the active source version."""

    def __init__(self, artifacts: NarrativeArtifactStore) -> None:
        self._artifacts = artifacts

    def read(
        self,
        *,
        document_id: str,
        source_id: str,
        source_sha256: str,
    ) -> NarrativeArtifactRead:
        artifact, payload = self._artifacts.read_visible(
            document_id=document_id,
            source_id=source_id,
            source_sha256=source_sha256,
        )
        try:
            text = payload.decode("utf-8", errors="strict")
            require_canonical_json(text)
            bundle = NarrativeBundle.from_dict(json.loads(text))
        except (UnicodeDecodeError, TypeError, ValueError, NarrativeContractError) as exc:
            raise NarrativeProjectionError(
                "stored narrative bundle failed its strict wire contract"
            ) from exc
        source = bundle.source_ref
        if (
            bundle.schema_version != "narrative-bundle/2.0"
            or source.document_id != artifact.document_id
            or source.source_id != artifact.source_id
            or source.content_sha256 != artifact.source_sha256
            or source.document_id != document_id
            or source.source_id != source_id
            or source.content_sha256 != source_sha256
        ):
            raise NarrativeProjectionError(
                "stored narrative bundle does not match its source binding"
            )
        return NarrativeArtifactRead(artifact=artifact, bundle=bundle)


class NarrativeEffectDispatcher:
    """Dispatch only narrative bundle effects; the general outbox stays untouched."""

    def __init__(
        self,
        automation: AutomationStore,
        artifacts: NarrativeArtifactStore,
    ) -> None:
        self._automation = automation
        self._artifacts = artifacts

    def dispatch_next(
        self,
        *,
        worker_id: str,
        now: str,
        lease_until: str,
        expected_generation: int,
    ) -> NarrativeProjectionReceipt:
        require_utc_timestamp(now)
        require_utc_timestamp(lease_until)
        lease = self._automation.claim_next_outbox(
            worker_id=worker_id,
            lease_token=f"narrative-outbox-{uuid.uuid4().hex}",
            now=now,
            lease_until=lease_until,
            expected_generation=expected_generation,
            allowed_effect_types=(EFFECT_TYPE,),
        )
        if lease is None:
            return NarrativeProjectionReceipt(None, "empty")

        try:
            effect, bundle, payload = self._prepare_effect(lease.effect_id)
            version = self._artifacts.prepare(
                self._draft(effect, bundle),
                payload,
            )
        except (
            IntegrityViolationError,
            NarrativeArtifactError,
            NarrativeContractError,
            NarrativeProjectionError,
            RecordNotFoundError,
            TypeError,
            ValueError,
        ) as exc:
            return self._retry_or_fail(lease, now=now, permanent=True, error=exc)
        except (OSError, sqlite3.Error, AutomationStoreError) as exc:
            return self._retry_or_fail(lease, now=now, permanent=False, error=exc)

        try:
            self._automation.ack_outbox(
                outbox_id=lease.outbox_id,
                lease_token=lease.lease_token,
                runtime_generation=lease.runtime_generation,
                verified_at=now,
                actual_after_hash=version.content_sha256,
            )
        except Exception as exc:
            current = self._automation.get_effect(effect.effect_id)
            if (
                current is not None
                and current.status is EffectStatus.VERIFIED
                and current.actual_after_hash == version.content_sha256
            ):
                return NarrativeProjectionReceipt(
                    effect.effect_id, "activation_pending", version.artifact_version_id
                )
            return self._retry_or_fail(
                lease, now=now, permanent=False, error=exc
            )

        try:
            # Pause/enable uses this same catalog operation lock. If pause wins
            # after AUTO ACK, keep the prepared object invisible until a later
            # enabled generation reconciles it. If publication wins, pause cannot
            # cross the visibility transaction.
            with CatalogOperationLock(
                self._artifacts.catalog_dir,
                operation="narrative-bundle-activate",
            ):
                gate = self._automation.read_runtime_gate()
                if (
                    gate.desired_state is not RuntimeState.ENABLED
                    or gate.control_generation != lease.runtime_generation
                ):
                    return NarrativeProjectionReceipt(
                        effect.effect_id,
                        "activation_pending",
                        version.artifact_version_id,
                    )
                verified = self._automation.get_effect(effect.effect_id)
                if (
                    verified is None
                    or verified.status is not EffectStatus.VERIFIED
                    or verified.actual_after_hash != version.content_sha256
                ):
                    return NarrativeProjectionReceipt(
                        effect.effect_id,
                        "activation_pending",
                        version.artifact_version_id,
                    )
                visible = self._artifacts.activate(
                    effect.effect_id,
                    verified_after_hash=version.content_sha256,
                    activated_at=now,
                )
        except (
            AutomationStoreError,
            CatalogOperationLockedError,
            NarrativeArtifactError,
            OSError,
            sqlite3.Error,
        ):
            # AUTO ACK is durable. A later enabled reconciliation completes this
            # short second-store transition without claiming or replaying effects.
            return NarrativeProjectionReceipt(
                effect.effect_id, "activation_pending", version.artifact_version_id
            )
        return NarrativeProjectionReceipt(
            effect.effect_id, "visible", visible.artifact_version_id
        )

    def reconcile_prepared(
        self, *, activated_at: str, limit: int = 100
    ) -> tuple[str, ...]:
        require_utc_timestamp(activated_at)
        activated: list[str] = []
        for artifact in self._artifacts.prepared_effects(limit=limit):
            try:
                with CatalogOperationLock(
                    self._artifacts.catalog_dir,
                    operation="narrative-bundle-reconcile",
                ):
                    gate = self._automation.read_runtime_gate()
                    if gate.desired_state is not RuntimeState.ENABLED:
                        continue
                    effect = self._automation.get_effect(artifact.effect_id)
                    if (
                        effect is None
                        or effect.status is not EffectStatus.VERIFIED
                        or effect.actual_after_hash != artifact.content_sha256
                    ):
                        continue
                    self._artifacts.activate(
                        artifact.effect_id,
                        verified_after_hash=effect.actual_after_hash,
                        activated_at=activated_at,
                    )
            except (CatalogOperationLockedError, NarrativeSourceNotCurrentError):
                continue
            activated.append(artifact.effect_id)
        return tuple(activated)

    def _prepare_effect(
        self, effect_id: str
    ) -> tuple[Effect, NarrativeBundle, bytes]:
        effect = self._automation.get_effect(effect_id)
        if effect is None:
            raise RecordNotFoundError(f"effect {effect_id!r} not found")
        if effect.effect_type != EFFECT_TYPE:
            raise NarrativeProjectionError("outbox effect type is not narrative bundle")
        if effect.status not in {EffectStatus.PLANNED, EffectStatus.PENDING}:
            raise NarrativeProjectionError("outbox effect is not pending publication")
        result = self._automation.result_for_effect(effect_id)
        if result.outcome is not HandlerOutcome.SUCCEEDED or len(result.effects) != 1:
            raise NarrativeProjectionError("effect has no unique successful handler result")
        if result.effects[0] != effect:
            raise NarrativeProjectionError("handler result emitted a different effect")
        bundle = NarrativeBundle.from_dict(dict(result.result))
        bundle_hash = canonical_json_hash(bundle.to_dict())
        expected_target = (
            "urn:company-wiki:narrative-bundle:"
            f"{bundle.source_ref.document_id}:{bundle.source_ref.content_sha256}"
        )
        if (
            effect.target != expected_target
            or effect.intended_after_hash != bundle_hash
        ):
            raise NarrativeProjectionError("effect hash or target differs from bundle")
        payload = canonical_json(bundle.to_dict()).encode("utf-8")
        if not payload or canonical_json_hash(bundle.to_dict()) != effect.intended_after_hash:
            raise NarrativeProjectionError("bundle bytes do not match intended effect hash")
        return effect, bundle, payload

    @staticmethod
    def _draft(effect: Effect, bundle: NarrativeBundle) -> NarrativeArtifactDraft:
        producer_name = "company_wiki.narrative_bundle"
        producer_version = bundle.versions.bundle_producer
        artifact_role = "narrative_bundle"
        work_key = canonical_json_hash(
            {
                "schema_version": "narrative-work-key/1.0",
                "document_id": bundle.source_ref.document_id,
                "source_id": bundle.source_ref.source_id,
                "source_sha256": bundle.source_ref.content_sha256,
                "artifact_role": artifact_role,
                "producer_name": producer_name,
                "producer_version": producer_version,
                "policy_sha256": bundle.expected_read_policy_sha256,
            }
        )
        return NarrativeArtifactDraft(
            effect_id=effect.effect_id,
            work_key=work_key,
            document_id=bundle.source_ref.document_id,
            source_id=bundle.source_ref.source_id,
            source_sha256=bundle.source_ref.content_sha256,
            producer_name=producer_name,
            producer_version=producer_version,
            policy_sha256=bundle.expected_read_policy_sha256,
            selection_status=bundle.selection.status,
            quality_status=bundle.quality_status,
            metadata_json=canonical_json(
                {
                    "bundle_schema": bundle.schema_version,
                    "summary_status": bundle.summary.status,
                }
            ),
            created_at=effect.created_at,
            artifact_role=artifact_role,
        )

    def _retry_or_fail(
        self,
        lease,
        *,
        now: str,
        permanent: bool,
        error: Exception,
    ) -> NarrativeProjectionReceipt:
        budget = 1 if permanent else MAX_OUTBOX_ATTEMPTS
        retry_at = self._retry_at(now, lease.attempt_count)
        try:
            outcome = self._automation.retry_outbox(
                outbox_id=lease.outbox_id,
                lease_token=lease.lease_token,
                runtime_generation=lease.runtime_generation,
                now=now,
                not_before=retry_at,
                error=f"NARRATIVE_PROJECTION_{type(error).__name__}",
                max_attempts=budget,
            )
        except LeaseLostError:
            return NarrativeProjectionReceipt(lease.effect_id, "lease_lost")
        status = "failed" if outcome["status"] == "failed" else "retry_scheduled"
        return NarrativeProjectionReceipt(lease.effect_id, status)

    @staticmethod
    def _retry_at(now: str, attempt_count: int) -> str:
        seconds = min(2 ** min(attempt_count, 8), RETRY_MAX_SECONDS)
        instant = datetime.fromisoformat(now.replace("Z", "+00:00")) + timedelta(
            seconds=seconds
        )
        return instant.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


__all__ = [
    "NarrativeArtifactRead",
    "NarrativeBundleReader",
    "NarrativeEffectDispatcher",
    "NarrativeProjectionError",
    "NarrativeProjectionReceipt",
]
