"""Validate an explicit policy upgrade without weakening the legacy drift guard."""
from copy import deepcopy
from hashlib import sha256
import json
from pathlib import Path
import subprocess

import pytest

from company_wiki.document_understanding.profiles import registry, list_profiles


ROOT = next(parent for parent in Path(__file__).resolve().parents if (parent / "pyproject.toml").is_file())
BASE = Path(__file__).resolve().parent
FIXTURE = "tests/fixtures/du9_geometry_policy/legacy_profile_sha256.json"
CATALOG = "src/company_wiki/document_understanding/profiles/reading_catalog.json"
EXPECTED_CHANGED = {"hk_periodic", "sec_20f", "prospectus", "earnings_call"}


def git_json(ref, path):
    return json.loads(subprocess.check_output(["git", "show", ref + ":" + path], cwd=ROOT, text=True, encoding="utf-8"))


def digest(value):
    return sha256(json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def wires():
    return {p["profile_id"]: digest(p) for p in list_profiles()}


def test_exact_four_snapshots_are_derived_from_reviewed_old_and_new_policy_bytes(monkeypatch):
    old = git_json("912f6fbd", FIXTURE)
    new = json.loads((ROOT / FIXTURE).read_text(encoding="utf-8"))
    assert len(old) == 15 and old.keys() == new.keys()
    assert {key for key in old if old[key] != new[key]} == EXPECTED_CHANGED
    assert wires() == new
    before_catalog = git_json("912f6fbd^", CATALOG)
    before_families = {f["id"]: f for f in before_catalog["families"]}
    current_families = {f["id"]: f for f in registry._CATALOG["families"]}
    assert {key for key in before_families if before_families[key] != current_families[key]} == {
        "sec_20f", "hk_interim_report", "earnings_call_transcript", "prospectus_hk", "prospectus_cn"}
    with monkeypatch.context() as patch:
        patch.setattr(registry, "_CATALOG", before_catalog)
        assert wires() == old
    receipt = json.loads((BASE.parent / "policy-baseline-upgrade.json").read_text(encoding="utf-8"))
    assert set(receipt["changed"]) == EXPECTED_CHANGED
    assert set(receipt["unchanged_profile_ids"]) == old.keys() - EXPECTED_CHANGED
    assert all(receipt["changed"][key] == {"before": old[key], "after": new[key]} for key in EXPECTED_CHANGED)
    original_review = json.loads((BASE / "report.json").read_text(encoding="utf-8"))
    assert all(sha256((ROOT / p).read_bytes()).hexdigest() == h for p, h in original_review["reviewed_sha256"].items())


def test_original_drift_assertion_still_rejects_an_unapproved_policy_change(monkeypatch):
    from unit.du9_geometry_policy import test_geometry_policy as original_gate
    changed = deepcopy(registry._CATALOG)
    next(f for f in changed["families"] if f["id"] == "cn_annual_report")["reading_questions"].append("Unapproved independent drift probe.")
    monkeypatch.setattr(registry, "_CATALOG", changed)
    with pytest.raises(AssertionError):
        original_gate.test_legacy_wire_fingerprints_only_change_with_an_explicit_policy_upgrade()


def test_geometry_metadata_alone_still_cannot_leak_into_legacy_wires(monkeypatch):
    from unit.du9_geometry_policy import test_geometry_policy as original_gate
    changed = deepcopy(registry._CATALOG)
    next(f for f in changed["families"] if f["id"] == "cn_annual_report")["sections"][0]["geometry_intent"] = {
        "discover": "context_only", "fine": "explicit_only", "demand_class": "context"}
    monkeypatch.setattr(registry, "_CATALOG", changed)
    original_gate.test_legacy_wire_fingerprints_only_change_with_an_explicit_policy_upgrade()
