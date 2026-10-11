from pathlib import Path
root = Path("C:/Users/郑曾波/Projects/_harness_worktrees/w05/audit-loop-root")
p = root / "skills/revenue-forecast-audit/scripts/pool_progress.py"
t = p.read_text(encoding="utf-8")
old = '    return (not reasons), reasons\n'
assert t.count(old) == 1
t = t.replace(old, '''    if any(entry.get("cost_usd") is None for entry in state["possibly_paid_invocation_refs"]):
        reasons.append("not_clean_pending_charge")
    return (not reasons), reasons
''')
old = '            "pending_reconciles": pending,\n'
assert old in t
t = t.replace(old, '''            "pending_reconciles": pending,
            "open_major_refs": [entry["ref"] for entry in state["open_root_causes"]
                                 if not entry["fixed"] and _is_major(entry["severity"], entry["substantive"])],
''')
old = '    if streak >= DEFAULT_CLEAN_STOP:\n        if facts["outstanding_retests"]:'
assert old in t
t = t.replace(old, '''    if streak >= DEFAULT_CLEAN_STOP:
        if facts["open_major_refs"]:
            return {"action": "resume_remediation",
                    "why": "new clean samples cannot close older unresolved major findings",
                    "args": {"refs": facts["open_major_refs"]}}
        if facts["outstanding_retests"]:''')
old = '        elif criteria["missing_markets_obtainable"]:'
assert old in t
t = t.replace(old, '''        elif criteria["open_major_refs"]:
            diagnostics.append(_diag("stop_criteria_blocked_open_majors",
                                     "older major findings remain unresolved; sampling does not close them"))
        elif criteria["missing_markets_obtainable"]:''')
p.write_bytes(t.encode())
print("Closed unknown-charge clean and global unresolved-major stop rules")
