"""Emitted config loads through the production entry; mismatch is rejected."""
import json
from pathlib import Path

import pytest

from company_wiki.resource_budget import WorkBudget
from company_wiki.source_catalog.narrative_pdf_enhancement import configured_paragraph_runtime
from company_wiki.source_catalog.narrative_pdf_paragraphs import align_paragraphs
from tools.pdf_runtime_deployment import deployment
from unit.test_pdf_paragraph_alignment import document, proposal


def test_require_ascii_accepts_ascii_and_rejects_non_ascii():
    deployment.require_ascii(Path("C:/plain/runtime-target"))
    with pytest.raises(deployment.DeploymentError, match="ASCII"):
        deployment.require_ascii(Path("C:/\u4e2d\u6587/runtime-target"))


def test_build_plan_rejects_non_ascii_target(tmp_path):
    from unit.test_w22_pdf_deployment_plan import mini_source
    profile, probe = mini_source(tmp_path)
    with pytest.raises(deployment.DeploymentError, match="ASCII"):
        deployment.build_plan(tmp_path / "\u4e2d\u6587", profile, probe)


def emitted_config(tmp_path: Path) -> Path:
    profile = {
        "schema_version": "pdf-paragraph-runtime/2",
        "python": str(tmp_path / "ascii-target" / "env" / "Scripts" / "python.exe"),
        "artifacts": str(tmp_path / "ascii-target" / "artifacts"),
        "model_sha256": "b" * 64,
        "model_config_sha256": "c" * 64,
        "docling_version": "2.96.0",
        "runtime_versions": {key: "1" for key in (
            "python", "docling-core", "docling-ibm-models", "torch", "pymupdf", "pypdfium2")},
        "environment_sha256": "d" * 64,
        "environment_algorithm": "pdf-runtime-closure/2",
        "max_seconds": 120, "max_pages": 3, "max_memory_bytes": 4 * 1024 ** 3,
    }
    path = tmp_path / "paragraph-runtime.config.json"
    path.write_text(json.dumps(profile, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def test_emitted_config_loads_through_production_entry(tmp_path, monkeypatch):
    config_path = emitted_config(tmp_path)
    monkeypatch.setenv("COMPANY_WIKI_PDF_ENHANCEMENT_CONFIG", str(config_path))
    enhancement = configured_paragraph_runtime()
    assert enhancement is not None
    assert enhancement.config.python == str(tmp_path / "ascii-target" / "env" / "Scripts" / "python.exe")
    assert enhancement.config.environment_algorithm == "pdf-runtime-closure/2"
    recipe = dict(enhancement.describe_recipe())
    assert recipe["environment_algorithm"] == "pdf-runtime-closure/2"
    assert recipe["model_sha256"] == "b" * 64 and recipe["offline"] is True
    assert recipe["max_seconds"] == 120 and recipe["max_pages"] == 3
    monkeypatch.delenv("COMPANY_WIKI_PDF_ENHANCEMENT_CONFIG")
    assert configured_paragraph_runtime() is None


def test_emitted_config_without_algorithm_binding_is_rejected(tmp_path, monkeypatch):
    config_path = emitted_config(tmp_path)
    raw = json.loads(config_path.read_text(encoding="utf-8"))
    raw.pop("environment_algorithm")
    broken = tmp_path / "broken.json"
    broken.write_text(json.dumps(raw), encoding="utf-8")
    monkeypatch.setenv("COMPANY_WIKI_PDF_ENHANCEMENT_CONFIG", str(broken))
    with pytest.raises(ValueError, match="environment algorithm"):
        configured_paragraph_runtime()


def test_tampered_proposal_remains_rejected_on_matching_geometry():
    """Negative control bound to this card: an off-by-one-character proposal
    with otherwise valid geometry must never join native members."""
    parsed = document()
    good = proposal(parsed)
    tampered = proposal(parsed, text="The new product generated revenue of 12.4 million dollers; rollout is not yet approved.")
    aligned = align_paragraphs(parsed, [good, tampered], work_budget=WorkBudget(100_000))
    assert aligned.accepted_groups == 1
    assert aligned.rejected_groups == 1
    assert aligned.parsed.units == parsed.units or all(
        unit.metadata.get("reading_layout", {}).get("paragraph_membership")
        for unit in aligned.parsed.units)
    only_bad = align_paragraphs(parsed, [tampered], work_budget=WorkBudget(100_000))
    assert only_bad.accepted_groups == 0
