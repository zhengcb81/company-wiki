"""Real source-catalog official CLI lifecycle in an isolated synthetic catalog."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys


def test_real_public_import_project_reopen_read_export_and_failure(tmp_path):
    (tmp_path / "companies").mkdir()
    config = tmp_path / "config.json"
    config.write_text(json.dumps({"schema_version": "1.0", "catalog_dir": "catalog",
        "roots": [{"root_id": "company_raw", "path": "companies", "kind": "company_raw"}]}),
        encoding="utf-8")
    value = {"ok": True, "result": {"page": 1, "page_size": 1, "page_count": 1,
        "item_total": 1, "items": [{"ref": 901, "org_id": 1, "org_name": "测试公司",
        "q": "新业务何时交付？", "a": "新业务预计四季度交付。", "answered": True,
        "created_at": "2026-09-01 10:00:00", "updated_at": "2026-09-01 10:00:00"}]}}
    original = (json.dumps(value, ensure_ascii=False, indent=2).replace("\n", "\r\n")
                + "\r\n ").encode("utf-8")
    sha = hashlib.sha256(original).hexdigest()
    original_file = tmp_path / "原件.json"
    original_file.write_bytes(original)
    repo = Path(__file__).resolve().parents[2]
    env = {**os.environ, "PYTHONPATH": str(repo / "src"), "PYTHONDONTWRITEBYTECODE": "1"}

    def execute(operation, request, *, input_file=None):
        request_file = tmp_path / "请求.json"
        request_file.write_text(json.dumps(request, ensure_ascii=False), encoding="utf-8")
        argv = [sys.executable, "-X", "utf8", "-B", "-m", "company_wiki.source_catalog.cli",
                "official", "--config", str(config), "--project-root", str(tmp_path),
                "--operation", operation, "--request", str(request_file)]
        if input_file is not None:
            argv.extend(["--input-file", str(input_file)])
        return subprocess.run(argv, cwd=tmp_path, env=env, capture_output=True, timeout=60)

    imported = execute("import", {"schema_version": "official-source-import-request/2",
        "request_id": "synthetic-cli-" + sha, "max_bytes": 1048576, "content_sha256": sha,
        "mime_type": "application/json", "document_kind": "investor_relations",
        "source_subject": {"kind": "multi_issuer_event", "event_namespace": "fixture",
                           "event_id": "901", "issuer_refs": [], "attribution_status": "partial"},
        "capture_receipt": {"capture_method": "local_document", "tool_name": "synthetic-cli",
            "tool_call_id": sha, "captured_at": "2026-10-10T00:00:00Z",
            "response_bytes": len(original), "content_sha256": sha}}, input_file=original_file)
    assert imported.returncode == 0, imported.stderr
    ref = json.loads(imported.stdout)["source_ref"]
    projected = execute("project", {"schema_version": "official-json-projection-request/1",
        "parent_source_refs": [ref], "layout_id": "official-flat-list",
        "issuer": {"provider_company_id": 1}, "as_of_date": "2026-10-08", "persist": True})
    assert projected.returncode == 0, projected.stderr
    projection = json.loads(projected.stdout)["projection"]
    for operation, schema in [("replay", "official-json-replay-request/1"),
                              ("export", "source-projection-export-request/1")]:
        result = execute(operation, {"schema_version": schema, "projection_id": projection["projection_id"]})
        assert result.returncode == 0, result.stderr
        assert isinstance(json.loads(result.stdout), dict)
    read = execute("read", {"schema_version": "official-source-read-request/1", "source_ref": ref})
    assert read.returncode == 0, read.stderr
    assert read.stdout == original
    assert hashlib.sha256(read.stdout).hexdigest() == sha
    bad = execute("project", {"schema_version": "unknown"})
    assert bad.returncode == 2
    assert bad.stdout == b""
    assert json.loads(bad.stderr)["schema_version"] == "official-source-failure/1"
    assert str(tmp_path).encode() not in bad.stderr
    assert original_file.read_bytes() == original
