"""Read-only real-snapshot probe for DU3-GEOMETRY node C (test-side only).

Reuses the *existing* native probe (``real_probe`` in the DU2-LAYOUT fixtures) for
its SHA-verified bindings and UNAVAILABLE conventions, then extracts REAL dict
spans, words and ``find_tables`` cell geometry that the DU3 projection consumes.
It never writes to an original, never copies one into the repository, and never
enters the product module.  Every emitted unit id is a *probe* id (``locator`` is
``None``): no production locator is claimed.

Bindings are local-only ``{sample_id: absolute path}`` in an uncommitted file.  A
missing file or SHA mismatch yields UNAVAILABLE, never a pass.  Extraction is
bounded by real page count / word / cell / text-byte / wall-clock budgets.
"""

from __future__ import annotations

import sys
import time
import unicodedata
from pathlib import Path

_HERE = Path(__file__).resolve()
_LH_FIXTURES = _HERE.parents[2] / "document_understanding_layout_hints"
if str(_LH_FIXTURES) not in sys.path:
    sys.path.insert(0, str(_LH_FIXTURES))

try:  # reuse the existing native probe's hashing + sample conventions
    import real_probe  # type: ignore

    sha256_of = real_probe.sha256_of
except Exception:  # pragma: no cover - fallback if the sibling fixture is absent
    real_probe = None

    def sha256_of(path: Path) -> str:
        import hashlib

        digest = hashlib.sha256()
        with Path(path).open("rb") as handle:
            for chunk in iter(lambda: handle.read(1 << 20), b""):
                digest.update(chunk)
        return digest.hexdigest()


try:
    import fitz  # PyMuPDF, read-only real extraction
except Exception:  # pragma: no cover - hosts without PyMuPDF
    fitz = None


#: Real geometry samples.  The first four are the card's priority pages and reuse
#: the DU2-LAYOUT probe SHAs; the fifth is a NEW company page not used in debugging.
GEOMETRY_SAMPLES = (
    {
        "sample_id": "hk-miniso-annual-store-table",
        "label": "名创优品 2024 港股年报 p12 门店表（中英双栏多列经营表）",
        "pages": [12],
        "sha256": "07f4937e0558fc31189a56236313ad93c1cef4182adb10ebaf4f355acb9bf1cf",
    },
    {
        "sample_id": "cn-hengfeng-offering-cross-page",
        "label": "恒锋工具 2020 向特定对象发行募集说明书 p61-62（跨页项目概况表）",
        "pages": [61, 62],
        "sha256": "37f7c62de54b33eb8f978c3ee5525471c9c7150b9cbaedc10901aa8280550d2e",
    },
    {
        "sample_id": "cn-jinhe-convertible-tables",
        "label": "金禾实业可转债募集说明书 p223-224（6列表+跨页备案表）",
        "pages": [223, 224],
        "sha256": "3ce59fde98956a0b0370f76d5039a7025b73909a2673b7b677fca7a46d43650e",
    },
    {
        "sample_id": "cn-amec-annual-narrative",
        "label": "中微公司 2025 年报 p41（叙述页，行内数字负例）",
        "pages": [41],
        "sha256": "d64c410832f22f5127277bad6dc357c664aede523561af99150c494857fd3aa5",
    },
    {
        "sample_id": "cn-shihua-annual-store-table",
        "label": "世华科技 2020 年报 p5（新公司样本，未参与调试）",
        "pages": [5],
        "sha256": "67aab7994dc03f90143ddb82088f91c9cf2fce95286ef434404b6498b47faa06",
    },
)

# Real extraction budgets (card C: bound page count / bytes / time).
MAX_PAGES_PER_SAMPLE = 2
MAX_WORDS_PER_PAGE = 2000
MAX_CELLS_PER_PAGE = 2000
MAX_TEXT_BYTES = 64 * 1024
TIME_BUDGET_S = 15.0


def sample_spec(sample_id: str) -> dict:
    for spec in GEOMETRY_SAMPLES:
        if spec["sample_id"] == sample_id:
            return dict(spec)
    raise KeyError(sample_id)


def fingerprint(path: Path) -> dict:
    st = Path(path).stat()
    return {"sha256": sha256_of(path), "mtime_ns": st.st_mtime_ns, "size": st.st_size}


