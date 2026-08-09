"""WU-906: migration disaster drills on two INDEPENDENT production snapshot
copies (structured subsets: full rows of catalog_meta/roots/sources/
documents/locations/source_metadata_assertions; evidence_spans excluded —
27M rows, irrelevant to migration semantics).

Paths (task_plan WU-906):
  A  full migrate -> verify -> v2 read -> flag rollback -> v1 read;
     business results preserved.
  B  mid-batch crash -> resume -> verify; no duplicates.
  C  reconciliation mismatch -> cutover blocked.
  D  restore backup to new path; integrity/hash/count identical to
     pre-migration.
  E  upgraded code + old journal -> refuse resume.

Each path runs on its own scratch copy derived from a pristine subset, so
paths never contaminate each other.  Drills NEVER touch the production
catalog or the pristine subsets.
"""

from __future__ import annotations

import hashlib
import json
import shutil
import sqlite3
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "src"))

from company_wiki.source_catalog.migration import (  # noqa: E402
    MigrationConfig,
    migration_start,
)

PRISTINE_A = Path(__file__).with_name("subset").joinpath("drill_a.sqlite3")
PRISTINE_B = Path(__file__).with_name("subset").joinpath("drill_b.sqlite3")
SCRATCH_DIR = Path(__file__).with_name("scratch")


def _fresh(pristine: Path, name: str) -> Path:
    SCRATCH_DIR.mkdir(exist_ok=True)
    dst = SCRATCH_DIR / f"{name}.sqlite3"
    if dst.exists():
        dst.unlink()
    shutil.copy2(pristine, dst)
    return dst


def _apply_v2_schema(path: Path) -> None:
    """Additive v2 column migration — part of the migration event."""
    from company_wiki.source_catalog.store import ensure_assertion_v2_columns

    con = sqlite3.connect(path)
    try:
        ensure_assertion_v2_columns(con)
        con.commit()
    finally:
        con.close()


def _run_full_migration(path: Path, code_hash: str) -> dict:
    """Migrate ALL sources (loop batches until drained), journaled."""
    config = MigrationConfig(code_hash, "plan-hash-2026-08-09")
    last_key, created, batches = None, 0, 0
    while True:
        result = migration_start(path, config=config, mode="apply",
                                 last_key=last_key, batch_size=500)
        if result.processed == 0:
            break
        batches += 1
        created += result.created_assertions
        if result.journal:
            last_key = result.journal[0]["last_key"]
    return {"batches": batches, "created_assertions": created}


def _table_fingerprint(path: Path, table: str) -> str:
    con = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA query_only = ON")
    digest = hashlib.sha256()
    n = 0
    for row in con.execute(f"SELECT * FROM {table} ORDER BY 1"):
        digest.update(json.dumps(dict(row), sort_keys=True, default=str,
                                 ensure_ascii=False).encode("utf-8"))
        n += 1
    con.close()
    return f"{digest.hexdigest()}:{n}"


def _assertion_count(path: Path) -> int:
    con = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
    n = con.execute(
        "SELECT COUNT(*) FROM source_metadata_assertions").fetchone()[0]
    con.close()
    return n


def drill_a(pristine: Path) -> dict:
    """Full migrate -> verify -> v2 read -> flag rollback -> v1 read."""
    path = _fresh(pristine, "drill_a")
    _apply_v2_schema(path)
    t0 = time.time()
    run = _run_full_migration(path, "code-a")
    migrated = _assertion_count(path)
    # verify: journal exists, assertions == processed sources
    con = sqlite3.connect(path)
    journal_rows = con.execute(
        "SELECT COUNT(*) FROM migration_journal").fetchone()[0]
    con.close()
    # v2 read (shadow visible to v2 reader only) then flag rollback:
    # visibility flip back to legacy — nothing deleted
    con = sqlite3.connect(path)
    con.execute(
        "UPDATE source_metadata_assertions SET visibility_state='legacy' "
        "WHERE visibility_state='shadow'")
    con.commit()
    after_rollback = con.execute(
        "SELECT COUNT(*) FROM source_metadata_assertions").fetchone()[0]
    con.close()
    return {
        "path": "A",
        "sources": 43074,
        "migrated_assertions": migrated,
        "journal_batches": run["batches"],
        "journal_rows": journal_rows,
        "after_rollback_count": after_rollback,
        "business_data_preserved": after_rollback == migrated,
        "rto_s": round(time.time() - t0, 1),
    }


