"""D4-03: document model + shared engine run without catalog runtime.

These are behaviour probes in fresh interpreters, not import-string scans.  The
isolated run refuses every SourceCatalog / store / acquisition / automation
module and then actually normalizes small HTML, DOCX and PPTX bytes, replays
their locators, and runs the shared document-understanding chain.  The same
probe runs unblocked: it must produce the identical observation *and* must not
load those runtime modules on its own.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

SOURCE = Path(__file__).resolve().parents[2] / "src"

_PROBE = r'''
import importlib.abc
import hashlib
import io
import json
import sys
import zipfile
from datetime import datetime

RUNTIME_PREFIXES = (
    "company_wiki.source_catalog",
    "company_wiki.automation",
    "company_wiki.ingest",
    "company_wiki.canonical_ingest",
    "company_wiki.run_store",
    "company_wiki.scheduler",
    "company_wiki.wiki_repository",
    "company_wiki.source_registry",
)
RUNTIME_EXACT = ("sqlite3",)


class RefuseRuntime(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        blocked = any(
            fullname == prefix or fullname.startswith(prefix + ".")
            for prefix in RUNTIME_PREFIXES
        ) or fullname in RUNTIME_EXACT
        if blocked:
            raise AssertionError("document layer imported runtime owner: " + fullname)
        return None


source_root = sys.argv[1]
mode = sys.argv[2]
sys.path.insert(0, source_root)
if mode == "isolated":
    sys.meta_path.insert(0, RefuseRuntime())

from company_wiki.document_normalization import (
    NormalizationLimits,
    normalize_document,
    replay_unit,
)
from company_wiki.document_understanding import understand_units

HTML = (
    "<html><body><h1>Acme 2025 annual report</h1>"
    "<p>Operating revenue was 1.23 billion, up 8% year on year.</p>"
    "<p>The company plans to expand overseas capacity.</p></body></html>"
).encode()
DOCX_MIME = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
PPTX_MIME = (
    "application/vnd.openxmlformats-officedocument.presentationml.presentation"
)
W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"


def para(text):
    return "<w:p><w:r><w:t>" + text + "</w:t></w:r></w:p>"


def _zipinfo(name):
    info = zipfile.ZipInfo(name, date_time=(2020, 1, 1, 0, 0, 0))
    info.compress_type = zipfile.ZIP_DEFLATED
    return info


def _deterministic_zip(data):
    out = io.BytesIO()
    with zipfile.ZipFile(io.BytesIO(data)) as src, zipfile.ZipFile(
        out, "w", compression=zipfile.ZIP_DEFLATED
    ) as dst:
        for name in sorted(src.namelist()):
            dst.writestr(_zipinfo(name), src.read(name))
    return out.getvalue()


def docx_bytes():
    body = (
        para("Acme Fourth Quarter Earnings Conference Call")
        + para("Speaker 1 00:00:05")
        + para("We expanded overseas capacity and signed new customers this quarter.")
        + para("Speaker 2 00:03:11")
        + para("When will the new capacity ramp?")
    )
    out = io.BytesIO()
    with zipfile.ZipFile(out, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr(
            _zipinfo("[Content_Types].xml"),
            '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
            '<Override PartName="/word/document.xml" ContentType="application/vnd.'
            'openxmlformats-officedocument.wordprocessingml.document.main+xml"/></Types>',
        )
        archive.writestr(
            _zipinfo("word/document.xml"),
            '<w:document xmlns:w="' + W + '"><w:body>' + body + "</w:body></w:document>",
        )
    return out.getvalue()


def pptx_bytes():
    from pptx import Presentation
    from pptx.util import Inches

    deck = Presentation()
    slide = deck.slides.add_slide(deck.slide_layouts[5])
    box = slide.shapes.add_textbox(Inches(1), Inches(1), Inches(6), Inches(2))
    box.text_frame.text = "Operating revenue was 1.23 billion, up 8% year on year."
    deck.core_properties.created = datetime(2020, 1, 1)
    deck.core_properties.modified = datetime(2020, 1, 1)
    deck.core_properties.last_modified_by = "probe"
    deck.core_properties.revision = 1
    raw = io.BytesIO()
    deck.save(raw)
    return _deterministic_zip(raw.getvalue())


def source_id_for(data):
    return "urn:company-wiki:source:sha256:" + hashlib.sha256(data).hexdigest()


limits = NormalizationLimits()
html_doc = normalize_document(
    HTML,
    source_id=source_id_for(HTML),
    source_sha256=hashlib.sha256(HTML).hexdigest(),
    mime_type="text/html",
    limits=limits,
)
docx = docx_bytes()
docx_doc = normalize_document(
    docx,
    source_id=source_id_for(docx),
    source_sha256=hashlib.sha256(docx).hexdigest(),
    mime_type=DOCX_MIME,
    limits=limits,
)
pptx = pptx_bytes()
pptx_doc = normalize_document(
    pptx,
    source_id=source_id_for(pptx),
    source_sha256=hashlib.sha256(pptx).hexdigest(),
    mime_type=PPTX_MIME,
    limits=limits,
)


def doc_record(document, original):
    return {
        "format_name": document.format_name,
        "parser_name": document.parser_name,
        "parser_version": document.parser_version,
        "line_count": document.structure.line_count,
        "errors": list(document.structure.errors),
        "coverage_complete": document.structure.coverage_complete,
        "unit_texts": [unit.raw_text for unit in document.units],
        "unit_roles": [unit.source_role for unit in document.units],
        "unit_kinds": [unit.unit_kind for unit in document.units],
        "replay": [
            replay_unit(
                original,
                source_sha256=document.source_sha256,
                unit=unit,
                limits=limits,
            )
            for unit in document.units
        ],
        "native_turns": [
            dict(unit.metadata["native_speaker_turn"])
            if "native_speaker_turn" in unit.metadata
            else None
            for unit in document.units
        ],
    }


understanding = understand_units(
    html_doc.units,
    source_id=html_doc.source_id,
    source_sha256=html_doc.source_sha256,
    title="Acme 2025 annual report",
    declared_kind="annual_report",
    mime_type="text/html",
)
canonical = json.dumps(understanding, sort_keys=True, default=str, ensure_ascii=False)
observation = {
    "html": doc_record(html_doc, HTML),
    "docx": doc_record(docx_doc, docx),
    "pptx": doc_record(pptx_doc, pptx),
    "understanding": {
        "sha256": hashlib.sha256(canonical.encode("utf-8")).hexdigest(),
        "schema_version": understanding["schema_version"],
        "route_profile": understanding["route"]["profile_id"],
        "section_count": understanding["plan"]["section_count"],
        "package_count": understanding["plan"]["package_count"],
    },
}
leaked = sorted(
    name
    for name in sys.modules
    if any(name == prefix or name.startswith(prefix + ".") for prefix in RUNTIME_PREFIXES)
    or name in RUNTIME_EXACT
)
print("PROBE_JSON:" + json.dumps(
    {"observation": observation, "leaked": leaked},
    sort_keys=True,
    ensure_ascii=True,
))
'''


def _run_probe(mode: str) -> dict:
    # A fresh interpreter binds this source tree directly: pytest's conftest
    # only mutates the parent process, and -I ignores inherited PYTHONPATH.
    # ``errors="replace"`` keeps a non-UTF-8 child traceback (for example a
    # GBK console encoding on Windows) from masking the real assertion.
    completed = subprocess.run(
        [sys.executable, "-I", "-B", "-c", _PROBE, str(SOURCE), mode],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=180,
    )
    assert completed.returncode == 0, completed.stderr
    line = next(
        line for line in completed.stdout.splitlines() if line.startswith("PROBE_JSON:")
    )
    return json.loads(line[len("PROBE_JSON:") :])


def test_document_layer_normalizes_and_understands_without_catalog_runtime():
    result = _run_probe("isolated")
    observation = result["observation"]

    assert observation["html"]["unit_texts"] == [
        "Acme 2025 annual report",
        "Operating revenue was 1.23 billion, up 8% year on year.",
        "The company plans to expand overseas capacity.",
    ]
    assert observation["html"]["replay"] == observation["html"]["unit_texts"]
    assert observation["html"]["errors"] == []
    assert observation["html"]["coverage_complete"] is True

    assert observation["docx"]["unit_texts"] == [
        "Acme Fourth Quarter Earnings Conference Call",
        "Speaker 1 00:00:05",
        "We expanded overseas capacity and signed new customers this quarter.",
        "Speaker 2 00:03:11",
        "When will the new capacity ramp?",
    ]
    assert observation["docx"]["replay"] == observation["docx"]["unit_texts"]
    assert observation["docx"]["errors"] == []

    # The shared turn grammar still observes native speaker turns inside DOCX.
    turns = observation["docx"]["native_turns"]
    assert turns[0] is None
    assert turns[1]["speaker"] == "Speaker 1" and turns[1]["timestamp"] == "00:00:05"
    assert turns[2]["turn_id"] == turns[1]["turn_id"]
    assert turns[3]["speaker"] == "Speaker 2" and turns[3]["timestamp"] == "00:03:11"
    assert observation["docx"]["unit_roles"][1:3] == ["unknown", "unknown"]

    # PPTX imports the structure owner inside its parse function; a module-level
    # scan cannot see it, so the isolated run must actually parse a deck.
    assert observation["pptx"]["format_name"] == "pptx"
    assert observation["pptx"]["unit_texts"] == [
        "Operating revenue was 1.23 billion, up 8% year on year."
    ]
    assert observation["pptx"]["replay"] == observation["pptx"]["unit_texts"]
    assert observation["pptx"]["errors"] == []

    assert observation["understanding"]["schema_version"] == "du-pipeline/1"
    assert observation["understanding"]["route_profile"]
    assert observation["understanding"]["package_count"] >= 1
    assert result["leaked"] == []


def test_isolated_observation_matches_unblocked_runtime():
    isolated = _run_probe("isolated")
    normal = _run_probe("normal")

    # Nothing may load catalog/store/acquisition/automation even when it could.
    assert normal["leaked"] == []
    # Same bytes, same units, same locators, same reading plan either way.
    assert isolated["observation"] == normal["observation"]


def test_blocking_guard_actually_stops_a_catalog_import():
    # Guards the probe itself: a blocked module must abort the child process
    # rather than silently succeeding through a different code path.
    guard = (
        "import importlib.abc, sys\n"
        "sys.path.insert(0, sys.argv[1])\n"
        "class Refuse(importlib.abc.MetaPathFinder):\n"
        "    def find_spec(self, fullname, path=None, target=None):\n"
        "        if fullname.startswith('company_wiki.source_catalog'):\n"
        "            raise AssertionError('blocked ' + fullname)\n"
        "sys.meta_path.insert(0, Refuse())\n"
        "import company_wiki.source_catalog\n"
    )
    completed = subprocess.run(
        [sys.executable, "-I", "-B", "-c", guard, str(SOURCE)],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=120,
    )
    assert completed.returncode != 0
    assert "blocked company_wiki.source_catalog" in completed.stderr
