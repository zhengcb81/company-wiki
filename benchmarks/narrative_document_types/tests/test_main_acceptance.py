"""MAIN counterexamples: truthful provenance and read-only benchmark boundaries."""
from __future__ import annotations

import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess

import pytest

import run_benchmark as runner
from evaluator import GoldenValidationError, evaluate
from test_evaluator_unit import SAMPLE, _default_points, _golden, _selection


@pytest.fixture
def tiny_package(tmp_path, monkeypatch):
    package = tmp_path / "package"
    raw = tmp_path / "originals"
    package.mkdir()
    raw.mkdir()
    points = _default_points()
    data = b""
    for index, point in enumerate(points, 1):
        quote = point["quote"].encode("utf-8")
        point["locator"] = {
            "line_start": index, "line_end": index,
            "byte_start": len(data), "byte_end": len(data) + len(quote),
        }
        data += quote + b"\n"
    data += b"padding\n"
    source = raw / "source.txt"
    source.write_bytes(data)
    sample = dict(SAMPLE, source_format="txt", root_key="raw",
                  relative_path="source.txt", title="fixture", existing_kind="quarterly_report",
                  sha256=hashlib.sha256(data).hexdigest(), byte_size=len(data))
    golden = _golden(points, scope={"unit": "txt_line", "lines_read": [[1, 6]],
                                   "lines_total": 7, "uncovered": "padding", "ambiguities": []})
    docs = {"samples.json": {"samples": [sample]}, "golden.json": golden,
            "local.json": {"roots": {"raw": str(raw)}}}
    for name, value in docs.items():
        (package / name).write_text(json.dumps(value, ensure_ascii=False), encoding="utf-8")
    monkeypatch.setattr(runner, "_run_sample", lambda sample, path, **kwargs:
                        (_selection([], sha=sample["sha256"]), {}))
    return package, source, sample, golden


def _run(tiny_package, tmp_path, **kwargs):
    return runner.run(package_root=tiny_package[0],
                      output=kwargs.pop("output", tmp_path / "report.json"),
                      temp_root=kwargs.pop("temp_root", tmp_path / "scratch"), **kwargs)


def test_runtime_baseline_is_actual_head_not_card_baseline(tiny_package, tmp_path):
    report = _run(tiny_package, tmp_path)
    head = subprocess.check_output(["git", "-C", str(runner.REPO_ROOT), "rev-parse", "HEAD"],
                                   text=True).strip()
    assert report["baseline"] == head
    assert report["card_baseline"] == runner.CARD_BASELINE
    assert report["runtime_code_sha256"]["run_benchmark.py"] == runner._sha256(Path(runner.__file__))
    assert not (tmp_path / "scratch").exists()


def test_txt_golden_checks_bytes_as_well_as_lines(tiny_package):
    _, source, sample, golden = tiny_package
    point = golden["samples"]["T01"]["points"][0]
    check = runner._locator_check_factory(sample, source, {})
    assert check(sample, point)
    wrong = dict(point, locator=dict(point["locator"], byte_start=1))
    assert not check(sample, wrong)
    wrong = dict(point, locator=dict(point["locator"], line_start=2, line_end=2))
    assert not check(sample, wrong)


def test_overwrite_cannot_replace_an_original(tiny_package, tmp_path):
    source = tiny_package[1]
    before = source.read_bytes()
    with pytest.raises(ValueError, match="read-only"):
        _run(tiny_package, tmp_path, output=source, overwrite=True)
    assert source.read_bytes() == before


def test_temp_root_cannot_be_an_original_root(tiny_package, tmp_path):
    with pytest.raises(ValueError, match="read-only"):
        _run(tiny_package, tmp_path, temp_root=tiny_package[1].parent)


def test_overwrite_cannot_replace_an_unknown_owner_file(tiny_package, tmp_path):
    output = tmp_path / "owner.json"
    output.write_text('{"owner": "keep"}', encoding="utf-8")
    with pytest.raises(ValueError, match="benchmark report"):
        _run(tiny_package, tmp_path, output=output, overwrite=True)
    assert output.read_text(encoding="utf-8") == '{"owner": "keep"}'


def test_preexisting_scratch_is_preserved(tiny_package, tmp_path):
    scratch = tmp_path / "scratch"
    scratch.mkdir()
    (scratch / "owner.txt").write_text("keep", encoding="utf-8")
    with pytest.raises(FileExistsError, match="scratch"):
        _run(tiny_package, tmp_path)
    assert (scratch / "owner.txt").read_text(encoding="utf-8") == "keep"


