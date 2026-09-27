from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import uuid

import pytest

from company_wiki.source_catalog.narrative_retrieval import (
    NARRATIVE_EVIDENCE_BUNDLE_SCHEMA_VERSION,
    NarrativeEvidenceResolver,
    NarrativeEvidenceSearch,
)


PROJECT_ROOT = Path(__file__).resolve().parents[2]
PLAN_ROOT = PROJECT_ROOT / "docs" / "plans" / "narrative-evidence-pilot-2026-09-26"
TRANSCRIPT_ROOT = PROJECT_ROOT.parent / "earnings-transcripts" / "earnings-transcripts" / "transcripts"


def _tree_snapshot(root: Path) -> dict[str, tuple]:
    snapshot = {}
    paths = [root, *sorted(root.rglob("*"))]
    for path in paths:
        if path.is_symlink():
            raise AssertionError(f"test tree must not contain symlinks: {path}")
        stat = path.stat()
        relative = "." if path == root else path.relative_to(root).as_posix()
        attributes = getattr(stat, "st_file_attributes", None)
        if path.is_dir():
            snapshot[relative] = ("directory", stat.st_mtime_ns, attributes)
            continue
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        snapshot[relative] = ("file", stat.st_size, stat.st_mtime_ns, attributes, digest)
    return snapshot


def _copy_sample(sample: dict, run_root: Path) -> None:
    source_root = TRANSCRIPT_ROOT if sample["language"] == "en" else PROJECT_ROOT
    source = (source_root / sample["path"]).resolve(strict=True)
    if not source.is_relative_to(source_root.resolve(strict=True)):
        raise AssertionError(f"sample escaped its read-only source root: {sample['id']}")
    staged_root = run_root / "inputs" / ("transcripts" if sample["language"] == "en" else "company")
    staged = staged_root / sample["path"]
    staged.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(source, staged)
    digest = hashlib.sha256(staged.read_bytes()).hexdigest()
    assert digest.startswith(sample["sha256_prefix"]), f"staged source hash mismatch: {sample['id']}"


