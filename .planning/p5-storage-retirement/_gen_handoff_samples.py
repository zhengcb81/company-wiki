"""Generate handoff sample manifest/receipts on an isolated real-schema fixture."""

import sys, tempfile, shutil, json, sqlite3
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, "tests/unit_only_" if False else str(REPO / "tests"))
sys.path.insert(0, str(REPO / "tools"))
sys.path.insert(0, "tests/unit")

from test_p5_storage_retirement_common import build_catalog  # noqa: E402

OUT = REPO / "docs" / "implementation" / "handoffs" / "P5-STORAGE" / "samples"
TOOL = REPO / "tools" / "legacy_storage_retirement.py"


def main() -> dict:
    metrics: dict = {}
    root = Path(tempfile.mkdtemp(prefix="p5-handoff-"))
    try:
        config, store, _facts = build_catalog(root)
        config_path = root / "catalog.json"
        config_path.write_text(
            json.dumps(
                {
                    "schema_version": "1.0",
                    "catalog_dir": str(config.catalog_dir),
                    "roots": [
                        {
                            "root_id": root_spec.root_id,
                            "path": str(root_spec.path),
                            "kind": root_spec.kind,
                            "priority": root_spec.priority,
                        }
                        for root_spec in config.roots
                    ],
                }
            ),
            encoding="utf-8",
        )
        __os = __import__("os")
        env = {
            "PYTHONPATH": str(REPO / "src"),
            "PATH": __os.environ["PATH"],
            "USERPROFILE": __os.environ.get("USERPROFILE", ""),
            "HOME": __os.environ.get("HOME", ""),
        }

        def run(*args):
            import subprocess

            proc = subprocess.run(
                [sys.executable, str(TOOL), *args],
                capture_output=True,
                env=env,
                timeout=300,
            )
            assert proc.returncode == 0, proc.stderr.decode("utf-8", "replace")
            return proc

        (root / "src_news.md").write_bytes(b"x")
        manifest_path = root / "sample_manifest.json"
        run("inventory", "--config", str(config_path), "--output", str(manifest_path))
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        for i in manifest["candidates"]:
            i["path"] = "<fixture>/derived/..."
        manifest["catalog_dir"] = "<fixture>/catalog"
        manifest["database_path"] = "<fixture>/catalog/catalog.sqlite3"
        sqlite3.connect(config.database_path).close()

        receipts = {}
        import subprocess

        proc = subprocess.run(
            [
                sys.executable,
                str(TOOL),
                "retire-derived",
                "--config",
                str(config_path),
                "--manifest",
                str(manifest_path),
                "--receipt",
                str(root / "retire.json"),
                "--apply",
            ],
            capture_output=True,
            env=env,
            timeout=300,
        )
        assert proc.returncode == 0, proc.stderr.decode("utf-8", "replace")
        receipts["retire-derived"] = json.loads(
            (root / "retire.json").read_text(encoding="utf-8")
        )
        keep = root / "keep.jsonl"
        sqliteconn = sqlite3.connect(config.database_path)
        pair = sqliteconn.execute(
            "SELECT source_id, locator FROM evidence_spans LIMIT 1"
        ).fetchone()
        sqliteconn.close()
        keep.write_text(
            json.dumps({"source_id": pair[0], "locator": pair[1]}), encoding="utf-8"
        )
        sel = root / "selection.json"
        sel.write_text(
            json.dumps(
                {
                    "schema_version": "cwp-span-selection/1",
                    "parser_name": "plain_text",
                    "parser_version": "1.0.0",
                    "source_ids": [],
                    "document_ids": [],
                }
            ),
            encoding="utf-8",
        )
        proc = subprocess.run(
            [
                sys.executable,
                str(TOOL),
                "prune-spans",
                "--config",
                str(config_path),
                "--selection",
                str(sel),
                "--keep-refs",
                str(keep),
                "--receipt",
                str(root / "prune.json"),
                "--apply",
            ],
            capture_output=True,
            env=env,
            timeout=300,
        )
        assert proc.returncode == 0, proc.stderr.decode("utf-8", "replace")
        receipts["prune-spans"] = json.loads(
            (root / "prune.json").read_text(encoding="utf-8")
        )
        proc = subprocess.run(
            [
                sys.executable,
                str(TOOL),
                "vacuum",
                "--config",
                str(config_path),
                "--receipt",
                str(root / "vacuum.json"),
                "--apply",
            ],
            capture_output=True,
            env=env,
            timeout=300,
        )
        assert proc.returncode == 0, proc.stderr.decode("utf-8", "replace")
        receipts["vacuum"] = json.loads(
            (root / "vacuum.json").read_text(encoding="utf-8")
        )

        def trim(obj):
            if isinstance(obj, dict):
                return {k: trim(v) for k, v in obj.items() if k not in {"candidates"}}
            if isinstance(obj, tuple):
                return [trim(v) for v in obj]
            if isinstance(obj, list):
                return [trim(v) for v in obj]
            return obj

        OUT.mkdir(parents=True, exist_ok=True)
        manifest["candidates"] = manifest["candidates"][:2]
        (OUT / "sample_manifest.json").write_text(
            json.dumps(manifest, ensure_ascii=False, indent=1, sort_keys=True),
            encoding="utf-8",
        )
        for op, report in receipts.items():
            trimmed = trim(report)
            report["candidates"] = (
                report["candidates"][:2]
                if isinstance(report.get("candidates"), list)
                else report.get("candidates")
            )
            (OUT / f"sample_{op}_receipt.json").write_text(
                json.dumps(trimmed, ensure_ascii=False, indent=1, sort_keys=True),
                encoding="utf-8",
            )
            metrics[op] = {
                "deleted": len(report["deleted"])
                if isinstance(report["deleted"], list)
                else report["deleted"],
                "already_absent": len(report["already_absent"])
                if isinstance(report["already_absent"], list)
                else report["already_absent"],
                "files_bytes_before": report["files_bytes_before"],
                "files_bytes_after": report["files_bytes_after"],
                "database_bytes_before": report["database_bytes_before"],
                "database_bytes_after": report["database_bytes_after"],
                "page_count_before": report["page_count_before"],
                "page_count_after": report["page_count_after"],
                "freelist_before": report["freelist_before"],
                "freelist_after": report["freelist_after"],
                "integrity": report["integrity_check"],
                "fk": report["foreign_key_check"],
                "facts_tables": len(report["source_facts_after"]),
                "facts_equal": report["source_facts_before"]
                == report["source_facts_after"],
                "status": report["status"],
            }
        print(json.dumps(metrics, ensure_ascii=False))
        for path in sorted(OUT.glob("*.json")):
            print("wrote", path.name, path.stat().st_size, "bytes")
    finally:
        shutil.rmtree(root, ignore_errors=True)
    return metrics


if __name__ == "__main__":
    main()
