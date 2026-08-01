"""CW-1 contract tests for deterministic read-only source export."""

import hashlib
import importlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tomllib

import pytest


ROOT = Path(__file__).resolve().parents[2]
BUNDLE_FIELDS = {
    "schema_version",
    "export_id",
    "bundle_sha256",
    "source_manifest_schema_version",
    "evidence_span_schema_version",
    "counts",
    "manifests",
    "evidence_spans",
}


def _contract():
    module_name = "company_wiki.source_contract"
    assert importlib.util.find_spec(module_name) is not None
    return importlib.import_module(module_name)


def _canonical_hash(value) -> str:
    text = json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    )
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _record_pair(module, root: Path, name: str, text: str, entity: str):
    source = root / "raw" / f"{name}.md"
    source.parent.mkdir(parents=True, exist_ok=True)
    source.write_text(text, encoding="utf-8")
    manifest = module.SourceManifest.from_file(
        root=root,
        file_path=source,
        entity_ids=(entity,),
        source_type=module.SourceType.ORIGINAL_NEWS,
        published_date="2026-07-16",
        retrieved_at="2026-07-17T09:30:00Z",
        collector_name="contract-fixture",
        collector_version="1.0.0",
        mime_type="text/markdown",
    )
    span = module.EvidenceSpan.create(
        source_id=manifest.source_id,
        coordinates=module.EvidenceCoordinates(
            page_number=None,
            paragraph_index=0,
            table_index=None,
            row_index=None,
            column_index=None,
            char_start=0,
            char_end=len(text),
        ),
        raw_text=text,
        structured_value=None,
        parser_name="markdown-parser",
        parser_version="1.0.0",
        parse_status=module.ParseStatus.PARSED,
        quality_flags=(),
    )
    return source, manifest, span


def _write_jsonl(path: Path, records, *, pretty: bool = False) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if pretty:
        lines = [json.dumps(item, ensure_ascii=False, separators=(", ", ": ")) for item in records]
    else:
        lines = [json.dumps(item, ensure_ascii=False, sort_keys=True, separators=(",", ":")) for item in records]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _run_cli(cwd: Path, *args: str) -> subprocess.CompletedProcess[str]:
    cwd.mkdir(parents=True, exist_ok=True)
    env = os.environ.copy()
    env["PYTHONPATH"] = str(ROOT / "src")
    env["MINIMAX_API_KEY"] = "must-not-be-read"
    env["MIMO_API_KEY"] = "must-not-be-read"
    return subprocess.run(
        [sys.executable, "-m", "company_wiki.source_contract.cli", *args],
        cwd=cwd,
        env=env,
        text=True,
        encoding="utf-8",
        capture_output=True,
        timeout=10,
        check=False,
    )


def _tree_snapshot(root: Path):
    return tuple(
        (path.relative_to(root).as_posix(), path.read_bytes(), path.stat().st_mtime_ns)
        for path in sorted(item for item in root.rglob("*") if item.is_file())
    )


def test_bundle_builds_content_addressed_canonical_identity(tmp_path):
    module = _contract()
    root = tmp_path / "repo"
    _, manifest, span = _record_pair(module, root, "北方华创", "订单增长", "SZSE:002371")

    bundle = module.SourceExportBundle.build(
        root=root,
        manifests=(manifest,),
        evidence_spans=(span,),
    )

    assert module.SOURCE_EXPORT_SCHEMA_VERSION == "1.0.0"
    assert set(bundle.to_dict()) == BUNDLE_FIELDS
    payload = {
        "schema_version": "1.0.0",
        "source_manifest_schema_version": "1.0.0",
        "evidence_span_schema_version": "1.0.0",
        "counts": {"source_manifests": 1, "evidence_spans": 1},
        "manifests": [manifest.to_dict()],
        "evidence_spans": [span.to_dict()],
    }
    assert bundle.bundle_sha256 == _canonical_hash(payload)
    assert bundle.export_id == (
        "urn:company-wiki:source-export:sha256:" + bundle.bundle_sha256
    )
    assert json.loads(bundle.canonical_json()) == bundle.to_dict()


