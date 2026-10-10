"""One-off patch applier for FF M3-USAGE GREEN (kept in PWF for audit)."""
import io

FF = r"C:/Users/郑曾波/.codex/worktrees/m3-acquisition-usage-20261010/filing-fetch/scripts"

# ---------------- ff_provider_cause.py ----------------
import os as _os

p = FF + "/ff_provider_cause.py"
t = io.open(p, encoding="utf-8").read()
if "ACQUISITION_OBSERVATION_SCHEMA" not in t:

    old = '''_ACQUISITION_FAILURE_KEYS = frozenset({
        "schema_version", "code", "retryable", "provider_started", "usage_complete",
        "acquisition_usage", "usage_scope",
    })
    _USAGE_KEYS = frozenset({"schema_version", "response_bytes", "cost_usd"})'''
    new = '''_ACQUISITION_FAILURE_KEYS = frozenset({
        "schema_version", "code", "retryable", "provider_started", "usage_complete",
        "acquisition_usage", "usage_scope",
    })
    _USAGE_KEYS = frozenset({"schema_version", "response_bytes", "cost_usd"})

    # M3-USAGE: observed-usage sibling, passed through verbatim once validated.
    # FF never recomputes totals, never infers a fee, never re-verifies MIME or
    # company identity; producer values survive or the whole object is dropped.
    ACQUISITION_OBSERVATION_SCHEMA = "acquisition-observation/1"
    _OBSERVATION_OUTCOMES = frozenset({
        "downloaded_new", "deduplicated_after_download",
        "reused_before_download", "reused_after_discovery",
        "missing", "ambiguous", "gap_plan", "gap_plan_provider_unavailable",
        "failed",
    })
    _ACQUISITION_OBSERVATION_KEYS = frozenset({
        "schema_version", "usage_scope", "outcome", "provider_started",
        "usage_complete", "wire_body_bytes", "wire_usage_complete",
        "entity_body_bytes", "http_exchanges", "http_exchanges_complete",
        "cost_usd", "http_observation",
    })
    _HTTP_OBSERVATION_KEYS = frozenset({
        "status_code", "mime_type", "content_encoding", "wire_content_length",
    })'''
    assert t.count(old) == 1
    t = t.replace(old, new)

    old = '''def source_condition(operation: str, reason: Any) -> dict[str, Any]:'''
    new = '''def _validated_http_observation(value: Any) -> dict[str, Any] | None:
        """Finite four-field protocol metadata, or None; no arbitrary headers."""
        if not isinstance(value, dict) or set(value) != _HTTP_OBSERVATION_KEYS:
            return None
        status = value.get("status_code")
        if isinstance(status, bool) or not isinstance(status, int) or status < 0:
            return None
        result = {"status_code": status}
        for key in ("mime_type", "content_encoding"):
            text = value.get(key)
            if not isinstance(text, str) or not text or len(text) > 128:
                return None
            result[key] = text
        length = value.get("wire_content_length")
        if length is not None and (isinstance(length, bool)
                                   or not isinstance(length, int) or length < 0):
            return None
        result["wire_content_length"] = length
        return result


    def validated_acquisition_observation(value: Any) -> dict[str, Any] | None:
        """Copy the producer operation observation; any deviation drops it whole."""
        if not isinstance(value, dict) or set(value) != _ACQUISITION_OBSERVATION_KEYS:
            return None
        if (value["schema_version"] != ACQUISITION_OBSERVATION_SCHEMA
                or value["usage_scope"] != "operation"):
            return None
        outcome = value.get("outcome")
        if outcome not in _OBSERVATION_OUTCOMES:
            return None
        result: dict[str, Any] = {
            "schema_version": ACQUISITION_OBSERVATION_SCHEMA,
            "usage_scope": "operation",
            "outcome": outcome,
        }
        for key in ("provider_started", "usage_complete", "wire_usage_complete",
                    "http_exchanges_complete"):
            flag = value.get(key)
            if flag is not None and not isinstance(flag, bool):
                return None
            result[key] = flag
        for key in ("wire_body_bytes", "entity_body_bytes"):
            count = value.get(key)
            if isinstance(count, bool) or not isinstance(count, int) or count < 0:
                return None
            result[key] = count
        exchanges = value.get("http_exchanges")
        if isinstance(exchanges, bool) or not isinstance(exchanges, int) or exchanges < 0:
            return None
        result["http_exchanges"] = exchanges
        cost = value.get("cost_usd")
        if cost is not None:
            if not isinstance(cost, str):
                return None
            try:
                amount = Decimal(cost)
            except (InvalidOperation, ValueError):
                return None
            if not amount.is_finite() or amount < 0:
                return None
        result["cost_usd"] = cost
        http_observation = value.get("http_observation")
        if http_observation is not None:
            http_observation = _validated_http_observation(http_observation)
            if http_observation is None:
                return None
        result["http_observation"] = http_observation
        return result


    def source_condition(operation: str, reason: Any) -> dict[str, Any]:'''
    assert t.count(old) == 1
    t = t.replace(old, new)

    old = '''def diagnose_stderr_observation(operation: str, stderr_text: str) -> tuple[str, dict[str, Any], dict[str, Any] | None]:
        """Decode cause and the same existing producer receipt in one bounded parse."""
        payload = _parse_structured(stderr_text)
        ff_code, legacy_cause = _map_structured(payload)
        evidence = _acquisition_evidence(payload.get("acquisition_failure")) if payload else None
        receipt = validated_acquisition_failure(payload.get("acquisition_failure")) if payload else None
        if evidence is None:
            return ff_code, build_cause(operation, legacy_cause), receipt
        safe_code, started, complete = evidence
        projected = build_cause(operation, safe_code, provider_started=started, usage_complete=complete)
        # Generic taxonomy owns retry semantics. Producer retryable is diagnostic,
        # never authorization for FF to issue a second potentially charged request.
        projected["retry_scope"] = _retry_scope(legacy_cause)
        return ff_code, projected, receipt'''
    new = '''def diagnose_stderr_observation(operation: str, stderr_text: str) -> tuple[str, dict[str, Any], dict[str, Any] | None, dict[str, Any] | None]:
        """Decode cause, producer receipt and the usage observation in one parse."""
        payload = _parse_structured(stderr_text)
        ff_code, legacy_cause = _map_structured(payload)
        evidence = _acquisition_evidence(payload.get("acquisition_failure")) if payload else None
        receipt = validated_acquisition_failure(payload.get("acquisition_failure")) if payload else None
        observation = (validated_acquisition_observation(payload.get("acquisition_observation"))
                       if payload else None)
        if evidence is None:
            return ff_code, build_cause(operation, legacy_cause), receipt, observation
        safe_code, started, complete = evidence
        projected = build_cause(operation, safe_code, provider_started=started, usage_complete=complete)
        # Generic taxonomy owns retry semantics. Producer retryable is diagnostic,
        # never authorization for FF to issue a second potentially charged request.
        projected["retry_scope"] = _retry_scope(legacy_cause)
        return ff_code, projected, receipt, observation'''
    assert t.count(old) == 1
    t = t.replace(old, new)

    old = '''    code, cause, _ = diagnose_stderr_observation(operation, stderr_text)
        return code, cause'''
    new = '''    code, cause, _receipt, _observation = diagnose_stderr_observation(operation, stderr_text)
        return code, cause'''
    assert t.count(old) == 1
    t = t.replace(old, new)

    old = '''__all__ = [
        "UPSTREAM_CAUSE_SCHEMA_VERSION",
        "ACQUISITION_FAILURE_CODES",'''
    new = '''__all__ = [
        "UPSTREAM_CAUSE_SCHEMA_VERSION",
        "ACQUISITION_FAILURE_CODES",
        "ACQUISITION_OBSERVATION_SCHEMA",
        "validated_acquisition_observation",'''
    assert t.count(old) == 1
    t = t.replace(old, new)
    io.open(p, "w", encoding="utf-8", newline="\n").write(t)

