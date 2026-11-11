"""Windows parser-tree ownership uses the public multiprocessing handle."""

from __future__ import annotations

import ast
from pathlib import Path


SOURCE = Path(__file__).resolve().parents[2] / "src" / "company_wiki" / "source_catalog" / "normalizer.py"


def test_windows_job_does_not_read_private_process_handle():
    tree = ast.parse(SOURCE.read_text(encoding="utf-8"), filename=str(SOURCE))
    job = next(
        node for node in tree.body
        if isinstance(node, ast.ClassDef) and node.name == "_WindowsParserJob"
    )
    source = ast.unparse(job)

    assert "process.sentinel" in source
    assert "process._handle" not in source
    assert 'getattr(process, "_handle"' not in source