def test_record_order_and_json_whitespace_do_not_change_export(tmp_path):
    module = _contract()
    root = tmp_path / "repo"
    _, first_manifest, first_span = _record_pair(
        module, root, "北方华创", "订单增长", "SZSE:002371"
    )
    _, second_manifest, second_span = _record_pair(
        module, root, "中微公司", "刻蚀设备", "SSE:688012"
    )

    first = module.SourceExportBundle.build(
        root=root,
        manifests=(first_manifest, second_manifest),
        evidence_spans=(first_span, second_span),
    )
    second = module.SourceExportBundle.build(
        root=root,
        manifests=(second_manifest, first_manifest),
        evidence_spans=(second_span, first_span),
    )

    assert first == second
    assert first.canonical_json() == second.canonical_json()


def test_exact_duplicate_records_are_idempotently_deduplicated(tmp_path):
    module = _contract()
    root = tmp_path / "repo"
    _, manifest, span = _record_pair(module, root, "中芯国际", "资本开支", "HKEX:00981")
    bundle = module.SourceExportBundle.build(
        root=root,
        manifests=(manifest, manifest),
        evidence_spans=(span, span),
    )
    assert bundle.counts == {"source_manifests": 1, "evidence_spans": 1}


def test_incremental_union_matches_full_replay_byte_for_byte(tmp_path):
    module = _contract()
    root = tmp_path / "repo"
    _, first_manifest, first_span = _record_pair(
        module, root, "北方华创", "订单增长", "SZSE:002371"
    )
    _, second_manifest, second_span = _record_pair(
        module, root, "中微公司", "刻蚀设备", "SSE:688012"
    )
    base = module.SourceExportBundle.build(
        root=root,
        manifests=(first_manifest,),
        evidence_spans=(first_span,),
    )
    incremental = module.SourceExportBundle.build(
        root=root,
        manifests=(second_manifest,),
        evidence_spans=(second_span,),
        base=base,
    )
    full = module.SourceExportBundle.build(
        root=root,
        manifests=(first_manifest, second_manifest),
        evidence_spans=(first_span, second_span),
    )
    assert incremental == full
    assert incremental.canonical_json() == full.canonical_json()


def test_noop_incremental_replay_preserves_exact_bundle(tmp_path):
    module = _contract()
    root = tmp_path / "repo"
    _, manifest, span = _record_pair(module, root, "中微公司", "刻蚀设备", "SSE:688012")
    base = module.SourceExportBundle.build(
        root=root, manifests=(manifest,), evidence_spans=(span,)
    )
    replay = module.SourceExportBundle.build(
        root=root, manifests=(), evidence_spans=(), base=base
    )
    assert replay == base
    assert replay.canonical_json() == base.canonical_json()


def test_from_dict_is_strict_and_rejects_bundle_hash_tampering(tmp_path):
    module = _contract()
    root = tmp_path / "repo"
    _, manifest, span = _record_pair(module, root, "北方华创", "订单增长", "SZSE:002371")
    bundle = module.SourceExportBundle.build(
        root=root, manifests=(manifest,), evidence_spans=(span,)
    )
    assert module.SourceExportBundle.from_dict(bundle.to_dict()) == bundle

    unknown = bundle.to_dict()
    unknown["rating"] = "buy"
    with pytest.raises(ValueError, match="unknown fields"):
        module.SourceExportBundle.from_dict(unknown)

    tampered = bundle.to_dict()
    tampered["bundle_sha256"] = "b" * 64
    with pytest.raises(ValueError, match="bundle_sha256"):
        module.SourceExportBundle.from_dict(tampered)