print("ff_provider_cause patched")

# ---------------- filing_contracts.py ----------------
p = FF + "/filing_contracts.py"
t = io.open(p, encoding="utf-8").read()
old = '''        upstream_cause: dict[str, Any] | None = None,
        acquisition_failure: dict[str, Any] | None = None,
    ) -> None:'''
new = '''        upstream_cause: dict[str, Any] | None = None,
        acquisition_failure: dict[str, Any] | None = None,
        acquisition_observation: dict[str, Any] | None = None,
    ) -> None:'''
assert t.count(old) == 1
t = t.replace(old, new)
old = '''        self.upstream_cause = upstream_cause
        self.acquisition_failure = validated_acquisition_failure(acquisition_failure)'''
new = '''        self.upstream_cause = upstream_cause
        self.acquisition_failure = validated_acquisition_failure(acquisition_failure)
        # M3-USAGE: same fail-closed pass-through as the failure receipt —
        # only a validated operation observation rides, garbage is dropped.
        self.acquisition_observation = validated_acquisition_observation(acquisition_observation)'''
assert t.count(old) == 1
t = t.replace(old, new)
old = "from ff_provider_cause import STAGES, validated_acquisition_failure, validated_cause"
assert t.count(old) == 1
t = t.replace(old, "from ff_provider_cause import (\n    validated_acquisition_failure,\n    validated_acquisition_observation,\n    validated_cause,\n)")
io.open(p, "w", encoding="utf-8", newline="\n").write(t)
print("filing_contracts patched")

