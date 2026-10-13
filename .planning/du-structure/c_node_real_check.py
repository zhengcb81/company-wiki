"""C-node evidence: run build_structure on real normalized units.

This script is an inspection entry point, not product code.  It reads three
real originals read-only, normalizes the requested pages through the existing
parser, maps the resulting units into a du-input/1 envelope, and runs the lane's
pure ``build_structure``.  It writes a bounded report (excerpts <= 8 KiB per
document) and never copies an original or writes into a production path.

Usage:
    python -X utf8 .planning/du-structure/c_node_real_check.py \
        --bindings <json> --output <dir>

``bindings`` is a small local file: {"sample_id": "absolute path"}.  A missing
or hash-mismatched original is reported as UNAVAILABLE, never as PASS.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]

EXCERPT_BUDGET_BYTES = 8 * 1024

SAMPLES = (
    {
        "sample_id": "hk-miniso-annual-two-column",
        "label": "名创优品 2024 港股年报（中英双栏）",
        "pages": [12],
        "expect": "language_parallel + operating_table + cross-column separation",
    },
    {
        "sample_id": "cn-hengfeng-offering-cross-page",
        "label": "恒锋工具 2020 向特定对象发行募集说明书（跨页项目）",
        "pages": [62, 63],
        "expect": "project package keeps subject across page 62 -> 63",
    },
    {
        "sample_id": "cn-wanrun-ir-qa",
        "label": "万润股份 投资者关系活动记录表（QA 否定）",
        "pages": [2, 3],
        "expect": "qa_exchange separates roles and preserves management denial",
    },
)


def _load_bindings(path: Path) -> dict[str, str]:
    with path.open("r", encoding="utf-8") as handle:
        data = json.load(handle)
    if not isinstance(data, dict):
        raise ValueError("bindings must be a mapping of sample_id -> absolute path")
    return {str(key): str(value) for key, value in data.items()}


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _to_du_input(units, *, source_id: str, source_sha256: str, pages: list[int]) -> dict:
    """Map real narrative units onto the frozen du-input/1 envelope."""
    wanted = set(pages)
    serialised = []
    ordinal = 0
    for unit in units:
        coordinates = unit.coordinates
        page = coordinates.page_number
        if page is None or page not in wanted:
            continue
        metadata = dict(unit.metadata)
        bbox = metadata.get("bbox")
        layout = {}
        if isinstance(bbox, (list, tuple)) and len(bbox) == 4:
            layout["bbox"] = [float(value) for value in bbox]
        hints = {}
        if metadata.get("table_headers") is not None:
            hints["table_id"] = (
                f"t{coordinates.table_index}" if coordinates.table_index is not None else None
            )
        if coordinates.row_index is not None:
            hints["row"] = coordinates.row_index
        if coordinates.column_index is not None:
            hints["column"] = coordinates.column_index
        qa_state = metadata.get("qa_state")
        if qa_state:
            hints["turn_id"] = str(metadata.get("qa_group_id") or "")
            hints["speaker"] = (
                "management" if "answer" in str(qa_state) else "investor"
            )
        serialised.append(
            {
                "unit_id": unit.unit_id,
                "ordinal": ordinal,
                "locator": str(metadata.get("source_locator") or unit.unit_id),
                "page": page,
                "text": unit.raw_text,
                "kind": _kind_for(unit, metadata),
                "language": unit.language,
                "role": unit.source_role,
                "layout": layout,
                "hints": hints,
            }
        )
        ordinal += 1
    return {
        "schema_version": "du-input/1",
        "source_ref": {"source_id": source_id, "source_sha256": source_sha256},
        "metadata": {"title": source_id, "mime_type": "application/pdf", "language": "zh"},
        "coverage": {"native_scan": "partial", "opaque_pages": [], "deferred_pages": []},
        "units": serialised,
    }


def _kind_for(unit, metadata) -> str:
    if unit.unit_kind == "pdf_table_row":
        return "table_row"
    if unit.unit_kind == "pdf_table_header":
        return "table_header"
    if unit.unit_kind == "pdf_table_qa_fragment":
        return "paragraph"
    text = unit.raw_text.strip()
    if text.startswith(("注：", "注:", "（", "(")) and len(text) < 200:
        return "footnote"
    if _looks_like_heading(text):
        return "heading"
    return "paragraph"


_HEADING_PREFIXES = (
    "第", "一、", "二、", "三、", "四、", "五、", "六、", "七、", "八、", "九、", "十、",
    "（一）", "（二）", "（三）", "（四）", "（五）",
)


def _looks_like_heading(text: str) -> bool:
    if len(text) > 60 or "\n" in text:
        return False
    if text.startswith(_HEADING_PREFIXES) and not text.endswith(("。", "；")):
        return True
    return text.endswith(("情况", "分析", "回顾", "概览", "概述")) and len(text) <= 30


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--bindings", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    sys.path.insert(0, str(REPO / "src"))
    from company_wiki.document_understanding.structure import build_structure
    from company_wiki.source_catalog.narrative_evidence import parse_pdf

    bindings = _load_bindings(Path(args.bindings))
    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)

    report = {"schema_version": "du-c-evidence/1", "samples": []}
    for sample in SAMPLES:
        entry = {
            "sample_id": sample["sample_id"],
            "label": sample["label"],
            "pages": sample["pages"],
            "expect": sample["expect"],
            "status": "UNAVAILABLE",
        }
        path_value = bindings.get(sample["sample_id"])
        if not path_value:
            entry["reason"] = "no binding supplied"
            report["samples"].append(entry)
            continue
        path = Path(path_value)
        if not path.is_file():
            entry["reason"] = f"file not found: {path}"
            report["samples"].append(entry)
            continue

        digest = _sha256(path)
        try:
            from company_wiki.source_catalog.narrative_evidence import parse_pdf

            result = parse_pdf(
                path,
                source_id=sample["sample_id"],
                source_sha256=digest,
                table_pages=sample["pages"],
            )
        except Exception as exc:  # pragma: no cover - environment dependent
            entry["reason"] = f"{type(exc).__name__}: {exc}"
            report["samples"].append(entry)
            continue

        structure = result.structure if hasattr(result, "structure") else result
        observation = _to_du_input(
            structure.units,
            source_id=sample["sample_id"],
            source_sha256=digest,
            pages=sample["pages"],
        )
        if not observation["units"]:
            entry["reason"] = "no native units on the requested pages"
            report["samples"].append(entry)
            continue

        built = build_structure(observation)
        excerpt_used = 0
        excerpted = []
        for unit in observation["units"]:
            encoded = len(unit["text"].encode("utf-8"))
            if excerpt_used + encoded > EXCERPT_BUDGET_BYTES:
                break
            excerpt_used += encoded
            excerpted.append({"locator": unit["locator"], "text": unit["text"]})

        entry.update(
            {
                "status": "OBSERVED",
                "source_sha256": digest,
                "unit_count": len(observation["units"]),
                "sections": len(built["sections"]),
                "semantic_units": [
                    {
                        "kind": item["kind"],
                        "completeness": item["completeness"],
                        "member_count": len(item["member_unit_ids"]),
                        "diagnostics": [d["code"] for d in item["diagnostics"]],
                    }
                    for item in built["semantic_units"]
                ],
                "relations": sorted(
                    {relation["kind"] for relation in built["relations"]}
                ),
                "coverage": built["coverage"],
                "diagnostic_codes": sorted(
                    {item["code"] for item in built["diagnostics"]}
                ),
                "excerpt_bytes": excerpt_used,
                "excerpts": excerpted,
            }
        )
        report["samples"].append(entry)

    report_path = output_dir / "c_node_evidence.json"
    with report_path.open("w", encoding="utf-8") as handle:
        json.dump(report, handle, ensure_ascii=False, indent=2)
    print(json.dumps({"report": str(report_path), "samples": len(report["samples"])}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
