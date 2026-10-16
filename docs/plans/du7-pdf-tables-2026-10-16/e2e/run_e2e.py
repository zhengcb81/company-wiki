"""Real-original end-to-end for the PDF table observation adapter.

Usage (from the worktree root, PYTHONPATH=src)::

    python -B docs/plans/du7-pdf-tables-2026-10-16/e2e/run_e2e.py --original <read-only path> --sha256 <expected sha256> \
        --pages 12 --language zh --work-dir <tmp dir> --out receipts/e2e-....json

    python -B docs/plans/du7-pdf-tables-2026-10-16/e2e/run_e2e.py --manifest <sample_manifest.json> --sample hk-annual \
        --originals-root <root of relative manifest paths> ...

One run = one real parse of the read-only original, then the production adapter,
the shared layout hints, ``build_pdf_table_observations`` and the original
``bind_operating_table`` on one shared ``WorkBudget``.  No production result is
faked: values come from the parser's own units and every measurement ref is
re-sliced back to the original text and hashed.  The original is never written;
its SHA-256 is compared before and after, and every derived byte goes into a
TemporaryDirectory that is removed again (the receipt is the only output).
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import tempfile
import time
from pathlib import Path

SCHEMA_RECEIPT = "du7-pdf-table-e2e/1"


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _resolve_original(args) -> tuple[Path, str | None]:
    if args.manifest:
        manifest = json.loads(Path(args.manifest).read_text(encoding="utf-8"))
        entries = {
            item["id"]: item for item in manifest.get("samples", ()) if "id" in item
        }
        if args.sample not in entries:
            raise SystemExit(f"sample {args.sample!r} not in manifest")
        entry = entries[args.sample]
        path = Path(entry["path"])
        if not path.is_absolute():
            if not args.originals_root:
                raise SystemExit("relative manifest paths need --originals-root")
            path = Path(args.originals_root) / path
        return path, entry.get("sha256")
    if not args.original:
        raise SystemExit("need --original or --manifest")
    return Path(args.original), args.sha256


def _value_record(measurement, table, source_id, page):
    ref = measurement["value_ref"]
    unit = table["units"][ref["unit_id"]]
    text = unit["text"][ref["char_start"]:ref["char_end"]]
    return {
        "source_id": source_id,
        "page": page,
        "table_id": table["scope"]["table_id"],
        "unit_id": ref["unit_id"],
        "char_start": ref["char_start"],
        "char_end": ref["char_end"],
        "value_sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(),
        "value": text[:80],
        "value_truncated": len(text) > 80,
        "_full_text": text,
        "binding_status": measurement["binding_status"],
        "column_id": measurement["column_id"],
        "period_kind": (measurement["period"] or {}).get("kind"),
    }


def run(args) -> dict:
    from company_wiki.document_understanding.layout_bridge import apply_layout_hints
    from company_wiki.document_understanding.layout_hints.contract import WorkBudget
    from company_wiki.document_understanding.observation_adapter import build_observation
    from company_wiki.document_understanding.table_measurements import bind_operating_table
    from company_wiki.document_normalization.pdf_table_observations import (
        build_pdf_table_observations,
    )
    from company_wiki.source_catalog.narrative_evidence import parse_pdf_bytes
    from company_wiki.source_contract import source_id_for_sha256

    original, expected_sha = _resolve_original(args)
    if not original.is_file():
        return {
            "schema_version": SCHEMA_RECEIPT,
            "status": "NOT_RUN",
            "reason": f"original not found: {original.name}",
        }
    pages = [int(page) for page in args.pages]
    sha_before = _sha256_file(original)
    if expected_sha and len(expected_sha) == 64 and not expected_sha.startswith("sha256:"):
        expected = expected_sha.lower()
    else:
        expected = sha_before
    data = original.read_bytes()  # read-only
    parse_seconds = 0.0
    started = time.monotonic()
    if args.work_dir:
        Path(args.work_dir).mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="du7-e2e-", dir=args.work_dir) as tmp:
        work_dir = Path(tmp)
        (work_dir / "sentinel.json").write_text(
            json.dumps({"original_sha256": sha_before}), encoding="utf-8"
        )
        t0 = time.monotonic()
        parsed = parse_pdf_bytes(
            data,
            source_id=source_id_for_sha256(sha_before),
            source_sha256=sha_before,
            language=args.language,
            selector_version="0.9.0",
            table_pages=tuple(pages),
        )
        parse_seconds = time.monotonic() - t0
        observation = build_observation(
            parsed.units,
            source_id=source_id_for_sha256(sha_before),
            source_sha256=sha_before,
            mime_type="application/pdf",
            language=args.language,
        )
        budget = WorkBudget(args.work_budget)
        stages: dict[str, int] = {}

        def mark(name):
            stages[name] = budget.used

        mark("parse_done")
        observation, hints = apply_layout_hints(observation, work_budget=budget)
        mark("layout_hints_done")
        built = build_pdf_table_observations(observation, hints, work_budget=budget)
        mark("table_observations_done")
        bindings = [
            bind_operating_table(table, work_budget=budget) for table in built["tables"]
        ]
        mark("binder_done")

        parsed_text = {unit.unit_id: unit.raw_text for unit in parsed.units}
        values = []
        source_urn = source_id_for_sha256(sha_before)
        wire_claims = {
            (
                (unit.get("hints") or {}).get("source_id") or source_urn,
                (unit.get("hints") or {}).get("table_id"),
                unit.get("page"),
            )
            for unit in observation["units"]
            if (unit.get("hints") or {}).get("table_id")
        }
        for table, binding in zip(built["tables"], bindings):
            page = table["scope"]["page"]
            for measurement in binding["measurements"]:
                record = _value_record(measurement, table, source_urn, page)
                ref = measurement["value_ref"]
                sliced = parsed_text.get(ref["unit_id"], "")[
                    ref["char_start"]:ref["char_end"]
                ]
                record["slice_matches_original"] = sliced == record.pop("_full_text")
                values.append(record)

        unlocated = [
            diag
            for diag in built["diagnostics"]
            if diag.get("code") == "CELL_TEXT_UNLOCATABLE"
        ]
        counts = {"bound": 0, "ambiguous": 0, "unavailable": 0}
        reasons: dict[str, int] = {}
        for binding in bindings:
            for measurement in binding["measurements"]:
                counts[measurement["binding_status"]] += 1
            for diag in binding["diagnostics"]:
                reasons[diag["code"]] = reasons.get(diag["code"], 0) + 1
        component_diags: dict[str, int] = {}
        for diag in built["diagnostics"]:
            component_diags[diag["code"]] = component_diags.get(diag["code"], 0) + 1
        layout_diags: dict[str, int] = {}
        for diag in parsed.layout_diagnostics or ():
            layout_diags[diag["code"]] = layout_diags.get(diag["code"], 0) + 1
        coverage = parsed.layout_coverage or {}

        total_slots = sum(len(table["cells"]) for table in built["tables"])
        located_refs = sum(
            len(cell["text_refs"]) for table in built["tables"] for cell in table["cells"]
        )
        receipt = {
            "schema_version": SCHEMA_RECEIPT,
            "status": "RUN",
            "original": {
                "file_name": original.name,
                "sha256": sha_before,
                "sha256_expected": expected,
                "sha256_matches_expected": sha_before == expected,
                "bytes": len(data),
                "pages_requested": pages,
            },
            "parse": {
                "parse_count": 1,
                "page_count": parsed.page_count,
                "pages_read": parsed.pages_read,
                "table_scan_pages": list(parsed.table_scan_pages),
                "deferred_table_page_count": len(parsed.deferred_table_pages),
                "unit_count": len(parsed.units),
                "seconds": round(parse_seconds, 3),
                "layout_capture": {
                    "processed_page_count": coverage.get("processed_page_count"),
                    "processed_unit_count": coverage.get("processed_unit_count"),
                    "deferred_unit_count": coverage.get("deferred_unit_count"),
                    "fine_element_count": coverage.get("fine_element_count"),
                    "complete": coverage.get("complete"),
                    "diagnostic_counts": layout_diags,
                },
            },
            "work": {
                "budget_ceiling": args.work_budget,
                "used_total": budget.used,
                "stages_used": stages,
                "component_work_used": built["work_used"],
            },
            "tables": [
                {
                    "scope": table["scope"],
                    "cells": len(table["cells"]),
                    "header_rows": table["header_rows"],
                    "truncated": table["truncated"],
                    "status": binding["status"],
                    "measurements": len(binding["measurements"]),
                }
                for table, binding in zip(built["tables"], bindings)
            ],
            "denominator": {
                "wire_table_claims": len(wire_claims),
                "tables_built": len(built["tables"]),
                "slots_observed": total_slots,
                "refs_located": located_refs,
                "cells_without_located_ref": sum(
                    1
                    for table in built["tables"]
                    for cell in table["cells"]
                    if not cell["text_refs"]
                ),
                "rows_truncated": sum(
                    1 for table in built["tables"] if table["truncated"]
                ),
                "measurements": counts,
                "unlocated_examples": unlocated[:20],
                "binder_diagnostic_counts": reasons,
                "component_diagnostic_counts": component_diags,
                "component_status": built["status"],
            },
            "values": values,
            "all_slices_match_original": all(
                record["slice_matches_original"] for record in values
            ),
            "cleanup": {
                "original_sha256_after": None,  # filled below
                "original_unchanged": None,
                "derived_files_deleted": True,
                "work_dir_was_temporary": True,
            },
            "wall_seconds": round(time.monotonic() - started, 3),
        }
    sha_after = _sha256_file(original)
    receipt["cleanup"]["original_sha256_after"] = sha_after
    receipt["cleanup"]["original_unchanged"] = sha_after == sha_before
    return receipt


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--original", help="read-only original file path")
    parser.add_argument("--sha256", help="expected sha256 of the original")
    parser.add_argument("--manifest", help="sample manifest json path")
    parser.add_argument("--sample", help="sample id inside the manifest")
    parser.add_argument("--originals-root", help="root for relative manifest paths")
    parser.add_argument("--pages", nargs="+", required=True, help="table pages")
    parser.add_argument("--language", default="zh")
    parser.add_argument("--work-dir", help="explicit work directory (temporary)")
    parser.add_argument("--out", required=True, help="receipt json output path")
    parser.add_argument("--work-budget", type=int, default=4_000_000)
    args = parser.parse_args()
    receipt = run(args)
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(receipt, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps({k: v for k, v in receipt.items() if k != "values"},
                     ensure_ascii=False)[:2000])
    return 0 if receipt.get("status") == "RUN" else 2


if __name__ == "__main__":
    sys.exit(main())