def _unavailable(sample_id: str, reason: str) -> dict:
    return {"status": "unavailable", "sample_id": sample_id, "reason": reason}


def _span_units(page, page_no: int, sample_id: str, seq_start: int, words, budget):
    """Text spans -> (units, bindings).  Real bbox + font runs + contained words."""
    units = []
    bindings = []
    seq = seq_start
    snapshot = page.get_text("dict", sort=False)
    for block in snapshot.get("blocks", ()):
        if block.get("type") != 0:
            continue
        for line in block.get("lines", ()):
            for span in line.get("spans", ()):
                text = unicodedata.normalize("NFC", span.get("text", "")).strip()
                if not text:
                    continue
                bbox = [round(float(v), 3) for v in span.get("bbox", ())]
                if len(bbox) != 4:
                    continue
                text_bytes = len(text.encode("utf8"))
                if budget["bytes"] + text_bytes > MAX_TEXT_BYTES:
                    budget["truncated"] = True
                    return units, bindings, seq
                budget["bytes"] += text_bytes
                uid = f"probe-{sample_id}-p{page_no}-u{seq:04d}"
                size = span.get("size")
                flags = span.get("flags")
                weight = ("bold" if (isinstance(flags, int) and flags & 16) else "regular") if flags is not None else None
                units.append(
                    {
                        "unit_id": uid,
                        "ordinal": seq,
                        "page": page_no,
                        "locator": None,
                        "text": text,
                        "kind": "paragraph",
                        "role": "company_filing",
                        "parser": "probe_pymupdf",
                        "layout": {},
                    }
                )
                # words whose centre falls inside this span bbox
                span_words = []
                for wi, w in enumerate(words):
                    wx0, wy0, wx1, wy1, wtext = w[0], w[1], w[2], w[3], w[4]
                    cx, cy = (wx0 + wx1) / 2.0, (wy0 + wy1) / 2.0
                    if bbox[0] - 1 <= cx <= bbox[2] + 1 and bbox[1] - 1 <= cy <= bbox[3] + 1:
                        if budget["words"] >= MAX_WORDS_PER_PAGE:
                            break
                        budget["words"] += 1
                        span_words.append(
                            {
                                "text": wtext,
                                "bbox": [round(float(v), 3) for v in (wx0, wy0, wx1, wy1)],
                                "native_index": wi,
                            }
                        )
                bindings.append(
                    {
                        "unit_id": uid,
                        "bbox": bbox,
                        "source": "pdf_dict",
                        "font_runs": [
                            {
                                "char_start": 0,
                                "char_end": len(text),
                                "font_size": float(size) if size else None,
                                "font_weight": weight,
                                "font": span.get("font"),
                            }
                        ],
                        "words": span_words,
                    }
                )
                seq += 1
    return units, bindings, seq


def _table_bindings(page, page_no: int, sample_id: str, seq_start: int, budget):
    """find_tables rows -> one unit per row, with REAL per-cell bboxes."""
    units = []
    bindings = []
    seq = seq_start
    try:
        finder = page.find_tables()
    except Exception:
        return units, bindings, seq
    for t_index, table in enumerate(getattr(finder, "tables", ())):
        try:
            extracted = table.extract() or []
        except Exception:
            extracted = []
        rows = getattr(table, "rows", ())
        for r_index, row in enumerate(rows):
            row_cells = getattr(row, "cells", ()) or ()
            texts = extracted[r_index] if r_index < len(extracted) else []
            row_text_parts = []
            cells = []
            for c_index, cell_box in enumerate(row_cells):
                if budget["cells"] >= MAX_CELLS_PER_PAGE:
                    break
                budget["cells"] += 1
                ctext = texts[c_index] if c_index < len(texts) else ""
                ctext = unicodedata.normalize("NFC", str(ctext or "")).strip()
                if cell_box is None or len(cell_box) != 4:
                    continue
                cells.append(
                    {
                        "text": ctext,
                        "bbox": [round(float(v), 3) for v in cell_box],
                        "native_index": c_index,
                        "row": r_index,
                        "column": c_index,
                        "table_id": f"p{page_no}:t{t_index}",
                    }
                )
                if ctext:
                    row_text_parts.append(ctext)
            if not cells:
                continue
            row_text = " | ".join(row_text_parts)
            row_bytes = len(row_text.encode("utf8"))
            if budget["bytes"] + row_bytes > MAX_TEXT_BYTES:
                budget["truncated"] = True
                return units, bindings, seq
            budget["bytes"] += row_bytes
            bbox = [round(float(v), 3) for v in getattr(row, "bbox", table.bbox)]
            uid = f"probe-{sample_id}-p{page_no}-u{seq:04d}"
            units.append(
                {
                    "unit_id": uid,
                    "ordinal": seq,
                    "page": page_no,
                    "locator": None,
                    "text": row_text,
                    "kind": "table_row",
                    "role": "company_filing",
                    "parser": "probe_pymupdf",
                    "layout": {},
                }
            )
            bindings.append({"unit_id": uid, "bbox": bbox, "source": "pdf_table", "cells": cells})
            seq += 1
    return units, bindings, seq