def test_from_dict_rejects_boolean_or_non_integer_counts(tmp_path):
    module = _contract()
    root = tmp_path / "repo"
    _, manifest, span = _record_pair(module, root, "北方华创", "订单增长", "SZSE:002371")
    bundle = module.SourceExportBundle.build(
        root=root, manifests=(manifest,), evidence_spans=(span,)
    )
    for value in (True, "1", 1.0):
        data = bundle.to_dict()
        data["counts"]["source_manifests"] = value
        with pytest.raises((TypeError, ValueError), match="counts"):
            module.SourceExportBundle.from_dict(data)


def test_orphan_span_is_rejected(tmp_path):
    module = _contract()
    root = tmp_path / "repo"
    _, manifest, span = _record_pair(module, root, "北方华创", "订单增长", "SZSE:002371")
    with pytest.raises(ValueError, match="orphan"):
        module.SourceExportBundle.build(
            root=root, manifests=(), evidence_spans=(span,)
        )
    assert manifest.source_id == span.source_id


def test_same_manifest_id_with_different_metadata_is_a_conflict(tmp_path):
    module = _contract()
    root = tmp_path / "repo"
    _, manifest, span = _record_pair(module, root, "中微公司", "刻蚀设备", "SSE:688012")
    changed = manifest.to_dict()
    changed["collector_name"] = "different-collector"
    conflicting = module.SourceManifest.from_dict(changed)
    with pytest.raises(ValueError, match="manifest.*conflict"):
        module.SourceExportBundle.build(
            root=root,
            manifests=(manifest, conflicting),
            evidence_spans=(span,),
        )


def test_same_span_id_with_different_parser_metadata_is_a_conflict(tmp_path):
    module = _contract()
    root = tmp_path / "repo"
    _, manifest, span = _record_pair(module, root, "中微公司", "刻蚀设备", "SSE:688012")
    changed = span.to_dict()
    changed["parser_version"] = "2.0.0"
    conflicting = module.EvidenceSpan.from_dict(changed)
    assert conflicting.span_id == span.span_id
    with pytest.raises(ValueError, match="span.*conflict"):
        module.SourceExportBundle.build(
            root=root,
            manifests=(manifest,),
            evidence_spans=(span, conflicting),
        )


def test_same_source_locator_with_changed_output_is_a_conflict(tmp_path):
    module = _contract()
    root = tmp_path / "repo"
    _, manifest, span = _record_pair(module, root, "中微公司", "刻蚀设备", "SSE:688012")
    changed = module.EvidenceSpan.create(
        source_id=manifest.source_id,
        coordinates=span.coordinates,
        raw_text="不同输出",
        structured_value=None,
        parser_name="markdown-parser",
        parser_version="2.0.0",
        parse_status="parsed",
        quality_flags=(),
    )
    assert changed.locator == span.locator
    assert changed.span_id != span.span_id
    with pytest.raises(ValueError, match="locator.*conflict"):
        module.SourceExportBundle.build(
            root=root,
            manifests=(manifest,),
            evidence_spans=(span, changed),
        )


@pytest.mark.parametrize("mutation", ("delete", "move", "same_size_tamper"))
def test_export_fails_closed_when_raw_is_missing_moved_or_modified(tmp_path, mutation):
    module = _contract()
    root = tmp_path / "repo"
    source, manifest, span = _record_pair(
        module, root, "北方华创", "订单增长", "SZSE:002371"
    )
    if mutation == "delete":
        source.unlink()
    elif mutation == "move":
        source.rename(source.with_name("moved.md"))
    else:
        original = source.read_bytes()
        replacement = b"X" * len(original)
        assert len(replacement) == len(original)
        source.write_bytes(replacement)

    with pytest.raises(module.SourceManifestMismatchError):
        module.SourceExportBundle.build(
            root=root, manifests=(manifest,), evidence_spans=(span,)
        )


