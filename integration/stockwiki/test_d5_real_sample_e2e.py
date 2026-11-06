"""ROOT real-source replay over the delivered StockWiki/CWP E2E harness.

The selected PDF is read-only and copied by the stockwiki E2E helper into its
pytest temporary catalog.  This test does not write to the original company
document or either candidate checkout.
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
import os
from pathlib import Path
import sys


def test_real_sample_uses_processed_port_and_preserves_original(tmp_path, monkeypatch):
    sample_path = Path(os.environ["D5_REAL_PDF_SAMPLE"]).resolve(strict=True)
    stockwiki_root = Path(os.environ["STOCKWIKI_CODE_ROOT"]).resolve(strict=True)
    cwp_root = Path(os.environ["STOCKWIKI_CWP_PROJECT"]).resolve(strict=True)
    sample_before_stat = sample_path.stat()
    sample_bytes = sample_path.read_bytes()
    sample_before_sha256 = hashlib.sha256(sample_bytes).hexdigest()
    assert sample_bytes.startswith(b"%PDF-")

    e2e_path = stockwiki_root / "tests/e2e/test_cwp_processed_document.py"
    production_transport = stockwiki_root / "config/cwp_source_index.transport.json"
    transport_before = production_transport.read_bytes()
    transport_payload = json.loads(transport_before)
    assert transport_payload.get("processed_command"), (
        "the delivered production StockWiki transport must configure the CWP processed port"
    )
    spec = importlib.util.spec_from_file_location("d5_stockwiki_processed_e2e", e2e_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    assert Path(module.CWP_PROJECT).resolve(strict=True) == cwp_root

    # Replace only the generated PDF bytes. DOCX and XLSX remain format fixtures;
    # all three StockWiki entries and the producer CLI still run through the
    # original cross-repository E2E flow. The temporary workspace consumes the
    # checked-in production transport config, not the E2E's synthetic transport.
    monkeypatch.setattr(module, "_pdf_bytes", lambda: sample_bytes)
    build_workspace = module._workspace

    def _workspace_with_production_transport(workspace_tmp: Path, cwp_project: Path) -> Path:
        workspace = build_workspace(workspace_tmp, cwp_project)
        transport_path = workspace / "config" / "cwp_e2e.transport.json"
        transport_path.write_text(
            json.dumps(transport_payload), encoding="utf-8",
        )
        monkeypatch.setenv(
            "CWP_CATALOG_CONFIG", str(cwp_project / "config" / "source_catalog.yaml"),
        )
        monkeypatch.setenv("CWP_PYTHON", os.environ["STOCKWIKI_CWP_PYTHON"])
        monkeypatch.setenv("CWP_PYTHONPATH", str(cwp_root / "src"))
        return workspace

    monkeypatch.setattr(module, "_workspace", _workspace_with_production_transport)
    module.test_processed_document_port_serves_three_stockwiki_entries(
        tmp_path, monkeypatch,
    )
    assert production_transport.read_bytes() == transport_before

    sample_after_stat = sample_path.stat()
    sample_after_sha256 = hashlib.sha256(sample_path.read_bytes()).hexdigest()
    assert sample_after_sha256 == sample_before_sha256
    assert sample_after_stat.st_size == sample_before_stat.st_size
    assert sample_after_stat.st_mtime_ns == sample_before_stat.st_mtime_ns
