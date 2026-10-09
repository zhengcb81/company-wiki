"""Read archive page7 pixels, SEC registered text and terminal zero AUTO only.

No normalize_document/OCR/HTTP/import/runtime calls. One raw image is extracted
to an owned short TEMP for manual viewing, not treated as an OCR receipt.
"""
from dataclasses import asdict
import hashlib
import json
from pathlib import Path
import posixpath
import re
import sqlite3
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET
import zipfile

PROJECT = Path(__file__).resolve().parents[5]
sys.path.insert(0, str(PROJECT / "src"))
from company_wiki.source_catalog.config import load_catalog_config
from company_wiki.source_catalog.reader import ReadOnlyCatalogReader
from company_wiki.automation.narrative_run_store import NarrativeRunStore

OUT = Path(__file__).resolve().parent


def load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def identity(path):
    st = path.stat()
    h = hashlib.sha256()
    with path.open("rb") as f:
        for b in iter(lambda: f.read(1024 * 1024), b""):
            h.update(b)
    return {"path": str(path), "sha256": h.hexdigest(), "size": st.st_size, "mtime_ns": st.st_mtime_ns}


cases = load(PROJECT / "benchmarks/cross_market_rf/cases.json")
case = next(c for c in cases["cases"] if c["case"] == "US-MSFT")
index = load(PROJECT / cases["audit_index"])
source = next(s for s in case["sources"] if s["filename"] == "fy2027_segments_metrics.pptx")
artifact = next(a for a in index["artifacts"] if a.get("sha256") == source["sha256"] and a.get("storage") == "retained_object")
deck = Path(artifact["archive_path"])
before = identity(deck)
assert before["sha256"] == source["sha256"] and before["size"] == 4016522
statistics = load(PROJECT / "docs/implementation/main-local-pptx-ocr/real_22_page_statistics.json")

ns = {"p": "http://schemas.openxmlformats.org/presentationml/2006/main",
      "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships"}
with zipfile.ZipFile(deck) as z:
    presentation = ET.fromstring(z.read("ppt/presentation.xml"))
    relationships = {r.attrib["Id"]: r.attrib["Target"]
                     for r in ET.fromstring(z.read("ppt/_rels/presentation.xml.rels"))}
    seventh = presentation.find("p:sldIdLst", ns)[6]
    slide = posixpath.normpath("ppt/" + relationships[seventh.attrib["{" + ns["r"] + "}id"]])
    rel_part = posixpath.dirname(slide) + "/_rels/" + posixpath.basename(slide) + ".rels"
    image_rels = [r for r in ET.fromstring(z.read(rel_part)) if r.attrib["Type"].endswith("/image")]
    assert len(image_rels) == 1 and image_rels[0].attrib.get("TargetMode") != "External"
    image_part = posixpath.normpath(posixpath.dirname(slide) + "/" + image_rels[0].attrib["Target"])
    image_bytes = z.read(image_part)
expected_media = next(s["structured_value"]["media_sha256"] for s in statistics["selected_spans"]
                      if s["coordinates"]["page_number"] == 7)
assert hashlib.sha256(image_bytes).hexdigest() == expected_media
temporary = Path(tempfile.mkdtemp(prefix="mSel-")).resolve()
image = temporary / "page7.png"
image.write_bytes(image_bytes)
(temporary / "marker.json").write_text(json.dumps({"owner": "ocr_selection_diagnosis", "root": str(temporary),
                                                     "image": identity(image)}, ensure_ascii=False), encoding="utf-8")

# Existing genuine SEC annual2025 HTML provides baseline business-reporting
# scope. It is not substituted for the deck's later FY27-specific assertion.
sec = next(s for s in case["sources"] if "sec.gov" in s.get("url", ""))
sec_ref = sec["source_ref"]
catalog = load_catalog_config(PROJECT / "config/source_catalog.yaml", project_root=PROJECT)
with ReadOnlyCatalogReader(catalog.database_path) as reader:
    row = reader.exact_source_version(sec_ref["document_id"])
    assert row["content_sha256"] == sec["sha256"]
    locations = reader.exact_source_locations(sec_ref["document_id"], sec_ref["source_id"])
    root_specs = {r.root_id: r.path for r in catalog.roots}
    choices = []
    for location in locations:
        path = (root_specs[location["root_id"]] / location["relative_path"]).resolve()
        if path.is_relative_to(root_specs[location["root_id"]]) and path.is_file():
            choices.append(path)
    assert choices
    sec_path = choices[0]
