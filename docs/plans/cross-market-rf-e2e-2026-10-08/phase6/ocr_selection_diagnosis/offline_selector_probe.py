"""Offline causal probe over existing OCR excerpts, NOT a fresh OCR receipt.

No provider, OCR adapter, raw normalization, AUTO migration or live run. Units
are explicitly diagnostic projections; only existing original text is quoted.
"""
from dataclasses import asdict, replace
import hashlib
import json
from pathlib import Path
import socket
import subprocess
import sys

PROJECT = Path(__file__).resolve().parents[5]
sys.path.insert(0, str(PROJECT / "src"))
from company_wiki.source_catalog import narrative_candidates as nc
from company_wiki.source_catalog import narrative_evidence as ne
from company_wiki.source_catalog.narrative_document import DocumentStructure, NarrativeUnit
from company_wiki.source_contract import EvidenceCoordinates


def no_network(*_args, **_kwargs):
    raise AssertionError("offline probe must not access network")


socket.socket.connect = no_network
socket.create_connection = no_network

report_path = PROJECT / "docs/implementation/main-local-pptx-ocr/real_22_page_statistics.json"
raw = report_path.read_bytes()
real = json.loads(raw)
fixture_sha = hashlib.sha256(b"offline existing OCR excerpt classifier projection").hexdigest()
fixture_id = "urn:company-wiki:source:sha256:" + fixture_sha
rules = ne._candidate_rules()


def unit(text, index=0, *, kind="pptx_image_ocr_line", role="company_filing", page=7, box=None):
    identifier = hashlib.sha256(f"{text}|{kind}|{role}|{page}|{index}".encode()).hexdigest()
    return NarrativeUnit(
        unit_id="urn:company-wiki:narrative-unit:sha256:" + identifier,
        source_id=fixture_id, parser_name="offline-diagnostic-projection", parser_version="1.0.0",
        coordinates=EvidenceCoordinates(page_number=page, paragraph_index=index),
        raw_text=text, unit_kind=kind, source_role=role, language="en",
        quality_flags=("ocr_used", "layout_ambiguous") if kind == "pptx_image_ocr_line" else (),
        metadata={"offline_diagnostic": True, "not_a_fresh_ocr_output": True,
                  "ocr_box": box or [10, 100 + 40 * index, 500, 130 + 40 * index],
                  "bbox": box or [10, 100 + 40 * index, 500, 130 + 40 * index]})


def trace(item):
    text = item.raw_text
    assessment = nc.assess_unit(item, rules)
    facts = rules.operating_facts(text)
    topics = rules.topics(text)
    return {"text": text, "source_role": item.source_role, "unit_kind": item.unit_kind,
            "length": len(text), "topics": topics, "operating_fact": asdict(facts),
            "signals": asdict(nc._signals(text, topics, rules)),
            "pre_signal": nc._pre_signal(text, rules), "excluded": nc._excluded(item, rules),
            "static_definition": bool(rules.static_definition.search(text)),
            "dropped_financial": assessment.dropped_financial,
            "candidate": None if assessment.candidate is None else {
                "topics": assessment.candidate.topics, "reasons": assessment.candidate.reasons,
                "score": assessment.candidate.score}}


def select(items, *, complete=False):
    doc = DocumentStructure(source_id=fixture_id, source_sha256=fixture_sha, language="en", units=tuple(items),
                            page_count=1, pages_read=1, opaque_pages=() if complete else (7,), line_count=len(items))
    package = ne.select_narrative_evidence(doc, title="FY27 Segments and Investor Metrics", existing_kind="investor_relations")
    return {"status": package.status, "candidate_count": package.candidate_count,
            "selected_count": len(package.evidence_spans), "coverage_complete": package.coverage_complete,
            "dropped_financial_count": package.dropped_financial_count,
            "visual_groups": len(ne._pdf_context_groups(items)),
            "selected_texts": [s.raw_text for s in package.evidence_spans]}


page7 = real["qa_bounded_previews"]["7"]
actual = [unit(q["text"], q["index"], box=q["box"]) for q in page7]
diagnoses = {"actual_page7_preview_projection": {"trace": [trace(u) for u in actual], "selection": select(actual)}}
for role in ("management", "image_text"):
    diagnoses["role_counterfactual_" + role] = select([replace(u, source_role=role) for u in actual])