# ---------------- ff_v2_envelope.py ----------------
p = FF + "/ff_v2_envelope.py"
t = io.open(p, encoding="utf-8").read()
old = '''from ff_provider_cause import STAGES, validated_acquisition_failure, validated_cause'''
new = '''from ff_provider_cause import (
    STAGES,
    validated_acquisition_failure,
    validated_acquisition_observation,
    validated_cause,
)'''
assert t.count(old) == 1
t = t.replace(old, new)

old = '''        receipt = validated_acquisition_failure(handle.get("acquisition_failure"))
        if receipt is not None:
            filing["acquisition_failure"] = receipt
        return {
            "schema_version": FILING_V2_RESPONSE_SCHEMA_VERSION,
            "status": "gap",'''
new = '''        receipt = validated_acquisition_failure(handle.get("acquisition_failure"))
        if receipt is not None:
            filing["acquisition_failure"] = receipt
        # M3-USAGE: faithful pass-through of the producer operation observation.
        observation = validated_acquisition_observation(handle.get("acquisition_observation"))
        if observation is not None:
            filing["acquisition_observation"] = observation
        return {
            "schema_version": FILING_V2_RESPONSE_SCHEMA_VERSION,
            "status": "gap",'''
assert t.count(old) == 1
t = t.replace(old, new)

old = '''        "resolution_outcome": handle.get("resolution_outcome"),
        "download_events": events,
    }
    return {'''
new = '''        "resolution_outcome": handle.get("resolution_outcome"),
        "download_events": events,
    }
    # M3-USAGE: faithful pass-through of the producer operation observation.
    observation = validated_acquisition_observation(handle.get("acquisition_observation"))
    if observation is not None:
        filing["acquisition_observation"] = observation
    return {'''
assert t.count(old) == 1
t = t.replace(old, new)

old = '''    upstream_cause: dict[str, Any] | None = None,
    acquisition_failure: dict[str, Any] | None = None,
    stage: str | None = None,
    attempts: int | None = None,
) -> dict[str, Any]:'''
new = '''    upstream_cause: dict[str, Any] | None = None,
    acquisition_failure: dict[str, Any] | None = None,
    stage: str | None = None,
    attempts: int | None = None,
    acquisition_observation: dict[str, Any] | None = None,
) -> dict[str, Any]:'''
assert t.count(old) == 1
t = t.replace(old, new)

