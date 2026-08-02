"""AUTO-3 planner/policy/registry contract tests.

Each test asserts the production module paths exist before importing them.
All tests use fixed values and tmp_path; no network, LLM or production data.
"""

import hashlib
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[2]
REGISTRY_PATH = ROOT / "src" / "company_wiki" / "automation" / "registry.py"
POLICY_PATH = ROOT / "src" / "company_wiki" / "automation" / "policy.py"
PLANNER_PATH = ROOT / "src" / "company_wiki" / "automation" / "planner.py"


def _registry_mod():
    assert REGISTRY_PATH.is_file()
    from company_wiki.automation import registry
    return registry


def _policy_mod():
    assert POLICY_PATH.is_file()
    from company_wiki.automation import policy
    return policy


def _planner_mod():
    assert PLANNER_PATH.is_file()
    from company_wiki.automation import planner
    return planner


def _models():
    from company_wiki.automation import models
    return models


INPUT_HASH = hashlib.sha256(b"auto-3-input").hexdigest()


def _make_event(m=None, event_type="source.revision_registered", **overrides):
    m = m or _models()
    defaults = dict(
        event_id="evt-auto3-001",
        event_type=event_type,
        subject_type="source_revision",
        subject_id="rev-auto3-001",
        input_hash=INPUT_HASH,
        payload_json=m.canonical_json({"key": "value"}),
        policy_version="v1",
        occurred_at="2026-07-12T09:00:00Z",
        observed_at="2026-07-12T09:00:00Z",
    )
    defaults.update(overrides)
    return m.Event(**defaults)


# --------------------------------------------------------------------------- #
# Registry tests.
# --------------------------------------------------------------------------- #
def test_registry_known_types():
    reg = _registry_mod().create_default_registry()
    known = reg.known_job_types()
    assert "source.normalize" in known
    assert "source.analyze" in known
    assert "gold.validate_receipt" in known


def test_registry_unknown_job_type_raises():
    reg = _registry_mod().create_default_registry()
    with pytest.raises(_registry_mod().UnknownJobTypeError):
        reg.get("nonexistent.handler")


def test_registry_handler_spec_frozen():
    reg = _registry_mod().create_default_registry()
    spec = reg.get("source.normalize")
    assert spec.network is False
    assert spec.llm is False
    assert spec.default_max_attempts == 2


# --------------------------------------------------------------------------- #
# Policy tests.
# --------------------------------------------------------------------------- #
def test_policy_rejects_network_handler():
    p = _policy_mod()
    r = _registry_mod()
    spec = r.HandlerSpec(
        job_type="net.handler", handler_version="1.0.0",
        input_schema="X.v1", result_schema="X.v1",
        effect_class="artifact_only", allowed_paths=("artifacts/**",),
        network=True, llm=False, default_max_attempts=1,
        retryable_errors=(), human_errors=(), terminal_errors=(),
    )
    with pytest.raises(p.PolicyViolationError, match="network"):
        p.compute_risk(spec)


def test_policy_rejects_llm_handler():
    p = _policy_mod()
    r = _registry_mod()
    spec = r.HandlerSpec(
        job_type="llm.handler", handler_version="1.0.0",
        input_schema="X.v1", result_schema="X.v1",
        effect_class="artifact_only", allowed_paths=("artifacts/**",),
        network=False, llm=True, default_max_attempts=1,
        retryable_errors=(), human_errors=(), terminal_errors=(),
    )
    with pytest.raises(p.PolicyViolationError, match="LLM"):
        p.compute_risk(spec)


def test_policy_rejects_path_outside_allowlist():
    p = _policy_mod()
    r = _registry_mod()
    spec = r.HandlerSpec(
        job_type="bad.path", handler_version="1.0.0",
        input_schema="X.v1", result_schema="X.v1",
        effect_class="artifact_only", allowed_paths=("companies/**",),
        network=False, llm=False, default_max_attempts=1,
        retryable_errors=(), human_errors=(), terminal_errors=(),
    )
    config = p.PolicyConfig(allowed_effect_paths=("artifacts/**",))
    with pytest.raises(p.PolicyViolationError, match="not covered"):
        p.compute_risk(spec, config=config)


def test_policy_rejects_excessive_fan_out():
    p = _policy_mod()
    r = _registry_mod()
    spec = r.create_default_registry().get("source.normalize")
    config = p.PolicyConfig(max_fan_out=5)
    with pytest.raises(p.PolicyViolationError, match="fan_out"):
        p.compute_risk(spec, fan_out=10, config=config)


def test_policy_computes_risk_deterministically():
    p = _policy_mod()
    r = _registry_mod()
    spec = r.create_default_registry().get("source.normalize")
    risk1 = p.compute_risk(spec)
    risk2 = p.compute_risk(spec)
    assert risk1 == risk2 == _models().RiskClass.LOW


def test_policy_schema_change_forces_high():
    p = _policy_mod()
    r = _registry_mod()
    spec = r.create_default_registry().get("source.normalize")
    risk = p.compute_risk(spec, schema_change=True)
    assert risk == _models().RiskClass.HIGH


def test_policy_knowledge_write_is_medium():
    p = _policy_mod()
    r = _registry_mod()
    spec = r.create_default_registry().get("gold.promote_reviewed")
    risk = p.compute_risk(spec)
    assert risk == _models().RiskClass.MEDIUM


