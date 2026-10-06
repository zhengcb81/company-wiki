"""Read-only page/line extractor used only while annotating golden points.

This is an annotation aid, not part of the benchmark's evaluation path. It
never writes next to the original and never modifies the source: text is
copied into a caller-supplied scratch directory under the lane ``tmp/`` root
so the annotator can read real pages with the ordinary file reader.

Usage::

    python tools/extract_pages.py --source <abs path> --out tmp/extract/<id>
"""

from __future__ import annotations

import argparse
from pathlib import Path
import shutil
import sys


def extract(source: Path, out_dir: Path) -> int:
    source = source.resolve(strict=True)
    out_dir = out_dir.resolve()
    if source.is_relative_to(out_dir):
        raise ValueError("annotation output must not contain the original")
    scratch = Path(__file__).resolve().parents[3] / "tmp"
    if not out_dir.is_relative_to(scratch) or out_dir == scratch:
        raise ValueError("annotation output must be a new directory under repository tmp")
    out_dir.mkdir(parents=True, exist_ok=False)
    try:
        return _extract_units(source, out_dir)
    except BaseException:
        shutil.rmtree(out_dir)
        raise


def _extract_units(source: Path, out_dir: Path) -> int:
    suffix = source.suffix.casefold()
    if suffix == ".pdf":
        import fitz  # noqa: PLC0415 - optional dependency, only for PDFs

        document = fitz.open(source)
        try:
            for index, page in enumerate(document, start=1):
                target = out_dir / f"page_{index:04d}.txt"
                target.write_text(page.get_text("text"), encoding="utf-8", newline="\n")
            return document.page_count
        finally:
            document.close()
    if suffix in {".txt", ".md"}:
        text = source.read_text(encoding="utf-8-sig", errors="strict")
        lines = text.splitlines()
        for index, line in enumerate(lines, start=1):
            target = out_dir / f"line_{index:05d}.txt"
            target.write_text(line + "\n", encoding="utf-8", newline="\n")
        return len(lines)
    raise SystemExit(f"unsupported source type: {suffix}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    count = extract(args.source, args.out)
    print(f"extracted {count} units into {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
