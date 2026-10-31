"""W23 comparison entry: hermetic checks of the frozen inputs and the
evaluation pipeline.  No model load, no network, no literal host paths.
Real rendering/inference is exercised by the runner scripts, never CI.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
PLAN = REPO / "docs" / "plans" / "w23-xiaomi-ocr-2026-10-30"


@pytest.fixture(scope="module")
def manifest():
    return json.loads((PLAN / "sample_manifest.json").read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def gold():
    return json.loads((PLAN / "gold.json").read_text(encoding="utf-8"))


def test_manifest_schema_and_frozen_counts(manifest):
    assert manifest["schema_version"] == "cwp-ocr-sample-manifest/1"
    assert manifest["counts"] == {
        "documents": 7, "pages": 14, "eval": 8, "holdout": 5,
        "synthetic_degradation": 1,
    }
    assert manifest["render"]["dpi"] == 200
    assert "frozen_before_engine_outputs" not in manifest  # freeze flag lives on gold, not the sample manifest
    roles = {p["role"] for p in manifest["pages"]}
    assert roles == {"eval", "holdout", "eval_degraded"}


def test_manifest_pages_have_identity_and_unique_ids(manifest):
    ids = [p["page_id"] for p in manifest["pages"]]
    assert len(ids) == len(set(ids))
    for page in manifest["pages"]:
        assert len(page["png_sha256"]) == 64
        assert page["reason"]
        doc = manifest["documents"][page["doc"]]
        assert len(doc["content_sha256"]) == 64
        assert doc["market"] in {"CN", "HK", "US"}
        assert doc["relative_path"]


def test_degraded_page_declared_synthetic(manifest):
    degraded = [p for p in manifest["pages"] if p["role"] == "eval_degraded"]
    assert len(degraded) == 1
    assert degraded[0]["degradation"]["note"] == "synthetic_degradation,不代表真实扫描覆盖"
    assert "synthetic_degraded" in degraded[0]["page_id"]


def test_gold_schema_and_freeze_flag(gold):
    assert gold["schema_version"] == "cwp-ocr-gold/1"
    assert gold["frozen_before_engine_outputs"] is True
    assert len(gold["pages"]) == 14


def test_gold_covers_every_manifest_page(manifest, gold):
    for page in manifest["pages"]:
        assert page["page_id"] in gold["pages"], page["page_id"]
        entry = gold["pages"][page["page_id"]]
        assert entry["full_text"].strip()
        assert entry["provenance"]


def test_gold_fact_numbers_exist_in_page_text(gold):
    import re

    pattern = re.compile(r"[0-9][0-9,\.\-%]*")
    for page_id, page in gold["pages"].items():
        text_nums = {n.replace(",", "").rstrip(".-%") for n in pattern.findall(page["full_text"])}
        for fact in page.get("facts", []) + page.get("conditions", []):
            for n in pattern.findall(fact):
                assert n.replace(",", "").rstrip(".-%") in text_nums, (page_id, n)


def test_markets_and_languages_covered(manifest):
    markets = {spec["market"] for spec in manifest["documents"].values()}
    languages = {spec["language"] for spec in manifest["documents"].values()}
    assert markets == {"CN", "HK", "US"}
    assert languages == {"zh-CN", "zh", "en"}


def test_evaluation_pipeline_with_stub_backend(manifest, gold):
    import sys

    if str(REPO) not in sys.path:
        sys.path.insert(0, str(REPO))
    from tools.ocr_comparison.compare import evaluate_split

    def stub_backend(page_id):
        gold_text = gold["pages"][page_id]["full_text"]
        return {"status": "ok", "text": gold_text, "repetition": {"suspicious": False}}

    records = [stub_backend(p["page_id"]) | {"page_id": p["page_id"]} for p in manifest["pages"]]
    # Completion-aware policy: a timeout WITH produced text is scored as a
    # quality result (its partial text counts); a page with no output at all
    # is excluded with its reason. Neither may poison the other pages.
    by_id = {r["page_id"]: r for r in records}
    records[0]["status"] = "timeout"
    broken = by_id["amec_h1_2026_p009"]  # second eval page
    broken["status"] = "error"
    broken["text"] = ""
    result = evaluate_split(gold, records, manifest, arm="STUB")
    assert result["arm"] == "STUB"
    eval_agg = result["eval"]["aggregate"]
    assert eval_agg["pages_failed"] == ["error"]
    timed_out = next(p for p in result["eval"]["per_page"] if p["page_status"] == "timeout")
    assert timed_out["cer_strict"] == 0.0  # partial text scored, not dropped
    perfect = [p for p in result["eval"]["per_page"] if p["page_status"] == "ok"]
    assert perfect
    assert all(p["cer_strict"] == 0.0 for p in perfect)
    assert result["holdout"]["aggregate"]["pages_failed"] == []
    assert all(p["cer_strict"] == 0.0 for p in result["holdout"]["per_page"])
    assert all(p["numbers"]["recall"] == 1.0 for p in result["holdout"]["per_page"])


def test_ci_domain_stays_light():
    """The W23 domain loads no models and touches no network.  torch itself may
    be imported by the safetensors read-only-mapping roundtrip test (a library
    import, not a model); transformers/rapidocr/onnxruntime/pypdfium2 must stay
    absent in this domain."""
    import sys

    heavy = [name for name in sys.modules if name.split(".")[0] in {"transformers", "rapidocr", "onnxruntime", "pypdfium2"}]
    assert heavy == []