def load_snapshot(bindings: dict[str, str], sample_id: str) -> dict:
    """Build a real ``du-layout-snapshot/1`` + ``du-input/1`` pair (read-only)."""
    if fitz is None:
        return _unavailable(sample_id, "PyMuPDF not installed")
    try:
        spec = sample_spec(sample_id)
    except KeyError:
        return _unavailable(sample_id, f"unknown sample {sample_id}")
    raw_path = bindings.get(sample_id)
    if not raw_path:
        return _unavailable(sample_id, f"binding missing for {sample_id}")
    path = Path(raw_path)
    if not path.is_file():
        return _unavailable(sample_id, f"file not found: {path.name}")
    fp_before = fingerprint(path)
    if fp_before["sha256"] != spec["sha256"]:
        return _unavailable(
            sample_id,
            f"sha mismatch: expected {spec['sha256'][:12]} got {fp_before['sha256'][:12]}",
        )

    deadline = time.monotonic() + TIME_BUDGET_S
    budget = {"words": 0, "cells": 0, "bytes": 0, "truncated": False}
    pages_out = []
    all_units = []
    mapping = []
    seq = 0
    doc = fitz.open(path)
    try:
        for page_no in spec["pages"][:MAX_PAGES_PER_SAMPLE]:
            if time.monotonic() > deadline:
                break
            page = doc[page_no - 1]
            d = page.get_text("dict", sort=False)
            width = round(float(d.get("width", 0) or 0), 3)
            height = round(float(d.get("height", 0) or 0), 3)
            rect_w = round(float(page.rect.width), 3)
            rect_h = round(float(page.rect.height), 3)
            words = page.get_text("words") or []
            budget["words"] = 0
            budget["cells"] = 0
            page_bindings = []

            span_units, span_bindings, seq = _span_units(page, page_no, sample_id, seq, words, budget)
            all_units.extend(span_units)
            page_bindings.extend(span_bindings)

            table_units, table_bindings, seq = _table_bindings(page, page_no, sample_id, seq, budget)
            all_units.extend(table_units)
            page_bindings.extend(table_bindings)

            for unit in span_units + table_units:
                mapping.append(
                    {
                        "unit_id": unit["unit_id"],
                        "sample_id": sample_id,
                        "page": page_no,
                        "kind": unit["kind"],
                        "quote": unit["text"][:60],
                    }
                )
                # byte accounting lives in the span/table builders (MAX_TEXT_BYTES enforced there)
            pages_out.append(
                {
                    "page": page_no,
                    "width": width,
                    "height": height,
                    "coordinate_frame": "dict",
                    "rotation": int(page.rotation or 0),
                    "dict_width": width,
                    "dict_height": height,
                    "rect_width": rect_w,
                    "rect_height": rect_h,
                    "bindings": page_bindings,
                }
            )
    finally:
        doc.close()

    snapshot = {
        "schema_version": "du-layout-snapshot/1",
        "pages": pages_out,
    }
    return {
        "status": "ok",
        "sample_id": sample_id,
        "label": spec["label"],
        "source_sha256": spec["sha256"],
        "snapshot": snapshot,
        "units": all_units,
        "probe_mapping": mapping,
        "fp_before": fp_before,
        "budget": dict(budget),
    }


def load_bindings_file(path: Path) -> dict:
    import json

    p = Path(path)
    if not p.is_file():
        return {}
    data = json.loads(p.read_text(encoding="utf8"))
    return {str(k): str(v) for k, v in data.items()} if isinstance(data, dict) else {}
