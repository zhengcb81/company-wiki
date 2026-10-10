"""One-off patch applier: fetch_filing.py M3-USAGE GREEN (PWF audit copy)."""
import io

p = r"C:/Users/郑曾波/.codex/worktrees/m3-acquisition-usage-20261010/filing-fetch/scripts/fetch_filing.py"
t = io.open(p, encoding="utf-8").read()

# 1) operation DTO field whitelist gains the sibling
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

# 2) both diagnose call sites unpack the fourth element
old = "        code, cause, receipt = ff_provider_cause.diagnose_stderr_observation("
assert t.count(old) == 2
t = t.replace(old, "        code, cause, receipt, observation = ff_provider_cause.diagnose_stderr_observation(")

# 4) _validated_operation: compute the sibling next to the receipt
old = '''    receipt = ff_provider_cause.validated_acquisition_failure(payload.get("acquisition_failure"))
    if ('''
assert t.count(old) == 1
t = t.replace(old, '''    receipt = ff_provider_cause.validated_acquisition_failure(payload.get("acquisition_failure"))
    observation = ff_provider_cause.validated_acquisition_observation(
        payload.get("acquisition_observation"))
    if (''')

# 5) remaining acquisition_failure=receipt sites (all in _validated_operation)
old = "            acquisition_failure=receipt,"
assert t.count(old) == 7, t.count(old)
t = t.replace(old, "            acquisition_failure=receipt,\n            acquisition_observation=observation,")

# 6) v2 gap attach
old = '''    receipt = ff_provider_cause.validated_acquisition_failure(result.get("acquisition_failure"))
    if receipt is not None:
        gap["acquisition_failure"] = receipt
    return gap'''
new = '''    receipt = ff_provider_cause.validated_acquisition_failure(result.get("acquisition_failure"))
    if receipt is not None:
        gap["acquisition_failure"] = receipt
    observation = ff_provider_cause.validated_acquisition_observation(
        result.get("acquisition_observation"))
    if observation is not None:
        gap["acquisition_observation"] = observation
    return gap'''
assert t.count(old) == 1
t = t.replace(old, new)

# 7) v2 handle attach
old = '''        "policy_hash": result.get("policy_hash"),
    }
    _record_download_events(stats, handle)'''
new = '''        "policy_hash": result.get("policy_hash"),
    }
    observation = ff_provider_cause.validated_acquisition_observation(
        result.get("acquisition_observation"))
    if observation is not None:
        handle["acquisition_observation"] = observation
    _record_download_events(stats, handle)'''
assert t.count(old) == 1
t = t.replace(old, new)

# 8) v2 non-completed status errors keep the sibling
old = '''            acquisition_failure=ff_provider_cause.validated_acquisition_failure(result.get("acquisition_failure")),
        )
    outcome = result.get("outcome")'''
new = '''            acquisition_failure=ff_provider_cause.validated_acquisition_failure(result.get("acquisition_failure")),
            acquisition_observation=ff_provider_cause.validated_acquisition_observation(
                result.get("acquisition_observation")),
        )
    outcome = result.get("outcome")'''
assert t.count(old) == 1
t = t.replace(old, new)

# 9) v2 error envelope emission
old = '''                upstream_cause=exc.upstream_cause,
                acquisition_failure=exc.acquisition_failure,
                stage=exc.stage,
                attempts=exc.attempts,
            )'''
new = '''                upstream_cause=exc.upstream_cause,
                acquisition_failure=exc.acquisition_failure,
                stage=exc.stage,
                attempts=exc.attempts,
                acquisition_observation=exc.acquisition_observation,
            )'''
assert t.count(old) == 1
t = t.replace(old, new)

io.open(p, "w", encoding="utf-8", newline="\n").write(t)
print("fetch_filing patched")
