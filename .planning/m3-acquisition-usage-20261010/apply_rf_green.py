"""One-off patch applier: RF M3-USAGE GREEN (PWF audit copy)."""
import io

RF = r"C:/Users/郑曾波/.codex/worktrees/m3-acquisition-usage-20261010/revenue-forecast/scripts"

# ---------------- filing_upstream_cause.py ----------------
p = RF + "/filing_upstream_cause.py"
t = io.open(p, encoding="utf-8").read()

old = '''def failure_observation(payload: Any) -> dict[str, Any]:'''
new = '''# M3-USAGE: observed-usage sibling. Pure validation of the producer's
# operation observation; no recomputation, no fee inference, no MIME or
# identity re-verification — values pass through or the object is dropped.
ACQUISITION_OBSERVATION_SCHEMA = "acquisition-observation/1"
OBSERVATION_OUTCOMES = frozenset({
    "downloaded_new", "deduplicated_after_download",
    "reused_before_download", "reused_after_discovery",
    "missing", "ambiguous", "gap_plan", "gap_plan_provider_unavailable",
    "failed",
})
_OBSERVATION_KEYS = frozenset({
    "schema_version", "usage_scope", "outcome", "provider_started",
    "usage_complete", "wire_body_bytes", "wire_usage_complete",
    "entity_body_bytes", "http_exchanges", "http_exchanges_complete",
    "cost_usd", "http_observation",
})
_HTTP_OBSERVATION_KEYS = frozenset({
    "status_code", "mime_type", "content_encoding", "wire_content_length",
})


def validated_acquisition_observation(value: Any) -> dict[str, Any] | None:
    """Copy the operation observation iff it matches the closed contract."""
    if not isinstance(value, dict) or set(value) != _OBSERVATION_KEYS:
        return None
    if (value["schema_version"] != ACQUISITION_OBSERVATION_SCHEMA
            or value["usage_scope"] != "operation"):
        return None
    outcome = value.get("outcome")
    if outcome not in OBSERVATION_OUTCOMES:
        return None
    result: dict[str, Any] = {
        "schema_version": ACQUISITION_OBSERVATION_SCHEMA,
        "usage_scope": "operation",
        "outcome": outcome,
    }
    for key in ("provider_started", "usage_complete", "wire_usage_complete",
                "http_exchanges_complete"):
        flag = value.get(key)
        if flag is not None and type(flag) is not bool:
            return None
        result[key] = flag
    for key in ("wire_body_bytes", "entity_body_bytes"):
        count = value.get(key)
        if type(count) is not int or count < 0:
            return None
        result[key] = count
    exchanges = value.get("http_exchanges")
    if type(exchanges) is not int or exchanges < 0:
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
        if (not isinstance(http_observation, dict)
                or set(http_observation) != _HTTP_OBSERVATION_KEYS):
            return None
        status = http_observation.get("status_code")
        if type(status) is not int or status < 0:
            return None
        checked = {"status_code": status}
        for key in ("mime_type", "content_encoding"):
            text = http_observation.get(key)
            if not isinstance(text, str) or not text or len(text) > 128:
                return None
            checked[key] = text
        length = http_observation.get("wire_content_length")
        if length is not None and (type(length) is not int or length < 0):
            return None
        checked["wire_content_length"] = length
        http_observation = checked
    result["http_observation"] = http_observation
    return result


def failure_observation(payload: Any) -> dict[str, Any]:'''
assert t.count(old) == 1
t = t.replace(old, new)

old = '''    cause = validated_cause(detail.get("upstream_cause"))
    receipt = validated_acquisition_failure(detail.get("acquisition_failure"))
    if cause is not None:
        result["upstream_cause"] = cause
    if receipt is not None:
        result["acquisition_failure"] = receipt'''
new = '''    cause = validated_cause(detail.get("upstream_cause"))
    receipt = validated_acquisition_failure(detail.get("acquisition_failure"))
    observation = validated_acquisition_observation(detail.get("acquisition_observation"))
    if cause is not None:
        result["upstream_cause"] = cause
    if receipt is not None:
        result["acquisition_failure"] = receipt
    if observation is not None:
        result["acquisition_observation"] = observation'''
assert t.count(old) == 1
t = t.replace(old, new)
io.open(p, "w", encoding="utf-8", newline="\n").write(t)
print("filing_upstream_cause patched")

# ---------------- filing_fetch_client.py ----------------
p = RF + "/filing_fetch_client.py"
t = io.open(p, encoding="utf-8").read()

old = '''        upstream_cause: dict[str, Any] | None = None,
        acquisition_failure: dict[str, Any] | None = None,
        stage: str | None = None,
        attempts: int | None = None,
        calls: int | None = None,
        downloads: int | None = None,
        source_failure_reason: str | None = None,
    ) -> None:
        super().__init__(message)
        self.status = status if isinstance(status, str) and status in FAILURE_STATUSES else None'''
new = '''        upstream_cause: dict[str, Any] | None = None,
        acquisition_failure: dict[str, Any] | None = None,
        stage: str | None = None,
        attempts: int | None = None,
        calls: int | None = None,
        downloads: int | None = None,
        source_failure_reason: str | None = None,
        acquisition_observation: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.status = status if isinstance(status, str) and status in FAILURE_STATUSES else None'''
assert t.count(old) == 1
t = t.replace(old, new)

