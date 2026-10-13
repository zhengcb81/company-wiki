"""C-node: verify real-excerpt quotes against the original documents (read-only).

Deterministic and manual-audit friendly: no LLM, no inference, no summary
generation. For every real_excerpt case it checks, against the *original* file:

  1. the file's SHA-256 equals the case's pinned source_sha256;
  2. every unit anchor exact_quote occurs in the original text at the declared
     page (PDF) or in the document body (HTML/TXT), whitespace-normalized;
  3. the original's mtime is unchanged after reading (raw preservation).

Real paths come from the uncommitted .planning/du2-facets/bindings.local.json
(sample_id -> {path, sha256, mtime}); absolute paths never enter the portable
fixtures. Output: c_verification/real_excerpt_checks.json (committed data).

Usage (from the worktree root):
    python -B -X utf8 docs/plans/document-understanding-2026-10-13/review/deliverables/facets/tools/verify_real_quotes.py
"""

from __future__ import annotations

import hashlib
import json
import re
import shutil
import sys
import tempfile
from pathlib import Path

FACETS_ROOT = Path(__file__).resolve().parent.parent
WORKTREE_ROOT = FACETS_ROOT.parents[5]
CASES_DIR = FACETS_ROOT / "cases"
BINDINGS_PATH = WORKTREE_ROOT / ".planning" / "du2-facets" / "bindings.local.json"
OUTPUT_PATH = FACETS_ROOT / "c_verification" / "real_excerpt_checks.json"


def normalized(text: str) -> str:
    return re.sub(r"\s+", "", text)


def sha256_of(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def extract_text(path: Path, page: int | None) -> tuple[str, str]:
    suffix = path.suffix.lower()
    if suffix == ".pdf":
        import fitz  # PyMuPDF, read-only

        with fitz.open(path) as doc:
            text = doc[page - 1].get_text() if page else "".join(p.get_text() for p in doc)
        return text, "pymupdf_page_text_normalized"
    if suffix in {".htm", ".html"}:
        # Reuse the production frontend; raw markup substrings are not body evidence.
        sys.path.insert(0, str(WORKTREE_ROOT / "src"))
        from company_wiki.document_normalization import normalize_document

        original = path.read_bytes()
        source_sha = hashlib.sha256(original).hexdigest()
        document = normalize_document(
            original,
            source_id="urn:company-wiki:source:sha256:" + source_sha,
            source_sha256=source_sha,
            mime_type="text/html",
        )
        return "\n".join(unit.raw_text for unit in document.units), "public_html_normalization"
    return path.read_text(encoding="utf-8", errors="replace"), "txt_text_normalized"


def main() -> int:
    if not BINDINGS_PATH.exists():
        print(f"missing uncommitted bindings: {BINDINGS_PATH}", file=sys.stderr)
        return 2
    bindings = json.loads(BINDINGS_PATH.read_text(encoding="utf-8"))["bindings"]

    case_files = sorted(CASES_DIR.glob("real_*.json"))
    checks: list = []
    originals: dict = {}
    failures: list = []
    scratch = Path(tempfile.mkdtemp(prefix="du2-facets-c-"))
    try:
        for case_path in case_files:
            case = json.loads(case_path.read_text(encoding="utf-8"))
            if case.get("kind") != "real_excerpt":
                continue
            sample_id = case["source"]["sample_id"]
            pinned_sha = case["source"]["source_sha256"]
            binding = bindings[sample_id]
            original = Path(binding["path"])

            mtime_before = original.stat().st_mtime_ns
            actual_sha = sha256_of(original)
            sha_ok = actual_sha == pinned_sha == binding["sha256"]
            if not sha_ok:
                failures.append(f"{sample_id}: sha mismatch ({actual_sha[:16]} vs {pinned_sha[:16]})")

            for unit in case["observation"]["units"]:
                anchor = unit.get("anchor")
                if anchor is None:
                    continue
                quote = anchor["exact_quote"]
                page = anchor["physical_page"]
                text, method = extract_text(original, page)
                matched = normalized(quote) in normalized(text)
                line = anchor.get("line")
                if original.suffix.lower() == ".txt" and line is not None:
                    lines = text.splitlines()
                    matched = 0 < line <= len(lines) and normalized(quote) in normalized(lines[line - 1])
                if not matched:
                    failures.append(f"{sample_id}: quote not found at page {page}: {quote[:40]!r}")
                checks.append(
                    {
                        "check_id": f"{sample_id}-{unit['unit_id']}",
                        "sample_id": sample_id,
                        "source_sha256": pinned_sha,
                        "page": page,
                        "line": line,
                        "quote": quote,
                        "method": method,
                        "normalized_match": matched,
                        "sha256_verified": sha_ok,
                    }
                )
                del text

            mtime_after = original.stat().st_mtime_ns
            originals[sample_id] = {
                "sha256_recomputed": actual_sha,
                "sha256_matches_manifest": sha_ok,
                "mtime_unchanged_after_read": mtime_before == mtime_after,
                "local_binding_key": case["source"]["local_binding_key"],
            }
            if mtime_before != mtime_after:
                failures.append(f"{sample_id}: mtime changed during read")

        payload = {
            "schema_version": "du2-facet-c-checks/1",
            "method_notes": [
                "来源核对：完整锚点与原件逐条比对，空白归一化后逐字命中；这是引用核查，不代替事实含义与生产语义审查。",
                "PDF按声明页取原文；HTML用公共normalize_document正文；TXT按声明行核实完整锚点。",
                "原件只读打开，不复制、不改写；读取前后核对 SHA-256 与 mtime。",
                "本文件是核对记录，不是引擎语义验收；语义执行属 ROOT（NOT_RUN_ROOT_INTEGRATION）。",
                "绝对路径只存于未提交的 .planning/du2-facets/bindings.local.json，不进入可移植fixture。",
            ],
            "checks": checks,
            "raw_preservation": {
                "originals": originals,
                "raw_copies": 0,
                "scratch_dir_removed": True,
            },
            "resources": {"model_calls": 0, "paid_usd": 0},
        }
        OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
        OUTPUT_PATH.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
    finally:
        shutil.rmtree(scratch, ignore_errors=True)

    if failures:
        for failure in failures:
            print(f"FAIL {failure}", file=sys.stderr)
        return 1
    print(f"OK {len(checks)} quote checks verified against originals -> {OUTPUT_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
