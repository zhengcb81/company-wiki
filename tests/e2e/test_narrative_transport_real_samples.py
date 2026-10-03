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
    _E6_REAL_SAMPLES, _e6_production_fingerprint, _e6_source_paths,
)
from support.narrative_transport_fixture import published_fixture


pytestmark = [
    pytest.mark.real_data,
    pytest.mark.skipif(
        os.environ.get("COMPANY_WIKI_RUN_EXTERNAL_DATA_TESTS") != "1",
        reason="set COMPANY_WIKI_RUN_EXTERNAL_DATA_TESTS=1 for local raw sample E2E",
    ),
]


@pytest.mark.parametrize("sample", _E6_REAL_SAMPLES, ids=lambda sample: sample["sample_id"])
def test_real_raw_bundle_survives_public_cli_and_full_locator_replay(
    tmp_path: Path, sample: dict,
) -> None:
    _, paths = _e6_source_paths()
    original = paths[sample["sample_id"]]
    assert original.is_file(), f"required sample unavailable: {sample['sample_id']}"
    raw = original.read_bytes()
    digest = hashlib.sha256(raw).hexdigest()
    assert digest == sample["sha256"]
    production_before = _e6_production_fingerprint()
    original_stat = original.stat()
    try:
        source_spec = dict(sample, data=raw)
        kind = "txt" if sample["sample_id"] == "T01" else "pdf"
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
            assert reference["byte_size"] <= 1_310_720
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
