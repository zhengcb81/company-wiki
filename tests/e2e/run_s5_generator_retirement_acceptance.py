"""Explicit raw-only CLI acceptance on real PDF/TXT copies, outside routine CI.

Run with --annual-report <AMEC FY2025 PDF> --transcript <MSFT Q4 FY2026 TXT>.
The pinned bytes are copied into a unique short repository tmp root. The actual
scan and fingerprint-backfill CLIs, spawned parsers and catalog run normally.
No downloads, models, production catalog writes or whole-document artifacts.
"""

from __future__ import annotations

import argparse
from contextlib import closing
import hashlib
import json
import os
from pathlib import Path
import shutil
import sqlite3
import subprocess
import sys
import tempfile

import yaml


REPO_ROOT = Path(__file__).resolve().parents[2]
PINNED = {
    "annual.pdf": "d64c410832f22f5127277bad6dc357c664aede523561af99150c494857fd3aa5",
    "transcript.txt": "4ac3b4f0fa1be928b56b4ef9775cac694a1712d46785bb1fa28d2a6a68d7852a",
}


def _sha(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1_048_576), b""):
            digest.update(block)
    return digest.hexdigest()


def _cli(root: Path, *arguments: str) -> dict:
    environment = dict(os.environ, PYTHONPATH=str(REPO_ROOT / "src"),
                       PYTHONUTF8="1", PYTHONDONTWRITEBYTECODE="1",
                       PYTHON_DOTENV_DISABLED="1", COMPANY_WIKI_NETWORK="blocked",
                       COMPANY_WIKI_REAL_LLM="0")
    for name in ("OPENAI_API_KEY", "MINIMAX_API_KEY", "MIMO_API_KEY", "DEEPSEEK_API_KEY"):
        environment.pop(name, None)
    result = subprocess.run(
        [sys.executable, "-B", "-m", "company_wiki.source_catalog.cli", "--config",
         str(root / "config" / "source_catalog.yaml"), *arguments],
        cwd=root, env=environment, capture_output=True, timeout=180,
    )
    if result.returncode:
        raise RuntimeError(f"catalog {arguments[0]} failed: {result.stderr.decode('utf-8', 'replace')[-2000:]}")
    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError as error:
        raise RuntimeError(
            f"catalog {arguments[0]} returned invalid JSON; "
            f"stdout_bytes={len(result.stdout)}, head={result.stdout[:300]!r}, "
            f"stderr_tail={result.stderr[-1000:]!r}"
        ) from error


def _facts(database: Path) -> dict:
    with closing(sqlite3.connect(database)) as connection:
        return {
            "sources": connection.execute(
                "SELECT source_id,content_sha256,byte_size FROM sources ORDER BY source_id"
            ).fetchall(),
            "documents": connection.execute(
                "SELECT document_id,primary_source_id,source_status FROM documents ORDER BY document_id"
            ).fetchall(),
            "locations": connection.execute(
                "SELECT location_id,source_id,manifest_json FROM locations ORDER BY location_id"
            ).fetchall(),
        }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--annual-report", type=Path, required=True)
    parser.add_argument("--transcript", type=Path, required=True)
    arguments = parser.parse_args()
    originals = {"annual.pdf": arguments.annual_report.resolve(strict=True),
                 "transcript.txt": arguments.transcript.resolve(strict=True)}
    for name, original in originals.items():
        if _sha(original) != PINNED[name]:
            raise ValueError(f"pinned original bytes changed: {name}")
    sizes = {name: original.stat().st_size for name, original in originals.items()}
    temp_parent = REPO_ROOT / "tmp"
    temp_parent.mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="s5g-", dir=temp_parent) as temporary:
        root = Path(temporary).resolve(strict=True)
        if root.parent != temp_parent.resolve(strict=True):
            raise ValueError("test root escaped its designated parent")
        raw = root / "raw"
        raw.mkdir()
        for name, original in originals.items():
            shutil.copyfile(original, raw / name)
        configuration = root / "config"
        configuration.mkdir()
        (configuration / "source_catalog.yaml").write_text(yaml.safe_dump({
            "schema_version": "1.0", "catalog_dir": ".source_catalog",
            "roots": [{"root_id": "fixture", "path": "raw", "kind": "directory", "priority": 10}],
        }), encoding="utf-8")
        _cli(root, "scan")
        database = root / ".source_catalog" / "catalog.sqlite3"
        before = _facts(database)
        first = _cli(root, "fingerprint-backfill", "--limit", "2")
        repeat = _cli(root, "fingerprint-backfill", "--limit", "2")
        assert (first["completed"], first["failed"], first["unsupported"]) == (2, 0, 0), first
        assert repeat["completed"] == 0, repeat
        assert _facts(database) == before
        with closing(sqlite3.connect(database)) as connection:
            counts = {table: connection.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
                      for table in ("sources", "documents", "artifacts", "evidence_spans")}
            assert counts == {"sources": 2, "documents": 2, "artifacts": 0, "evidence_spans": 0}, counts
            assert connection.execute(
                "SELECT COUNT(*) FROM document_fingerprint_state WHERE status='completed'"
            ).fetchone()[0] == 2
            fingerprints = connection.execute("SELECT text_fingerprint FROM documents").fetchall()
            assert all(isinstance(row[0], str) and len(row[0]) == 64 for row in fingerprints)
        assert not (root / ".source_catalog" / "derived").exists()
        assert list((root / ".source_catalog" / "parser_tmp").iterdir()) == []
        for name, original in originals.items():
            assert _sha(original) == PINNED[name] == _sha(raw / name)
            assert original.stat().st_size == sizes[name] == (raw / name).stat().st_size
    assert not root.exists()
    print(json.dumps({
        "schema_version": "s5-generator-retirement-acceptance/1", "state": "green",
        "actual_cli": ["scan", "fingerprint-backfill", "fingerprint-backfill"],
        "raw": [{"name": name, "sha256": PINNED[name], "bytes": sizes[name]} for name in originals],
        "originals_preserved": True, "source_facts_unchanged": True,
        "artifacts": 0, "evidence_spans": 0, "derived_created": False,
        "test_root_restored_absent": True, "test_root": str(root),
        "external_llm_posts": 0, "downloads": 0, "production_cleanup_executed": False,
    }, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
