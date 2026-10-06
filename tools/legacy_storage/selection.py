"""Legacy derived-object selection for inventory / retire-derived.

Candidates come ONLY from the artifacts table rows whose role+generator are
within the known legacy set AND whose registered path physically lives under
``catalog_dir/derived``.  Everything else is classified and kept.
"""

from __future__ import annotations

from pathlib import Path

from legacy_storage.core import (
    FACT_TABLES,
    LEGACY_RECORD_TABLES,
    PROTECTED_TABLES,
    directed_inside,
    file_sha256,
    normalized,
    read_connection,
    table_digest,
)

LEGACY_ROLES = frozenset({"normalized", "summary", "sections", "markdown"})
LEGACY_GENERATORS = frozenset(
    {
        "source_catalog_normalizer",
        "source_catalog_extractive_summary",
        "source_catalog_llm_summary",
        "source_catalog_section_extractor",
    }
)
LEGACY_STATUS_RETIRED = "retired"

# Direct parser labels used before the source_catalog_* writer namespace.
# Version and role are deliberately pinned: new parsers are not cleanup targets.
LEGACY_PARSERS = frozenset({
    ("html_markdownify", "1.0.0"), ("structured_text", "1.0.0"),
    ("pymupdf_page_text", "1.26.7"), ("plain_text", "1.0.0"),
    ("python_docx", "1.0.0"), ("unsupported_format", "1.0.0"),
    ("antiword", "1.0.0"), ("dayu_docling", "1.10.0"),
    ("openpyxl", "3.1.5"), ("pdf_page_aware_core", "1.26.7"),
})


def is_legacy_artifact(row: dict, derived: Path) -> bool:
    role = row["artifact_role"]
    if role not in LEGACY_ROLES:
        return False
    if row["generator_name"] in LEGACY_GENERATORS:
        return True
    if role == "normalized" and (row["generator_name"], row["generator_version"]) in LEGACY_PARSERS:
        return True
    # The oldest summary writer had empty generator columns. Its SHA-addressed
    # summary.md layout, role and document binding distinguish it from unknowns.
    digest = row["document_id"].rsplit(":", 1)[-1]
    return (
        role == "summary" and row["generator_name"] == row["generator_version"] == ""
        and len(digest) == 64 and all(c in "0123456789abcdef" for c in digest)
        and normalized(Path(row["path"])) == normalized(derived / digest[:2] / digest / "summary.md")
    )


def classify_artifact_rows(database_path: Path, derived_dir: Path) -> dict:
    """Split artifacts table rows into candidates / excluded / dangling."""
    with read_connection(database_path) as connection:
        rows = list(
            connection.execute(
                "SELECT artifact_id, document_id, artifact_role, path, content_sha256,"
                " byte_size, generator_name, generator_version, status"
                " FROM artifacts"
            )
        )
    candidates, excluded, dangling = [], [], []
    for row in rows:
        artifact_id, role, generator, status = row[0], row[2], row[6], row[8]
        entry = {
            "artifact_id": artifact_id,
            "document_id": row[1],
            "artifact_role": role,
            "path": str(Path(row[3])),
            "content_sha256": row[4],
            "byte_size": row[5],
            "generator_name": generator,
            "generator_version": row[7],
            "status": status,
        }
        if not is_legacy_artifact(entry, derived_dir):
            excluded.append(dict(entry, reason="unknown_generator"))
            continue
        if role not in LEGACY_ROLES:
            excluded.append(dict(entry, reason="role_not_legacy"))
            continue
        path = Path(row[3])
        if not directed_inside(path, derived_dir):
            excluded.append(dict(entry, reason="path_outside_derived"))
            continue
        if status not in {"completed", "partial", "unsupported", "failed", "retired"}:
            excluded.append(dict(entry, reason=f"status_{status}"))
            continue
        if not path.is_file() or path.is_symlink():
            excluded.append(dict(entry, reason="file_missing"))
            dangling.append(entry)
            continue
        if row[4] != file_sha256(path):
            excluded.append(dict(entry, reason="content_hash_mismatch"))
            continue
        if role == "sections":
            managed, manage_error = _sections_managed_files(path, derived_dir)
            if manage_error is not None:
                excluded.append(dict(entry, reason=manage_error))
                continue
            entry["managed_files"] = managed
        candidates.append(entry)
    return {"candidates": candidates, "excluded": excluded, "dangling": dangling}


