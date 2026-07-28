"""Artifact reconciliation: match derived files against the current catalog DB.

§10.6.9 / §10.7.6: Old derived files are matched via fail-closed rules.
"""

from __future__ import annotations

import hashlib
import re
import sqlite3
import uuid
from dataclasses import dataclass, field
from pathlib import Path

import yaml


_FM_DELIM = re.compile(r"^---\s*$", re.MULTILINE)


@dataclass
class ReconciliationRow:
    path: str
    file_sha: str
    role: str
    verdict: str
    document_id: str | None = None
    source_id: str | None = None
    reason: str = ""


@dataclass
class ReconciliationReport:
    role: str
    total: int = 0
    matched: int = 0
    detached: int = 0
    conflict: int = 0
    already_indexed: int = 0
    missing_frontmatter: int = 0
    hash_mismatch: int = 0
    rows: list[ReconciliationRow] = field(default_factory=list)


def _parse_frontmatter(file_path: Path) -> dict[str, str] | None:
    try:
        text = file_path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return None
    parts = _FM_DELIM.split(text, maxsplit=2)
    if len(parts) < 3:
        return None
    try:
        fm = yaml.safe_load(parts[1])
    except yaml.YAMLError:
        return None
    if not isinstance(fm, dict):
        return None
    return {str(k): str(v) for k, v in fm.items()}


def reconcile(
    catalog_path: Path,
    derived_dir: Path,
    *,
    role: str = "normalized",
    limit: int = 0,
    dry_run: bool = True,
) -> ReconciliationReport:
    report = ReconciliationReport(role=role)
    conn = sqlite3.connect(str(catalog_path))
    conn.row_factory = sqlite3.Row

    suffix = f"{role}.md"
    files = sorted(derived_dir.rglob(suffix))
    report.total = len(files)
    count = 0

    for file_path in files:
        count += 1
        if limit and count > limit:
            break

        rel = file_path.relative_to(derived_dir)
        parts = rel.parts
        if len(parts) < 3 or parts[-1] != suffix:
            report.detached += 1
            report.rows.append(
                ReconciliationRow(
                    path=str(rel),
                    file_sha="",
                    role=role,
                    verdict="detached",
                    reason="unexpected_path_pattern",
                )
            )
            continue

        file_sha = parts[1]
        fm = _parse_frontmatter(file_path)
        if fm is None:
            report.missing_frontmatter += 1
            report.rows.append(
                ReconciliationRow(
                    path=str(rel),
                    file_sha=file_sha,
                    role=role,
                    verdict="missing_frontmatter",
                    reason="cannot_parse_yaml",
                )
            )
            continue

        doc_id = fm.get("document_id", "")
        src_id = fm.get("source_id", "")
        fm_sha = fm.get("source_sha256", "")
        fm_role = fm.get("artifact_role", "")
        parser = fm.get("parser_name", "")
        pxver = fm.get("parser_version", "")

        if fm_role != role:
            report.detached += 1
            report.rows.append(
                ReconciliationRow(
                    path=str(rel),
                    file_sha=file_sha,
                    role=role,
                    document_id=doc_id,
                    source_id=src_id,
                    verdict="detached",
                    reason=f"role_mismatch: {fm_role}",
                )
            )
            continue

        source = conn.execute(
            "SELECT source_id, content_sha256 FROM sources WHERE source_id=?",
            (src_id,),
        ).fetchone()
        if source is None:
            report.detached += 1
            report.rows.append(
                ReconciliationRow(
                    path=str(rel),
                    file_sha=file_sha,
                    role=role,
                    document_id=doc_id,
                    source_id=src_id,
                    verdict="detached",
                    reason="source_not_in_catalog",
                )
            )
            continue

        doc = conn.execute(
            "SELECT document_id FROM documents WHERE document_id=? AND primary_source_id=?",
            (doc_id, src_id),
        ).fetchone()
        if doc is None:
            report.detached += 1
            report.rows.append(
                ReconciliationRow(
                    path=str(rel),
                    file_sha=file_sha,
                    role=role,
                    document_id=doc_id,
                    source_id=src_id,
                    verdict="detached",
                    reason="document_not_in_catalog",
                )
            )
            continue

        db_sha = source["content_sha256"]
        if db_sha != fm_sha or db_sha != file_sha:
            report.hash_mismatch += 1
            report.rows.append(
                ReconciliationRow(
                    path=str(rel),
                    file_sha=file_sha,
                    role=role,
                    document_id=doc_id,
                    source_id=src_id,
                    verdict="hash_mismatch",
                    reason=f"db={db_sha[:12]} fm={fm_sha[:12]} path={file_sha[:12]}",
                )
            )
            continue

        existing = conn.execute(
            "SELECT artifact_id FROM artifacts WHERE document_id=? AND artifact_role=?",
            (doc_id, role),
        ).fetchone()
        if existing:
            report.already_indexed += 1
            report.rows.append(
                ReconciliationRow(
                    path=str(rel),
                    file_sha=file_sha,
                    role=role,
                    document_id=doc_id,
                    source_id=src_id,
                    verdict="already_indexed",
                    reason=f"artifact_id={existing['artifact_id']}",
                )
            )
            continue

        report.matched += 1
        row = ReconciliationRow(
            path=str(rel),
            file_sha=file_sha,
            role=role,
            document_id=doc_id,
            source_id=src_id,
            verdict="matched",
            reason="",
        )
        if not dry_run:
            _apply_match(conn, file_path, row, parser, pxver)
        report.rows.append(row)

    conn.commit()
    conn.close()
    return report


# Backward-compat alias for callers expecting the legacy name.
reconcile_artifacts = reconcile


def _apply_match(
    conn: sqlite3.Connection,
    file_path: Path,
    row: ReconciliationRow,
    parser_name: str,
    parser_version: str,
) -> None:
    artifact_id = f"urn:company-wiki:artifact:{uuid.uuid4().hex[:12]}"
    file_size = file_path.stat().st_size
    sha = hashlib.sha256(file_path.read_bytes()).hexdigest()
    from datetime import datetime

    now = datetime.now().isoformat()
    conn.execute(
        """INSERT INTO artifacts
               (artifact_id, document_id, source_id, artifact_role, path,
                content_sha256, byte_size, mime_type, generator_name, generator_version,
                status, error, metadata_json, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, 'text/markdown', ?, ?, 'completed', NULL, '{}', ?)""",
        (
            artifact_id,
            row.document_id,
            row.source_id,
            row.role,
            str(file_path.resolve(strict=False)),
            sha,
            file_size,
            parser_name,
            parser_version,
            now,
        ),
    )
