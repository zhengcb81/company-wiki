"""Finite RF receiver checks replaying independent real FF CLI output."""

from copy import deepcopy
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

import pytest

from filing_upstream_cause import (
    failure_observation,
    parse_error_document,
    validated_filing_fetch_failure,
    validated_local_preparation_observation,
)

RF = Path(r"C:/Users/郑曾波/Projects/revenue-forecast-r1-local-observation")
EVIDENCE = Path(__file__).parent
FF_EVIDENCE = EVIDENCE.parent / "r1-local-observation-ff-independent-20261022"
OBS = "local_preparation_observation"


def compact(value):
    return json.dumps(
        value, ensure_ascii=False, allow_nan=False, separators=(",", ":")
    ).encode("utf-8")


def wire(large=False):
    artifact = FF_EVIDENCE / ("actual-cli-" + str(large) + ".json")
    return json.loads(artifact.read_text(encoding="utf-8"))["envelope"]


def test_owner_future_fields_remain_opaque_and_deep_copied():
    payload = wire()
    obs = payload[OBS]
    obs["status"] = "future_owner_status"
    obs["reason"] = "future_owner_counter"
    obs["local_read_limits"]["max_candidates"] = 512
    obs["operations"].append(
        {
            "schema_version": "urn:owner:budget/2",
            "machine_code": "file:missing",
            "new_owner_field": {"unresolved": None, "counter": 999},
        }
    )
    result = validated_filing_fetch_failure(payload)
    assert result == payload
    result[OBS]["operations"][-1]["new_owner_field"]["counter"] = 0
    assert payload[OBS]["operations"][-1]["new_owner_field"]["counter"] == 999
    assert result["status"] == "upstream_error"
    assert result[OBS]["local_io_usage"] is None


def test_unknown_provider_observations_stay_unknown_not_zero():
    payload = wire()
    payload["filing"]["upstream_cause"]["provider_started"] = None
    payload["filing"]["upstream_cause"]["usage_complete"] = None
    observed = failure_observation(payload)
    assert observed["filing_fetch_result"] == payload
    assert observed["upstream_cause"]["provider_started"] is None
    assert observed["upstream_cause"]["usage_complete"] is None
    assert observed["producer_exit_code"] == payload["filing"]["producer_exit_code"]
    assert OBS not in observed  # Sole complete sidecar holds the opaque owner object.


def test_legacy_no_optional_and_normal_gap_do_not_need_new_proof():
    payload = wire()
    del payload[OBS]
    assert validated_filing_fetch_failure(payload) == payload
    assert parse_error_document(json.dumps(payload)) == payload
    gap = deepcopy(payload)
    gap["status"] = "gap"
    gap["filing"] = {
        "status": "gap",
        "reason": "metadata_only_gap_plan",
        "gap_hash": "a" * 64,
        "download_events": 0,
    }
    gap["transcript"] = {
        "status": "not_applicable",
        "reason": "filing_not_capture_ready",
        "retryable": False,
    }
    assert validated_filing_fetch_failure(gap) == gap


def test_optional_extension_does_not_raise_old_base_limit():
    payload = wire(True)
    payload["calls"] = payload["downloads"] = 10**4200
    payload["filing"]["attempts"] = payload["filing"]["producer_exit_code"] = 10**4200
    assert len(compact({k: v for k, v in payload.items() if k != OBS})) > 16384
    assert validated_filing_fetch_failure(payload) is None


def sized_observation(target):
    value = wire()[OBS]
    value["operations"] = []
    value["diagnostics"] = []
    while (
        len(
            compact(
                {**value, "diagnostics": value["diagnostics"] + [{"reason": "a" * 256}]}
            )
        )
        <= target
    ):
        value["diagnostics"].append({"reason": "a" * 256})
    value["diagnostics"].append({"reason": "a"})
    delta = target - len(compact(value))
    if delta < 0:
        value["diagnostics"][-2]["reason"] = value["diagnostics"][-2]["reason"][:delta]
    else:
        value["diagnostics"][-1]["reason"] += "a" * delta
    assert len(compact(value)) == target
    assert all(1 <= len(row["reason"]) <= 256 for row in value["diagnostics"])
    return value


def test_exact_optional_128k_and_plus_one_copy_or_reject_whole():
    payload = wire()
    payload[OBS] = sized_observation(131072)
    assert validated_local_preparation_observation(payload[OBS]) == payload[OBS]
    assert validated_filing_fetch_failure(payload) == payload
    row = next(row for row in payload[OBS]["diagnostics"] if len(row["reason"]) < 256)
    row["reason"] += "a"
    assert len(compact(payload[OBS])) == 131073
    assert validated_filing_fetch_failure(payload) is None
    assert (
        failure_observation(payload)["upstream_cause"]
        == payload["filing"]["upstream_cause"]
    )


@pytest.mark.parametrize("change", ["version", "physical_schema"])
def test_small_bad_optional_cannot_claim_full_but_safe_cause_and_exit_survive(change):
    payload = wire()
    if change == "version":
        payload[OBS]["schema_version"] = "filing-local-preparation-observation/2"
    else:
        payload[OBS]["operations"].append(
            {"schema_version": "file:/C:/Users/example/raw.pdf"}
        )
    raw = json.dumps(payload)
    assert len(raw) < 65536
    parsed = parse_error_document(raw)
    assert parsed is not None
    observed = failure_observation(parsed)
    assert "filing_fetch_result" not in observed
    assert observed["upstream_cause"] == payload["filing"]["upstream_cause"]
    assert observed["producer_exit_code"] == payload["filing"]["producer_exit_code"]
    assert observed["calls"] == 3 and observed["downloads"] == 0