def test_failure_removes_only_its_own_scratch(tiny_package, tmp_path, monkeypatch):
    def fail(sample, path, *, temp_root, **kwargs):
        temp_root.mkdir(exist_ok=True)
        (temp_root / "partial.json").write_text("partial", encoding="utf-8")
        raise RuntimeError("injected parser failure")
    monkeypatch.setattr(runner, "_run_sample", fail)
    with pytest.raises(RuntimeError, match="injected parser failure"):
        _run(tiny_package, tmp_path)
    assert not (tmp_path / "scratch").exists()
    assert not (tmp_path / "report.json").exists()


def test_hash_change_is_detected_even_when_size_and_mtime_match(tiny_package, tmp_path, monkeypatch):
    def mutate(sample, path, **kwargs):
        original_stat = path.stat()
        path.write_bytes(path.read_bytes().replace(b"padding", b"changed"))
        os.utime(path, ns=(original_stat.st_atime_ns, original_stat.st_mtime_ns))
        return _selection([], sha=sample["sha256"]), {}
    monkeypatch.setattr(runner, "_run_sample", mutate)
    with pytest.raises(OSError, match="original changed"):
        _run(tiny_package, tmp_path)
    assert not (tmp_path / "report.json").exists()
    assert not (tmp_path / "scratch").exists()


def test_golden_point_outside_declared_scope_is_rejected():
    points = _default_points()
    points[0]["locator"]["page_number"] = 4
    with pytest.raises(GoldenValidationError, match="scope"):
        evaluate(samples=[SAMPLE], golden=_golden(points), selections={"T01": _selection([])},
                 locator_check=lambda sample, point: True)


def test_peak_does_not_double_count_existing_measurement(tmp_path):
    (tmp_path / "measure.json").write_bytes(b"x" * 100)
    peak = runner._TempPeak(tmp_path)
    peak.record(100)
    assert peak.peak == 100


def test_clean_clone_keeps_manifest_checks_and_skips_only_real_reads(tmp_path, monkeypatch):
    import test_e2e_catalog as e2e
    import test_selection_integration as integration
    for name in ("samples.json", "golden.json", "report.json"):
        shutil.copyfile(runner.PACKAGE_ROOT / name, tmp_path / name)
    monkeypatch.setattr(integration, "PACKAGE_ROOT", tmp_path)
    manifests = integration.manifests.__wrapped__()
    integration.test_committed_report_validates_against_manifest_and_golden(manifests)
    integration.test_sample_manifest_covers_required_document_types(manifests)
    with pytest.raises(pytest.skip.Exception, match="local.json absent"):
        integration._roots(manifests)
    monkeypatch.setattr(e2e, "PACKAGE_ROOT", tmp_path)
    with pytest.raises(pytest.skip.Exception, match="local.json absent"):
        e2e.manifests.__wrapped__()


def _extractor():
    spec = importlib.util.spec_from_file_location(
        "docset_extract_pages", runner.PACKAGE_ROOT / "tools/extract_pages.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_annotation_helper_cannot_write_next_to_original(tmp_path):
    source = tmp_path / "line_00001.txt"
    source.write_bytes(b"original\n")
    with pytest.raises(ValueError, match="original"):
        _extractor().extract(source, source.parent)
    assert source.read_bytes() == b"original\n"


def test_annotation_helper_preserves_existing_output(tmp_path):
    source = tmp_path / "source.txt"
    source.write_bytes(b"original\n")
    out = tmp_path / "extract"
    out.mkdir()
    (out / "line_00001.txt").write_bytes(b"keep\n")
    with pytest.raises(FileExistsError):
        _extractor().extract(source, out)
    assert (out / "line_00001.txt").read_bytes() == b"keep\n"


def test_annotation_helper_new_scratch_and_failure_cleanup(tmp_path):
    source = tmp_path / "source.txt"
    source.write_bytes(b"first\nsecond\n")
    helper = _extractor()
    assert helper.extract(source, tmp_path / "extract") == 2
    assert (tmp_path / "extract/line_00002.txt").read_bytes() == b"second\n"
    source.write_bytes(b"\xff")
    with pytest.raises(UnicodeDecodeError):
        helper.extract(source, tmp_path / "bad-extract")
    assert not (tmp_path / "bad-extract").exists()
