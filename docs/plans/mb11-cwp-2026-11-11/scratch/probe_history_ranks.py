"""Scratch probe: roles/ranks of the B33 history fixture's two versions."""
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, r"C:\Users\郑曾波\Projects\mb11-cwp\src")
sys.path.insert(0, r"C:\Users\郑曾波\Projects\mb11-cwp\tests")

import importlib.util

spec = importlib.util.spec_from_file_location(
    "readiness_tests",
    r"C:\Users\郑曾波\Projects\mb11-cwp\tests\contract\test_public_source_readiness.py",
)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

tmp = Path(tempfile.mkdtemp(prefix="hist-"))
catalog = mod._build_history_catalog(tmp)
try:
    rows = catalog.reader.fetchall(
        "SELECT l.document_id, l.source_id, l.role, l.location_status, "
        "l.relative_path FROM locations l ORDER BY l.source_id, l.role"
    )
    for row in rows:
        print("loc:", dict(row))
    docs = catalog.reader.fetchall(
        "SELECT document_id, primary_source_id, source_status FROM documents"
    )
    for row in docs:
        print("doc:", dict(row))
    srcs = catalog.reader.fetchall(
        "SELECT source_id, content_sha256, byte_size FROM sources"
    )
    for row in srcs:
        print("src:", str(row["source_id"])[:40], row["byte_size"])

    # What do the pair candidates look like for the non-primary source?
    _, primary, history = mod._history_refs_via_browser(catalog)
    hist_ref = history["source_ref"]
    print("\nhistory ref:", hist_ref["source_id"][:50], hist_ref["content_sha256"][:16])
    cands = catalog.source_location_candidates(
        hist_ref["document_id"], hist_ref["source_id"]
    )
    for c in cands:
        print("candidate:", c.role, c.location_status, "rank=", c.candidate_rank,
              "excl=", c.exclusion_reason, c.relative_path[:60])
    # Query path
    from company_wiki.source_catalog.source_reader import SourceVersionReader
    reader = SourceVersionReader(catalog)
    try:
        ref = reader.query_ref(
            hist_ref["document_id"], hist_ref["source_id"],
            hist_ref["content_sha256"],
        )
        print("query_ref OK:", ref.source_id[:40])
    except Exception as exc:
        print("query_ref REFUSED:", type(exc).__name__, exc)
finally:
    catalog.close()
