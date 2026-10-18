"""The five P4 judgment classes as pure comparators (card 5.5).

Every function takes explicit inputs and returns outcomes; none of them reads the
environment, spawns a process, or touches the network, so each rule can be driven
directly with deliberately wrong inputs.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

from . import constants as C
from .jsonio import sha256_bytes


@dataclass(frozen=True)
class Outcome:
    """One named check result: a status, an optional error code, and detail."""

    name: str
    status: str
    code: str | None = None
    detail: dict[str, Any] = field(default_factory=dict)

    @property
    def ok(self) -> bool:
        return self.status == "pass"

    def reason(self) -> str | None:
        if self.status == "pass":
            return None
        return self.code or self.detail.get("reason") or self.status


def _fail(name: str, code: str, **detail: Any) -> Outcome:
    return Outcome(name=name, status="fail", code=code, detail=detail)


def _pass(name: str, **detail: Any) -> Outcome:
    return Outcome(name=name, status="pass", detail=detail)


# --- 5.5.1 ref roundtrip -----------------------------------------------------

def check_ref_roundtrip(
    *,
    expected_ref: dict[str, Any],
    manifest: dict[str, Any],
    receipt: dict[str, Any],
    raw_bytes: bytes,
    bundle_sha256: str | None = None,
    recomputed_bundle_sha256: str | None = None,
) -> list[Outcome]:
    """Manifest vs read receipt identity, raw bytes, and bundle self-consistency."""
    outcomes: list[Outcome] = []

    for side_name, side in (("manifest", manifest), ("receipt", receipt)):
        missing = sorted(
            key for key in C.REF_ROUNDTRIP_FIELDS if key not in side
        )
        if missing:
            outcomes.append(_fail(
                f"ref_roundtrip_{side_name}_fields", C.CODE_FIELD_MISSING,
                missing=missing,
            ))
        else:
            outcomes.append(_pass(f"ref_roundtrip_{side_name}_fields"))

    outcomes.append(Outcome(
        name="manifest_vs_receipt",
        status=(
            "pass"
            if all(manifest.get(key) == receipt.get(key) for key in C.REF_ROUNDTRIP_FIELDS)
            else "fail"
        ),
        code=None if all(
            manifest.get(key) == receipt.get(key) for key in C.REF_ROUNDTRIP_FIELDS
        ) else C.CODE_FIELD_MISSING,
        detail={
            "differing": sorted(
                key for key in C.REF_ROUNDTRIP_FIELDS
                if manifest.get(key) != receipt.get(key)
            )
        },
    ))

    outcomes.append(Outcome(
        name="manifest_matches_expected_ref",
        status=(
            "pass"
            if all(manifest.get(key) == expected_ref.get(key)
                   for key in C.REF_ROUNDTRIP_FIELDS)
            else "fail"
        ),
        code=None if all(
            manifest.get(key) == expected_ref.get(key)
            for key in C.REF_ROUNDTRIP_FIELDS
        ) else C.CODE_FIELD_MISSING,
        detail={
            "differing": sorted(
                key for key in C.REF_ROUNDTRIP_FIELDS
                if manifest.get(key) != expected_ref.get(key)
            )
        },
    ))

    actual_sha = sha256_bytes(raw_bytes)
    outcomes.append(Outcome(
        name="read_bytes_sha256",
        status="pass" if actual_sha == expected_ref["content_sha256"] else "fail",
        code=None if actual_sha == expected_ref["content_sha256"]
        else C.CODE_FIELD_MISSING,
        detail={"expected": expected_ref["content_sha256"], "actual": actual_sha},
    ))

    outcomes.append(Outcome(
        name="read_bytes_size",
        status="pass" if len(raw_bytes) == expected_ref["byte_size"] else "fail",
        code=None if len(raw_bytes) == expected_ref["byte_size"]
        else C.CODE_FIELD_MISSING,
        detail={"expected": expected_ref["byte_size"], "actual": len(raw_bytes)},
    ))

    if bundle_sha256 is not None and recomputed_bundle_sha256 is not None:
        outcomes.append(Outcome(
            name="bundle_sha256_recomputed",
            status="pass" if bundle_sha256 == recomputed_bundle_sha256 else "fail",
            code=None if bundle_sha256 == recomputed_bundle_sha256
            else C.CODE_FIELD_MISSING,
            detail={"declared": bundle_sha256, "recomputed": recomputed_bundle_sha256},
        ))

    return outcomes


# --- 5.5.2 identity / period -------------------------------------------------

def check_identity_period(
    *, manifest: dict[str, Any], facts: dict[str, Any]
) -> list[Outcome]:
    """Field-by-field facts comparison; a filled unknown is never allowed."""
    outcomes: list[Outcome] = []
    unknown_fields = sorted(set(facts) - C.FACT_KEY_SET)
    outcomes.append(Outcome(
        name="facts_shape",
        status="pass" if not unknown_fields and C.FACT_KEY_SET <= set(facts) else "fail",
        code=None if not unknown_fields and C.FACT_KEY_SET <= set(facts)
        else C.CODE_FIELD_MISSING,
        detail={
            "unknown": unknown_fields,
            "missing": sorted(C.FACT_KEY_SET - set(facts)),
        },
    ))

    filled: list[str] = []
    mismatched: list[str] = []
    for key in C.FACT_KEYS:
        if key not in facts or key not in manifest:
            continue
        left, right = manifest.get(key), facts.get(key)
        if (left is None) != (right is None):
            filled.append(key)
        elif left != right:
            mismatched.append(key)

    outcomes.append(Outcome(
        name="facts_unknown_not_filled",
        status="fail" if filled else "pass",
        code=C.CODE_FIELD_MISSING if filled else None,
        detail={"filled_fields": filled},
    ))
    outcomes.append(Outcome(
        name="facts_values_match_manifest",
        status="fail" if mismatched else "pass",
        code=C.CODE_FIELD_MISSING if mismatched else None,
        detail={"mismatched_fields": mismatched},
    ))

    published_ok = not (
        manifest.get("published_date") is None
        and facts.get("published_date") is not None
    )
    outcomes.append(Outcome(
        name="published_date_unknown_preserved",
        status="pass" if published_ok else "fail",
        code=None if published_ok else C.CODE_FIELD_MISSING,
        detail={
            "manifest_published_date": manifest.get("published_date"),
            "consumer_published_date": facts.get("published_date"),
        },
    ))
    return outcomes


# --- 5.5.3 units -------------------------------------------------------------

_DIGIT_RUN = re.compile(r"\d[\d,.]*")


def _magnitude_tokens(text: str) -> set[str]:
    """Numeric literals in ``text``, comma/space stripped per literal."""
    return {match.replace(",", "") for match in _DIGIT_RUN.findall(text)}


def check_unit_grounding(
    *,
    decoded_text: str,
    cwp_spans: list[dict[str, Any]],
    quotes: list[dict[str, Any]],
) -> list[Outcome]:
    """Unit tokens must be substrings of their quote and grounded in the source."""
    outcomes: list[Outcome] = []

    span_by_text = {
        str(span.get("raw_text")): span for span in cwp_spans
        if isinstance(span.get("raw_text"), str)
    }

    for index, quote in enumerate(quotes):
        label = f"quote[{index}]"
        if not isinstance(quote, dict) or not isinstance(quote.get("text"), str):
            outcomes.append(_fail(label, C.CODE_FIELD_MISSING, shape="invalid"))
            continue
        text = quote["text"]
        tokens = quote.get("unit_tokens")
        if not isinstance(tokens, list) or not all(
            isinstance(item, dict) and isinstance(item.get("text"), str)
            for item in tokens
        ):
            outcomes.append(_fail(label, C.CODE_FIELD_MISSING, shape="unit_tokens"))
            continue

        token_texts = [item["text"] for item in tokens]

        if not text:
            outcomes.append(_fail(label, C.CODE_UNIT_RESCALED, text="empty"))
            continue

        ungrounded = [token for token in token_texts if token not in text]
        outcomes.append(Outcome(
            name=f"{label}_tokens_are_substrings",
            status="fail" if ungrounded else "pass",
            code=C.CODE_UNIT_RESCALED if ungrounded else None,
            detail={"ungrounded_tokens": ungrounded, "text": text},
        ))

        in_source = text in decoded_text
        outcomes.append(Outcome(
            name=f"{label}_text_present_in_source",
            status="pass" if in_source else "fail",
            code=None if in_source else C.CODE_UNIT_RESCALED,
            detail={
                "text": text,
                "source_magnitudes": sorted(_magnitude_tokens(decoded_text)),
                "quote_magnitudes": sorted(_magnitude_tokens(text)),
            },
        ))

        if in_source:
            span = span_by_text.get(text)
            if span is None:
                outcomes.append(Outcome(
                    name=f"{label}_grounded_by_cwp_span",
                    status="fail",
                    code=C.CODE_UNIT_RESCALED,
                    detail={"reason": "no CWP span carries this quote text"},
                ))
            else:
                expected = span.get("unit_tokens") or []
                lost = [token for token in expected if token not in token_texts]
                outcomes.append(Outcome(
                    name=f"{label}_unit_tokens_preserved",
                    status="fail" if lost else "pass",
                    code=C.CODE_UNIT_RESCALED if lost else None,
                    detail={"lost_tokens": lost, "expected": expected},
                ))

    if not quotes:
        outcomes.append(Outcome(
            name="quotes_present", status="fail", code=C.CODE_FIELD_MISSING,
            detail={"reason": "consumer reported no quotes for a spanned source"},
        ))
    return outcomes


# --- 5.5.4 unknown availability ---------------------------------------------

def check_unknown_availability(
    *, cwp_availability_evidence: Any, availability: dict[str, Any]
) -> list[Outcome]:
    """A null upstream evidence must stay ``source_availability_unknown``."""
    outcomes: list[Outcome] = []
    if not isinstance(availability, dict):
        return [_fail("availability_shape", C.CODE_FIELD_MISSING, shape="not-an-object")]
    unknown_extra = sorted(set(availability) - C.AVAILABILITY_KEYS)
    missing = sorted(C.AVAILABILITY_KEYS - set(availability))
    outcomes.append(Outcome(
        name="availability_shape",
        status="fail" if unknown_extra or missing else "pass",
        code=C.CODE_FIELD_MISSING if unknown_extra or missing else None,
        detail={"unknown": unknown_extra, "missing": missing},
    ))

    if cwp_availability_evidence is None:
        status_ok = availability.get("status") == C.AVAILABILITY_UNKNOWN
        outcomes.append(Outcome(
            name="unknown_preserved",
            status="pass" if status_ok else "fail",
            code=None if status_ok else C.CODE_AVAILABILITY_LOST,
            detail={
                "expected": C.AVAILABILITY_UNKNOWN,
                "actual": availability.get("status"),
            },
        ))
        evidence_ok = availability.get("evidence") is None
        outcomes.append(Outcome(
            name="unknown_evidence_null",
            status="pass" if evidence_ok else "fail",
            code=None if evidence_ok else C.CODE_AVAILABILITY_LOST,
            detail={"actual": availability.get("evidence")},
        ))
    return outcomes


# --- 5.5.5 zero network / zero model ----------------------------------------

def check_zero_network_model(
    *, attempts: tuple[str, ...], observations: list[dict[str, Any]],
    llm_client_imported: bool,
) -> list[Outcome]:
    """Prove no network entry point fired and no model was called."""
    outcomes: list[Outcome] = []
    outcomes.append(Outcome(
        name="no_network_attempt",
        status="fail" if attempts else "pass",
        code=C.CODE_NETWORK_ATTEMPTED if attempts else None,
        detail={"attempts": list(attempts)},
    ))
    outcomes.append(Outcome(
        name="llm_client_not_imported",
        status="fail" if llm_client_imported else "pass",
        code=C.CODE_MODEL_ATTEMPTED if llm_client_imported else None,
        detail={"imported": llm_client_imported},
    ))

    counted: list[dict[str, Any]] = []
    for observation in observations:
        calls = observation.get("model_calls")
        count = calls.get("count") if isinstance(calls, dict) else None
        counted.append({"count": count})
    bad = [item for item in counted if item["count"] != 0]
    outcomes.append(Outcome(
        name="consumer_model_calls_zero",
        status="fail" if bad else "pass",
        code=C.CODE_MODEL_ATTEMPTED if bad else None,
        detail={"observed": counted},
    ))

    downloads: list[Any] = []
    for observation in observations:
        payload = observation.get("downloads")
        downloads.append(payload.get("count") if isinstance(payload, dict) else None)
    bad_downloads = [item for item in downloads if item != 0]
    outcomes.append(Outcome(
        name="consumer_downloads_zero",
        status="fail" if bad_downloads else "pass",
        code=C.CODE_NETWORK_ATTEMPTED if bad_downloads else None,
        detail={"observed": downloads},
    ))
    return outcomes


def summarize(outcomes: list[Outcome]) -> str:
    """``pass`` only when every outcome passed; a mixed result is ``fail``."""
    return "pass" if all(item.ok for item in outcomes) else "fail"


def failure_codes(outcomes: list[Outcome]) -> list[str]:
    return sorted({item.code for item in outcomes if item.code})
