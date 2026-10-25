"""Optional layout conversion stays bounded, offline and inside PDF reading."""
from dataclasses import replace
import json
from hashlib import sha256
import time

import pytest

from company_wiki._bounded_process import ChildTimeout
from company_wiki.resource_budget import WorkBudget
from company_wiki.source_catalog.narrative_pdf_enhancement import ParagraphEnhancement, ParagraphRuntimeConfig
from unit.test_pdf_paragraph_alignment import document


def config():
    return ParagraphRuntimeConfig("python", "existing-model", "b" * 64, "2.96.0", "c" * 64,
        {key: "1" for key in ("python", "docling-core", "docling-ibm-models", "torch", "pymupdf", "pypdfium2")}, "d" * 64)


def source():
    data = b"source fixture bytes"
    parsed = replace(document(), source_sha256=sha256(data).hexdigest())
    return data, parsed


def test_no_gap_no_process_and_deadline_or_bytes_falls_back_without_process():
    def forbidden(*args, **kwargs):
        raise AssertionError("runtime must not start")
    enhancer = ParagraphEnhancement(config(), runner=forbidden)
    parsed = document(("No full stop", "Another heading"))
    assert enhancer.enhance(b"x", parsed, work_budget=WorkBudget(10000), deadline=None).layout_diagnostics[-1]["status"] == "not_needed"
    data, parsed = source()
    assert enhancer.enhance(data, parsed, work_budget=WorkBudget(10000), deadline=time.monotonic()-1).layout_diagnostics[-1]["status"] == "deadline_no_capacity"
    enhancer = ParagraphEnhancement(replace(config(), max_input_bytes=1), runner=forbidden)
    assert enhancer.enhance(data, parsed, work_budget=WorkBudget(10000), deadline=None).layout_diagnostics[-1]["status"] == "source_byte_limit"


@pytest.mark.parametrize("failure", ["timeout", "wrong_sha", "oversized_items", "response_list", "items_scalar", "provenance_scalar", "bbox_scalar"])
def test_runtime_failure_keeps_originals_and_explicit_diagnostic(failure):
    data, parsed = source()
    def runner(*args, **kwargs):
        assert kwargs["env"]["HF_HUB_OFFLINE"] == "1"
        assert kwargs["timeout_seconds"] <= 120
        assert kwargs["stdout_cap_bytes"] == config().max_output_bytes
        if failure == "timeout":
            raise ChildTimeout("private deployment path should not escape")
        response = {"schema_version": "pdf-paragraph-response/1", "source_sha256": parsed.source_sha256,
                    "pages": [1], "docling_version": "2.96.0", "model_sha256": "b" * 64,
                    "model_config_sha256": "c" * 64, "runtime_versions": dict(config().runtime_versions), "items": []}
        response["converter_instances"] = 1
        response["environment_sha256"] = "d" * 64
        if failure == "response_list":
            return {"stdout": b"[]"}
        if failure == "wrong_sha":
            response["source_sha256"] = "c" * 64
        elif failure == "oversized_items":
            response["items"] = [{}] * 2049
        elif failure == "items_scalar":
            response["items"] = [1]
        elif failure == "provenance_scalar":
            response["items"] = [{"label": "text", "text": "x", "provenance": [1]}]
        elif failure == "bbox_scalar":
            response["items"] = [{"label": "text", "text": "x", "provenance": [{"page_no": 1, "bbox": 1}]}]
        return {"stdout": json.dumps(response).encode()}
    result = ParagraphEnhancement(config(), runner=runner).enhance(data, parsed, work_budget=WorkBudget(10000), deadline=None)
    assert result.units == parsed.units
    assert result.layout_diagnostics[-1]["status"] == "native_fallback"
    assert result.layout_coverage["reading_execution"]["status"] == "native_fallback"
    assert "private deployment" not in json.dumps(result.layout_diagnostics)


def test_complete_response_maps_exact_native_members_and_freezes_possible_backend():
    data, parsed = source()
    def runner(*args, **kwargs):
        request = json.loads(kwargs["input_bytes"])
        assert request["pages"] == [1]
        assert request["max_memory_bytes"] == 4 * 1024**3
        return {"stdout": json.dumps({"schema_version": "pdf-paragraph-response/1",
            "source_sha256": parsed.source_sha256, "pages": [1], "docling_version": "2.96.0",
            "model_sha256": "b" * 64, "model_config_sha256": "c" * 64,
            "runtime_versions": dict(config().runtime_versions), "converter_instances": 1,
            "environment_sha256": "d" * 64,
            "items": [{"label": "text", "text": " ".join(u.raw_text for u in parsed.units),
                "provenance": [{"page_no": 1, "bbox": {"l": 60, "r": 500, "t": 700,
                    "b": 665, "coord_origin": "BOTTOMLEFT"}}]}]}).encode()}
    enhancement = ParagraphEnhancement(config(), runner=runner)
    before = enhancement.describe_recipe()
    result = enhancement.enhance(data, parsed, work_budget=WorkBudget(10000), deadline=None)
    assert enhancement.describe_recipe() == before
    assert result.layout_diagnostics[-1]["accepted_groups"] == 1
    assert result.layout_diagnostics[-1]["actual_engine"] == "docling"
    assert result.layout_coverage["reading_execution"]["actual_engine"] == "docling"
    assert len({u.metadata["reading_layout"]["paragraph_membership"]["group"] for u in result.units}) == 1


def test_transitive_backend_or_preprocessor_version_changes_frozen_environment(monkeypatch):
    from types import SimpleNamespace
    from company_wiki.source_catalog import _paragraph_worker as worker
    packages = [SimpleNamespace(metadata={"Name": "docling-parse"}, version="1"),
                SimpleNamespace(metadata={"Name": "transformers"}, version="1")]
    monkeypatch.setattr(worker, "distributions", lambda: packages)
    before = worker.environment_sha256()
    packages[0].version = "2"
    assert worker.environment_sha256() != before
    packages[0].version, packages[1].version = "1", "2"
    assert worker.environment_sha256() != before
