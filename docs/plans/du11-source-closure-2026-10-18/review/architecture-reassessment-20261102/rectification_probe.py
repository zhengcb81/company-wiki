"""Offline reassessment probe; never opens production config/catalog or providers."""
from __future__ import annotations

from dataclasses import asdict, replace
import io
import json
from pathlib import Path
import sys
import tempfile
from unittest.mock import patch


def main():
    root = next(p for p in Path(__file__).resolve().parents
                if (p / "src/company_wiki").is_dir())
    sys.path[:0] = [str(root / "src"), str(root / "tests")]
    from company_wiki.document_normalization.local_ocr import LocalOCRConfig, OCRModelFile
    from company_wiki.source_catalog.narrative_normalization import NarrativeNormalization
    from company_wiki.source_catalog import source_export_v2_cli as export
    from company_wiki.source_catalog import official_source_cli as official
    from company_wiki.source_catalog import source_query_cli as query
    from company_wiki.source_catalog.resolver import SourceRequest

    class Input:
        def __init__(self, body):
            self.buffer = io.BytesIO(body)

    report = {}
    with tempfile.TemporaryDirectory(prefix="cwp-readonly-input-audit-") as directory:
        temp = Path(directory)
        (temp / "config").mkdir()
        model = OCRModelFile("C:/synthetic/model.onnx", "a" * 64)
        config = LocalOCRConfig(model, model, model, "synthetic", "synthetic", "b" * 64)
        path = temp / "config/local_ocr.json"
        raw = json.dumps(config.to_dict()).encode()
        path.write_bytes(raw)
        short = NarrativeNormalization.from_project(temp).snapshot()
        padded = raw + b" " * 65536
        assert json.loads(raw) == json.loads(padded)
        path.write_bytes(padded)
        try:
            NarrativeNormalization.from_project(temp)
            error = None
        except ValueError as exc:
            error = str(exc)
        report["ocr"] = {"compact_bytes": len(raw), "padded_bytes": len(padded),
                         "compact_accepted": short == config.to_dict(), "padded_error": error}
        path = temp / "request.json"
        raw = b'{"schema_version":"official-source-capture-request/1"}'
        path.write_bytes(raw)
        short = official._read_json(path)
        path.write_bytes(raw + b" " * 65536)
        try:
            official._read_json(path)
            error = None
        except ValueError as exc:
            error = str(exc)
        report["official_reader"] = {"compact_bytes": len(raw), "padded_bytes": path.stat().st_size,
                                     "compact_accepted": short == json.loads(raw), "padded_error": error}
    report["temporary_directory_removed"] = not Path(directory).exists()

    request = {"schema_version": export.SOURCE_REF_SCHEMA_VERSION, "source_refs": [], "evidence_spans": []}
    raw = json.dumps(request).encode()
    with patch.object(export.sys, "stdin", Input(raw)):
        short = export._read_request()
    padded = raw + b" " * (16 * 1024 * 1024)
    with patch.object(export.sys, "stdin", Input(padded)):
        try:
            export._read_request()
            error = None
        except ValueError as exc:
            error = str(exc)
    report["export_reader"] = {"compact_bytes": len(raw), "padded_bytes": len(padded),
                               "compact_accepted": short == ((), ()), "padded_error": error}
    raw = json.dumps(asdict(SourceRequest(entity="SYNTHETIC", document_kind="annual_report",
        as_of_date="2026-11-02", market="US", fiscal_year=2025, fiscal_period="FY"))).encode()
    rows = []
    for label, body in (("compact", raw), ("equivalent_padded", raw + b" " * 65536)):
        output = io.StringIO()
        with patch.object(query.sys, "stdin", Input(body)), patch.object(query.sys, "stdout", output), \
             patch.object(query, "load_catalog_config", side_effect=OSError("synthetic config unavailable")) as loader:
            code = query.main(["--config", "C:/synthetic/no-config.yaml"])
        rows.append({"input": label, "bytes": len(body), "config_owner_reached": loader.call_count == 1,
                     "exit": code, "output": json.loads(output.getvalue())})
    report["query_public_cli"] = rows

    from support.fresh_summary_fixture import grouped_selection, claim, draft_for
    from company_wiki.automation.narrative_model import NarrativeModelRequest, NarrativeModelResponse, decode_model_draft
    from company_wiki.automation.narrative_summary_assessment import prose_diagnostics, atomic_prose_diagnostics
    from company_wiki.automation.narrative_model_runtime import build_model_request, decode_model_draft as decode_runtime
    from company_wiki.automation.narrative_model_scoped import compile_scoped_model_view
    from unit.test_narrative_reading_transport import reading_context
    texts = tuple(f"公司第{i}号设备已完成交付，并已通过客户验收。" for i in range(21))
    selected = grouped_selection(texts, (None,) * 21)
    request = NarrativeModelRequest.from_selection(selected)
    payload = draft_for(selected, [claim(text, [f"e{i+1}"], [], name=f"c{i}") for i, text in enumerate(texts)])
    response = NarrativeModelResponse("offline", "fixture", request.prompt_version,
                                     json.dumps(payload, ensure_ascii=False).encode())
    report["claims_retained"] = len(decode_model_draft(response, selected=selected)["claims"])
    texts = ("公司计划在项目建成后为工厂提供产能保障。", "该安排仍须客户完成验收后方可投产。")
    rewritten = "公司已为工厂提供产能保障。"
    selected = grouped_selection(texts, ("conditional", "conditional"))
    request = NarrativeModelRequest.from_selection(selected)
    response = NarrativeModelResponse("offline", "fixture", request.prompt_version,
        json.dumps(draft_for(selected, [claim(rewritten, ["e1", "e2"], ["g1"])]), ensure_ascii=False).encode())
    legacy = decode_model_draft(response, selected=selected)
    context = reading_context(selected)
    context["groups"] = context["groups"][:1]
    selected = replace(selected, reading_context=context)
    request = build_model_request(selected, reading_projection_version="reading-model-input/7")
    view = compile_scoped_model_view(selected, max_claims=40)
    task = view.model_tasks[0]
    parts = [part for part, sid in view.to_binding()["task_parts"][task.key].items() if sid in task.support_ids]
    response = NarrativeModelResponse("offline", "fixture", request.prompt_version,
        json.dumps({"drafts_by_task": {task.key: [{"text": rewritten, "basis_parts": parts, "modality": "actual"}]}},
                   ensure_ascii=False).encode())
    current = decode_runtime(response, selected=selected, reading_projection_version="reading-model-input/7")
    report["semantic_open"] = {"source": texts, "claim": rewritten,
        "legacy": {"status": legacy["status"], "needs_review": legacy["claims"][0]["needs_review"]},
        "v7": {"status": current["status"], "needs_review": current["claims"][0]["needs_review"]},
        "prose_diagnostics": prose_diagnostics(texts[0], rewritten, "actual"),
        "atomic_diagnostics": atomic_prose_diagnostics(texts[0], rewritten, "actual")}
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
