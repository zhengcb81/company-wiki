"""Card section 5.5.5: zero network and zero model for the whole session.

The guard raises ``AssertionError`` on every socket entry point and records the
attempt; section 6 requires one deliberate trigger to surface as
``p4_network_attempted`` with the case failing.  The model side asserts the CWP
LLM client was never imported and that every observation reports
``model_calls.count == 0``.
"""

from __future__ import annotations

import socket
import sys

import pytest

from .support import checks, cwp, netguard, observations
from .support import constants as C


def test_p4_socket_guard_records_attempt(p4_case, monkeypatch) -> None:
    """One triggered ``socket.connect`` raises and is recorded as an attempt."""
    case = p4_case()
    netguard.reset_for_test()
    # tests/conftest.py re-patches socket per test; restore the lane guard so the
    # assertion under test is the lane's own (card section 10 asks for this probe).
    monkeypatch.setattr(
        socket.socket, "connect", netguard.guard("socket.socket.connect"),
    )
    with pytest.raises(netguard.NetworkAttempted) as excinfo:
        socket.socket(socket.AF_INET, socket.SOCK_STREAM).connect(("127.0.0.1", 1))
    assert isinstance(excinfo.value, AssertionError), (
        "the guard must raise AssertionError (card section 5.5.5)"
    )
    assert netguard.attempts() == ("socket.socket.connect",), (
        f"the attempt must be recorded; got {netguard.attempts()!r}"
    )

    outcomes = checks.check_zero_network_model(
        attempts=netguard.attempts(), observations=[], llm_client_imported=False,
    )
    failing = {o.name: o for o in outcomes if not o.ok}
    assert "no_network_attempt" in failing, (
        f"a recorded attempt must fail no_network_attempt; observed {sorted(failing)}"
    )
    assert failing["no_network_attempt"].code == C.CODE_NETWORK_ATTEMPTED, (
        f"expected {C.CODE_NETWORK_ATTEMPTED}; "
        f"got {failing['no_network_attempt'].code}"
    )
    case.check("network_attempt_recorded", "pass", {
        "code": C.CODE_NETWORK_ATTEMPTED,
        "attempts": list(netguard.attempts()),
    })
    netguard.reset_for_test()
    case.settle("pass")


def test_p4_llm_client_not_imported(p4_case) -> None:
    """The CWP LLM client must never enter this process (section 8: 0 model)."""
    case = p4_case()
    imported = sorted(
        name for name in sys.modules
        if name.startswith("company_wiki.llm_client") or name == "llm_client"
    )
    assert not imported, f"the lane must not import an LLM client; found {imported}"

    outcomes = checks.check_zero_network_model(
        attempts=(), observations=[], llm_client_imported=bool(imported),
    )
    failing = [o.name for o in outcomes if not o.ok]
    case.check("llm_client_not_imported", "fail" if failing else "pass",
               {"failing": failing})
    assert not failing, f"zero-model checks failed -> {failing}"
    case.settle("pass")


def test_p4_model_calls_zero(p4_case, p4_sources, p4_manifest, p4_reads) -> None:
    """A derived observation reports zero downloads and zero model calls."""
    case = p4_case()
    item = p4_sources[0]
    read = p4_reads[item["relative_path"]]
    spans = [s for s in p4_manifest["spans"] if s["source_id"] == item["source_id"]]
    obs = observations.observation_from_manifest(
        consumer="ff",
        manifest=cwp.manifest_for(p4_manifest["bundle"], item["source_id"]),
        receipt=read.receipt,
        spans=spans,
    )
    assert obs["model_calls"] == {"count": 0}, (
        f"model_calls must be 0; got {obs['model_calls']!r}"
    )
    assert obs["downloads"] == {"count": 0}, (
        f"downloads must be 0; got {obs['downloads']!r}"
    )

    outcomes = checks.check_zero_network_model(
        attempts=(), observations=[obs], llm_client_imported=False,
    )
    failing = [o.name for o in outcomes if not o.ok]
    case.check("model_calls_zero", "fail" if failing else "pass",
               {"failing": failing})
    assert not failing, f"zero-count checks failed -> {failing}"
    case.settle("pass")


def test_p4_nonzero_model_call_fails(p4_case) -> None:
    """A single counted model call is a ``p4_model_attempted`` failure."""
    case = p4_case()
    observation = {
        "schema_version": C.P4_OBSERVATION_SCHEMA,
        "consumer": "ff",
        "source_ref": {}, "facts": {},
        "availability": {"status": C.AVAILABILITY_UNKNOWN, "evidence": None},
        "quotes": [],
        "downloads": {"count": 0},
        "model_calls": {"count": 1},
    }
    outcomes = checks.check_zero_network_model(
        attempts=(), observations=[observation], llm_client_imported=False,
    )
    failing = {o.name: o for o in outcomes if not o.ok}
    assert "consumer_model_calls_zero" in failing, (
        "a nonzero model_calls.count must fail consumer_model_calls_zero; "
        f"observed {sorted(failing)}"
    )
    assert failing["consumer_model_calls_zero"].code == C.CODE_MODEL_ATTEMPTED, (
        f"expected {C.CODE_MODEL_ATTEMPTED}; "
        f"got {failing['consumer_model_calls_zero'].code}"
    )
    case.check("nonzero_model_call_detected", "pass", {
        "code": C.CODE_MODEL_ATTEMPTED,
        "observed": failing["consumer_model_calls_zero"].detail["observed"],
    })
    case.settle("pass")
