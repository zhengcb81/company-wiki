"""Replay corpus sources through CWP's real versioned source reader.

Only an owned temporary catalog is written. Configured original roots are read
through register_sources -> query_ref -> open_version; no originals are copied.
HTML uses canonical normalization and batched locator replay. These checks
establish source/locator integrity, never semantic summary quality.
"""
from __future__ import annotations

import argparse
from dataclasses import asdict, replace
import hashlib
import json
from pathlib import Path
import sys
import tempfile

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _support import iter_anchors, load_cases, norm  # noqa: E402


def verify_case(case, reader):
    from company_wiki.source_catalog.source_reader import SourceRef

    result = {"case_id": case["case_id"], "checks": [], "status": "PASS"}

    def check(name, ok):
        result["checks"].append({"check": name, "status": "PASS" if ok else "FAIL"})
        if not ok:
            result["status"] = "FAIL"

    try:
        declared = SourceRef(**case["source_ref"])
        ref = reader.query_ref(declared.document_id, declared.source_id, declared.content_sha256)
        check("source_ref_identity", ref == declared)
        opened = reader.open_version(ref, purpose="source_export")
        check("actual_source_sha", opened.content_sha256 == declared.content_sha256)
        result["source_ref"] = asdict(ref)
        anchors = list(iter_anchors(case))
        if case["carrier"] == ".pdf":
            import fitz

            with fitz.open(stream=opened.data, filetype="pdf") as doc:
                pages = {}
                for fid, kind, a in anchors:
                    p = a.get("page")
                    valid = type(p) is int and 1 <= p <= doc.page_count
                    check(f"{kind}:{fid}:physical_page", valid)
                    if valid:
                        if p not in pages:
                            pages[p] = norm(doc[p - 1].get_text("text"))
                        check(f"{kind}:{fid}:quote", norm(a["exact_quote"]) in pages[p])
        else:
            from company_wiki.document_normalization import (
                NormalizationLimits, normalize_document, replay_units,
            )

            limits = NormalizationLimits()
            doc = normalize_document(opened.data, source_id=ref.source_id,
                                     source_sha256=ref.content_sha256,
                                     mime_type=ref.mime_type, limits=limits)
            units = {u.unit_id: u for u in doc.units}
            selected = {}
            for fid, kind, a in anchors:
                unit = units.get(a.get("unit_id"))
                valid = (a.get("location_kind") == "unit" and unit is not None
                         and a.get("source_locator") == unit.metadata["source_locator"])
                check(f"{kind}:{fid}:canonical_locator", valid)
                if valid:
                    check(f"{kind}:{fid}:quote", norm(a["exact_quote"]) in norm(unit.raw_text))
                    selected[unit.unit_id] = unit
            if selected:
                replayed = replay_units(opened.data, source_sha256=ref.content_sha256,
                                        units=selected.values(), limits=limits)
                check("canonical_batched_replay", replayed == tuple(u.raw_text for u in selected.values()))
    except Exception as exc:
        check(f"source_or_locator_error:{type(exc).__name__}", False)
    return result


def verify_corpus(cases, project_root):
    from company_wiki.source_catalog import SourceCatalog
    from company_wiki.source_catalog.config import load_catalog_config
    from company_wiki.source_catalog.source_location import resolve_source_location
    from company_wiki.source_catalog.source_reader import SourceVersionReader

    config_path = project_root / "config/source_catalog.yaml"
    config_sha = hashlib.sha256(config_path.read_bytes()).hexdigest()
    config = load_catalog_config(config_path, project_root=project_root)
    roots = {r.root_id: r for r in config.roots}
    groups = {}
    originals = {}
    for case in cases:
        binding = case["source_binding"]
        rid, relative = binding["root_id"], binding["relative_path"]
        path = resolve_source_location(roots[rid], relative)
        stat = path.stat()
        originals[path] = (stat.st_size, stat.st_mtime_ns)
        groups.setdefault(rid, set()).add(relative)
    with tempfile.TemporaryDirectory(prefix="du10-gold-source-replay-") as temp:
        owned = Path(temp)
        sentinel = owned / "sentinel"
        sentinel.write_bytes(b"existing isolated fixture sentinel")
        catalog = SourceCatalog(replace(config, catalog_dir=owned / "catalog"))
        try:
            registration = [catalog.register_sources(root_id=rid, relative_paths=paths)
                            for rid, paths in groups.items()]
            results = [verify_case(c, SourceVersionReader(catalog)) for c in cases]
            registration_ok = all(r.errors == 0 for r in registration)
            sentinel_ok = sentinel.read_bytes() == b"existing isolated fixture sentinel"
        finally:
            catalog.close()
    originals_ok = all((p.stat().st_size, p.stat().st_mtime_ns) == before
                       for p, before in originals.items())
    config_ok = config_sha == hashlib.sha256(config_path.read_bytes()).hexdigest()
    return {
        "schema_version": "du10-goldset-source-replay/2",
        "cases_total": len(cases), "results": results,
        "registration_errors_zero": registration_ok,
        "original_stat_unchanged": originals_ok, "production_config_unchanged": config_ok,
        "sentinel_unchanged": sentinel_ok, "owned_temp_removed": not owned.exists(),
        "semantic_quality_evaluated": False,
        "status": "PASS" if (results and all(r["status"] == "PASS" for r in results)
                               and registration_ok and originals_ok and config_ok and sentinel_ok
                               and not owned.exists()) else "FAIL",
    }


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--project-root", required=True, type=Path)
    p.add_argument("--output", required=True, type=Path)
    args = p.parse_args()
    sys.path.insert(0, str(args.project_root / "src"))
    receipt = verify_corpus(load_cases(), args.project_root)
    args.output.write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"cases": receipt["cases_total"], "status": receipt["status"]}))
    return 0 if receipt["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
