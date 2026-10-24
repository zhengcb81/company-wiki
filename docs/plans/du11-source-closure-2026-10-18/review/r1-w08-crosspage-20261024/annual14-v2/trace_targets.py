"""Read-only, bounded target trace for the annual14 source-quality review.

This wraps the existing public selector functions, records only target units on
PDF pages 14 and 119-120, and leaves all selector return values unchanged. It
does not call a model, change a source catalog/config, download, or copy a raw
document. The selector receipt is written to a caller-supplied temporary path;
the bounded trace is written to --trace-output.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import re
import sys
from collections.abc import Mapping
from dataclasses import asdict, is_dataclass
from pathlib import Path
from typing import Any


REPO = Path(__file__).resolve().parents[6]
RUNNER = REPO / ".planning/r1-w08-real-20261023/run_real_selection_prose_quality_20261023.py"
TRACE_SCHEMA = "w08-annual14-target-selector-trace/1"
MAX_TRACE_BYTES = 512 * 1024
MAX_UNIT_TEXT_CHARS = 1400

A12_TERMS = (
    "预计2026年公司整体收入达到",
    "上述提及的2026年全年经营业绩展望",
    "在手订单情况为基础预测",
    "全球医药行业发展平稳",
    "国际贸易环境",
    "国家监管环境稳定",
    "不构成公司对投资者的实质承诺",
    "存在较大的不确定性",
)
A13_TERMS = (
    "按照业务类型披露收入确认和计量所采用的会计政策",
    "履行了合同中的履约义务",
    "某一时段内履行的履约义务",
    "某一时点履行的履约义务",
    "预收销售商品或服务款项",
    "合同负债",
    "待履行了相关履约义务时再转为收入",
)


def compact(value: str) -> str:
    return re.sub(r"\s+", "", value)


def labels(unit: Any) -> list[str]:
    page = getattr(getattr(unit, "coordinates", None), "page_number", None)
    text = compact(getattr(unit, "raw_text", "") or "")
    result: list[str] = []
    if page == 14 and any(compact(term) in text for term in A12_TERMS):
        result.append("ST-A12")
    if page in {119, 120} and any(compact(term) in text for term in A13_TERMS):
        result.append("ST-A13")
    return result


def convert(value: Any) -> Any:
    if is_dataclass(value):
        return asdict(value)
    if isinstance(value, (set, frozenset)):
        return sorted(value)
    if hasattr(value, "to_dict"):
        return value.to_dict()
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    return str(value)


def unit_row(unit: Any) -> dict[str, Any]:
    text = getattr(unit, "raw_text", "") or ""
    return {
        "id": getattr(unit, "unit_id", None),
        "target": labels(unit),
        "text_excerpt": text[:MAX_UNIT_TEXT_CHARS],
        "text_truncated": len(text) > MAX_UNIT_TEXT_CHARS,
        "coordinates": convert(getattr(unit, "coordinates", None)),
        "kind": getattr(unit, "unit_kind", None),
        "role": getattr(unit, "source_role", None),
    }


def compact_profile(profile: Any) -> dict[str, Any]:
    keep = ("profile_id", "family", "regime", "form_type", "section_role", "priority")
    return {name: profile.get(name) for name in keep if name in profile}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--trace-output", type=Path, required=True)
    args, runner_args = parser.parse_known_args()
    if not runner_args or runner_args[0] != "--scope":
        raise SystemExit("pass the existing runner's --scope/--source-index/--oracle/--output/--code-root arguments")

    spec = importlib.util.spec_from_file_location("w08_bounded_real_runner", RUNNER)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load existing bounded runner: {RUNNER}")
    runner = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(runner)

    from company_wiki.source_catalog import narrative_finalize as finalize
    from company_wiki.source_catalog import narrative_reading as reading
    from company_wiki.source_catalog import narrative_operating_relations as operating_relations
    from company_wiki.source_catalog.narrative_revenue_guidance import revenue_guidance_premise
    from company_wiki.document_understanding import narrative_continuity as continuity

    trace: dict[str, Any] = {
        "schema_version": TRACE_SCHEMA,
        "instrumentation": "Records original function outputs only; selector return values are unchanged.",
        "targets": [],
    }
    originals = {
        "understand": reading._understand,
        "admitted": reading._admitted,
        "candidates": reading._candidates,
        "plan_budget_items": finalize.plan_budget_items,
        "local_qualification_dependencies": operating_relations.SourceOperatingSession.local_qualification_dependencies,
        "native": continuity._Analysis.native,
        "edge": continuity._Analysis.edge,
    }

    def understand(parsed: Any, *positional: Any, **keywords: Any) -> Any:
        target_units = [unit for unit in parsed.units if labels(unit)]
        trace["targets"] = [unit_row(unit) for unit in target_units]
        result = originals["understand"](parsed, *positional, **keywords)
        target_ids = {unit.unit_id for unit in target_units}
        trace["target_profiles"] = {
            unit_id: compact_profile(profile)
            for unit_id, profile in result.get("reading_plan", {}).get("unit_profiles", {}).items()
            if unit_id in target_ids
        }
        sections = result.get("structure", {}).get("sections", ())
        trace["target_sections"] = [
            {
                **{key: value for key, value in section.items() if key != "body_unit_ids"},
                "target_body_ids": sorted(target_ids & set(section.get("body_unit_ids", ()))),
                "body_count": len(section.get("body_unit_ids", ())),
            }
            for section in sections
            if target_ids & set(section.get("body_unit_ids", ()))
        ]
        trace["parsed_unit_count"] = len(parsed.units)
        return result

    def admitted(unit: Any, *positional: Any, **keywords: Any) -> Any:
        result = originals["admitted"](unit, *positional, **keywords)
        if labels(unit):
            kind = positional[1] if len(positional) > 1 else keywords.get("kind")
            trace.setdefault("admission", []).append(
                {"unit": unit_row(unit), "kind": kind, "fact": convert(result[1]), "admitted": result[0]}
            )
        return result

    def candidates(parsed: Any, pipeline: Any, *positional: Any, **keywords: Any) -> Any:
        result = originals["candidates"](parsed, pipeline, *positional, **keywords)
        target_ids = {row["id"] for row in trace["targets"]}
        trace["candidate_targets"] = [
            {
                "unit": unit_row(candidate.unit),
                "score": candidate.score,
                "reasons": list(candidate.reasons),
                "topics": list(candidate.topics),
                "reading": convert(result[1].get(candidate.unit.unit_id)),
            }
            for candidate in result[0]
            if labels(candidate.unit)
        ]
        trace["eligible_targets"] = [
            row for row in result[2] if target_ids & set(row.get("member_unit_ids", ()))
        ]
        trace["withheld_targets"] = [
            row for row in result[4] if target_ids & set(row.get("known_unit_ids", ()))
        ]
        trace["candidate_count"] = len(result[0])
        return result

    def plan_budget_items(items: Any, *positional: Any, **keywords: Any) -> Any:
        result = originals["plan_budget_items"](items, *positional, **keywords)
        target_items = [item for item in items if labels(item.payload.unit)]

        def item_row(item: Any) -> dict[str, Any]:
            return {
                "id": item.item_id,
                "target": labels(item.payload.unit),
                "text_excerpt": (item.payload.unit.raw_text or "")[:MAX_UNIT_TEXT_CHARS],
                "page": item.page_key,
                "score": item.score,
                "reasons": list(item.reasons),
                "priority": item.reading_priority,
                "topics": list(item.reading_topics),
                "required": list(item.required_item_ids),
                "context_only": item.is_context_only,
                "value_band": item.value_band,
                "chars": item.evidence_chars,
            }

        target_ids = {item.item_id for item in target_items}
        selected_ids = {item.item_id for item in result[0]}
        trace["budget_target_items"] = [item_row(item) for item in target_items]
        trace["budget_target_decisions"] = [
            {**item_row(item), "selected": item.item_id in selected_ids} for item in target_items
        ]
        trace["budget_target_diagnostics"] = [
            convert(diagnostic)
            for diagnostic in result[1]
            if getattr(diagnostic, "item_id", None) in target_ids
            or target_ids.intersection(getattr(diagnostic, "item_ids", ()))
        ]
        return result

    def local_qualification_dependencies(self: Any, edges: Any, *, origins: Any = None,
                                         section_ids: Any = None) -> Any:
        result = originals["local_qualification_dependencies"](
            self, edges, origins=origins, section_ids=section_ids
        )
        source_origins = origins if origins is not None else {}

        def origins_for_material(material_id: str) -> list[str]:
            matches = [original_id for original_id, mapped_id in source_origins.items()
                       if mapped_id == material_id]
            return matches or [material_id]

        for edge in edges:
            if edge.get("basis") != "source_body_adjacency":
                continue
            left_original, right_original = edge.get("left"), edge.get("right")
            if not isinstance(left_original, str) or not isinstance(right_original, str):
                continue
            left = source_origins.get(left_original, left_original)
            right = source_origins.get(right_original, right_original)
            a = self.units.get(left) or self.originals.get(left)
            b = self.units.get(right) or self.originals.get(right)
            if a is None or b is None or not (labels(a) or labels(b)):
                continue
            trace.setdefault("target_adjacency_edges", []).append({
                "left_id": left_original,
                "right_id": right_original,
                "left_target": labels(a),
                "right_target": labels(b),
                "left_page": getattr(getattr(a, "coordinates", None), "page_number", None),
                "right_page": getattr(getattr(b, "coordinates", None), "page_number", None),
                "left_excerpt": (getattr(a, "raw_text", "") or "")[:500],
                "right_excerpt": (getattr(b, "raw_text", "") or "")[:500],
                "forward_guidance_premise_match": revenue_guidance_premise(
                    a.raw_text, b.raw_text, follows=True
                ),
                "reverse_guidance_premise_match": revenue_guidance_premise(
                    b.raw_text, a.raw_text, follows=False
                ),
                "dependency_added": right in result.get(left, ()),
            })
        for left, rights in result.items():
            a = self.units.get(left) or self.originals.get(left)
            if a is None:
                continue
            for right in rights:
                b = self.units.get(right) or self.originals.get(right)
                if b is None or not (labels(a) or labels(b)):
                    continue
                a_coordinates = getattr(a, "coordinates", None)
                b_coordinates = getattr(b, "coordinates", None)
                a_origins = origins_for_material(left)
                b_origins = origins_for_material(right)
                a_sections = sorted({section_ids[uid] for uid in a_origins
                                     if section_ids and isinstance(section_ids.get(uid), str)
                                     and section_ids.get(uid)})
                b_sections = sorted({section_ids[uid] for uid in b_origins
                                     if section_ids and isinstance(section_ids.get(uid), str)
                                     and section_ids.get(uid)})
                a_page = getattr(a_coordinates, "page_number", None)
                b_page = getattr(b_coordinates, "page_number", None)
                a_paragraph = getattr(a_coordinates, "paragraph_index", None)
                b_paragraph = getattr(b_coordinates, "paragraph_index", None)
                trace.setdefault("target_qualification_dependencies", []).append({
                    "left_id": left, "right_id": right,
                    "left_original_ids": a_origins, "right_original_ids": b_origins,
                    "left_target": labels(a), "right_target": labels(b),
                    "left_page": a_page, "right_page": b_page,
                    "left_paragraph": a_paragraph, "right_paragraph": b_paragraph,
                    "paragraph_gap": (b_paragraph - a_paragraph
                                      if type(a_paragraph) is int and type(b_paragraph) is int else None),
                    "left_section_ids": a_sections, "right_section_ids": b_sections,
                    "same_section": bool(a_sections and b_sections
                                         and set(a_sections).intersection(b_sections)),
                    "basis": ("explicit_same_page_section_reference_one_gap"
                              if a_page == b_page and type(a_paragraph) is int
                              and type(b_paragraph) is int and b_paragraph - a_paragraph == 2
                              else "existing_source_dependency"),
                    "left_excerpt": (getattr(a, "raw_text", "") or "")[:500],
                    "right_excerpt": (getattr(b, "raw_text", "") or "")[:500],
                })
        return result

    def native(self: Any, unit: Any, provenance: Any, profile: Any, section: Any,
               headings: Any, left_closed: bool) -> Any:
        result = originals["native"](self, unit, provenance, profile, section, headings, left_closed)
        paragraph = provenance.get("paragraph_index")
        if unit.get("page") == 14 and isinstance(paragraph, int) and 28 <= paragraph <= 38:
            trace.setdefault("page14_native_diagnostics", []).append({
                "unit_id": unit.get("unit_id"), "kind": unit.get("kind"), "page": unit.get("page"),
                "ordinal": unit.get("ordinal"), "wire_paragraph": unit.get("paragraph_index"),
                "paragraph_index": paragraph, "text": unit.get("text", ""),
                "role": unit.get("role"), "source_id": provenance.get("source_id"),
                "source_id_provenance": provenance.get("source_id"),
                "observed_kind": provenance.get("observed_kind"),
                "block_index": provenance.get("block_index"),
                "block_char_start": provenance.get("block_char_start"),
                "block_char_end": provenance.get("block_char_end"),
                "block_sha256": provenance.get("block_sha256"),
                "bbox": provenance.get("bbox"), "coordinate_frame": provenance.get("coordinate_frame"),
                "font_size": provenance.get("font_size"), "font_weight": provenance.get("font_weight"),
                "section": section, "left_closed": left_closed,
                "native": None if result is None else {
                    "source": result.source, "page": result.page, "ordinal": result.ordinal,
                    "paragraph": result.paragraph, "block": result.block, "bbox": result.bbox,
                    "frame": result.frame, "column": result.column, "font": result.font,
                    "scope": result.scope, "left_closed": result.left_closed,
                },
            })
        return result

    def edge(self: Any, left: Any, right: Any, **kwargs: Any) -> Any:
        result = originals["edge"](self, left, right, **kwargs)
        if left.page == right.page == 14 and (
            28 <= left.paragraph <= 38 or 28 <= right.paragraph <= 38
        ):
            trace.setdefault("page14_edge_attempts", []).append({
                "left_id": left.unit.get("unit_id"), "right_id": right.unit.get("unit_id"),
                "left_text": left.unit.get("text", ""), "right_text": right.unit.get("text", ""),
                "left": {"ordinal": left.ordinal, "paragraph": left.paragraph, "block": left.block,
                         "bbox": left.bbox, "frame": left.frame, "column": left.column,
                         "font": left.font, "scope": left.scope, "source": left.source,
                         "role": left.unit.get("role")},
                "right": {"ordinal": right.ordinal, "paragraph": right.paragraph, "block": right.block,
                          "bbox": right.bbox, "frame": right.frame, "column": right.column,
                          "font": right.font, "scope": right.scope, "source": right.source,
                          "role": right.unit.get("role")},
                "basis": result,
            })
        return result

    reading._understand = understand
    reading._admitted = admitted
    reading._candidates = candidates
    finalize.plan_budget_items = plan_budget_items
    operating_relations.SourceOperatingSession.local_qualification_dependencies = local_qualification_dependencies
    continuity._Analysis.native = native
    continuity._Analysis.edge = edge
    output_path = Path(runner_args[runner_args.index("--output") + 1])
    trace["selection_output_path"] = str(output_path)
    try:
        sys.argv = [str(RUNNER), *runner_args]
        runner.main()
        if output_path.exists():
            selection = json.loads(output_path.read_text(encoding="utf-8"))
            task_terms = tuple(compact(term) for term in (*A12_TERMS, *A13_TERMS))
            selected_text = {span.get("span_id"): span.get("raw_text", "")
                             for span in selection.get("selected_spans", ())
                             if isinstance(span, Mapping) and isinstance(span.get("span_id"), str)}
            target_span_ids = {
                span_id for span_id, text in selected_text.items()
                if any(term in compact(text) for term in task_terms)
            }
            trace["selected_context_views_with_target_terms"] = []
            for group in selection.get("reading_context", {}).get("groups", ()):
                for view in group.get("citation_views", ()):
                    support_ids = list(view.get("support_evidence_ids", ()))
                    context_ids = list(view.get("context_evidence_ids", ()))
                    if not target_span_ids.intersection((*support_ids, *context_ids)):
                        continue
                    trace["selected_context_views_with_target_terms"].append({
                        "group_id": group.get("group_id"), "kind": group.get("kind"),
                        "section_role": group.get("section_role"),
                        "support": [{"span_id": span_id, "text": selected_text.get(span_id, "")[:MAX_UNIT_TEXT_CHARS]}
                                    for span_id in support_ids],
                        "context": [{"span_id": span_id, "text": selected_text.get(span_id, "")[:MAX_UNIT_TEXT_CHARS]}
                                    for span_id in context_ids],
                    })
            trace["selection_receipt_sha256"] = runner.sha(output_path)
            trace["selection_stats"] = {
                key: selection.get(key)
                for key in ("physical_pages", "units", "candidate_count", "selected_count", "selected_chars", "work_budget")
            }
    finally:
        reading._understand = originals["understand"]
        reading._admitted = originals["admitted"]
        reading._candidates = originals["candidates"]
        finalize.plan_budget_items = originals["plan_budget_items"]
        continuity._Analysis.native = originals["native"]
        continuity._Analysis.edge = originals["edge"]
        operating_relations.SourceOperatingSession.local_qualification_dependencies = originals[
            "local_qualification_dependencies"
        ]

    blob = (json.dumps(trace, ensure_ascii=False, indent=2, default=convert) + "\n").encode("utf-8")
    if len(blob) > MAX_TRACE_BYTES:
        raise RuntimeError(f"bounded target trace exceeded {MAX_TRACE_BYTES} bytes: {len(blob)}")
    args.trace_output.parent.mkdir(parents=True, exist_ok=True)
    args.trace_output.write_bytes(blob)
    print(json.dumps({"trace_output": str(args.trace_output), "trace_bytes": len(blob), "targets": len(trace["targets"]), "candidate_count": trace.get("candidate_count")}, ensure_ascii=False))


if __name__ == "__main__":
    main()