old = '''        observed = failure_observation({"upstream_cause": upstream_cause, "acquisition_failure": acquisition_failure,
                                       "stage": stage, "attempts": attempts, "calls": calls, "downloads": downloads,
                                       "source_failure_reason": source_failure_reason})
        self.upstream_cause = observed.get("upstream_cause")
        self.acquisition_failure = observed.get("acquisition_failure")'''
new = '''        observed = failure_observation({"upstream_cause": upstream_cause, "acquisition_failure": acquisition_failure,
                                       "stage": stage, "attempts": attempts, "calls": calls, "downloads": downloads,
                                       "source_failure_reason": source_failure_reason,
                                       "acquisition_observation": acquisition_observation})
        self.upstream_cause = observed.get("upstream_cause")
        self.acquisition_failure = observed.get("acquisition_failure")
        self.acquisition_observation = observed.get("acquisition_observation")'''
assert t.count(old) == 1
t = t.replace(old, new)

old = '''    upstream_cause: dict[str, Any] | None = None,
    acquisition_failure: dict[str, Any] | None = None,
    stage: str | None = None,
    attempts: int | None = None,
    calls: int | None = None,
    downloads: int | None = None,
    source_failure_reason: str | None = None,
) -> None:
    """Write a structured error document to stderr (success stream on stdout)."""'''
new = '''    upstream_cause: dict[str, Any] | None = None,
    acquisition_failure: dict[str, Any] | None = None,
    stage: str | None = None,
    attempts: int | None = None,
    calls: int | None = None,
    downloads: int | None = None,
    source_failure_reason: str | None = None,
    acquisition_observation: dict[str, Any] | None = None,
) -> None:
    """Write a structured error document to stderr (success stream on stdout)."""'''
assert t.count(old) == 1
t = t.replace(old, new)

old = '''    payload.update(failure_observation({"upstream_cause": upstream_cause, "acquisition_failure": acquisition_failure,
                                       "stage": stage, "attempts": attempts, "calls": calls, "downloads": downloads,
                                       "source_failure_reason": source_failure_reason}))'''
new = '''    payload.update(failure_observation({"upstream_cause": upstream_cause, "acquisition_failure": acquisition_failure,
                                       "stage": stage, "attempts": attempts, "calls": calls, "downloads": downloads,
                                       "source_failure_reason": source_failure_reason,
                                       "acquisition_observation": acquisition_observation}))'''
assert t.count(old) == 1
t = t.replace(old, new)

old = '''            stage=exc.stage, attempts=exc.attempts, calls=exc.calls, downloads=exc.downloads,
            source_failure_reason=exc.source_failure_reason,
        )
        return 2'''
new = '''            stage=exc.stage, attempts=exc.attempts, calls=exc.calls, downloads=exc.downloads,
            source_failure_reason=exc.source_failure_reason,
            acquisition_observation=exc.acquisition_observation,
        )
        return 2'''
assert t.count(old) == 1
t = t.replace(old, new)
io.open(p, "w", encoding="utf-8", newline="\n").write(t)
print("filing_fetch_client patched")

# ---------------- source_preparation.py ----------------
p = RF + "/source_preparation.py"
t = io.open(p, encoding="utf-8").read()

old = '''    def __init__(self, message: str, *, upstream_cause: dict | None = None,
                 acquisition_failure: dict | None = None, stage: str | None = None,
                 attempts: int | None = None, calls: int | None = None, downloads: int | None = None,
                 source_failure_reason: str | None = None):
        super().__init__(message)
        observed = failure_observation({"upstream_cause": upstream_cause, "acquisition_failure": acquisition_failure,
                                       "stage": stage, "attempts": attempts, "calls": calls, "downloads": downloads,
                                       "source_failure_reason": source_failure_reason})
        self.upstream_cause = observed.get("upstream_cause")
        self.acquisition_failure = observed.get("acquisition_failure")'''
new = '''    def __init__(self, message: str, *, upstream_cause: dict | None = None,
                 acquisition_failure: dict | None = None, stage: str | None = None,
                 attempts: int | None = None, calls: int | None = None, downloads: int | None = None,
                 source_failure_reason: str | None = None,
                 acquisition_observation: dict | None = None):
        super().__init__(message)
        observed = failure_observation({"upstream_cause": upstream_cause, "acquisition_failure": acquisition_failure,
                                       "stage": stage, "attempts": attempts, "calls": calls, "downloads": downloads,
                                       "source_failure_reason": source_failure_reason,
                                       "acquisition_observation": acquisition_observation})
        self.upstream_cause = observed.get("upstream_cause")
        self.acquisition_failure = observed.get("acquisition_failure")
        self.acquisition_observation = observed.get("acquisition_observation")'''
assert t.count(old) == 1
t = t.replace(old, new)

old = '''        failure.update(failure_observation({key: getattr(exc, key, None) for key in
                       ("upstream_cause", "acquisition_failure", "stage", "attempts", "calls", "downloads", "source_failure_reason")}))'''
new = '''        failure.update(failure_observation({key: getattr(exc, key, None) for key in
                       ("upstream_cause", "acquisition_failure", "stage", "attempts", "calls", "downloads",
                        "source_failure_reason", "acquisition_observation")}))'''
assert t.count(old) == 1
t = t.replace(old, new)
io.open(p, "w", encoding="utf-8", newline="\n").write(t)
print("source_preparation patched")
