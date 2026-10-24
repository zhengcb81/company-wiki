"""Canonical purpose policy reaches real wire/cache identity without any POST."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import socket
import tempfile
from types import SimpleNamespace
import urllib.request

import pytest
import yaml

from config import Config
from company_wiki.automation.narrative_batch_request import NarrativeBatchRequest
from company_wiki.automation.narrative_contracts import SourceRevisionEventPayload
from company_wiki.automation.narrative_generation import generation_manifest, generation_sha256
from company_wiki.automation.narrative_http_model import NarrativeHTTPModel, model_options_from_config
from company_wiki.automation.narrative_model import NarrativeModelRequest
from support.narrative_model_request_fixture import selection


PROVIDERS = ("mimo", "deepseek", "minimax")
FAKE_KEY = "purpose-policy-fixture-not-a-live-credential"


def fingerprint(path):
    return hashlib.sha256(path.read_bytes()).hexdigest(), path.stat().st_size, path.stat().st_mtime_ns


@pytest.fixture
def canonical_copy(monkeypatch):
    """Copy actual deployment bytes, then own and completely remove the test root."""
    production = Path(__file__).resolve().parents[2] / "config.yaml"
    production_before = fingerprint(production)
    canonical_bytes = production.read_bytes()
    raw = yaml.safe_load(canonical_bytes)
    for name in ("MINIMAX_API_KEY", "MIMO_API_KEY", "DEEPSEEK_API_KEY",
                 "OPENAI_API_KEY", "ANTHROPIC_API_KEY"):
        monkeypatch.setenv(name, FAKE_KEY)
    monkeypatch.setenv("TAVILY_API_KEY", "independent-search-fixture-no-live-credential")
    monkeypatch.setenv("PYTHON_DOTENV_DISABLED", "1")

    def no_network(*_args, **_kwargs):
        pytest.fail("purpose policy serialization must never execute network/model transport")

    monkeypatch.setattr(NarrativeHTTPModel, "generate", no_network)
    monkeypatch.setattr(urllib.request, "urlopen", no_network)
    monkeypatch.setattr(socket, "create_connection", no_network)
    monkeypatch.setattr(socket.socket, "connect", no_network)
    with tempfile.TemporaryDirectory(prefix="cw-purpose-policy-") as name:
        root = Path(name)
        monkeypatch.setenv("WIKI_ROOT", str(root))
        sentinel = root / "existing.txt"
        sentinel.write_bytes(b"preserve pre-existing test contents")
        path = root / "canonical.yaml"
        path.write_bytes(canonical_bytes)
        copy_before = fingerprint(path)

        def load(provider):
            return Config.load(path, llm_provider=provider)

        def variant(name, modified, provider):
            variant_path = root / (name + ".yaml")
            variant_path.write_text(yaml.safe_dump(modified, allow_unicode=True), encoding="utf-8")
            before = fingerprint(variant_path)
            try:
                return Config.load(variant_path, llm_provider=provider)
            finally:
                assert fingerprint(variant_path) == before

        try:
            yield SimpleNamespace(path=path, raw=raw, load=load, variant=variant)
        finally:
            assert fingerprint(production) == production_before
            assert fingerprint(path) == copy_before
            assert sentinel.read_bytes() == b"preserve pre-existing test contents"
    assert not root.exists()


def request_body(config, *, purpose="narrative"):
    options = model_options_from_config(config.llm, purpose=purpose)
    actual = NarrativeHTTPModel(**options).request_bytes(NarrativeModelRequest.from_selection(selection()))
    assert FAKE_KEY.encode() not in actual
    assert FAKE_KEY not in json.dumps(options)
    assert FAKE_KEY not in json.dumps(config._raw)
    return options, json.loads(actual), hashlib.sha256(actual).hexdigest()


@pytest.mark.parametrize("provider", PROVIDERS)
def test_canonical_narrative_only_policy_reaches_wire_and_keeps_loaded_profile(canonical_copy, provider):
    configured = canonical_copy.load(provider)
    without_policy = deepcopy(canonical_copy.raw)
    without_policy["llm"].pop("generation_policy", None)
    original = canonical_copy.variant("legacy", without_policy, provider)
    expected = ({"reasoning_effort": "low"} if provider == "minimax"
                else {"thinking": {"type": "disabled"}})
    wire_keys = set(expected)
    expected_wire = ({"reasoning_effort": "low"} if provider == "minimax"
                     else {"thinking": "disabled"})
    assert configured.llm.generation_options("narrative") == expected
    options, body, _ = request_body(configured)
    old_options, old_body, _ = request_body(original)
    assert {key: options[key] for key in wire_keys} == expected_wire
    expected_body = ({"reasoning_effort": "low"} if provider == "minimax"
                     else {"thinking": {"type": "disabled"}})
    assert {key: body[key] for key in wire_keys} == expected_body
    assert {key: value for key, value in options.items() if key not in wire_keys} == old_options
    assert {key: value for key, value in body.items() if key not in wire_keys} == old_body
    for field in ("provider", "model", "base_url", "max_tokens", "temperature", "reasoning_split", "api_key_env"):
        assert getattr(configured.llm, field) == getattr(original.llm, field)
    assert options["max_output_tokens"] == configured.llm.max_tokens == 8192
    token_field = "max_tokens" if provider == "deepseek" else "max_completion_tokens"
    assert ({"max_tokens", "max_completion_tokens"} & body.keys()) == {token_field}
    assert body[token_field] == 8192
    assert body["model"] == configured.llm.model
    assert options["endpoint"] == configured.llm.base_url.rstrip("/") + "/chat/completions"
    assert body["temperature"] == configured.llm.temperature
    assert body.get("reasoning_split") is (True if provider == "minimax" and configured.llm.reasoning_split else None)
    for purpose in ("general", "research"):
        assert configured.llm.generation_options(purpose) == {}
        other_options, other_body, _ = request_body(configured, purpose=purpose)
        assert not wire_keys.intersection(other_options) and not wire_keys.intersection(other_body)
        assert other_options == old_options and other_body == old_body


def batch_request(options):
    selected = selection()
    request = NarrativeBatchRequest.from_dict({
        "schema_version": "narrative-batch-request/1", "run_id": "purpose-identity",
        "sources": [selected.source_ref.to_dict()], "profile": "P1", "model": options,
        "max_seconds": 30, "max_tokens": 60000, "max_cost_usd": "0.10",
        "pricing": {"version": "fixture", "input_micro_usd_per_million_tokens": 1,
                    "output_micro_usd_per_million_tokens": 1},
    })
    payload = SourceRevisionEventPayload.from_dict({
        "schema_version": "source-revision-event/2.0", "source_ref": selected.source_ref.to_dict(),
        "expected_read_policy_sha256": selected.expected_read_policy_sha256,
        "source_metadata": selected.source_metadata.to_dict(),
    })
    manifest = generation_manifest(request, payload, execution_versions=request.execution_versions)
    return request, manifest


@pytest.mark.parametrize("provider", PROVIDERS)
def test_canonical_policy_changes_actual_request_and_generation_not_source_or_purpose_label(canonical_copy, provider):
    configured = canonical_copy.load(provider)
    without_policy = deepcopy(canonical_copy.raw)
    without_policy["llm"].pop("generation_policy", None)
    original = canonical_copy.variant("legacy", without_policy, provider)
    new_options, new_body, new_sha = request_body(configured)
    old_options, old_body, old_sha = request_body(original)
    current, new_manifest = batch_request(new_options)
    legacy, old_manifest = batch_request(old_options)
    assert current.input_hash != legacy.input_hash
    assert generation_sha256(new_manifest) != generation_sha256(old_manifest)
    assert new_sha != old_sha  # The actual serialized HTTP request changed.
    assert current.sources == legacy.sources
    assert new_manifest["source_ref"] == old_manifest["source_ref"]
    assert new_manifest["source_metadata"] == old_manifest["source_metadata"]
    assert new_body["messages"] == old_body["messages"]  # No prompt/source rewrite.
    for purpose in ("general", "research"):
        equivalent, equivalent_body, equivalent_sha = request_body(configured, purpose=purpose)
        same_request, same_manifest = batch_request(equivalent)
        assert equivalent_body == old_body and equivalent_sha == old_sha
        assert same_request.input_hash == legacy.input_hash
        assert generation_sha256(same_manifest) == generation_sha256(old_manifest)


@pytest.mark.parametrize("provider", PROVIDERS)
def test_explicit_enabled_override_is_configuration_and_is_never_forced_disabled(canonical_copy, provider):
    modified = deepcopy(canonical_copy.raw)
    modified["llm"].setdefault("generation_policy", {}).setdefault(provider, {})["narrative"] = {"thinking": "enabled"}
    configured = canonical_copy.variant("explicit-enabled", modified, provider)
    assert configured.llm.generation_options("narrative") == {"thinking": {"type": "enabled"}}
    options, body, _ = request_body(configured)
    assert options["thinking"] == "enabled" and body["thinking"] == {"type": "enabled"}
    assert configured.llm.generation_options("general") == configured.llm.generation_options("research") == {}


def test_other_provider_has_no_implicit_narrative_override(canonical_copy):
    configured = canonical_copy.load("openai")
    assert configured.llm.generation_options("narrative") == {}
    options, body, _ = request_body(configured)
    assert "thinking" not in options and "thinking" not in body


@pytest.mark.parametrize("bad_policy", [
    {"deepsek": {"narrative": {"thinking": "disabled"}}},
    {"mimo": {"narrative": {"max_tokens": 20000}}},
    {"deepseek": {"narrative": {"thinking": "adaptive"}}},
])
def test_malformed_policy_stays_config_responsibility_before_transport(canonical_copy, monkeypatch, bad_policy):
    modified = deepcopy(canonical_copy.raw)
    modified["llm"]["generation_policy"] = bad_policy

    def no_transport_construction(*_args, **_kwargs):
        pytest.fail("invalid configuration must fail before transport construction")

    monkeypatch.setattr("company_wiki.automation.narrative_http_model.NarrativeHTTPModel", no_transport_construction)
    with pytest.raises(ValueError, match="generation_policy"):
        canonical_copy.variant("invalid-policy", modified, "mimo")
