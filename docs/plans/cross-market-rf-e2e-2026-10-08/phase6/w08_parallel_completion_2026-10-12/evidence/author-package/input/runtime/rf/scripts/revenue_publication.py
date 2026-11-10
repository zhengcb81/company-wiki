"""Publication receipts for formal revenue forecast output.

A publication receipt certifies that a forecast result has passed the
self-contained output validator.  Since the receipt is only issued from a
verification context produced by ``validate_published_forecast`` (the strong,
input-required entry), a weakly-validated or forged artifact cannot obtain a
valid receipt.

Design rules (task_plan.md Phase 2 / Phase 6 A1):

* ``result_sha256`` continues to cover the whole result (including this receipt),
  so existing tamper/rehash contracts are unchanged.
* ``validated_payload_sha256`` excludes both ``result_sha256`` and
  ``publication_receipt`` so the receipt never references itself (no recursion /
  non-determinism).
* ``gate_ids`` reflect the gates that actually executed during strong
  validation (see ``expected_publication_gates``), never a fixed claim.
* ``verification_context_sha256`` binds the receipt to the exact
  ``VerificationContext`` returned by ``validate_published_forecast``; the
  validator recomputes it so a receipt built from a weaker or fabricated
  context is rejected.
* This module never re-runs the revenue model — it only hashes and validates.

SECURITY BOUNDARY (B1 / REM-02): two different things live in this module.

* ``validate_publication_receipt`` is a **hash-consistency check on one artifact**
  and **NOT a security boundary** (see its docstring and
  :class:`PublicationReceiptOnlyWarning`).
* ``validate_forecast_output`` in :mod:`revenue_report` is the consumer entry
  point: it re-runs the bounded input-gated recomputations and the attestation
  binding.  **Consumers must call ``validate_forecast_output``**, never
  ``validate_publication_receipt`` alone.

Attestation (B1 / REM-01): a receipt claiming ``attestation_status ==
"host_signed"`` must carry a ``publication_attestation`` binding record that
verifies against the trust domain, per I-08-A E27 (``attestation_missing_record``).
The label is never accepted on set membership.
"""

from __future__ import annotations

import re
from typing import Any

from contracts.evidence import ForecastInputError
from revenue_core import (
    ENGINE_VERSION,
    PUBLICATION_RECEIPT_SCHEMA_VERSION,
    canonical_sha256,
    require,
)


class PublicationReceiptOnlyWarning(UserWarning):
    """Marker: ``validate_publication_receipt`` is NOT a security boundary.

    Exported so a caller (and a test) can see the limitation without reading the
    source.  The function checks only that a receipt's self-hashes, gate set and
    verification context are internally consistent with the artifact they travel
    with; a fully-recomputed forgery satisfies all of them.  Use
    ``revenue_report.validate_forecast_output`` for consumer-side validation.
    """


# Gates certified by the strong validator (validate_published_forecast) when
# the artifact carries sensitivity results.
OUTPUT_RECOMPUTATION_GATE = "output_recomputation"
SENSITIVITY_SHOCK_RECOMPUTATION_GATE = "sensitivity_shock_recomputation"


def expected_publication_gates(result: dict[str, Any]) -> tuple[str, ...]:
    """The gates the strong validator actually executes for *result*.

    Deterministic so the verification-context binding can be recomputed by any
    consumer.  Sensitivity shock recomputation only runs when the result
    carries sensitivity data; otherwise only the structural output
    recomputation gate applies.
    """
    gates = [OUTPUT_RECOMPUTATION_GATE]
    if result.get("sensitivities"):
        gates.append(SENSITIVITY_SHOCK_RECOMPUTATION_GATE)
    return tuple(gates)


