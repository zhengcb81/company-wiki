"""Projection generation binds semantic inputs without altering raw generations."""

from copy import deepcopy
from types import SimpleNamespace

import pytest

from company_wiki.narrative_subject import NarrativeSubject
from company_wiki.automation.models import canonical_json
from company_wiki.automation import narrative_generation as generation
from company_wiki.automation.narrative_contracts import SourceRevisionEventPayload


def _binding():
    parents = []
    for marker in ("a", "b"):
        sha = marker * 64
        parents.append(
            {
                "schema_version": "2.0",
                "document_id": "urn:company-wiki:document:sha256:" + sha,
                "source_id": "urn:company-wiki:source:sha256:" + sha,
                "content_sha256": sha,
                "byte_size": 123,
                "mime_type": "application/json",
            }
        )
    return {
        "kind": "official_json",
        "item_key": "urn:company-wiki:source-projection:sha256:" + "c" * 64,
        "subject_sha256": "c" * 64,
        "parent_source_refs": parents,
        "issuer": {
            "provider_company_id": 901,
            "canonical_name": "First Org",
            "market": "CN",
        },
        "as_of_date": "2026-10-10",
        "adapter": {
            "parser": "cwp_official_json/1.0.1",
            "structure_parser_version": "1.0.1",
            "layout_id": "official-flat-list",
            "layout_version": "1.0.0",
            "layout_fingerprint": "d" * 64,
        },
        "coverage": {
            "pagination_complete": True,
            "pages": [{"records": 1}, {"records": 1}],
            "diagnostics": [],
        },
    }


def _request(**options):
    model = {
        "model_id": "configured-flash",
        "endpoint": "https://model.invalid/v1/chat/completions",
        "max_output_tokens": 2400,
        "temperature": 0.2,
        "thinking": "disabled",
        "reasoning_effort": "low",
        "reasoning_split": False,
        "output_token_field": "max_completion_tokens",
        "api_key_env": "TEST_KEY_NAME",
        "timeout_seconds": 60,
        "allow_local_http": False,
        "max_request_bytes": 262144,
        "max_response_bytes": 262144,
    }
    model.update(options)
    return SimpleNamespace(
        profile="P2",
        model_options=model,
        max_seconds=60,
        max_tokens=10000,
        max_cost_usd="0.10",
        run_id="one",
        refresh=False,
    )


def _versions():
    return {
        "selector": "1.3.0",
        "adapter": "openai-compatible-http/1",
        "prompt": "official-narrative/1",
        "model_request_schema": "narrative-model-request/2",
        "handlers": {
            "source.narrative_select": "3.0.0",
            "source.narrative_summarize": "3.0.0",
            "source.narrative_verify": "3.0.0",
        },
    }


def _manifest(*, binding=None, request=None, versions=None, **kwargs):
    options = {
        "language": "en",
        "execution_versions": versions or _versions(),
        "bundle_producer": "2.0.0",
        "narrative_adapter_version": "official-json-narrative/1",
    }
    options.update(kwargs)
    return generation.projection_generation_manifest(
        request or _request(),
        NarrativeSubject.from_dict(binding or _binding()),
        **options,
    )


def test_exact_subject_and_model_have_stable_canonical_identity():
    one = _manifest()
    assert one == _manifest(
        binding=deepcopy(_binding()), request=_request(), versions=deepcopy(_versions())
    )
    assert generation.generation_sha256(one) == generation.generation_sha256(
        _manifest()
    )
    assert one["schema_version"] == "narrative-generation/2"
    assert one["subject_binding"] == _binding()
    assert (one["bundle_schema"], one["select_schema"], one["summary_schema"]) == (
        "narrative-bundle/3.0",
        "narrative-select-result/3.0",
        "narrative-summary-result/3.0",
    )
    assert one["parser_component"] == {"name": "cwp_official_json", "version": "1.0.1"}
    assert one["source_adapter"] == _binding()["adapter"]


@pytest.mark.parametrize(
    "mutation",
    [
        "issuer",
        "as_of",
        "projection",
        "first_parent",
        "second_parent",
        "parser",
        "structure_parser",
        "layout_id",
        "layout_version",
        "layout_fingerprint",
        "coverage",
    ],
)
def test_every_bound_projection_identity_change_changes_generation(mutation):
    binding = _binding()
    if mutation == "issuer":
        binding["issuer"]["provider_company_id"] = 902
    elif mutation == "as_of":
        binding["as_of_date"] = "2026-10-09"
    elif mutation == "projection":
        binding["subject_sha256"] = "e" * 64
        binding["item_key"] = "urn:company-wiki:source-projection:sha256:" + "e" * 64
    elif mutation in {"first_parent", "second_parent"}:
        parent = binding["parent_source_refs"][mutation == "second_parent"]
        parent.update(
            content_sha256="f" * 64,
            source_id="urn:company-wiki:source:sha256:" + "f" * 64,
        )
    elif mutation == "coverage":
        binding["coverage"]["pagination_complete"] = False
    else:
        field = {
            "structure_parser": "structure_parser_version",
            "parser": "parser",
            "layout_id": "layout_id",
            "layout_version": "layout_version",
            "layout_fingerprint": "layout_fingerprint",
        }[mutation]
        binding["adapter"][field] = (
            "cwp_official_json/1.0.2"
            if mutation == "parser"
            else ("e" * 64 if mutation == "layout_fingerprint" else "updated")
        )
    assert generation.generation_sha256(
        _manifest(binding=binding)
    ) != generation.generation_sha256(_manifest())