# Offline concatenation tests the semantic classifier only, NOT a claimed
# paragraph or replayable joined span. No missing first OCR line is supplied.
definitions = " ".join(q["text"] for q in page7 if q["index"] in (1, 2, 3))
joined = unit(definitions)
diagnoses["joined_existing_definition_classifier_only"] = {"trace": trace(joined), "selection": select([joined])}
for index in (11, 20):
    q = next(q for q in page7 if q["index"] == index)
    diagnoses["complete_actual_scope_change_line_" + str(index)] = trace(unit(q["text"], index, box=q["box"]))
metric = next(q for q in real["qa_bounded_previews"]["18"] if q["index"] == 82)
diagnoses["actual_metric_definition_excerpt"] = trace(unit(metric["text"], 82, page=18, box=metric["box"]))

# Synthetic positive control isolates the existing format-specific grouping
# fault separately from the missing business-scope semantic class.
control = [unit("We launched", 0), unit("a new product for overseas customers.", 1)]
diagnoses["synthetic_existing_business_action_split_ocr"] = select(control)
diagnoses["synthetic_existing_business_action_joined"] = select([unit("We launched a new product for overseas customers.")])
diagnoses["synthetic_existing_business_action_split_pdf_counterfactual"] = select([
    replace(u, unit_kind="pdf_text_block", quality_flags=(),
            metadata={"bbox": u.metadata["bbox"], "pdf_block": index}) for index, u in enumerate(control)])

negative_texts = ["Microsoft", "FY27 Investor Metrics", "As Restated", "40% 39% 42% 40%",
                  "Microsoft 365 commercial cloud revenue growth", "We increased product revenue by 40% this quarter."]
diagnoses["synthetic_and_actual_label_negative_controls"] = [{"trace": trace(unit(t)), "selection": select([unit(t)])}
                                                             for t in negative_texts]
financial = unit("Revenue 100 120", kind="pdf_table_row")
financial = replace(financial, metadata={"row_cells": ["Revenue", "100", "120"]})
diagnoses["synthetic_financial_row_complete_control"] = {"trace": trace(financial), "selection": select([financial], complete=True)}

assert diagnoses["actual_page7_preview_projection"]["selection"]["selected_count"] == 0
assert diagnoses["actual_page7_preview_projection"]["selection"]["dropped_financial_count"] == 0
assert diagnoses["complete_actual_scope_change_line_11"]["candidate"] is None
assert diagnoses["complete_actual_scope_change_line_20"]["candidate"] is None
assert diagnoses["joined_existing_definition_classifier_only"]["selection"]["selected_count"] == 0
assert diagnoses["synthetic_existing_business_action_split_ocr"]["selected_count"] == 0
assert diagnoses["synthetic_existing_business_action_joined"]["selected_count"] == 1
assert diagnoses["synthetic_existing_business_action_split_pdf_counterfactual"]["selected_count"] == 2
assert all(d["selection"]["selected_count"] == 0 for d in diagnoses["synthetic_and_actual_label_negative_controls"])
assert diagnoses["synthetic_financial_row_complete_control"]["selection"]["status"] == "skipped_no_narrative"
result = {"schema_version": "ocr-selection-offline-causal-probe/1", "status": "CAUSE_REPRODUCED",
          "head": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=PROJECT, text=True).strip(),
          "probe_file_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
          "existing_ocr_report": {"path": str(report_path), "sha256": hashlib.sha256(raw).hexdigest(),
                                  "original_sha256": real["source_sha256"], "recognized_lines": real["recognized_lines"]},
          "scope": "Existing bounded OCR preview text projected into transient structure units; synthetic controls explicitly separated.",
          "not_a_live_ocr_or_provider_receipt": True, "network_calls": 0, "ocr_inferences": 0,
          "raw_normalizations": 0, "suppliers": 0, "auto_mutations": 0, "temp_roots": [],
          "diagnoses": diagnoses}
target = Path(__file__).with_name("offline_selector_probe.json")
target.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(json.dumps({"status": result["status"], "head": result["head"],
                  "actual_preview_selected": diagnoses["actual_page7_preview_projection"]["selection"]["selected_count"],
                  "actual_preview_dropped_financial": diagnoses["actual_page7_preview_projection"]["selection"]["dropped_financial_count"],
                  "ocr_split_selected": diagnoses["synthetic_existing_business_action_split_ocr"]["selected_count"],
                  "joined_selected": diagnoses["synthetic_existing_business_action_joined"]["selected_count"],
                  "pdf_split_selected": diagnoses["synthetic_existing_business_action_split_pdf_counterfactual"]["selected_count"],
                  "suppliers": 0, "ocr_inferences": 0}))