class VerificationContext:
    """Opaque record of a successful strong validation.

    Produced only by ``validate_published_forecast`` (or by test helpers that
    deliberately simulate a fully-informed attacker recomputing every hash).
    ``executed_gate_ids`` is derived from the result content, so a receipt built
    for an artifact whose sensitivity was forged without running the shock
    recomputation cannot match the strong gate contract.
    """

    __slots__ = ("validated_input_sha256", "executed_gate_ids", "validator_version")

    def __init__(
        self,
        validated_input_sha256: str,
        executed_gate_ids: tuple[str, ...],
        validator_version: str,
    ) -> None:
        if not isinstance(validated_input_sha256, str) or not validated_input_sha256:
            raise TypeError("validated_input_sha256 must be a non-empty string")
        if not isinstance(executed_gate_ids, tuple) or not executed_gate_ids:
            raise TypeError("executed_gate_ids must be a non-empty tuple")
        if not isinstance(validator_version, str) or not validator_version:
            raise TypeError("validator_version must be a non-empty string")
        self.validated_input_sha256 = validated_input_sha256
        self.executed_gate_ids = executed_gate_ids
        self.validator_version = validator_version

    def to_dict(self) -> dict[str, Any]:
        return {
            "validated_input_sha256": self.validated_input_sha256,
            "executed_gate_ids": list(self.executed_gate_ids),
            "validator_version": self.validator_version,
        }

    def context_sha256(self) -> str:
        return canonical_sha256(self.to_dict())


# The output-recomputation gate is certified by validate_published_forecast, not
# by the execution receipt, so it lives on the publication receipt.
PUBLICATION_GATE_IDS = expected_publication_gates({"sensitivities": []})


def _payload_sha256(result: dict[str, Any]) -> str:
    """Hash the result payload excluding the two receipt/hash fields."""
    payload = {
        key: value
        for key, value in result.items()
        if key not in ("result_sha256", "publication_receipt")
    }
    return canonical_sha256(payload)


def _receipt_sha256(receipt: dict[str, Any]) -> str:
    return canonical_sha256(
        {key: value for key, value in receipt.items() if key != "receipt_sha256"}
    )


ATTESTATION_STATUSES = {"host_signed", "unattested"}

# --- Publication attestation binding record (B1 / REM-01, I-08-A E27) -------
# The record is the thing that makes the `host_signed` label evidentiary.  Its
# field set is CLOSED: an extra or missing key is a rejection, so a record can
# never be given a meaning by a later reader that this validator did not check.
PUBLICATION_ATTESTATION_DOMAIN = "revenue-forecast/publication-attestation/v1"
PUBLICATION_ATTESTATION_SCHEMA_VERSION = "1.0"
PUBLICATION_ATTESTATION_ALGORITHM = "ed25519"
PUBLICATION_ATTESTATION_FIELDS = frozenset(
    {
        "attestation_payload_schema_version",
        "domain_separator",
        "issuer",
        "key_id",
        "algorithm",
        "fingerprint",
        "request_id",
        "payload_sha256",
        "signed_at",
        "signature",
    }
)

