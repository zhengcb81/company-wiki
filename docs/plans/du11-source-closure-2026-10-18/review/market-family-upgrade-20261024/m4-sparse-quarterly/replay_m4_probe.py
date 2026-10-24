"""Trace two local Q1 PDFs through parse, fact ownership, selection, and cards."""
from __future__ import annotations

from hashlib import sha256
from pathlib import Path
import json
import sys

ROOT = next(p for p in Path(__file__).resolve().parents if (p / "pyproject.toml").is_file())
sys.path.insert(0, str(ROOT))

from company_wiki.document_understanding.geometry_intent.reading import PdfReadingContext  # noqa: E402
from company_wiki.document_understanding.source_cards import source_cards  # noqa: E402
from company_wiki.document_understanding.summary_tasks import build_summary_task_plan  # noqa: E402
from company_wiki.resource_budget import new_document_work_budget  # noqa: E402
from company_wiki.source_catalog.narrative_business_groups import _operating_fact  # noqa: E402
from company_wiki.source_catalog.narrative_evidence import parse_pdf_bytes, select_narrative_evidence  # noqa: E402
from company_wiki.source_catalog import narrative_reading  # noqa: E402
from company_wiki.source_catalog.narrative_source_purpose import source_purpose  # noqa: E402

SAMPLES = {
    "中微公司": (ROOT / "companies/中微公司/raw/financial_reports/中微公司：2026年第一季度报告.pdf",
                "ab7bb0076b2a3fb42ebca7b54d1b167a790221e394613ce544e275b249eb3268"),
    "珀莱雅": (ROOT / "companies/珀莱雅/raw/financial_reports/珀莱雅：珀莱雅化妆品股份有限公司2026年第一季度报告.pdf",
               "873df9697b20c8c8882f9f16f60bdf755bc6b1b27022f2cd491ebc94c012a49e"),
}
NEEDLES = ("8300", "8,300", "300 多台", "300多台", "Angnova", "140:1", "Domingo", "700:1", "224.23%", "政府补助")


def unit_row(unit):
    coords = unit.coordinates
    return {"unit_id": unit.unit_id, "page": coords.page_number,
            "paragraph": coords.paragraph_index, "text": unit.raw_text,
            "pdf_block": unit.metadata.get("pdf_block"),
            "block_sha256": unit.metadata.get("block_sha256"),
            "block_char_start": unit.metadata.get("block_char_start"),
            "block_char_end": unit.metadata.get("block_char_end")}