def test_g1_source_to_summary_pipeline_is_confined_and_cleans_up(tmp_path: Path) -> None:
    baseline = _tree_snapshot(tmp_path)
    parent_stat = tmp_path.stat()
    run_root = tmp_path / f"run-{uuid.uuid4().hex}"
    assert not run_root.exists()

    manifest = json.loads((PLAN_ROOT / "g1_sample_manifest.json").read_text(encoding="utf-8"))
    sample_ids = {"P06", "T02"}
    selected_samples = [sample for sample in manifest["samples"] if sample["id"] in sample_ids]
    assert {sample["id"] for sample in selected_samples} == sample_ids
    for sample in selected_samples:
        source_root = TRANSCRIPT_ROOT if sample["language"] == "en" else PROJECT_ROOT
        if not (source_root / sample["path"]).is_file():
            pytest.skip(f"local G1 sample unavailable: {sample['id']}")

    run_root.mkdir()
    try:
        for sample in selected_samples:
            _copy_sample(sample, run_root)

        staged_manifest = {**manifest, "samples": selected_samples}
        manifest_path = run_root / "inputs" / "g1_sample_manifest.json"
        manifest_path.write_text(
            json.dumps(staged_manifest, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        claims_doc = json.loads((PLAN_ROOT / "g1_summary_claims.json").read_text(encoding="utf-8"))
        staged_claims = {
            **claims_doc,
            "claims": [claim for claim in claims_doc["claims"] if claim["sample_id"] in sample_ids],
        }
        claims_path = run_root / "inputs" / "g1_summary_claims.json"
        claims_path.write_text(
            json.dumps(staged_claims, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )

        metrics_path = run_root / "outputs" / "metrics.json"
        package_path = run_root / "outputs" / "selected-evidence.json"
        summary_path = run_root / "outputs" / "summary-validation.json"
        metrics_command = [
            sys.executable,
            str(PROJECT_ROOT / "scripts" / "narrative_evidence_pilot.py"),
            "--run-root",
            str(run_root),
            "--company-root",
            str(run_root / "inputs" / "company"),
            "--transcript-root",
            str(run_root / "inputs" / "transcripts"),
            "--manifest",
            str(manifest_path),
            "--output",
            str(metrics_path),
            "--package-output",
            str(package_path),
        ]
        env = os.environ.copy()
        env["PYTHONDONTWRITEBYTECODE"] = "1"
        metrics_result = subprocess.run(
            metrics_command,
            cwd=PROJECT_ROOT,
            env=env,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=False,
        )
        assert metrics_result.returncode == 0, metrics_result.stdout + metrics_result.stderr

        summary_command = [
            sys.executable,
            str(PROJECT_ROOT / "scripts" / "narrative_summary_review_pilot.py"),
            "--run-root",
            str(run_root),
            "--metrics",
            str(metrics_path),
            "--manifest",
            str(manifest_path),
            "--claims",
            str(claims_path),
            "--output",
            str(summary_path),
        ]
        summary_result = subprocess.run(
            summary_command,
            cwd=PROJECT_ROOT,
            env=env,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=False,
        )
        assert summary_result.returncode == 0, summary_result.stdout + summary_result.stderr

        metrics = json.loads(metrics_path.read_text(encoding="utf-8"))
        package_bundle = json.loads(package_path.read_text(encoding="utf-8"))
        assert metrics["totals"]["documents"] == 2
        assert metrics["totals"]["locator_roundtrip_failed_count"] == 0
        assert metrics["totals"]["anchor_check_failure_count"] == 0
        assert Path(metrics["generated_from_manifest"]).is_relative_to(run_root)
        assert all(Path(root).is_relative_to(run_root) for root in metrics["read_only_roots"])
        rows = {row["sample_id"]: row for row in metrics["samples"]}
        assert set(rows) == sample_ids
        assert all(row["locator_roundtrip_verified_count"] > 0 for row in rows.values())
        assert all(row["summary_input_bytes"] == row["summary_input_file_bytes"] for row in rows.values())
        assert all(row["anchor_check_failure_count"] == 0 for row in rows.values())
        assert metrics["selected_evidence_package"]["path"] == "outputs/selected-evidence.json"
        assert metrics["selected_evidence_package"]["byte_size"] == package_path.stat().st_size
        assert metrics["totals"]["selected_package_output_bytes"] == package_path.stat().st_size
        assert package_path.stat().st_size < metrics["totals"]["source_file_bytes"]
        assert package_bundle["schema_version"] == NARRATIVE_EVIDENCE_BUNDLE_SCHEMA_VERSION
        assert all(
            source["summary_input"]["summary_scope"] == "selected_evidence_only"
            for source in package_bundle["sources"]
        )
        package_rows = {source["sample_id"]: source for source in package_bundle["sources"]}
        assert set(package_rows) == sample_ids
        assert all(
            package_rows[sample_id]["summary_input"]["source_sha256"]
            == rows[sample_id]["source_sha256"]
            for sample_id in sample_ids
        )
        retrieval = NarrativeEvidenceSearch(package_bundle)
        pdf_hits = retrieval.search("向下游装配产业领域的延伸")
        transcript_hits = retrieval.search("TOO EARLY TO SPECULATE")
        assert pdf_hits and pdf_hits[0].document_kind == "equity_offering_prospectus"
        assert transcript_hits and transcript_hits[0].document_kind == "investor_call_transcript"
        assert transcript_hits[0].phrase_match is True
        assert all(hit.evidence_ids and hit.locators for hit in (*pdf_hits, *transcript_hits))
        package_anchors = {
            (source["summary_input"]["source_id"], evidence_id, locator)
            for source in package_bundle["sources"]
            for evidence in source["summary_input"]["evidence"]
            for evidence_id, locator in zip(evidence["evidence_ids"], evidence["locators"])
        }
        assert all(
            (hit.source_id, evidence_id, locator) in package_anchors
            for hit in (*pdf_hits, *transcript_hits)
            for evidence_id, locator in zip(hit.evidence_ids, hit.locators)
        )
        for sample in selected_samples:
            input_root = run_root / "inputs" / (
                "transcripts" if sample["language"] == "en" else "company"
            )
            staged_path = input_root / sample["path"]
            assert rows[sample["id"]]["source_sha256"] == hashlib.sha256(
                staged_path.read_bytes()
            ).hexdigest()
        assert "too early to speculate" in " ".join(
            item["excerpt"] for item in rows["T02"]["selected_evidence_preview"]
        ).casefold()

        summary = json.loads(summary_path.read_text(encoding="utf-8"))
        assert summary["status"] == "citation_and_role_checks_passed"
        assert summary["sample_count"] == 2
        assert summary["claim_count"] == 3
        assert all(draft["draft_status"] == "needs_review" for draft in summary["drafts"])
        assert summary["source_metrics"] == metrics_path.name
        assert summary["claim_spec"] == claims_path.name
        assert not list((run_root / "state" / "measure_tmp").iterdir())
        assert not any(
            "bilingual" in path.name.casefold() or "interleaved" in path.name.casefold()
            for path in run_root.rglob("*")
        )

        escaped_metrics = tmp_path / "escaped-metrics.json"
        escaped_metrics_command = list(metrics_command)
        escaped_metrics_command[escaped_metrics_command.index("--output") + 1] = str(
            escaped_metrics
        )
        escaped_metrics_result = subprocess.run(
            escaped_metrics_command,
            cwd=PROJECT_ROOT,
            env=env,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=False,
        )
        assert escaped_metrics_result.returncode != 0
        assert "inside --run-root" in escaped_metrics_result.stderr
        assert not escaped_metrics.exists()

        escaped_package = tmp_path / "escaped-package.json"
        escaped_package_command = list(metrics_command)
        escaped_package_command[
            escaped_package_command.index("--package-output") + 1
        ] = str(escaped_package)
        escaped_package_result = subprocess.run(
            escaped_package_command,
            cwd=PROJECT_ROOT,
            env=env,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=False,
        )
        assert escaped_package_result.returncode != 0
        assert "inside --run-root" in escaped_package_result.stderr
        assert not escaped_package.exists()

        escaped_summary = tmp_path / "escaped-summary.json"
        escaped_summary_command = [*summary_command[:-1], str(escaped_summary)]
        escaped_summary_result = subprocess.run(
            escaped_summary_command,
            cwd=PROJECT_ROOT,
            env=env,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=False,
        )
        assert escaped_summary_result.returncode != 0
        assert "inside --run-root" in escaped_summary_result.stderr
        assert not escaped_summary.exists()
    finally:
        if run_root.exists():
            shutil.rmtree(run_root)
        os.utime(tmp_path, ns=(parent_stat.st_atime_ns, parent_stat.st_mtime_ns))
        assert _tree_snapshot(tmp_path) == baseline


def test_selected_evidence_search_recovers_g1_anchors_across_all_samples(
    tmp_path: Path,
) -> None:
    baseline = _tree_snapshot(tmp_path)
    parent_stat = tmp_path.stat()
    run_root = tmp_path / f"multidoc-{uuid.uuid4().hex}"
    assert not run_root.exists()

    manifest = json.loads((PLAN_ROOT / "g1_sample_manifest.json").read_text(encoding="utf-8"))
    selected_samples = manifest["samples"]
    assert len(selected_samples) == 12
    for sample in selected_samples:
        source_root = TRANSCRIPT_ROOT if sample["language"] == "en" else PROJECT_ROOT
        if not (source_root / sample["path"]).is_file():
            pytest.skip(f"local G1 sample unavailable: {sample['id']}")

    run_root.mkdir()
    try:
        for sample in selected_samples:
            _copy_sample(sample, run_root)

        manifest_path = run_root / "inputs" / "g1_sample_manifest.json"
        manifest_path.parent.mkdir(parents=True, exist_ok=True)
        manifest_path.write_text(
            json.dumps({**manifest, "samples": selected_samples}, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        metrics_path = run_root / "outputs" / "metrics.json"
        package_path = run_root / "outputs" / "selected-evidence.json"
        command = [
            sys.executable,
            str(PROJECT_ROOT / "scripts" / "narrative_evidence_pilot.py"),
            "--run-root",
            str(run_root),
            "--company-root",
            str(run_root / "inputs" / "company"),
            "--transcript-root",
            str(run_root / "inputs" / "transcripts"),
            "--manifest",
            str(manifest_path),
            "--output",
            str(metrics_path),
            "--package-output",
            str(package_path),
        ]
        env = os.environ.copy()
        env["PYTHONDONTWRITEBYTECODE"] = "1"
        result = subprocess.run(
            command,
            cwd=PROJECT_ROOT,
            env=env,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=False,
        )
        assert result.returncode == 0, result.stdout + result.stderr

        metrics = json.loads(metrics_path.read_text(encoding="utf-8"))
        bundle = json.loads(package_path.read_text(encoding="utf-8"))
        assert metrics["totals"]["documents"] == 12
        assert metrics["totals"]["locator_roundtrip_failed_count"] == 0
        assert metrics["totals"]["anchor_check_failure_count"] == 0
        assert package_path.stat().st_size == metrics["totals"]["selected_package_output_bytes"]
        assert package_path.stat().st_size < metrics["totals"]["source_file_bytes"]

        metric_rows = {row["sample_id"]: row for row in metrics["samples"]}
        package_rows = {row["sample_id"]: row for row in bundle["sources"]}
        assert set(metric_rows) == set(package_rows) == {
            sample["id"] for sample in selected_samples
        }
        for sample in selected_samples:
            staged_root = run_root / "inputs" / (
                "transcripts" if sample["language"] == "en" else "company"
            )
            staged_source = staged_root / sample["path"]
            source_sha256 = hashlib.sha256(staged_source.read_bytes()).hexdigest()
            assert metric_rows[sample["id"]]["source_sha256"] == source_sha256
            assert (
                package_rows[sample["id"]]["summary_input"]["source_sha256"]
                == source_sha256
            )

        retrieval = NarrativeEvidenceSearch(bundle)
        source_paths = {}
        for sample in selected_samples:
            source = package_rows[sample["id"]]["summary_input"]
            if source["evidence"]:
                staged_root = run_root / "inputs" / (
                    "transcripts" if sample["language"] == "en" else "company"
                )
                source_paths[source["source_id"]] = staged_root / sample["path"]
        resolver = NarrativeEvidenceResolver(
            bundle,
            raw_paths_by_source_id=source_paths,
        )
        resolved_group_count = 0
        for source in bundle["sources"]:
            summary = source["summary_input"]
            for evidence in summary["evidence"]:
                group_id = evidence.get("context_group_id") or evidence["evidence_id"]
                resolved = resolver.resolve_group(
                    source_id=summary["source_id"],
                    evidence_group_id=group_id,
                )
                assert resolved.source_sha256 == summary["source_sha256"]
                assert resolved.evidence_ids == tuple(evidence["evidence_ids"])
                assert resolved.locators == tuple(evidence["locators"])
                assert resolved.raw_text == evidence["raw_text"]
                resolved_group_count += 1

        package_anchors = {
            (
                source["summary_input"]["source_id"],
                evidence_id,
                locator,
            )
            for source in bundle["sources"]
            for evidence in source["summary_input"]["evidence"]
            for evidence_id, locator in zip(evidence["evidence_ids"], evidence["locators"])
        }
        checked_anchors = 0
        for sample_id, row in metric_rows.items():
            source_id = package_rows[sample_id]["summary_input"]["source_id"]
            for anchor in row["anchor_checks"]:
                if anchor["match_scope"] != "selected_span_window":
                    continue
                expected_ids = set(anchor["matched_evidence_ids"])
                assert expected_ids
                hits = retrieval.search(anchor["matched_term"], limit=100)
                matching_hits = [hit for hit in hits if hit.source_id == source_id]
                matching_anchor_hits = [
                    hit for hit in matching_hits
                    if expected_ids.intersection(hit.evidence_ids)
                ]
                assert matching_anchor_hits, (
                    f"retrieval missed selected anchor {sample_id}/{anchor['check_id']}"
                )
                resolved_hit = resolver.resolve(matching_anchor_hits[0])
                assert resolved_hit.source_id == source_id
                assert expected_ids.intersection(resolved_hit.evidence_ids)
                for hit in matching_hits:
                    assert all(
                        (hit.source_id, evidence_id, locator) in package_anchors
                        for evidence_id, locator in zip(hit.evidence_ids, hit.locators)
                    )
                checked_anchors += 1
        assert checked_anchors > 0
        assert resolved_group_count == sum(
            len(source["summary_input"]["evidence"]) for source in bundle["sources"]
        )
        assert resolved_group_count > 0
        assert not list((run_root / "state" / "measure_tmp").iterdir())
    finally:
        if run_root.exists():
            shutil.rmtree(run_root)
        os.utime(tmp_path, ns=(parent_stat.st_atime_ns, parent_stat.st_mtime_ns))
        assert _tree_snapshot(tmp_path) == baseline