sec_before = identity(sec_path)
assert sec_before["sha256"] == sec["sha256"]
from bs4 import BeautifulSoup
soup = BeautifulSoup(sec_path.read_bytes(), "html.parser")
paragraphs = []
for paragraph in soup.find_all("p"):
    text = " ".join(paragraph.get_text(" ", strip=True).split())
    if re.search(r"(?:reportable|operat(?:e|ing)|financial results in).{0,100}segments?", text, re.I):
        if 60 <= len(text) <= 1600 and text not in paragraphs:
            paragraphs.append(text)
    if len(paragraphs) >= 3:
        break
assert paragraphs

origin = Path(r"C:\Users\郑曾波\AppData\Local\Temp\mOCR-srw9_9oe")
db = origin / "auto/first.sqlite3"
db_before = identity(db)
run_id = "mocr-20261009T045902-933be853-first"
store = NarrativeRunStore(db)
run = store.get_run(run_id)
budget = asdict(store.budget_snapshot(run_id))
reservations = [asdict(r) for r in store.reservations_for_run(run_id)]
with sqlite3.connect(db.as_uri() + "?mode=ro", uri=True) as conn:
    conn.execute("PRAGMA query_only=ON")
    conn.row_factory = sqlite3.Row
    jobs = [dict(r) for r in conn.execute("SELECT job_id,job_type,status,last_error_code,last_error_detail FROM jobs ORDER BY job_type")]
    attempts = [dict(r) for r in conn.execute("SELECT job_id,started_at,finished_at,outcome,error_code,error_detail FROM attempts ORDER BY started_at")]
    active = conn.execute("SELECT count(*) FROM attempts WHERE finished_at IS NULL").fetchone()[0]
assert len(jobs) == len(run.job_ids) == 3
assert all(j["status"] == "dead_letter" for j in jobs) and active == 0
assert reservations == [] and budget["charged_tokens"] == budget["charged_micro_usd"] == 0
assert budget["unknown_reservations"] == budget["unsettled_reservations"] == 0
assert identity(deck) == before and identity(sec_path) == sec_before and identity(db) == db_before
result = {"schema_version": "ocr-selection-primary-read/1", "status": "PRIMARY_READ_ONLY_COMPLETE_IMAGE_AWAITING_VIEW",
          "head": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=PROJECT, text=True).strip(),
          "deck_original": before, "original_unchanged": True,
          "page7": {"display_ordinal": 7, "ooxml_slide_id": int(seventh.attrib["id"]),
                    "slide_part": slide, "image_part": image_part, "media_sha256": expected_media,
                    "owned_image": identity(image), "viewing_root": str(temporary)},
          "sec": {"url": sec["url"], "source_ref": sec_ref, "original": sec_before,
                  "original_unchanged": True, "paragraphs": paragraphs,
                  "role": "FY2025 baseline reporting-scope context only, not FY27 chronology proof"},
          "origin_auto": {"root": str(origin), "database": db_before, "database_unchanged": True,
                          "run_id": run_id, "run_input_hash": run.input_hash, "jobs": jobs, "attempts": attempts,
                          "budget": budget, "reservations": reservations, "active_attempts": active, "terminal": True},
          "network_calls": 0, "suppliers": 0, "ocr_inferences": 0, "raw_normalizations": 0,
          "root_retained_for_recovery": True}
(OUT / "primary_evidence.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(json.dumps({"status": result["status"], "image_for_view": str(image), "SEC_paragraphs": len(paragraphs),
                  "origin_terminal": True, "charged_tokens": 0, "charged_micro_usd": 0, "unknown": 0,
                  "ocr_inferences": 0, "suppliers": 0}))
