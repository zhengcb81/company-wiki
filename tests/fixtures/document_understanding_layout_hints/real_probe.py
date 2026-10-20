"""Read-only PyMuPDF sampling of REAL originals for DU2-LAYOUT C-node checks.

Test-side tooling only.  This is NOT a production second parser: it exists so
the lane can verify its pure ``derive_layout_hints`` capability against real
font/geometry evidence that the current production frontends do not yet pass
through.  It never writes to an original, never copies one into the repository,
and labels every emitted unit id as a *probe* id (no production locator is
claimed: ``locator`` is ``None`` and the probe-id -> page/bbox mapping is kept
as evidence).

Bindings are local-only: ``{"sample_id": "absolute path"}`` in an uncommitted
file.  A missing file or SHA mismatch yields UNAVAILABLE, never a pass.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

try:
    import pymupdf as fitz  # PyMuPDF, read-only observation of font size/geometry
except Exception:  # pragma: no cover - exercised only on hosts without PyMuPDF
    fitz = None

PROBE_SAMPLES = (
    {
        "sample_id": "hk-miniso-annual-store-table",
        "label": "名创优品 2024 港股年报 p12 门店表（中英双栏，多列经营表）",
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
        "label": "金禾实业可转债募集说明书 p223-224（6列表 + 跨页备案表）",
        "pages": [223, 224],
        "sha256": "3ce59fde98956a0b0370f76d5039a7025b73909a2673b7b677fca7a46d43650e",
    },
    {
        "sample_id": "cn-amec-annual-narrative",
        "label": "中微公司 2025 年报 p41（叙述页，行内数字负例）",
        "pages": [41],
        "sha256": "d64c410832f22f5127277bad6dc357c664aede523561af99150c494857fd3aa5",
    },
)

EXCERPT_BUDGET_BYTES = 8 * 1024


def sha256_of(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def sample_spec(sample_id: str) -> dict:
    for spec in PROBE_SAMPLES:
        if spec["sample_id"] == sample_id:
            return dict(spec)
    raise KeyError(sample_id)


def load_probe_input(
    bindings: dict[str, str], sample_id: str, *, mode: str = "span"
) -> dict:
    """Build a du2-layout-input/1 envelope from a real original (read-only).

    ``mode="span"`` keeps one unit per text span (fine granularity: columns can
    be proven from geometry).  ``mode="row_collapse`` merges each visual row of
    spans into one whole-row unit, reproducing the coarse granularity of the
    current production input (no cell coordinates survive).
    """
    if fitz is None:
        return {
            "status": "unavailable",
            "reason": "PyMuPDF not installed",
            "sample_id": sample_id,
        }
    if mode not in ("span", "row_collapse"):
        raise ValueError(f"unknown probe mode: {mode}")
    spec = sample_spec(sample_id)
    raw_path = bindings.get(sample_id)
    if not raw_path:
        return {
            "status": "unavailable",
            "reason": f"binding missing for {sample_id}",
            "sample_id": sample_id,
        }
    path = Path(raw_path)
    if not path.is_file():
        return {
            "status": "unavailable",
            "reason": f"file not found: {path}",
            "sample_id": sample_id,
        }
    actual_sha = sha256_of(path)
    if actual_sha != spec["sha256"]:
        return {
            "status": "unavailable",
            "reason": f"sha mismatch: expected {spec['sha256'][:12]} got {actual_sha[:12]}",
            "sample_id": sample_id,
        }

    pages_out: list[dict] = []
    mapping: list[dict] = []
    seq = 0
    doc = fitz.open(path)
    try:
        for page_no in spec["pages"]:
            page = doc[page_no - 1]
            spans: list[dict] = []
            for block in page.get_text("dict")["blocks"]:
                if block.get("type") != 0:
                    continue
                for line in block["lines"]:
                    for span in line["spans"]:
                        text = span["text"]
                        if not text.strip():
                            continue
                        spans.append(
                            {
                                "text": text,
                                "bbox": [round(float(v), 2) for v in span["bbox"]],
                                "size": round(float(span["size"]), 2),
                                "font": span["font"],
                                "bold": bool(span["flags"] & 16),
                            }
                        )
            spans.sort(
                key=lambda s: ((s["bbox"][1] + s["bbox"][3]) / 2.0, s["bbox"][0])
            )
            if mode == "span":
                rows = [[s] for s in spans]
            else:
                rows = []
                for span in spans:
                    yc = (span["bbox"][1] + span["bbox"][3]) / 2.0
                    if rows:
                        last = rows[-1]
                        ref_yc = sum(
                            (s["bbox"][1] + s["bbox"][3]) / 2.0 for s in last
                        ) / len(last)
                        height = max(s["bbox"][3] - s["bbox"][1] for s in last + [span])
                        if abs(yc - ref_yc) <= 0.6 * max(height, 6.0):
                            last.append(span)
                            continue
                    rows.append([span])

            units = []
            for row in rows:
                bbox = [
                    min(s["bbox"][0] for s in row),
                    min(s["bbox"][1] for s in row),
                    max(s["bbox"][2] for s in row),
                    max(s["bbox"][3] for s in row),
                ]
                size = max(s["size"] for s in row)
                bold = all(s["bold"] for s in row) and len(row) > 0
                text = " ".join(s["text"] for s in row)
                unit_id = f"probe-{sample_id}-p{page_no}-u{seq:04d}"
                units.append(
                    {
                        "unit_id": unit_id,
                        "ordinal": seq,
                        "locator": None,
                        "text": text,
                        "bbox": bbox,
                        "font_size": size,
                        "font_weight": "bold" if bold else "regular",
                        "kind": "text",
                        "upstream_hints": {
                            "probe_mode": mode,
                            "geometry_granularity": "row"
                            if mode == "row_collapse"
                            else "span",
                        },
                    }
                )
                mapping.append(
                    {
                        "unit_id": unit_id,
                        "sample_id": sample_id,
                        "page": page_no,
                        "bbox": bbox,
                        "font_size": size,
                        "bold": bold,
                        "quote": text.strip()[:120],
                    }
                )
                seq += 1
            pages_out.append(
                {
                    "page": page_no,
                    "width": round(float(page.rect.width), 2),
                    "height": round(float(page.rect.height), 2),
                    "units": units,
                }
            )
    finally:
        doc.close()

    observation = {
        "schema_version": "du2-layout-input/1",
        "source_ref": {
            "source_id": sample_id,
            "source_sha256": spec["sha256"],
            "probe_note": "test-only probe units; locator intentionally null",
        },
        "coverage": {"opaque_pages": [], "deferred_pages": []},
        "pages": pages_out,
    }
    return {
        "status": "ok",
        "sample_id": sample_id,
        "label": spec["label"],
        "source_sha256": spec["sha256"],
        "mode": mode,
        "observation": observation,
        "probe_mapping": mapping,
    }


def capped_mapping(mapping: list[dict]) -> list[dict]:
    """Cap total quote bytes per source at EXCERPT_BUDGET_BYTES (evidence hygiene)."""
    out: list[dict] = []
    used = 0
    for item in mapping:
        quote = item["quote"]
        size = len(quote.encode("utf8"))
        if used + size > EXCERPT_BUDGET_BYTES:
            out.append({**item, "quote": "", "quote_omitted": True})
            continue
        used += size
        out.append(item)
    return out


def write_mapping_evidence(path: Path, results: list[dict]) -> None:
    """Write probe-id -> page/bbox mapping evidence (no absolute paths).

    The fine-grained (``span``) probe carries the full id->coordinate mapping;
    the collapsed (``row_collapse``) probe is recorded as counts only, because
    it is derived from the same spans and would duplicate the evidence.
    """
    samples = []
    for r in results:
        if r.get("status") != "ok":
            continue
        entry = {
            "sample_id": r["sample_id"],
            "label": r["label"],
            "source_sha256": r["source_sha256"],
            "mode": r["mode"],
            "unit_count": len(r["probe_mapping"]),
        }
        if r["mode"] == "span":
            entry["probe_mapping"] = capped_mapping(r["probe_mapping"])
        else:
            entry["probe_mapping_note"] = (
                "derived from the same page spans as the span probe; "
                "row-collapsed ids share the page/coordinate provenance above"
            )
            entry["page_extent"] = {
                "first_unit": r["probe_mapping"][0]["unit_id"]
                if r["probe_mapping"]
                else None,
                "last_unit": r["probe_mapping"][-1]["unit_id"]
                if r["probe_mapping"]
                else None,
            }
        samples.append(entry)
    payload = {
        "schema_version": "du2-layout-probe-mapping/1",
        "note": "probe ids map to original page coordinates; they are NOT production locators",
        "samples": samples,
        "unavailable": [
            {"sample_id": r["sample_id"], "reason": r.get("reason")}
            for r in results
            if r.get("status") != "ok"
        ],
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=1) + "\n", encoding="utf8"
    )
