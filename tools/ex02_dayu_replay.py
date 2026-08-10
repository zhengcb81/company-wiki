"""FC-602 replay: EX-02 dayu-only exact reuse preconditions (read-only).

Selects real dayu_portfolio filings whose primary file exists, whose
meta is complete (ingest_complete, fiscal_year, https source_url,
identity), whose content hash has NO active location in any other root
(dayu-only), and whose catalog record is an active original_primary dayu
location.  The REUSED_EXACT resolution itself is pinned by the fixture
tests; this replay proves the real samples satisfy every reuse
precondition — read-only SQL + file hashing, nothing written.
"""
import hashlib
import json
import sqlite3
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DAYU_ROOT = Path(r"C:\Users\郑曾波\Projects\dayu-agent\workspace\portfolio")
CATALOG_PATH = PROJECT_ROOT / ".source_catalog" / "catalog.sqlite3"
MIN_SAMPLES = 2


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _exclusive(con: sqlite3.Connection, content_sha256: str) -> bool:
    row = con.execute(
        """SELECT COUNT(*) c FROM locations l
           JOIN sources s ON s.source_id = l.source_id
           WHERE l.root_id != 'dayu_portfolio'
             AND l.location_status = 'active'
             AND s.content_sha256 = ?""",
        (content_sha256,),
    ).fetchone()
    return row[0] == 0


def _active_dayu_primary(con: sqlite3.Connection, content_sha256: str) -> bool:
    row = con.execute(
        """SELECT COUNT(*) c FROM locations l
           JOIN sources s ON s.source_id = l.source_id
           WHERE l.root_id = 'dayu_portfolio'
             AND l.location_status = 'active'
             AND l.role = 'original_primary'
             AND s.content_sha256 = ?""",
        (content_sha256,),
    ).fetchone()
    return row[0] >= 1


def _select_samples() -> list[dict]:
    con = sqlite3.connect(f"file:{CATALOG_PATH}?mode=ro", uri=True)
    samples = []
    try:
        for ticker in sorted(p for p in DAYU_ROOT.iterdir() if p.is_dir()):
            filings = ticker / "filings"
            if not filings.is_dir():
                continue
            for filing in sorted(filings.iterdir()):
                if not filing.is_dir():
                    continue
                meta_path = filing / "meta.json"
                if not meta_path.is_file():
                    continue
                try:
                    meta = json.loads(meta_path.read_text(encoding="utf-8"))
                except (OSError, UnicodeError, json.JSONDecodeError):
                    continue
                if not isinstance(meta, dict) or meta.get("ingest_complete") is not True:
                    continue
                if not meta.get("fiscal_year"):
                    continue
                source_url = str(meta.get("source_url") or "")
                if not source_url.startswith("https://"):
                    continue
                primary_name = str(
                    meta.get("selected_primary_document")
                    or meta.get("primary_document") or ""
                )
                # adapter preferred-selection rules: declared primary
                # (never _docling.json), then .pdf, then .htm/.html, then any
                files = [f for f in filing.iterdir() if f.is_file()]
                names = {f.name: f for f in files}
                primary = None
                if primary_name and not primary_name.endswith("_docling.json"):
                    primary = names.get(primary_name)
                if primary is None:
                    primary = next(
                        (f for f in files if f.suffix.lower() == ".pdf"), None)
                if primary is None:
                    primary = next(
                        (f for f in files
                         if f.suffix.lower() in {".htm", ".html"}
                         and f.name != "meta.json"), None)
                if primary is None:
                    primary = next(
                        (f for f in files
                         if f.name != "meta.json"
                         and not f.name.endswith("manifest.json")
                         and not f.name.endswith("_docling.json")), None)
                if primary is None:
                    continue
                digest = _sha256_file(primary)
                if not _exclusive(con, digest):
                    continue
                if not _active_dayu_primary(con, digest):
                    continue
                samples.append({
                    "ticker": ticker.name,
                    "filing_id": filing.name,
                    "fiscal_year": meta.get("fiscal_year"),
                    "form_type": str(meta.get("form_type") or ""),
                    "source_id": str(meta.get("source_id") or ""),
                    "content_sha256": digest,
                })
                if len(samples) >= MIN_SAMPLES:
                    break
            if len(samples) >= MIN_SAMPLES:
                break
    finally:
        con.close()
    if len(samples) < MIN_SAMPLES:
        raise SystemExit(
            f"FAIL: only {len(samples)} dayu-only samples found, need "
            f"{MIN_SAMPLES}"
        )
    return samples


def main() -> int:
    samples = _select_samples()
    results = []
    for sample in samples:
        results.append({
            "sample": f"{sample['ticker']}-FY{sample['fiscal_year']}",
            "filing_id": sample["filing_id"],
            "form_type": sample["form_type"],
            "content_sha256": sample["content_sha256"][:16],
            "exclusive_of_other_roots": True,
            "active_dayu_original_primary": True,
            "meta_complete": True,  # fiscal_year + https source_url + ingest_complete
        })
    print(json.dumps({
        "result": f"EX-02 preconditions passed ({len(results)}/{len(results)})",
        "samples": results,
    }, ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
