"""Owner-only raw sample -> real DAG -> persistent object -> public CLI.

The raw bytes and SHA oracle are real. Capture metadata is an isolated fixture,
not an assertion that the production catalog has historical reuse eligibility.
No network or production catalog write is involved.
"""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path

import pytest

from contract.test_narrative_transport_cli import _cli, _reference
from integration.test_narrative_runtime_e2e import (
    _E6_REAL_SAMPLES, _e6_production_fingerprint, _e6_project_root, _e6_source_paths,
)
from support.narrative_transport_fixture import published_fixture


pytestmark = [
    pytest.mark.real_data,
    pytest.mark.skipif(
        os.environ.get("COMPANY_WIKI_RUN_EXTERNAL_DATA_TESTS") != "1",
        reason="set COMPANY_WIKI_RUN_EXTERNAL_DATA_TESTS=1 for local raw sample E2E",
    ),
]


_ADDITIONAL_MARKET_SAMPLES = (
    {
        "sample_id": "CN-H1",
        "relative_path": "中微公司/raw/financial_reports/semi_annual/2026-08-19_cninfo_1225482884_2026年半年度报告.pdf",
        "entity_name": "中微公司", "title": "中微公司2026年半年度报告",
        "document_kind": "semi_annual_report", "language": "zh",
        "sha256": "182e2062fed950cd32310099cdf47f392c791440ce251f5e3bab7137dbc932fe",
        "sidecar_overrides": {"market": "CN", "security_id": "688012.SH",
                              "fiscal_year": 2026, "fiscal_period": "H1"},
    },
    {
        "sample_id": "HK-H1",
        "relative_path": "金山雲/raw/financial_reports/semi_annual/2025-09-26_hkexnews_11857348_2025 中期報告.pdf",
        "entity_name": "金山雲", "title": "金山雲2025年中期報告",
        "document_kind": "semi_annual_report", "language": "zh",
        "sha256": "4f589193fae39fb53cb7d2121d93925b382bb052cfecbdc24e8e8271ea41bd36",
        "sidecar_overrides": {"market": "HK", "security_id": "03896",
                              "fiscal_year": 2025, "fiscal_period": "H1"},
    },
    {
        "sample_id": "CN-IR-DOCX",
        "relative_path": "吉比特/raw/research/中泰-吉比特财报交流会0409.mp3-文稿-转写结果.docx",
        "entity_name": "吉比特", "title": "吉比特财报交流会",
        "document_kind": "investor_call_transcript", "language": "zh",
        "sha256": "63777874f5956f37ed32f4839c170340af4f61ee7594b99423acc698968a158a",
        "sidecar_overrides": {"market": "CN", "security_id": "603444.SH", "fiscal_year": None,
                              "fiscal_period": None, "period_end": None},
    },
)


@pytest.mark.parametrize("sample", _E6_REAL_SAMPLES + _ADDITIONAL_MARKET_SAMPLES,
                         ids=lambda sample: sample["sample_id"])
def test_real_raw_bundle_survives_public_cli_and_full_locator_replay(
    tmp_path: Path, sample: dict,
) -> None:
    _, paths = _e6_source_paths()
    original = paths.get(sample["sample_id"])
    if original is None:
        companies = Path(os.environ.get("COMPANY_WIKI_E6_COMPANIES_ROOT", str(_e6_project_root() / "companies")))
        original = companies / sample["relative_path"]
    assert original.is_file(), f"required sample unavailable: {sample['sample_id']}"
    raw = original.read_bytes()
    digest = hashlib.sha256(raw).hexdigest()
    assert digest == sample["sha256"]
    production_before = _e6_production_fingerprint()
    original_stat = original.stat()
    try:
        source_spec = dict(sample, data=raw, name=original.name)
        kind = original.suffix[1:].lower()
        with published_fixture(tmp_path, kind=kind, source_spec=source_spec) as fixture:
            reference = _reference(fixture)
            result = _cli(fixture, "read", {
                "schema_version": "narrative-read-request/1",
                "narrative_ref": reference, "as_of_date": "2026-09-01",
                "expected_source": fixture.expected_source,
            })
            assert result.returncode == 0, result.stderr.decode("utf-8", errors="replace")
            assert result.stdout == fixture.payload
            assert hashlib.sha256(result.stdout).hexdigest() == reference["artifact_sha256"]
            receipt = json.loads(result.stderr)
            bundle = json.loads(result.stdout)
            assert receipt["manifest"]["content_sha256"] == digest
            assert receipt["locator_count"] == len(bundle["evidence_spans"]) > 0
            assert receipt["replay_status"] == "verified"
            assert reference["byte_size"] == len(result.stdout)
            assert str(fixture.root) not in result.stderr.decode("utf-8")
            print(json.dumps({
                "sample": sample["sample_id"], "raw_bytes": len(raw),
                "artifact_bytes": reference["byte_size"],
                "locators": receipt["locator_count"],
                "quality_status": receipt["quality_status"],
            }, sort_keys=True))
    finally:
        assert hashlib.sha256(original.read_bytes()).hexdigest() == digest
        assert original.stat().st_mtime_ns == original_stat.st_mtime_ns
        assert _e6_production_fingerprint() == production_before