def test_incremental_export_reverifies_raw_referenced_only_by_base(tmp_path):
    module = _contract()
    root = tmp_path / "repo"
    source, manifest, span = _record_pair(
        module, root, "北方华创", "订单增长", "SZSE:002371"
    )
    base = module.SourceExportBundle.build(
        root=root, manifests=(manifest,), evidence_spans=(span,)
    )
    source.unlink()
    with pytest.raises(module.SourceManifestMismatchError):
        module.SourceExportBundle.build(
            root=root, manifests=(), evidence_spans=(), base=base
        )


def test_bundle_has_no_time_path_or_research_state_fields(tmp_path):
    module = _contract()
    root = tmp_path / "repo"
    _, manifest, span = _record_pair(module, root, "中芯国际", "资本开支", "HKEX:00981")
    exported = module.SourceExportBundle.build(
        root=root, manifests=(manifest,), evidence_spans=(span,)
    ).to_dict()
    forbidden = {
        "generated_at",
        "output_path",
        "rating",
        "target_price",
        "valuation",
        "review_decision",
        "accepted_investment_conclusion",
    }
    assert not forbidden & set(exported)


def test_cli_help_exposes_only_read_only_export_surface(tmp_path):
    result = _run_cli(tmp_path / "cwd", "--help")
    assert result.returncode == 0, result.stderr
    assert "export" in result.stdout
    assert "--output" not in result.stdout
    for forbidden in ("publish", "approve", "daemon", "stockwiki"):
        assert forbidden not in result.stdout.lower()


def test_cli_replays_identical_stdout_without_writing_source_or_cwd(tmp_path):
    module = _contract()
    root = tmp_path / "repo"
    _, manifest, span = _record_pair(module, root, "北方华创", "订单增长", "SZSE:002371")
    inputs = tmp_path / "inputs"
    manifests = inputs / "manifests.jsonl"
    spans = inputs / "spans.jsonl"
    _write_jsonl(manifests, [manifest.to_dict()], pretty=True)
    _write_jsonl(spans, [span.to_dict()], pretty=True)
    cwd = tmp_path / "cwd"
    cwd.mkdir()
    before = _tree_snapshot(root)

    args = (
        "export",
        "--root",
        str(root),
        "--manifests",
        str(manifests),
        "--spans",
        str(spans),
    )
    first = _run_cli(cwd, *args)
    second = _run_cli(cwd, *args)

    assert first.returncode == second.returncode == 0
    assert first.stderr == second.stderr == ""
    assert first.stdout == second.stdout
    assert first.stdout.endswith("\n") and first.stdout.count("\n") == 1
    assert json.loads(first.stdout)["counts"] == {
        "source_manifests": 1,
        "evidence_spans": 1,
    }
    assert _tree_snapshot(root) == before
    assert list(cwd.iterdir()) == []


def test_cli_incremental_output_matches_full_output(tmp_path):
    module = _contract()
    root = tmp_path / "repo"
    _, first_manifest, first_span = _record_pair(
        module, root, "北方华创", "订单增长", "SZSE:002371"
    )
    _, second_manifest, second_span = _record_pair(
        module, root, "中微公司", "刻蚀设备", "SSE:688012"
    )
    inputs = tmp_path / "inputs"
    first_manifests = inputs / "first-manifests.jsonl"
    first_spans = inputs / "first-spans.jsonl"
    second_manifests = inputs / "second-manifests.jsonl"
    second_spans = inputs / "second-spans.jsonl"
    all_manifests = inputs / "all-manifests.jsonl"
    all_spans = inputs / "all-spans.jsonl"
    _write_jsonl(first_manifests, [first_manifest.to_dict()])
    _write_jsonl(first_spans, [first_span.to_dict()])
    _write_jsonl(second_manifests, [second_manifest.to_dict()])
    _write_jsonl(second_spans, [second_span.to_dict()])
    _write_jsonl(all_manifests, [second_manifest.to_dict(), first_manifest.to_dict()])
    _write_jsonl(all_spans, [second_span.to_dict(), first_span.to_dict()])
    cwd = tmp_path / "cwd"

    base_result = _run_cli(
        cwd,
        "export",
        "--root",
        str(root),
        "--manifests",
        str(first_manifests),
        "--spans",
        str(first_spans),
    )
    assert base_result.returncode == 0, base_result.stderr
    base = inputs / "base.json"
    base.write_text(base_result.stdout, encoding="utf-8")
    incremental = _run_cli(
        cwd,
        "export",
        "--root",
        str(root),
        "--base",
        str(base),
        "--manifests",
        str(second_manifests),
        "--spans",
        str(second_spans),
    )
    full = _run_cli(
        cwd,
        "export",
        "--root",
        str(root),
        "--manifests",
        str(all_manifests),
        "--spans",
        str(all_spans),
    )
    assert incremental.returncode == full.returncode == 0
    assert incremental.stdout == full.stdout


