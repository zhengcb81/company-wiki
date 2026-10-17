"""DU10-CWP-SUMMARY-GOLDSET read-only anchor verifier (node C tool).

Deterministic, zero-model, zero-network. For every case it re-opens the local
original through the machine-local (uncommitted) bindings and checks:

1. the file's SHA-256 equals ``source_ref.source_sha256``;
2. mtime is unchanged across the read (originals stay untouched);
3. every fact/trap anchor quote is present on the claimed PDF physical page
   (or in the de-tagged document text for HTML), compared after removing all
   whitespace — the same rule the DU2 C-node tools use;
4. PDF page numbers exist in the document.

It only verifies data integrity and anchor replay. It does NOT judge economic
facts, support semantics, or summary quality.

Usage:
  python -B -X utf8 tests/verify_anchors.py --bindings <bindings.local.json> \
      [--output <receipt.json>]

Bindings file (machine-local, never committed): {"<case_id>": "<absolute path>"}.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from _support import (  # noqa: E402
    CARRIER_ROOTS,
    iter_anchors,
    load_cases,
    norm,
    page_text,
    resolve_binding,
    sha256_file,
)


def verify_case(case: dict, bindings: dict[str, str]) -> dict:
    cid = case["case_id"]
    result: dict = {"case_id": cid, "checks": [], "status": "PASS"}
    src = case["source_ref"]

    def check(name: str, ok: bool, detail: str = "") -> None:
        result["checks"].append({"check": name, "status": "PASS" if ok else "FAIL",
                                 "detail": detail})
        if not ok:
            result["status"] = "FAIL"

    try:
        path = resolve_binding(case, bindings)
    except (KeyError, ValueError) as exc:
        check("binding_resolves", False, str(exc))
        return result
    check("binding_resolves", True, path)

    mtime_before = os.path.getmtime(path)
    check("sha256_matches", sha256_file(path) == src["source_sha256"], path)
    mtime_after = os.path.getmtime(path)
    check("mtime_unchanged", mtime_before == mtime_after)

    carrier = case["carrier"]
    page_count = None
    if carrier == ".pdf":
        import fitz

        doc = fitz.open(path)
        page_count = doc.page_count
        doc.close()

    total = 0
    for fid, kind, a in iter_anchors(case):
        quote = a["exact_quote"]
        page = a.get("page")
        if carrier == ".pdf" and page is not None:
            if page_count is not None and not (1 <= page <= page_count):
                check(f"anchor[{fid}]page_in_range", False, f"page {page} > {page_count}")
                continue
        text = page_text(path, page, carrier)
        ok = norm(quote) in norm(text)
        total += len(norm(quote))
        check(f"anchor[{kind}:{fid}]", ok, (page and f"p{page}") or "document")
    result["quote_chars_normalized"] = total
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bindings", required=True)
    parser.add_argument("--output", default=None)
    args = parser.parse_args()

    bindings = json.loads(open(args.bindings, encoding="utf-8").read())
    cases = load_cases()
    results = [verify_case(c, bindings) for c in cases]

    missing = [c["case_id"] for c in cases if c["case_id"] not in bindings]
    receipt = {
        "schema_version": "du10-goldset-anchor-verify/1",
        "verified_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "cases_total": len(cases),
        "cases_bound": len(cases) - len(missing),
        "unbound_cases": missing,
        "results": results,
        "status": "PASS" if all(r["status"] == "PASS" for r in results) and not missing
        else "FAIL",
    }
    text = json.dumps(receipt, ensure_ascii=False, indent=1)
    if args.output:
        with open(args.output, "w", encoding="utf-8", newline="\n") as f:
            f.write(text + "\n")
    print(text)
    return 0 if receipt["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