def main():
    report = {"schema_version": "m4-real-q1-probe/1", "samples": []}
    for company, (path, expected_sha) in SAMPLES.items():
        raw = path.read_bytes()
        actual_sha = sha256(raw).hexdigest()
        assert actual_sha == expected_sha, (company, actual_sha)
        source_id = "urn:company-wiki:source:sha256:" + actual_sha
        parse_budget = new_document_work_budget()
        parsed = parse_pdf_bytes(raw, source_id=source_id, source_sha256=actual_sha,
                                 language="zh", selector_version="0.9.0",
                                 reading_context=PdfReadingContext(path.name, "unknown", "zh"),
                                 work_budget=parse_budget)
        selection_budget = new_document_work_budget()
        route = narrative_reading.route_document(path.name, existing_kind="unknown")
        trace_budget = new_document_work_budget()
        native_contexts = {}
        pipeline = narrative_reading._understand(
            parsed, title=path.name, kind=route.document_kind, mime_type=parsed.mime_type,
            work_budget=trace_budget, _native_contexts=native_contexts)
        prose_budget = new_document_work_budget()
        prose_packages, _, continuity, prose_blocked = narrative_reading._prose_reading_packages(
            parsed, pipeline, work_budget=prose_budget, _native_contexts=native_contexts)
        base_package_rows = []
        continuity_rows = []
        page_flow_rows = []
        if company == "中微公司":
            originals = {unit.unit_id: unit for unit in parsed.units}
            relevant_ids = {unit.unit_id for unit in parsed.units
                            if any(needle.casefold() in unit.raw_text.casefold()
                                   for needle in NEEDLES if needle != "政府补助")}
            for entry in pipeline.get("packages", {}).get("packages", ()):
                members = set(entry.get("member_unit_ids", ()))
                overlap = sorted(members & relevant_ids)
                if overlap:
                    base_package_rows.append({"kind": entry.get("kind"),
                                              "package_id": entry.get("package_id"),
                                              "target_ids": overlap,
                                              "member_count": len(members)})
            window_members = {uid: window for window in continuity.get("windows", ())
                              for uid in window.get("member_unit_ids", ())}
            observation = {row["unit_id"]: row for row in pipeline.get("observation", {}).get("units", ())}
            for unit in parsed.units:
                wire = observation.get(unit.unit_id, {})
                page, ordinal = wire.get("page"), wire.get("ordinal")
                if page not in {2, 3} or ordinal not in range(60, 82):
                    continue
                page_flow_rows.append({"ordinal": ordinal, "page": page,
                    "paragraph": unit.coordinates.paragraph_index, "text": unit.raw_text,
                    "bbox": wire.get("layout", {}).get("bbox"),
                    "column": wire.get("layout", {}).get("column"),
                    "pdf_block": unit.metadata.get("pdf_block"),
                    "block_char_start": unit.metadata.get("block_char_start"),
                    "block_char_end": unit.metadata.get("block_char_end"),
                    "window": list(window_members[unit.unit_id].get("member_unit_ids", ()))
                        if unit.unit_id in window_members else None,
                    "blocked": unit.unit_id in prose_blocked})
            for uid in relevant_ids:
                unit = next(item for item in parsed.units if item.unit_id == uid)
                owner_rows = [entry for entry in prose_packages if uid in entry.get("member_unit_ids", ())]
                window = window_members.get(uid)
                wire = observation.get(uid, {})
                profile = pipeline.get("reading_plan", {}).get("unit_profiles", {}).get(uid, {})
                base_rows = []
                for entry in pipeline.get("packages", {}).get("packages", ()):
                    members = entry.get("member_unit_ids", ())
                    if uid in members:
                        base_rows.append({"kind": entry.get("kind"),
                                          "members": [unit_row(originals[member])
                                                      for member in members if member in originals]})
                continuity_rows.append({
                    "unit": unit_row(unit), "observation_kind": wire.get("kind"),
                    "observation_role": wire.get("role"), "section_role": wire.get("hints", {}).get("section_role"),
                    "ordinal": wire.get("ordinal"), "layout": wire.get("layout"),
                    "source_block": {key: unit.metadata.get(key) for key in (
                        "pdf_block", "block_sha256", "block_char_start", "block_char_end")},
                    "profile": {key: profile.get(key) for key in (
                        "reading_profile_key", "section_role", "priority", "family", "document_kind")},
                    "base_packages": [{"kind": row["kind"], "package_id": row.get("package_id")}
                                     for row in owner_rows],
                    "base_package_members": base_rows,
                    "continuity_window": list(window.get("member_unit_ids", ())) if window else None,
                    "blocked": uid in prose_blocked,
                    "deferred_ranges": [row for row in continuity.get("deferred_unit_ranges", ())
                                        if row.get("source_id") == unit.source_id
                                        and row.get("page") == unit.coordinates.page_number
                                        and row.get("first_ordinal", 10**9) <= wire.get("ordinal", -1)
                                        <= row.get("last_ordinal", -1)],
                })
        session_state = {}
        trace_candidates, trace_reading, trace_eligible, trace_complete, trace_withheld = (
            narrative_reading._candidates(parsed, pipeline, work_budget=trace_budget,
                                          _session_state=session_state,
                                          _native_contexts=native_contexts))
        material_units = {u.unit_id: u for u in pipeline.get("_material_units", parsed.units)}
        traced_members = {}
        for entry in trace_eligible:
            for uid in entry.get("member_unit_ids", ()):
                traced_members.setdefault(session_state.get("session").owner_for(uid), []).append(entry)
        session = session_state["session"]
        package = select_narrative_evidence(parsed, title=path.name, existing_kind="unknown",
                                            selector_version="0.9.0", work_budget=selection_budget)
        selected = [span.raw_text or "" for span in package.evidence_spans]
        selected_text = "\n".join(selected)
        hits = []
        for index, unit in enumerate(parsed.units):
            if any(needle.casefold() in unit.raw_text.casefold() for needle in NEEDLES):
                group = parsed.units[max(0, index - 1):min(len(parsed.units), index + 2)]
                joined = "".join(member.raw_text for member in group)
                fact = _operating_fact(joined)
                session_uid = pipeline.get("_carrier_origins", {}).get(unit.unit_id, unit.unit_id)
                production_fact = session.fact(session_uid)
                owner_id = session.owner_for(session_uid)
                candidate_rows = [candidate for candidate in trace_candidates
                                  if any(needle.casefold() in candidate.unit.raw_text.casefold()
                                         for needle in NEEDLES)]
                hits.append({"matched_unit_index": index, "units": [unit_row(u) for u in group],
                             "joined_fact": {"eligible": fact.eligible, "reasons": list(fact.reasons),
                                             "score": fact.score, "financial_exempt": fact.financial_exempt},
                             "production_owner_id": owner_id,
                             "production_source_text": session.source_text(session_uid),
                             "production_fact": {"eligible": production_fact.eligible,
                                                 "reasons": list(production_fact.reasons),
                                                 "purpose": production_fact.purpose,
                                                 "financial_exempt": production_fact.financial_exempt},
                             "eligible_package_kinds": [entry["kind"] for entry in traced_members.get(owner_id, ())],
                             "eligible_package_text": ["".join(material_units[uid].raw_text
                                 for uid in entry.get("member_unit_ids", ()) if uid in material_units)
                                 for entry in traced_members.get(owner_id, ())],
                             "candidate_text": [candidate.unit.raw_text for candidate in candidate_rows],
                             "source_purpose_joined": source_purpose(joined),
                             "selected_needle_matches": [needle for needle in NEEDLES
                                 if needle.casefold() in selected_text.casefold()]} )
        task_plan = build_summary_task_plan(package.evidence_spans,
                                            reading_context=package.reading_context or {}, max_claims=40)
        cards = []
        for card in source_cards(task_plan, {span.span_id: span for span in package.evidence_spans}):
            cards.append({"available": card.available, "reason": card.reason,
                          "text": card.text or ""})
        available_card_text = "\n".join(card["text"] for card in cards if card["available"])
        if company == "中微公司":
            required = ("8300", "300 多台", "140:1", "700:1", "224.23%")
            missing = [needle for needle in required if needle not in selected_text]
            assert not missing, f"Zhongwei business evidence omitted from selected spans: {missing}"
            assert "与公司正常经营业务密切相关" not in available_card_text, (
                "generic non-recurring-gain template text became a summary card")
        else:
            assert "收回货款减少" in selected_text and "推广费增加" in selected_text, (
                "Proya's company-specific operating cash-flow explanation was omitted")
        report["samples"].append({
            "company": company, "path": str(path), "sha256_before": actual_sha,
            "sha256_after": sha256(path.read_bytes()).hexdigest(), "pages": parsed.page_count,
            "parsed_units": len(parsed.units), "parse_work_units": getattr(parse_budget, "used", None),
            "selection_work_units": getattr(selection_budget, "used", None),
            "trace_work_units": getattr(trace_budget, "used", None),
            "prose_work_units": getattr(prose_budget, "used", None),
            "base_owner_packages_for_key_units": base_package_rows,
            "continuity_for_key_units": continuity_rows,
            "page_flow_rows": page_flow_rows,
            "continuity_diagnostics": (continuity.get("diagnostics", {})
                                        if company == "中微公司" else {}),
            "continuity_ranges": (continuity.get("deferred_unit_ranges", ())
                                  if company == "中微公司" else ()),
            "continuity_complete": continuity.get("complete") if company == "中微公司" else None,
            "trace_candidate_count": len(trace_candidates),
            "trace_eligible_count": len(trace_eligible),
            "trace_complete": trace_complete,
            "trace_withheld_counts": {reason: sum(row.get("reason") == reason for row in trace_withheld)
                                      for reason in sorted({row.get("reason", "unknown")
                                                            for row in trace_withheld})},
            "trace_admission_counts": session_state.get("admission_trace", {}).get("counts", {}),
            "trace_rejection_counts": session_state.get("admission_trace", {}).get("rejection_counts", {}),
            "selection": {"status": package.status, "coverage_complete": package.coverage_complete,
                          "candidate_count": package.candidate_count,
                          "omitted_candidate_count": package.omitted_candidate_count,
                          "selection_limit": package.selection_limit,
                          "selected_spans": len(selected), "selected_chars": sum(map(len, selected))},
            "diagnostics": [dict(row) for row in package.selection_diagnostics],
            "hit_windows": hits,
            "selected_needle_matches": [needle for needle in NEEDLES
                                         if needle.casefold() in selected_text.casefold()],
            "selected_span_text": selected,
            "cards": cards,
        })
    output = Path(__file__).with_name("probe-result.json")
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps([{"company": row["company"], "sha256": row["sha256_after"],
                       "selection": row["selection"],
                       "continuity_complete": row["continuity_complete"],
                       "continuity_diagnostics": row["continuity_diagnostics"],
                       "key_unit_count": len(row["continuity_for_key_units"])}
                      for row in report["samples"]], ensure_ascii=False))


if __name__ == "__main__":
    main()
