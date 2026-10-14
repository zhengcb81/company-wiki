"""Compile the only runtime reading catalog from versioned design specifications.

This maintenance tool reads docs. The installed reader only loads reading_catalog.json.
--check is read-only and fails on meaningful drift; no profile/plugin/runtime is imported.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

SCHEMA = "du-reading-catalog/1"


def _json(path: Path) -> dict:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"expected mapping: {path.name}")
    return value


def _records(package: Path, schema: str) -> tuple[list[dict], list[dict]]:
    index = _json(package / "index.json")
    records = []
    seen = set()
    for relative in index["records"]:
        path = Path(relative)
        if path.is_absolute() or ".." in path.parts:
            raise ValueError("record reference must remain inside its data package")
        record = _json(package / path)
        if record.get("schema_version") != schema:
            raise ValueError(f"wrong record schema: {relative}")
        identifier = record.get("id")
        if not isinstance(identifier, str) or not identifier or identifier in seen:
            raise ValueError("record ids must be nonempty and unique")
        seen.add(identifier)
        if not record.get("version"):
            raise ValueError(f"missing component version: {identifier}")
        records.append(record)
    return records, index["coverage"]


def compile_catalog(source_root: Path, defaults_path: Path | None = None) -> dict:
    """Build deterministic data; this does not instantiate or run another reader."""
    data = source_root / "docs/plans/document-understanding-2026-10-13/review/deliverables"
    defaults_path = defaults_path or source_root / "src/company_wiki/document_understanding/profiles/reading_defaults.json"
    defaults = _json(defaults_path)
    families, family_coverage = _records(data / "families", "du2-family-spec/1")
    facets, facet_coverage = _records(data / "facets", "du2-facet-spec/1")
    family_ids = {record["id"] for record in families}
    for record in families:
        for key in ("sections", "reading_questions", "context_requirements", "recognition", "evidence_status"):
            if key not in record:
                raise ValueError(f"{record['id']} missing {key}")
        modifiers = record["applies_to"]["modifiers"]
        for axis, allowed in (("extent", {"full", "summary", "unknown"}),
                              ("revision", {"original", "amended", "supplement", "unknown"})):
            values = modifiers[axis]
            if not isinstance(values, list) or not values or not set(values) <= allowed:
                raise ValueError(f"{record['id']} {axis} must be an allowed-values array")
        for entry in record["sections"]:
            if not all(key in entry for key in ("role", "aliases", "heading_path", "priority", "questions")):
                raise ValueError("section must retain role, hierarchy, aliases and priority")
    for record in facets:
        for entry in record["positive_evidence"]:
            if "table_scan" in entry and type(entry["table_scan"]) is not bool:
                raise ValueError(f"{record['id']} table_scan must be a boolean")
    bindings = defaults["legacy_bindings"]
    legacy_ids = [binding["profile_id"] for binding in bindings]
    if len(legacy_ids) != len(set(legacy_ids)):
        raise ValueError("duplicate legacy id binding")
    for binding in bindings:
        if not set(binding["family_ids"]) <= family_ids:
            raise ValueError(f"unknown family reference: {binding['profile_id']}")
    return {"schema_version": SCHEMA, "families": families, "facets": facets,
            "family_coverage": family_coverage, "facet_coverage": facet_coverage,
            "legacy_bindings": bindings, "fallback": defaults["fallback"],
            "shared_focus": defaults["shared_focus"]}


def main() -> int:
    """Generate or verify the installed asset, without modifying design source data."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--defaults", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    output = args.output or args.source_root / "src/company_wiki/document_understanding/profiles/reading_catalog.json"
    try:
        catalog = compile_catalog(args.source_root, args.defaults)
        if args.check:
            if not output.is_file() or _json(output) != catalog:
                print("reading catalog drift; run tools/import_reading_policies.py", file=sys.stderr)
                return 1
        else:
            output.parent.mkdir(parents=True, exist_ok=True)
            output.write_bytes((json.dumps(catalog, ensure_ascii=False, indent=2) + "\n").encode("utf-8"))
        print(f"catalog {'verified' if args.check else 'compiled'}: {len(catalog['families'])} families, {len(catalog['facets'])} facets")
        return 0
    except (OSError, ValueError, KeyError) as exc:
        print(f"reading catalog error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