@pytest.mark.parametrize(
    "field,value",
    [
        ("model_id", "another-model"),
        ("endpoint", "https://other.invalid/v1/chat/completions"),
        ("max_output_tokens", 1000),
        ("thinking", "enabled"),
        ("reasoning_effort", "high"),
        ("temperature", 0.8),
        ("reasoning_split", True),
        ("output_token_field", "max_tokens"),
    ],
)
def test_every_actual_http_generation_option_is_bound(field, value):
    assert generation.generation_sha256(
        _manifest(request=_request(**{field: value}))
    ) != generation.generation_sha256(_manifest())


@pytest.mark.parametrize(
    "field", ["selector", "adapter", "prompt", "model_request_schema", "handlers"]
)
def test_actual_execution_components_are_bound(field):
    versions = _versions()
    if field == "handlers":
        versions[field]["source.narrative_verify"] = "3.0.1"
    else:
        versions[field] = "changed-producer"
    assert generation.generation_sha256(
        _manifest(versions=versions)
    ) != generation.generation_sha256(_manifest())


def test_profile_language_bundle_and_narrative_adapter_are_bound():
    expected = generation.generation_sha256(_manifest())
    request = _request()
    request.profile = "P4"
    assert generation.generation_sha256(_manifest(request=request)) != expected
    args = dict(
        execution_versions=_versions(),
        bundle_producer="2.0.0",
        narrative_adapter_version="official-json-narrative/1",
    )
    assert (
        generation.generation_sha256(
            generation.projection_generation_manifest(
                _request(),
                NarrativeSubject.from_dict(_binding()),
                language="zh",
                **args,
            )
        )
        != expected
    )
    assert generation.generation_sha256(_manifest(bundle_producer="2.0.1")) != expected
    assert (
        generation.generation_sha256(
            _manifest(narrative_adapter_version="official-json-narrative/2")
        )
        != expected
    )


def test_execution_only_resources_credentials_and_raw_parser_do_not_change_identity():
    request = _request(
        api_key_env="OTHER_KEY_NAME",
        api_key="synthetic-secret-must-not-persist",
        timeout_seconds=9,
        max_request_bytes=10000,
        max_response_bytes=12000,
        allow_local_http=True,
    )
    request.run_id = "another"
    request.max_tokens = 1
    request.max_seconds = 1
    request.max_cost_usd = "0"
    request.refresh = True
    versions = {
        **_versions(),
        "parser": "raw-parser-irrelevant",
        "document_normalization": "raw-ocr-irrelevant",
    }
    assert _manifest(request=request, versions=versions) == _manifest()
    encoded = canonical_json(_manifest(request=request, versions=versions))
    for absent in (
        "api_key",
        "OTHER_KEY_NAME",
        "synthetic-secret",
        "timeout_seconds",
        "max_request_bytes",
        "allow_local_http",
        "raw-parser-irrelevant",
    ):
        assert absent not in encoded


def test_none_optional_http_fields_equal_omitted_fields_and_token_default_matches_adapter():
    request = _request(
        thinking=None, temperature=None, reasoning_effort=None, reasoning_split=None
    )
    without = _request()
    for key in ("thinking", "temperature", "reasoning_effort", "reasoning_split"):
        without.model_options.pop(key)
    assert _manifest(request=request) == _manifest(request=without)
    request.model_options.pop("output_token_field")
    assert _manifest(request=request) == _manifest(
        request=SimpleNamespace(
            profile="P2",
            model_options={**request.model_options, "output_token_field": "max_tokens"},
        )
    )


def test_result_is_deeply_detached_from_every_caller_and_subject_snapshot():
    binding = _binding()
    subject = NarrativeSubject.from_dict(binding)
    request = _request()
    versions = _versions()
    one = generation.projection_generation_manifest(
        request,
        subject,
        language="en",
        execution_versions=versions,
        bundle_producer="2.0.0",
        narrative_adapter_version="official-json-narrative/1",
    )
    frozen = canonical_json(one)
    versions["handlers"]["source.narrative_verify"] = "mutated"
    request.model_options["temperature"] = 0.9
    binding["coverage"]["pages"][0]["records"] = 90
    assert canonical_json(one) == frozen
    one["subject_binding"]["coverage"]["pages"][0]["records"] = 99
    one["source_adapter"]["parser"] = "mutated"
    assert subject.to_dict()["coverage"]["pages"][0]["records"] == 1
    assert one["subject_binding"]["adapter"]["parser"] == "cwp_official_json/1.0.1"
    assert _manifest()["subject_binding"] == _binding()


