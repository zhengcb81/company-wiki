"""C 节点原文对照工具（不是 pytest 测试，不进入日常 CI）。

用法（在 families worktree 根目录）：
    python -B -X utf8 docs/plans/document-understanding-2026-10-13/review/deliverables/families/tests/c_node_quote_check.py

对 cases/ 中每个 real_excerpt case：
1) 用未提交 bindings.local.json（.planning/du2-families/ 下，缺省回退 worktree 根；或母计划
   sample_manifest.json 的相对路径）定位原件，只读；
2) 核对 source_sha256 与原件一致；
3) 逐 unit 把 exact_quote 与原文比对（PDF 按 anchor.physical_page 页文本、
   HTML 按 BeautifulSoup 去标签正文（line仅提示，非精确范围）；空白全部剔除后比较，因 PDF 抽取在换行处插入空格）；
4) native_text_empty 单元核对对应页确实无原生文本。

输出逐条 PASS/FAIL 汇总。本工具不改原件、不写派生、不做语义判断。
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path

PKG_ROOT = Path(__file__).resolve().parents[1]
WORKTREE_ROOT = Path(__file__).resolve().parents[7]
CASES_DIR = PKG_ROOT / "cases"


def _load_bindings(bindings_path: Path | None = None) -> dict[str, Path]:
    if bindings_path is not None:
        raw = json.loads(bindings_path.read_text(encoding="utf-8"))
        return {k: Path(v) for k, v in raw["bindings"].items()}
    for bindings_path in (
        WORKTREE_ROOT / ".planning" / "du2-families" / "bindings.local.json",
        WORKTREE_ROOT / "bindings.local.json",
    ):
        if bindings_path.exists():
            raw = json.loads(bindings_path.read_text(encoding="utf-8"))
            return {k: Path(v) for k, v in raw["bindings"].items()}
    manifest = WORKTREE_ROOT / "docs/plans/document-understanding-2026-10-13/sample_manifest.json"
    raw = json.loads(manifest.read_text(encoding="utf-8"))
    out: dict[str, Path] = {}
    for sample in raw["samples"]:
        p = Path(sample["path"])
        out[sample["id"]] = p if p.is_absolute() else WORKTREE_ROOT / p
    return out


def _squash(text: str) -> str:
    return re.sub(r"\s+", "", text)


def _page_text(path: Path, page_number: int) -> str:
    import fitz  # 只读解析，依赖本机 PyMuPDF
    with fitz.open(str(path)) as doc:
        return doc[page_number - 1].get_text()


def _html_text(path: Path) -> str:
    from bs4 import BeautifulSoup
    soup = BeautifulSoup(path.read_text(encoding="utf-8-sig", errors="replace"), "html.parser")
    for node in soup(["script", "style", "head"]):
        node.decompose()
    return soup.get_text(" ", strip=True)


def main(bindings_path: Path | None = None) -> int:
    bindings = _load_bindings(bindings_path)
    checks: list[tuple[str, str, str, bool]] = []
    for case_file in sorted(CASES_DIR.glob("*.json")):
        case = json.loads(case_file.read_text(encoding="utf-8"))
        if case["kind"] != "real_excerpt":
            continue
        sample_id = case["source"]["sample_id"]
        path = bindings[sample_id]
        data = path.read_bytes()
        sha_ok = hashlib.sha256(data).hexdigest() == case["source"]["source_sha256"]
        checks.append((case["case_id"], "-", f"sha256:{sample_id}", sha_ok))
        is_pdf = path.suffix.lower() == ".pdf"
        html_text = None if is_pdf else _html_text(path)
        for unit in case["observation"]["units"]:
            anchor = unit["anchor"]
            quote = anchor["exact_quote"]
            if unit.get("hints", {}).get("native_text_empty"):
                ok = is_pdf and not _page_text(path, anchor["physical_page"]).strip()
                checks.append((case["case_id"], unit["unit_id"], f"empty:p{anchor['physical_page']}", ok))
                continue
            if is_pdf:
                haystack = _page_text(path, anchor["physical_page"])
                where = f"p{anchor['physical_page']}"
            else:
                haystack = html_text or ""
                where = f"document_quote (line_hint={anchor['line']}; not_exact_range)"
            checks.append((case["case_id"], unit["unit_id"], where, _squash(quote) in _squash(haystack)))
    failed = [c for c in checks if not c[3]]
    print(f"checks={len(checks)} failed={len(failed)}")
    for item in failed:
        print("FAIL", *item)
    for item in checks:
        print("PASS" if item[3] else "FAIL", *item[:3])
    return 1 if failed else 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bindings", type=Path, help="Explicit uncommitted source bindings; originals are read-only")
    args = parser.parse_args()
    sys.exit(main(args.bindings))
