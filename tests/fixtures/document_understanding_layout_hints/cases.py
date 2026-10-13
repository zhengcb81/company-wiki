"""Fixture loading helpers for DU2-LAYOUT tests (test-side only)."""

from __future__ import annotations

import copy
import json
from pathlib import Path

FIXTURE_ROOT = Path(__file__).resolve().parent
INPUT_ROOT = FIXTURE_ROOT / "inputs"


def load_case(name: str) -> dict:
    """Return a fresh deep copy of one frozen du2-layout-input/1 fixture."""
    path = INPUT_ROOT / f"{name}.json"
    with path.open("r", encoding="utf8") as handle:
        return json.load(handle)


def case_names() -> list[str]:
    return sorted(path.stem for path in INPUT_ROOT.glob("*.json"))


def _scale_unit(seq: int, text: str, bbox, size, weight="regular", kind="paragraph") -> dict:
    return {
        "unit_id": f"s{seq}",
        "ordinal": seq,
        "locator": f"synthetic-scale-{seq}",
        "text": text,
        "bbox": list(bbox),
        "font_size": size,
        "font_weight": weight,
        "kind": kind,
        "upstream_hints": {},
    }


def scale_case(n_units: int, *, page_width: float = 595.0, page_height: float = 842.0) -> dict:
    """Deterministic synthetic document with ~``n_units`` units.

    The shape mix (headings, paragraphs, bilingual lanes, numeric tables with
    headers and footnotes) is fixed so scale runs measure a representative mix
    instead of one degenerate layout.
    """
    pages = []
    seq = 0
    y = 60.0
    page_no = 0
    current: list[dict] = []

    def flush():
        nonlocal current, page_no
        page_no += 1
        pages.append(
            {
                "page": page_no,
                "width": page_width,
                "height": page_height,
                "units": current,
            }
        )
        current = []

    while seq < n_units:
        y = 60.0
        page_no_units = 0
        while seq < n_units and y < page_height - 80.0:
            block = page_no_units % 7
            if block == 0:
                current.append(
                    _scale_unit(
                        seq,
                        f"第{page_no_units // 7 + 1}节 业务进展",
                        (60.0, y, 220.0, y + 18.0),
                        13.0,
                        weight="bold",
                        kind="heading",
                    )
                )
                seq += 1
                y += 30.0
            elif block in (1, 2):
                current.append(
                    _scale_unit(
                        seq,
                        f"段落叙述第{seq}单元，覆盖经营情况与产能建设进度等事项。",
                        (60.0, y, 520.0, y + 13.0),
                        9.5,
                    )
                )
                seq += 1
                y += 18.0
            elif block == 3:
                current.append(
                    _scale_unit(seq, "English column text for the same paragraph layout.", (60.0, y, 300.0, y + 13.0), 9.0)
                )
                seq += 1
                if seq < n_units:
                    current.append(
                        _scale_unit(seq, "中文分栏文本，与左侧英文并排但不逐句对应。", (320.0, y, 540.0, y + 13.0), 9.0)
                    )
                    seq += 1
                y += 18.0
            elif block == 4:
                current.append(
                    _scale_unit(seq, f"表{page_no_units // 7 + 1} 经营指标", (60.0, y, 160.0, y + 13.0), 10.5, weight="bold", kind="caption")
                )
                seq += 1
                y += 18.0
            else:
                cols = (60.0, 240.0, 380.0, 500.0)
                texts = (f"指标{seq}", f"{seq * 3 % 9000 + 1000:,}", f"{seq * 7 % 9000 + 1000:,}", f"{seq % 90 + 5}%")
                for col, text in zip(cols, texts, strict=False):
                    if seq >= n_units:
                        break
                    current.append(
                        _scale_unit(
                            seq,
                            text,
                            (col, y, col + 90.0, y + 12.0),
                            9.0,
                            weight="bold" if block == 4 and seq % 5 == 0 else "regular",
                        )
                    )
                    seq += 1
                y += 16.0
            page_no_units += 1
        flush()
    return {
        "schema_version": "du2-layout-input/1",
        "source_ref": {"source_id": f"synthetic-scale-{n_units}", "source_sha256": None},
        "coverage": {"opaque_pages": [], "deferred_pages": []},
        "pages": pages,
    }


def deep_copy(case: dict) -> dict:
    return copy.deepcopy(case)