@pytest.mark.parametrize(
    "change", ["duplicate", "truncated", "raw_cap", "untrusted_wrapper"]
)
def test_extended_raw_window_is_bounded_and_not_generic_large_json_permission(change):
    payload = wire(True)
    raw = json.dumps(payload, indent=2)
    assert len(raw.encode()) > 65536
    if change == "duplicate":
        raw = raw.replace('"calls": 3', '"calls": 3, "calls": 3', 1)
    elif change == "truncated":
        raw = raw[:-2]
    elif change == "raw_cap":
        raw = " " * (1024 * 1024) + raw
    else:
        raw = json.dumps({"error": "x" * 70000, "filing_fetch_result": payload})
    assert parse_error_document(raw) is None


def test_large_invalid_optional_cannot_use_new_extended_window():
    payload = wire(True)
    payload[OBS]["schema_version"] = "filing-local-preparation-observation/2"
    raw = json.dumps(payload, indent=2)
    assert len(raw.encode()) > 65536
    assert parse_error_document(raw) is None


@pytest.mark.parametrize("large", [False, True])
@pytest.mark.parametrize("entry", ["filing_fetch_client.py", "source_preparation.py"])
def test_actual_rf_child_and_preparation_keep_final_ff_wire(tmp_path, large, entry):
    sentinel = tmp_path / "keep.bin"
    sentinel.write_bytes(b"initial receiver fixture")
    root = tmp_path / "owned"
    root.mkdir()
    try:
        fake = root / "ff"
        (fake / "scripts").mkdir(parents=True)
        payload = wire(large)
        replay = fake / "wire.json"
        replay.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        (fake / "scripts/fetch_filing.py").write_text(
            "from pathlib import Path\nimport sys\nsys.stdin.read()\n"
            "sys.stdout.write((Path(__file__).parents[1]/'wire.json').read_text(encoding='utf-8'))\n"
            "raise SystemExit(2)\n",
            encoding="utf-8",
        )
        bootstrap = root / "bootstrap"
        bootstrap.mkdir()
        (bootstrap / "sitecustomize.py").write_text(
            "import socket\ndef refuse(*a,**k): raise RuntimeError('RF_INDEPENDENT_OFFLINE')\n"
            "socket.socket.connect=refuse\nsocket.create_connection=refuse\n",
            encoding="utf-8",
        )
        catalog = root / "catalog.yaml"
        catalog.write_text("{}", encoding="utf-8")
        command = [
            sys.executable,
            "-B",
            "-X",
            "utf8",
            str(RF / "scripts" / entry),
            "--result-envelope",
            "--filing-fetch-root",
            str(fake),
            "--timeout-seconds",
            "10",
        ]
        if entry == "source_preparation.py":
            command += ["--company-wiki-catalog-config", str(catalog)]
        env = {
            **os.environ,
            "PYTHONPATH": os.pathsep.join((str(bootstrap), str(RF / "scripts"))),
            "PYTHON_DOTENV_DISABLED": "1",
            "PYTHONDONTWRITEBYTECODE": "1",
        }
        request = {
            "schema_version": "2.0",
            "company_query": "AMD",
            "market": "US",
            "document_kind": "semi_annual_report",
            "mode": "exact",
            "fiscal_year": 2026,
            "fiscal_period": "H1",
            "as_of_date": "2026-10-21",
            "filing_intent": "reuse_only",
        }
        result = subprocess.run(
            command,
            input=json.dumps(request).encode(),
            cwd=root,
            env=env,
            capture_output=True,
            timeout=30,
            check=False,
        )
        assert result.returncode == (2 if entry == "filing_fetch_client.py" else 3)
        assert not result.stdout
        observed = json.loads(result.stderr)
        assert observed["filing_fetch_result"] == payload
        assert observed["upstream_cause"] == payload["filing"]["upstream_cause"]
        assert observed["producer_exit_code"] == payload["filing"]["producer_exit_code"]
        assert observed["calls"] == 3 and observed["downloads"] == 0
        assert observed["companion_observation"] == payload["transcript"]
        assert observed["filing_fetch_result"][OBS]["local_io_usage"] is None
        assert (
            observed["filing_fetch_result"][OBS]["operations"]
            == payload[OBS]["operations"]
        )
        if large:
            assert len(result.stderr) > 65536
        proof = {
            "entry": entry,
            "rf_exit": result.returncode,
            "replayed_ff_exit": 2,
            "local_producer_exit": observed["producer_exit_code"],
            "stderr_bytes": len(result.stderr),
            "stderr_sha256": hashlib.sha256(result.stderr).hexdigest(),
            "complete_sidecar_sha256": hashlib.sha256(
                compact(observed["filing_fetch_result"])
            ).hexdigest(),
            "expected_sidecar_sha256": hashlib.sha256(compact(payload)).hexdigest(),
            "diagnostics": len(payload[OBS]["diagnostics"]),
            "cause": observed["upstream_cause"],
            "companion": observed["companion_observation"],
            "calls": observed["calls"],
            "downloads": observed["downloads"],
        }
        (
            EVIDENCE / (entry.removesuffix(".py") + "-" + str(large) + ".json")
        ).write_text(json.dumps(proof, indent=2) + "\n", encoding="utf-8")
    finally:
        assert root.resolve().parent == tmp_path.resolve()
        shutil.rmtree(root)
        assert {p.name: p.read_bytes() for p in tmp_path.iterdir()} == {
            "keep.bin": b"initial receiver fixture"
        }