@pytest.mark.parametrize("value", [float("nan"), float("inf"), -float("inf"), object()])
def test_nonfinite_or_nonjson_semantic_model_values_are_rejected(value):
    with pytest.raises(ValueError):
        _manifest(request=_request(temperature=value))


@pytest.mark.parametrize("path_kind", ["windows_drive", "unc", "file_uri", "posix"])
def test_physical_locations_cannot_enter_semantic_binding(path_kind, tmp_path):
    # These are pure protocol data; construct their syntax independently of the
    # host. No synthetic Windows/UNC/POSIX location is opened on this machine.
    import ntpath
    from pathlib import PurePosixPath, PureWindowsPath

    if path_kind == "windows_drive":
        path = ntpath.join("Q:", ntpath.sep, "source")
        assert PureWindowsPath(path).is_absolute()
    elif path_kind == "unc":
        path = ntpath.sep * 2 + ntpath.join("example", "share", "source")
        assert PureWindowsPath(path).is_absolute()
    elif path_kind == "file_uri":
        path = (tmp_path / "source").as_uri()
    else:
        path = str(PurePosixPath(PurePosixPath().anchor or "/", "tmp", "source"))
        assert PurePosixPath(path).is_absolute()
    binding = _binding()
    binding["issuer"]["canonical_name"] = path
    with pytest.raises(ValueError):
        _manifest(binding=binding)


@pytest.mark.parametrize("location", ["adapter", "issuer", "coverage"])
def test_full_record_payloads_are_forbidden_but_coverage_record_counts_are_valid(
    location,
):
    binding = _binding()
    binding[location]["records"] = [{"raw_text": "full-record-copy"}]
    with pytest.raises(ValueError):
        _manifest(binding=binding)
    assert _manifest()["subject_binding"]["coverage"]["pages"][0]["records"] == 1


@pytest.mark.parametrize("field", ["selector", "adapter", "prompt"])
def test_required_actual_execution_versions_cannot_default_to_raw_globals(field):
    versions = _versions()
    versions.pop(field)
    with pytest.raises(ValueError):
        _manifest(versions=versions)


def test_projection_helper_refuses_raw_subject_and_secret_component_metadata():
    with pytest.raises(ValueError):
        generation.projection_generation_manifest(
            _request(),
            NarrativeSubject.from_raw(_binding()["parent_source_refs"][0]),
            language="en",
            execution_versions=_versions(),
            bundle_producer="2.0.0",
            narrative_adapter_version="official-json-narrative/1",
        )
    versions = _versions()
    versions["handlers"]["api_key_env"] = "SYNTHETIC_KEY"
    with pytest.raises(ValueError):
        _manifest(versions=versions)


@pytest.mark.parametrize(
    "field,value",
    [
        ("endpoint", "https://username:password@model.invalid/v1"),
        ("model_id", ""),
        ("max_output_tokens", True),
        ("max_output_tokens", 0),
        ("output_token_field", []),
        ("thinking", []),
        ("reasoning_effort", True),
        ("temperature", True),
        ("reasoning_split", 1),
    ],
)
def test_invalid_generation_essentials_fail_before_identity_can_be_used(field, value):
    with pytest.raises(ValueError):
        _manifest(request=_request(**{field: value}))


def test_old_raw_manifest_retains_exact_canonical_contract():
    parent = _binding()["parent_source_refs"][0]
    payload = SourceRevisionEventPayload.from_dict(
        {
            "schema_version": "source-revision-event/2.0",
            "source_ref": parent,
            "expected_read_policy_sha256": "f" * 64,
            "source_metadata": {
                "source_class": "filing",
                "title": "Old source",
                "document_kind": "annual_report",
                "language": "en",
            },
        }
    )
    versions = {
        "adapter": "legacy-adapter",
        "prompt": "legacy-prompt",
        "parser": "legacy-parser",
        "selector": "legacy-selector",
    }
    # The historical wire predates explicit effort. That absence remains exact;
    # requests with explicit effort now bind the real HTTP generation input.
    actual = generation.generation_manifest(
        _request(reasoning_effort=None), payload, execution_versions=versions
    )
    expected = {
        "schema_version": "narrative-generation/1",
        "source_ref": parent,
        "source_metadata": payload.source_metadata.to_dict(),
        "execution_versions": versions,
        "bundle_schema": "narrative-bundle/2.0",
        "select_schema": "narrative-select-result/2.0",
        "summary_schema": "narrative-summary-result/2.0",
        "parser_component": {"name": "selective_narrative_parser", "version": "0.1.1"},
        "bundle_producer": "1.0.0",
        "profile": "P2",
        "model": {
            "model_id": "configured-flash",
            "endpoint": "https://model.invalid/v1/chat/completions",
            "max_output_tokens": 2400,
            "thinking": "disabled",
            "temperature": 0.2,
            "reasoning_split": False,
            "output_token_field": "max_completion_tokens",
        },
    }
    assert canonical_json(actual) == canonical_json(expected)


def test_adaptive_thinking_matches_actual_http_model_configuration():
    value = _manifest(request=_request(thinking="adaptive"))
    assert value["model"]["thinking"] == "adaptive"
    assert generation.generation_sha256(value) != generation.generation_sha256(_manifest())