_HEX32 = re.compile(r"[0-9a-f]{32}")
_HEX64 = re.compile(r"[0-9a-f]{64}")
_HEX128 = re.compile(r"[0-9a-f]{128}")
_RFC3339_Z = re.compile(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z")

# The request's `result_sha256` member exists so the provider sees an
# unambiguous binding target, but its VALUE cannot be part of the signed record:
# `result_sha256` covers the receipt, and the receipt contains the record.  The
# record therefore carries no result digest, and this sentinel is what both the
# provider request and the reconstruction use, so the signature covers exactly
# the fields the record can bind.
SIGNED_RESULT_SHA256_SENTINEL = "0" * 64


def verify_ed25519_signature(
    fingerprint: str, signature: str, message: bytes
) -> None:
    """Verify an Ed25519 signature against a fingerprint in the trust domain.

    Fail-closed on every axis: unknown fingerprint, unavailable crypto library,
    malformed key, malformed signature, or a verification failure all raise.
    The trust domain is read from :func:`contracts.evidence._trusted_signer_public_keys`
    so there is exactly one loader (missing file ⇒ zero trusted signers).
    """
    from contracts.evidence import _trusted_signer_public_keys

    trusted = _trusted_signer_public_keys()
    require(
        fingerprint in trusted,
        f"provider_key_untrusted: attestation signer {fingerprint[:12]} is not "
        "trusted (E20)",
    )
    try:
        from cryptography.exceptions import InvalidSignature
        from cryptography.hazmat.primitives.asymmetric.ed25519 import (
            Ed25519PublicKey,
        )
    except ImportError as exc:  # pragma: no cover - optional dependency
        raise ForecastInputError(
            "attestation_signature_invalid: attestation signature verification "
            "unavailable"
        ) from exc
    try:
        public_key = Ed25519PublicKey.from_public_bytes(trusted[fingerprint])
        public_key.verify(bytes.fromhex(signature), message)
    except (InvalidSignature, ValueError) as exc:
        raise ForecastInputError(
            "attestation_signature_invalid: attestation signature verification "
            "failed (E14)"
        ) from exc


def validate_publication_attestation(
    result: dict[str, Any], receipt: dict[str, Any]
) -> None:
    """Validate the ``publication_attestation`` binding record (B1 / REM-01).

    Raises with the I-08-A code spelling in the message so a caller can classify
    the rejection without parsing prose:

    * ``attestation_missing_record`` (E27) — ``host_signed`` with no record.
    * ``attestation_missing_signature`` (E12) / ``attestation_malformed_signature``
      (E13) — absent or malformed signature.
    * ``attestation_domain_mismatch`` (E17) — wrong domain separator.
    * ``attestation_payload_hash_mismatch`` (E16) — the record does not bind the
      live payload / result / receipt.
    * ``provider_key_untrusted`` (E20) / ``issuer_key_binding_mismatch`` (E21) —
      trust-domain failures.
    * ``attestation_signature_invalid`` (E14) — Ed25519 verification failed.
    """
    record = receipt.get("publication_attestation")
    claims_signed = receipt.get("attestation_status") == "host_signed"
    if record is None:
        if claims_signed:
            # I-08-A §6.2 G3b: a package that CLAIMS a signature and cannot
            # produce the record is rejected.  Never silently downgraded.
            raise ForecastInputError(
                "attestation_missing_record: publication_receipt claims "
                "attestation_status='host_signed' but carries no "
                "publication_attestation record (E27)"
            )
        return
    require(
        isinstance(record, dict),
        "attestation_missing_record: publication_attestation must be an object",
    )
    missing = PUBLICATION_ATTESTATION_FIELDS - set(record)
    extra = set(record) - PUBLICATION_ATTESTATION_FIELDS
    require(
        not missing and not extra,
        "attestation_payload_fields: publication_attestation field set mismatch "
        f"(missing={sorted(missing)}, extra={sorted(extra)})",
    )
    require(
        record["attestation_payload_schema_version"]
        == PUBLICATION_ATTESTATION_SCHEMA_VERSION,
        "attestation_payload_fields: publication_attestation schema version mismatch",
    )
    require(
        record["domain_separator"] == PUBLICATION_ATTESTATION_DOMAIN,
        "attestation_domain_mismatch: publication_attestation domain_separator "
        f"must be {PUBLICATION_ATTESTATION_DOMAIN!r}",
    )
    require(
        record["algorithm"] == PUBLICATION_ATTESTATION_ALGORITHM,
        "attestation_payload_fields: publication_attestation algorithm must be "
        f"{PUBLICATION_ATTESTATION_ALGORITHM!r}",
    )
    for field in ("issuer", "key_id"):
        require(
            isinstance(record[field], str) and record[field].strip(),
            f"attestation_payload_fields: publication_attestation.{field} is required",
        )
    require(
        isinstance(record["fingerprint"], str)
        and _HEX32.fullmatch(record["fingerprint"]) is not None,
        "attestation_payload_fields: publication_attestation.fingerprint must be "
        "32 lowercase hex",
    )
    require(
        isinstance(record["request_id"], str)
        and _HEX64.fullmatch(record["request_id"]) is not None,
        "attestation_payload_fields: publication_attestation.request_id must be "
        "64 lowercase hex",
    )
    require(
        isinstance(record["signed_at"], str)
        and _RFC3339_Z.fullmatch(record["signed_at"]) is not None,
        "attestation_payload_fields: publication_attestation.signed_at must be "
        "RFC3339 UTC 'Z'",
    )
    require(
        isinstance(record["signature"], str) and record["signature"],
        "attestation_missing_signature: publication_attestation.signature is "
        "required (E12)",
    )
    require(
        _HEX128.fullmatch(record["signature"]) is not None,
        "attestation_malformed_signature: publication_attestation.signature must "
        "be 128 lowercase hex (E13)",
    )
    # Binding to the live artifact: the record must describe THIS publication.
    # The record binds the two fields that are knowable BEFORE the receipt
    # exists: the payload digest (everything except `result_sha256` and
    # `publication_receipt`) and the one-shot request id.  `result_sha256` and
    # the receipt's own hash are deliberately NOT record fields — a receipt
    # cannot contain its own hash (no fixpoint), and `result_sha256` covers the
    # receipt, which contains this record.  Nothing is left unbound: the
    # signature is over `request`, and `request` is reconstructed from the
    # record's bound fields, so any change to a bound value breaks the signature.
    require(
        record["payload_sha256"] == receipt.get("validated_payload_sha256"),
        "attestation_payload_hash_mismatch: publication_attestation.payload_sha256 "
        "does not match the receipt's validated payload (E16)",
    )
    # The signed message is rebuilt from the record's fields and the record's
    # signature is verified against it, so a record cannot be assembled from a
    # signature issued for some other request.
    request = publication_attestation_request(
        request_id=record["request_id"],
        payload_sha256=record["payload_sha256"],
        result_sha256=SIGNED_RESULT_SHA256_SENTINEL,
    )
    message = canonical_sha256(request).encode("ascii")
    verify_ed25519_signature(record["fingerprint"], record["signature"], message)


def publication_attestation_request(
    *,
    request_id: str,
    payload_sha256: str,
    result_sha256: str = SIGNED_RESULT_SHA256_SENTINEL,
) -> dict[str, Any]:
    """The exact object a provider signs over (B1 §3.4, oracle revisions r3/r4).

    ``canonical_payload_sha256`` is a redundant, explicitly-named copy of
    ``payload_sha256`` so the signing target is unambiguous at the provider; the
    signing target is the whole object including it.

    ``result_sha256`` is present so the request names the artifact it is for, but
    it is fixed to :data:`SIGNED_RESULT_SHA256_SENTINEL`: a real result digest
    covers the receipt, and the receipt contains this record, so signing the real
    value would be a fixpoint.  The artifact is nevertheless bound — the payload
    digest in this request covers every result field except ``result_sha256`` and
    ``publication_receipt``, and a change to either of those changes
    ``validated_payload_sha256``/``receipt_sha256``, which the receipt checks.
    """
    return {
        "attestation_request_schema_version": PUBLICATION_ATTESTATION_SCHEMA_VERSION,
        "domain_separator": PUBLICATION_ATTESTATION_DOMAIN,
        "request_id": request_id,
        "payload_sha256": payload_sha256,
        "result_sha256": result_sha256,
        "canonical_payload_sha256": payload_sha256,
    }


def build_publication_receipt(
    result: dict[str, Any],
    verification_context: VerificationContext | None = None,
    *,
    attestation_status: str = "unattested",
    publication_attestation: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build a publication receipt from a strong-validation verification context.

    Without a ``VerificationContext`` the receipt cannot certify the strong
    gates, so the call fails closed (RED: the public API must never hand back a
    pass receipt before strong validation has run).

    *attestation_status* records whether the host attestation was actually
    signed (R2.1): ``"host_signed"`` requires a **verified**
    ``publication_attestation`` binding record produced by a completed provider
    handshake (B1 / REM-01); without one the runtime can only produce
    ``"unattested"`` publications.  Passing ``"host_signed"`` without a record
    fails closed here, so a caller cannot mint the label directly.
    """
    if not isinstance(verification_context, VerificationContext):
        raise TypeError(
            "build_publication_receipt requires a VerificationContext produced "
            "by validate_published_forecast; a receipt cannot be self-issued"
        )
    if attestation_status not in ATTESTATION_STATUSES:
        raise ValueError(
            f"attestation_status must be one of {sorted(ATTESTATION_STATUSES)}"
        )
    if attestation_status == "host_signed":
        require(
            isinstance(publication_attestation, dict),
            "attestation_missing_record: attestation_status='host_signed' "
            "requires a publication_attestation record (E27)",
        )
    receipt = {
        "receipt_schema_version": PUBLICATION_RECEIPT_SCHEMA_VERSION,
        "schema_version": result["schema_version"],
        "engine_version": ENGINE_VERSION,
        "validated_input_sha256": verification_context.validated_input_sha256,
        "validated_payload_sha256": _payload_sha256(result),
        "validator_version": verification_context.validator_version,
        "gate_ids": list(verification_context.executed_gate_ids),
        "verification_context_sha256": verification_context.context_sha256(),
        "formal_output_mode": "formal",
        "freeform_override_allowed": False,
        "attestation_status": attestation_status,
    }
    if publication_attestation is not None:
        publication_attestation = dict(publication_attestation)
        publication_attestation["payload_sha256"] = receipt[
            "validated_payload_sha256"
        ]
        # The record must name THIS publication; the caller cannot know the
        # receipt's own hash before it exists, and the receipt cannot contain a
        # hash of itself, so the binding is re-checked at validation time.
        receipt["publication_attestation"] = publication_attestation
    receipt["receipt_sha256"] = _receipt_sha256(receipt)
    return receipt


def build_draft_receipt(result: dict[str, Any]) -> dict[str, Any]:
    """Build a draft-mode receipt that certifies no strong gate.

    Draft artifacts are not investment-consumable; the receipt records the
    draft mode so consumers can distinguish draft from formal at a glance.
    """
    receipt = {
        "receipt_schema_version": PUBLICATION_RECEIPT_SCHEMA_VERSION,
        "schema_version": result["schema_version"],
        "engine_version": ENGINE_VERSION,
        "validated_input_sha256": result["input_sha256"],
        "validated_payload_sha256": _payload_sha256(result),
        "validator_version": ENGINE_VERSION,
        "gate_ids": [],
        "verification_context_sha256": None,
        "formal_output_mode": "draft",
        "freeform_override_allowed": False,
    }
    receipt["receipt_sha256"] = _receipt_sha256(receipt)
    return receipt


def validate_publication_receipt(result: dict[str, Any]) -> None:
    """Hash-consistency check on one publication receipt — **NOT a security boundary**.

    (B1 / REM-02.)  Read this before using the function as a gate.

    What this function DOES check: that the receipt travels with an artifact it
    is internally consistent with — its schema/engine/input anchors, its
    ``validated_payload_sha256`` recomputed from the result payload, the gate set
    the strong validator would execute for this content, the verification-context
    digest those gates and that input imply, the draft/formal mode consistency,
    and its own ``receipt_sha256``.

    What this function does **NOT** check, and cannot: whether the artifact is
    authentic.  Every value it compares is either recomputed from the artifact
    itself or a public, non-secret hash, so an artifact whose values and hashes
    were all recomputed together after a mutation satisfies every comparison.
    That is by construction: it never re-runs an input-gated recomputation and
    (except for the attestation record below) it never consults an
    artifact-external authority.

    The one exception is the attestation binding: a receipt claiming
    ``attestation_status == "host_signed"`` must carry a verifying
    ``publication_attestation`` record, and a present record is always verified
    (see :func:`validate_publication_attestation`).  That closes the
    label-forgery path (I-08-A E27); it does not turn the rest of this function
    into an authenticity check.

    **Consumers must call** ``revenue_report.validate_forecast_output`` (or, with
    the original input in hand, ``revenue_report.validate_published_forecast``).
    Those entry points re-run the bounded input-gated recomputations from the
    embedded/validated input and are the security boundary.  This function is
    retained for callers that only need a cheap self-consistency assertion; it
    emits no runtime warning because the strong validator itself calls it on
    every validation (see :class:`PublicationReceiptOnlyWarning`).
    """
    require(
        "publication_receipt" in result,
        "forecast output missing field: publication_receipt",
    )
    receipt = result["publication_receipt"]
    require(isinstance(receipt, dict), "publication_receipt must be an object")
    require(
        receipt.get("receipt_schema_version") == PUBLICATION_RECEIPT_SCHEMA_VERSION,
        "publication_receipt receipt_schema_version mismatch",
    )
    require(
        receipt.get("schema_version") == result["schema_version"],
        "publication_receipt schema_version mismatch",
    )
    require(
        receipt.get("engine_version") == ENGINE_VERSION,
        "publication_receipt engine_version mismatch",
    )
    require(
        receipt.get("validated_input_sha256") == result["input_sha256"],
        "publication_receipt validated_input_sha256 mismatch",
    )
    require(
        receipt.get("validated_payload_sha256") == _payload_sha256(result),
        "publication_receipt validated_payload_sha256 mismatch",
    )
    require(
        receipt.get("validator_version") == ENGINE_VERSION,
        "publication_receipt validator_version mismatch",
    )
    attestation = receipt.get("attestation_status")
    require(
        attestation in (None, "host_signed", "unattested"),
        "publication_receipt attestation_status mismatch",
    )
    expected_gates = expected_publication_gates(result)
    require(
        receipt.get("gate_ids") == list(expected_gates),
        "publication_receipt gate_ids mismatch",
    )
    if receipt.get("formal_output_mode") == "formal":
        expected_context = VerificationContext(
            result["input_sha256"], expected_gates, ENGINE_VERSION
        )
        require(
            receipt.get("verification_context_sha256")
            == expected_context.context_sha256(),
            "publication_receipt verification context mismatch",
        )
    require(
        receipt.get("formal_output_mode") in {"formal", "draft"},
        "publication_receipt formal_output_mode mismatch",
    )
    # REV-08a (ZR-705): mode/state consistency — a draft-marked receipt must
    # carry the empty gate set; a downgraded formal receipt (formal_output_mode
    # flipped to "draft" while gate_ids stay non-empty, receipt rehashed) would
    # otherwise pass the checks above.  Reject the inconsistency.
    if receipt.get("formal_output_mode") == "draft":
        require(
            not receipt.get("gate_ids"),
            "publication_receipt draft mode must have empty gate_ids",
        )
    require(
        receipt.get("freeform_override_allowed") is False,
        "publication_receipt freeform_override_allowed must be false",
    )
    require(
        receipt.get("receipt_sha256") == _receipt_sha256(receipt),
        "publication_receipt receipt_sha256 mismatch",
    )
    # B1 / REM-01: the label is not accepted on set membership.  A `host_signed`
    # claim without a verifying record is rejected (I-08-A E27 / G3b), and a
    # record that IS present is verified even when the label is `unattested`,
    # so a record can never be present-but-ignored.
    if receipt.get("formal_output_mode") == "formal":
        validate_publication_attestation(result, receipt)