@pytest.mark.parametrize("problem", ("malformed", "blank_line", "orphan", "tampered_raw"))
def test_cli_errors_have_no_partial_stdout_or_writes(tmp_path, problem):
    module = _contract()
    root = tmp_path / "repo"
    source, manifest, span = _record_pair(
        module, root, "北方华创", "订单增长", "SZSE:002371"
    )
    inputs = tmp_path / "inputs"
    manifests = inputs / "manifests.jsonl"
    spans = inputs / "spans.jsonl"
    _write_jsonl(manifests, [manifest.to_dict()])
    _write_jsonl(spans, [span.to_dict()])
    if problem == "malformed":
        manifests.write_text("{not-json}\n", encoding="utf-8")
    elif problem == "blank_line":
        spans.write_text(span.canonical_json() + "\n\n", encoding="utf-8")
    elif problem == "orphan":
        manifests.write_text("", encoding="utf-8")
    else:
        source.write_bytes(b"X" * source.stat().st_size)
    cwd = tmp_path / "cwd"
    before = _tree_snapshot(root)

    result = _run_cli(
        cwd,
        "export",
        "--root",
        str(root),
        "--manifests",
        str(manifests),
        "--spans",
        str(spans),
    )
    assert result.returncode == 2
    assert result.stdout == ""
    assert "source export failed" in result.stderr
    assert "must-not-be-read" not in result.stderr
    assert _tree_snapshot(root) == before
    assert list(cwd.iterdir()) == []


def test_cli_rejects_no_inputs_and_missing_root_without_writes(tmp_path):
    cwd = tmp_path / "cwd"
    no_inputs = _run_cli(cwd, "export", "--root", str(tmp_path / "repo"))
    assert no_inputs.returncode == 2
    assert no_inputs.stdout == ""
    assert list(cwd.iterdir()) == []


def test_cli_rejects_explicit_but_empty_manifest_input(tmp_path):
    root = tmp_path / "repo"
    root.mkdir()
    manifests = tmp_path / "inputs" / "manifests.jsonl"
    manifests.parent.mkdir()
    manifests.write_text("", encoding="utf-8")
    cwd = tmp_path / "cwd"
    result = _run_cli(
        cwd,
        "export",
        "--root",
        str(root),
        "--manifests",
        str(manifests),
    )
    assert result.returncode == 2
    assert result.stdout == ""
    assert "source export failed" in result.stderr
    assert list(cwd.iterdir()) == []


def test_console_script_is_packaged():
    project = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    assert project["project"]["scripts"]["company-wiki-source-export"] == (
        "company_wiki.source_contract.cli:main"
    )


def test_export_contract_documentation_covers_replay_and_boundaries():
    text = (ROOT / "docs" / "contracts" / "source-export-v1.md").read_text(
        encoding="utf-8"
    )
    for term in (
        "stdout",
        "JSONL",
        "bundle_sha256",
        "export_id",
        "--base",
        "incremental",
        "replay",
        "raw",
        "StockWiki",
        "accepted investment conclusion",
    ):
        assert term in text
