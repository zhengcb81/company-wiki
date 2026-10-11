"""Create a read-only, batched fresh-reader probe in the owned tool package."""
from pathlib import Path

tree = Path(r"C:\Users\郑曾波\Projects\_harness_worktrees\w06\ff-contract-matrix-root")
(tree/"tools/offline_contract_matrix/source_proofs.py").write_text('''"""Fresh SourceVersionReader bytes and version counts from synthetic catalog only."""
from dataclasses import fields
import hashlib
import json
from pathlib import Path
import sys


def main():
    from company_wiki.source_catalog.config import load_catalog_config
    from company_wiki.source_catalog.service import SourceCatalog
    from company_wiki.source_catalog.source_reader import SourceRef, SourceVersionReader

    payload = json.load(sys.stdin)
    wiki = Path(payload["wiki"])
    catalog = SourceCatalog(load_catalog_config(wiki/"config/source_catalog.yaml", project_root=wiki))
    reader = SourceVersionReader(catalog)
    result = {}
    try:
        for reference in payload["refs"]:
            key = reference["document_id"]
            if key in result:
                continue
            try:
                ref = SourceRef(**{field.name: reference[field.name] for field in fields(SourceRef) if field.name in reference})
                verified = reader.open_version(ref)
                digest = hashlib.sha256(verified.data).hexdigest()
                row = catalog.reader.exact_source_version(ref.document_id)
                versions = catalog.reader.fetchone("SELECT COUNT(*) AS n FROM sources WHERE content_sha256=?", (digest,))["n"]
                locations = catalog.reader.fetchone("SELECT COUNT(*) AS n FROM locations WHERE source_id=? AND role='original_primary' AND location_status='active'", (ref.source_id,))["n"]
                source_content = None
                if ref.mime_type == "application/json":
                    parsed = json.loads(verified.data.decode("utf-8"))
                    if isinstance(parsed, list) and parsed:
                        source_content = parsed[0].get("content")
                    elif isinstance(parsed, dict):
                        source_content = parsed.get("content")
                elif ref.mime_type == "text/plain":
                    source_content = verified.data.decode("utf-8")
                result[key] = {"verified": digest == ref.content_sha256 and len(verified.data) == ref.byte_size,
                    "reference": reference, "content_sha256": digest, "byte_size": len(verified.data),
                    "source_versions": versions, "original_locations": locations,
                    "document_kind": row["document_kind"],
                    "metadata": json.loads(row["metadata_json"] or "{}"),
                    "original_language_content_sha256": None if source_content is None else hashlib.sha256(source_content.replace("\\r\\n", "\\n").replace("\\r", "\\n").encode("utf-8")).hexdigest()}
            except Exception as exc:
                result[key] = {"verified": False, "error": f"{type(exc).__name__}: {exc}"}
        print(json.dumps({"schema_version": "w06-fresh-source-proofs/1", "proofs": result}, ensure_ascii=False))
    finally:
        catalog.close()


if __name__ == "__main__":
    main()
''', encoding="utf-8")
print("Installed read-only synthetic fresh-reader batch probe.")