def _sections_managed_files(index_path: Path, derived_dir: Path) -> tuple[list, str | None]:
    import json

    if index_path.name != "index.json" or index_path.parent.name != "sections":
        return [], "index_not_legacy_sections"
    try:
        payload = json.loads(index_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, ValueError):
        return [], "index_unreadable"
    if not isinstance(payload, list):
        return [], "index_unreadable"
    managed = []
    for item in payload:
        if not isinstance(item, dict):
            return [], "index_member_invalid"
        role, section_path = item.get("role"), item.get("path")
        if not isinstance(role, str) or not role or not all(c.isascii() and (c.isalnum() or c == "_") for c in role):
            return [], "index_role_invalid"
        if not isinstance(section_path, str) or not section_path:
            return [], "index_path_invalid"
        target = Path(section_path)
        from legacy_storage.core import normalized
        if not directed_inside(target, derived_dir) or normalized(target) != normalized(index_path.parent / (role + ".md")):
            return [], "managed_path_not_index_member"
        if target.is_symlink() or (target.exists() and not target.is_file()):
            return [], "managed_path_not_file"
        managed.append({"path": str(target), "role": role,
                        "byte_size": target.stat().st_size if target.is_file() else 0,
                        "content_sha256": file_sha256(target) if target.is_file() else None})
    return managed, None


def inventory_view(config, database_path: Path) -> dict:
    """Selection view: unreferenced derived files + span parser stats + tables."""
    derived_dir = Path(config.derived_dir)
    parts = classify_artifact_rows(database_path, derived_dir)
    candidate_paths = set()
    for c in parts["candidates"]:
        candidate_paths.add(Path(c["path"]).resolve().as_posix())
        for managed in c.get("managed_files") or []:
            candidate_paths.add(Path(managed["path"]).resolve().as_posix())

    unreferenced = []
    if derived_dir.is_dir():
        for path in sorted(derived_dir.rglob("*")):
            if (
                path.is_file()
                and not path.is_symlink()
                and path.resolve().as_posix() not in candidate_paths
            ):
                unreferenced.append(
                    {
                        "path": path.relative_to(derived_dir).as_posix(),
                        "byte_size": path.stat().st_size,
                    }
                )

    schema_inventory: dict[str, dict[str, dict[str, object]]] = {}
    span_parser_counts, span_total = [], 0
    with read_connection(database_path) as connection:
        span_parser_counts = [
            {"parser_name": row[0], "parser_version": row[1], "count": row[2]}
            for row in connection.execute(
                "SELECT parser_name, parser_version, COUNT(*) FROM evidence_spans"
                " GROUP BY parser_name, parser_version ORDER BY parser_name"
            )
        ]
        span_total = int(
            connection.execute("SELECT COUNT(*) FROM evidence_spans").fetchone()[0]
        )
        names = tuple(
            row[0]
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
                " AND name NOT LIKE 'sqlite_%'"
            )
        )
        buckets: dict[str, list[str]] = {
            "fact": [],
            "protected": [],
            "legacy_record": [],
            "unknown": [],
        }
        for name in names:
            if name in FACT_TABLES:
                bucket = "fact"
            elif name in PROTECTED_TABLES:
                bucket = "protected"
            elif name in LEGACY_RECORD_TABLES:
                bucket = "legacy_record"
            else:
                bucket = "unknown"
            buckets[bucket].append(name)
        for bucket, members in buckets.items():
            schema_inventory[bucket] = {
                table: table_digest(connection, table) for table in sorted(members)
            }
    return {
        **parts,
        "unreferenced": unreferenced,
        "span_total": span_total,
        "span_parser_counts": span_parser_counts,
        "schema_inventory": schema_inventory,
    }