old = '''    receipt = validated_acquisition_failure(acquisition_failure)
    if receipt is not None:
        filing["acquisition_failure"] = receipt
    if isinstance(stage, str) and stage in STAGES:'''
new = '''    receipt = validated_acquisition_failure(acquisition_failure)
    if receipt is not None:
        filing["acquisition_failure"] = receipt
    observation = validated_acquisition_observation(acquisition_observation)
    if observation is not None:
        filing["acquisition_observation"] = observation
    if isinstance(stage, str) and stage in STAGES:'''
assert t.count(old) == 1
t = t.replace(old, new)
io.open(p, "w", encoding="utf-8", newline="\n").write(t)
print("ff_v2_envelope patched")

# ---------------- fetch_filing.py ----------------
p = FF + "/fetch_filing.py"
t = io.open(p, encoding="utf-8").read()

old = '''        "candidate",
        "gap_plan",
        "acquisition_failure",
    }
)'''
new = '''        "candidate",
        "gap_plan",
        "acquisition_failure",
        "acquisition_observation",
    }
)'''
assert t.count(old) == 1
t = t.replace(old, new)

# two diagnose_stderr_observation call sites in _run_company_wiki_json
old = """        code, cause, receipt = ff_provider_cause.diagnose_stderr_observation(
"""
assert t.count(old) == 2, t.count(old)
t = t.replace(old, '''        code, cause, receipt, observation = ff_provider_cause.diagnose_stderr_observation(
''')

old = "acquisition_failure=receipt,"
assert t.count(old) == 2, t.count(old)
t = t.replace(old, "acquisition_failure=receipt, acquisition_observation=observation,")

# v2 gap attach
old = """    receipt = ff_provider_cause.validated_acquisition_failure(result.get("acquisition_failure"))
    if receipt is not None:
        gap["acquisition_failure"] = receipt
    return gap"""
new = """    receipt = ff_provider_cause.validated_acquisition_failure(result.get("acquisition_failure"))
    if receipt is not None:
        gap["acquisition_failure"] = receipt
    observation = ff_provider_cause.validated_acquisition_observation(
        result.get("acquisition_observation"))
    if observation is not None:
        gap["acquisition_observation"] = observation
    return gap"""
assert t.count(old) == 1
t = t.replace(old, new)

# v2 handle attach (operation receipt block)
old = """    handle["operation_receipt"] = {
        "operation_schema_version": _SOURCE_OPERATION_VERSION,
        "operation": operation,
        "request_id": result["request_id"],
        "outcome": outcome,
        "download_events": events,
        "policy_hash": result.get("policy_hash"),
    }"""
new = old + """
    observation = ff_provider_cause.validated_acquisition_observation(
        result.get("acquisition_observation"))
    if observation is not None:
        handle["acquisition_observation"] = observation"""
assert t.count(old) == 1
t = t.replace(old, new)

# v2 non-completed status errors keep the observation too
old = """            acquisition_failure=ff_provider_cause.validated_acquisition_failure(result.get("acquisition_failure")),
        )
    outcome = result.get("outcome")"""
new = """            acquisition_failure=ff_provider_cause.validated_acquisition_failure(result.get("acquisition_failure")),
            acquisition_observation=ff_provider_cause.validated_acquisition_observation(
                result.get("acquisition_observation")),
        )
    outcome = result.get("outcome")"""
assert t.count(old) == 1
t = t.replace(old, new)

# v2 error envelope carries the sibling observation
old = """                upstream_cause=exc.upstream_cause,
                acquisition_failure=exc.acquisition_failure,
                stage=exc.stage,
                attempts=exc.attempts,
            )"""
new = """                upstream_cause=exc.upstream_cause,
                acquisition_failure=exc.acquisition_failure,
                stage=exc.stage,
                attempts=exc.attempts,
                acquisition_observation=exc.acquisition_observation,
            )"""
assert t.count(old) == 1
t = t.replace(old, new)
# v1 output stays frozen: the observation rides the v2 channel only.
io.open(p, "w", encoding="utf-8", newline=chr(10)).write(t)
print("fetch_filing patched")