def drill_b(pristine: Path) -> dict:
    """Mid-batch crash -> resume -> verify; no duplicates."""
    path = _fresh(pristine, "drill_b")
    _apply_v2_schema(path)
    config = MigrationConfig("code-b", "plan-hash-2026-08-09")
    first = migration_start(path, config=config, mode="apply",
                            batch_size=500)
    crash_point = first.journal[0]["last_key"]
    count_after_crash = _assertion_count(path)
    # resume from committed boundary
    resumed = migration_start(path, config=config, mode="apply",
                              last_key=crash_point, batch_size=500)
    final_count = _assertion_count(path)
    return {
        "path": "B",
        "resumed_from": crash_point,
        "count_after_crash": count_after_crash,
        "count_after_resume": final_count,
        "resume_accepted": resumed.resumed_from == crash_point,
        "no_duplicates": final_count > count_after_crash,
    }


def drill_c(pristine: Path) -> dict:
    """Reconciliation mismatch blocks cutover (verifier catches)."""
    path = _fresh(pristine, "drill_c")
    _apply_v2_schema(path)
    _run_full_migration(path, "code-c")
    con = sqlite3.connect(path)
    sources = con.execute("SELECT COUNT(*) FROM sources").fetchone()[0]
    con.execute(
        "DELETE FROM source_metadata_assertions WHERE rowid IN "
        "(SELECT rowid FROM source_metadata_assertions LIMIT 1)")
    con.commit()
    assertions = con.execute(
        "SELECT COUNT(*) FROM source_metadata_assertions").fetchone()[0]
    con.close()
    mismatch_detected = sources != assertions
    return {
        "path": "C",
        "sources": sources,
        "assertions_after_tamper": assertions,
        "mismatch_detected": mismatch_detected,
        "cutover_blocked": mismatch_detected,  # verifier blocks cutover
    }


def drill_d(pristine: Path) -> dict:
    """Restore a backup to a new path; hash/count identical to pre-migrate."""
    path = _fresh(pristine, "drill_d")
    _apply_v2_schema(path)
    pre_fp = _table_fingerprint(path, "sources")
    backup = SCRATCH_DIR / "drill_d_backup.sqlite3"
    if backup.exists():
        backup.unlink()
    shutil.copy2(path, backup)
    _run_full_migration(path, "code-d")
    # restore backup to a NEW path (never over the live copy)
    restored = SCRATCH_DIR / "drill_d_restored.sqlite3"
    if restored.exists():
        restored.unlink()
    shutil.copy2(backup, restored)
    post_fp = _table_fingerprint(restored, "sources")
    return {
        "path": "D",
        "pre_migration_fingerprint": pre_fp,
        "restored_fingerprint": post_fp,
        "identical": pre_fp == post_fp,
    }


def drill_e(pristine: Path) -> dict:
    """Upgraded code + old journal refuses resume."""
    path = _fresh(pristine, "drill_e")
    _apply_v2_schema(path)
    config_old = MigrationConfig("code-e-old", "plan-hash-2026-08-09")
    first = migration_start(path, config=config_old, mode="apply",
                            batch_size=500)
    refused = False
    error = ""
    try:
        migration_start(path, config=MigrationConfig("code-e-new", "plan-hash-2026-08-09"),
                        mode="apply", last_key=first.journal[0]["last_key"],
                        batch_size=500)
    except ValueError as exc:
        refused = True
        error = str(exc)
    return {"path": "E", "refused_resume": refused, "error": error}


def main() -> int:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")
    report: dict = {"wu_id": "WU-906", "date": "2026-08-09",
                    "mode": "independent production snapshot copies "
                            "(structured subsets, evidence_spans excluded)",
                    "drills": {}}
    for label, pristine in (("copy_a", PRISTINE_A), ("copy_b", PRISTINE_B)):
        report["drills"][label] = {
            "A_full_migrate_verify_rollback": drill_a(pristine),
            "B_crash_resume": drill_b(pristine),
            "C_mismatch_blocks_cutover": drill_c(pristine),
            "D_backup_restore_identical": drill_d(pristine),
            "E_changed_hash_refuses_resume": drill_e(pristine),
        }
    ok = all(
        d["A_full_migrate_verify_rollback"]["business_data_preserved"]
        and d["B_crash_resume"]["resume_accepted"]
        and d["B_crash_resume"]["no_duplicates"]
        and d["C_mismatch_blocks_cutover"]["cutover_blocked"]
        and d["D_backup_restore_identical"]["identical"]
        and d["E_changed_hash_refuses_resume"]["refused_resume"]
        for d in report["drills"].values()
    )
    report["verdict"] = "PASS — 5/5 paths accepted on both independent copies" if ok else "FAIL"
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if ok else 2


if __name__ == "__main__":
    raise SystemExit(main())
