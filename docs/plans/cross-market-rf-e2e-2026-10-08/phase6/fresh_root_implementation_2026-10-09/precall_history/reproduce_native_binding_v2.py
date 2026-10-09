"""Offline outer recorder -> installed RF native calls; restore owned fixtures."""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile


def main() -> None:
    profile = Path.home()
    audit = profile / "Projects/revenue-forecast-audit/skills/revenue-forecast-audit/scripts/audit_run.py"
    rf = profile / ".agents/skills/revenue-forecast"
    source_tests = profile / "Projects/revenue-forecast/tests"
    sys.path.insert(0, str(source_tests))
    from test_recognition_bridge import forecast_document

    receipt: dict = {
        "schema_version": "w11-native-recording/1",
        "provider_calls": 0,
        "paid_calls": 0,
        "fixture_is_synthetic_not_company_research": True,
        "calls": [],
    }
    with tempfile.TemporaryDirectory(prefix="w11-native-") as scratch:
        root = Path(scratch)
        env = dict(os.environ, PYTHONUTF8="1", PYTHONDONTWRITEBYTECODE="1",
                   REVENUE_PUBLICATION_REGISTRY=str(root / "registry.jsonl"))

        def cli(arguments: list[str], expected: int = 0) -> dict:
            completed = subprocess.run(
                [sys.executable, "-X", "utf8", "-B", str(audit), *arguments],
                env=env, cwd=root, capture_output=True, encoding="utf-8", timeout=30,
            )
            assert completed.returncode == expected, (completed.stdout, completed.stderr)
            return json.loads(completed.stdout)

        run = Path(cli(["init", "--root", str(root / "runs"), "--company", "Offline fixture",
                        "--as-of", "2026-10-08", "--run-id", "native"])['run'])
        scope = {"mode": "offline_skill_forward_test", "runtime_files": [
            {"path": str(rf / "scripts" / name),
             "sha256": hashlib.sha256((rf / "scripts" / name).read_bytes()).hexdigest()}
            for name in ("revenue_forecast.py", "revenue_core.py", "revenue_report.py")
        ]}
        (run / "scope.json").write_text(json.dumps(scope), encoding="utf-8")
        draft, result, markdown = root / "draft.json", root / "result.json", root / "report.md"
        native = [sys.executable, "-X", "utf8", "-B", str(rf / "scripts/revenue_forecast.py")]

        def capture(inputs: list[Path], command: list[str], expected: int = 0) -> dict:
            options = ["capture", "--run", str(run), "--role", "executor"]
            for item in inputs:
                options.extend(["--freeze-input", str(item)])
            observed = cli([*options, "--", *command], expected)
            for item in observed["input_snapshots"]:
                assert hashlib.sha256(Path(item["frozen_path"]).read_bytes()).hexdigest() == item["sha256"]
            receipt["calls"].append(observed)
            return observed

        first_bytes = b'{invalid pre-call model\r\n'
        draft.write_bytes(first_bytes)
        failed = capture([draft], [*native, str(draft), "--validate-only", "--verbose"], 2)
        assert not (root / "registry.jsonl").exists()
        data = forecast_document()
        second_bytes = (json.dumps(data, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
        draft.write_bytes(second_bytes)
        validated = capture([draft], [*native, str(draft), "--validate-only", "--verbose"])
        assert Path(validated["stdout_artifact"]).read_text(encoding="utf-8").strip() == "valid"
        assert not (root / "registry.jsonl").exists()
        published = capture([draft], [*native, str(draft), "--output", str(result), "--markdown", str(markdown)])
        output = json.loads(result.read_text(encoding="utf-8"))
        assert result.exists() and markdown.exists() and (root / "registry.jsonl").exists()
        strong = (
            "import json,pathlib,sys;sys.path.insert(0,sys.argv[1]);"
            "from revenue_report import validate_published_forecast;"
            "validate_published_forecast(json.loads(pathlib.Path(sys.argv[2]).read_text(encoding='utf-8'))," 
            "json.loads(pathlib.Path(sys.argv[3]).read_text(encoding='utf-8')));print('strong verified')"
        )
        assured = capture([result, draft], [sys.executable, "-X", "utf8", "-B", "-c", strong,
                                           str(rf / "scripts"), str(result), str(draft)])
        assert Path(assured["stdout_artifact"]).read_text(encoding="utf-8").strip() == "strong verified"
        assert Path(failed["input_snapshots"][0]["frozen_path"]).read_bytes() == first_bytes
        assert Path(validated["input_snapshots"][0]["frozen_path"]).read_bytes() == second_bytes
        assert draft.read_bytes() == second_bytes
        assert published["input_snapshots"][0]["sha256"] == validated["input_snapshots"][0]["sha256"]
        assert output["input_document"] == data
        trust = run / "execution/trust_boundary.json"
        trust.parent.mkdir(parents=True, exist_ok=True)
        trust.write_text(json.dumps({"schema_version": "fresh-runtime-trust-boundary/1",
            "attestation_status": "unattested", "actual_native_calls": 4,
            "known_tokens": 0, "known_cost_usd": 0,
            "authority_note": "Synthetic offline recording test; no company forecast quality assertion"}), encoding="utf-8")
        statement = cli(["trust-statement", "--run", str(run), "--trust-file", str(trust)])
        assert '"attestation_status": "unattested"' in Path(statement["artifact"]).read_text(encoding="utf-8")
        receipt.update(native_input_output_bound=True, validate_only_registry_zero_write=True,
                       earlier_failure_exact_bytes_retained=True, corrected_draft_not_modified=True,
                       actual_result_input_document_matches=True, statement=statement,
                       temporary_root=str(root), isolated_registry_entries=1)
    receipt["temporary_root_restored_absent"] = not root.exists()
    assert receipt["temporary_root_restored_absent"]
    target = Path(__file__).with_name("native_recording_binding_v2.json")
    target.write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"calls": len(receipt["calls"]), "native_checks": "PASS",
                      "temporary_root_restored_absent": True, "paid_calls": 0,
                      "receipt": str(target)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