# --------------------------------------------------------------------------- #
# Planner tests.
# --------------------------------------------------------------------------- #
def test_planner_deterministic_same_event_same_dag():
    pl = _planner_mod()
    r = _registry_mod()
    p = _policy_mod()
    reg = r.create_default_registry()
    config = p.PolicyConfig(allow_llm=True)
    evt = _make_event()
    dag1 = pl.plan_jobs(evt, reg, config)
    dag2 = pl.plan_jobs(evt, reg, config)
    assert dag1 == dag2


def test_planner_dag_acyclic():
    pl = _planner_mod()
    r = _registry_mod()
    p = _policy_mod()
    reg = r.create_default_registry()
    config = p.PolicyConfig(allow_llm=True)
    evt = _make_event()
    dag = pl.plan_jobs(evt, reg, config)
    # Build adjacency: temp_id → depends_on
    adj: dict[str, set[str]] = {j.temp_id: set() for j in dag.jobs}
    for child, parent in dag.dependencies:
        adj[child].add(parent)
    # DFS cycle detection.
    visited: set[str] = set()
    in_stack: set[str] = set()

    def dfs(node: str) -> bool:
        if node in in_stack:
            return True  # cycle
        if node in visited:
            return False
        visited.add(node)
        in_stack.add(node)
        for dep in adj.get(node, set()):
            if dfs(dep):
                return True
        in_stack.discard(node)
        return False

    for tid in adj:
        assert not dfs(tid), f"cycle detected involving {tid}"


def test_planner_source_revision_produces_normalize_and_analyze():
    pl = _planner_mod()
    r = _registry_mod()
    p = _policy_mod()
    reg = r.create_default_registry()
    config = p.PolicyConfig(allow_llm=True)
    evt = _make_event(event_type="source.revision_registered")
    dag = pl.plan_jobs(evt, reg, config)
    job_types = {j.job_type for j in dag.jobs}
    assert "source.normalize" in job_types
    assert "source.analyze" in job_types
    # analyze depends on normalize.
    normalize_tid = next(j.temp_id for j in dag.jobs if j.job_type == "source.normalize")
    analyze_tid = next(j.temp_id for j in dag.jobs if j.job_type == "source.analyze")
    assert (analyze_tid, normalize_tid) in dag.dependencies


def test_planner_timer_due_produces_execute_step():
    pl = _planner_mod()
    r = _registry_mod()
    _policy_mod()
    reg = r.create_default_registry()
    evt = _make_event(event_type="timer.due")
    dag = pl.plan_jobs(evt, reg)
    assert len(dag.jobs) == 1
    assert dag.jobs[0].job_type == "timer.execute_step"


def test_planner_unknown_event_fails_closed():
    pl = _planner_mod()
    r = _registry_mod()
    reg = r.create_default_registry()
    evt = _make_event(event_type="unknown.event.type")
    with pytest.raises(pl.PlannerError, match="unknown event type"):
        pl.plan_jobs(evt, reg)


def test_planner_policy_violation_propagates():
    pl = _planner_mod()
    r = _registry_mod()
    p = _policy_mod()
    reg = r.create_default_registry()
    # source.analyze requires LLM; policy forbids it.
    config = p.PolicyConfig(allow_llm=False)
    evt = _make_event(event_type="source.revision_registered")
    with pytest.raises(p.PolicyViolationError, match="LLM"):
        pl.plan_jobs(evt, reg, config)


def test_planner_analysis_proposal_produces_validate_and_review():
    pl = _planner_mod()
    r = _registry_mod()
    _policy_mod()
    reg = r.create_default_registry()
    evt = _make_event(event_type="analysis.proposal_ready")
    dag = pl.plan_jobs(evt, reg)
    job_types = {j.job_type for j in dag.jobs}
    assert "analysis.validate" in job_types
    assert "analysis.review" in job_types


def test_planner_gold_inputs_changed_produces_refresh():
    pl = _planner_mod()
    r = _registry_mod()
    reg = r.create_default_registry()
    evt = _make_event(event_type="gold.inputs_changed")
    dag = pl.plan_jobs(evt, reg)
    assert dag.jobs[0].job_type == "gold.refresh_packet"


def test_planner_review_receipt_changed_produces_validate():
    pl = _planner_mod()
    r = _registry_mod()
    reg = r.create_default_registry()
    evt = _make_event(event_type="review.receipt_changed")
    dag = pl.plan_jobs(evt, reg)
    assert dag.jobs[0].job_type == "gold.validate_receipt"


def test_planner_review_approved_produces_promote():
    pl = _planner_mod()
    r = _registry_mod()
    reg = r.create_default_registry()
    evt = _make_event(event_type="review.approved")
    dag = pl.plan_jobs(evt, reg)
    assert dag.jobs[0].job_type == "gold.promote_reviewed"


def test_planner_job_fields_populated():
    pl = _planner_mod()
    r = _registry_mod()
    p = _policy_mod()
    reg = r.create_default_registry()
    config = p.PolicyConfig(allow_llm=True)
    evt = _make_event()
    dag = pl.plan_jobs(evt, reg, config)
    for pj in dag.jobs:
        assert pj.temp_id
        assert pj.subject_type == evt.subject_type
        assert pj.subject_id == evt.subject_id
        assert pj.input_hash == evt.input_hash
        assert pj.policy_version == evt.policy_version
        assert pj.handler_version
        assert pj.max_attempts >= 1
