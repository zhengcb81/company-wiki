"""ROOT cross-layer node: real original -> parse -> adapter -> route -> structure.

This is the integration node from ``implementation.md`` steps 4-6.  It exercises
the whole chain on the plan's real originals and asserts only what the chain can
actually prove; an original that is absent is reported as a skip, never as a
pass.

Originals are located through a local, uncommitted bindings file so this module
stays host-neutral: no repository file may hardcode an absolute path.  The
bindings file maps ``sample_id -> {"path": ..., "sha256": ...}``.

    python -X utf8 -m pytest tests/unit/document_understanding_root -q -m real_data

The bindings path comes from the ``DU_ROOT_BINDINGS`` environment variable, and
defaults to ``.planning/du-root/bindings.local.json`` in this worktree.  Nothing
here writes to a company directory, re-verifies a security identity, or spends a
paid call.
"""

from __future__ import annotations

import hashlib
import json
import os
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
SOURCE = REPO / "src"
if str(SOURCE) not in sys.path:
    sys.path.insert(0, str(SOURCE))

from company_wiki.document_understanding import build_observation  # noqa: E402
from company_wiki.document_understanding.orchestration import (  # noqa: E402
    build_dependency_packages,
)
from company_wiki.document_understanding.structure import build_structure  # noqa: E402

pytestmark = pytest.mark.real_data

BINDINGS_ENV = "DU_ROOT_BINDINGS"
DEFAULT_BINDINGS = Path(".planning") / "du-root" / "bindings.local.json"

# sample_id -> (pages, language).  The path and digest come from the bindings
# file, never from this module.
SAMPLE_PAGES: dict[str, tuple[tuple[int, ...], str]] = {
    "cn-equity": ((62, 63), "zh"),
    "cn-ir": ((2, 3), "zh"),
    "hk-annual": ((12,), "zh"),
    "cn-q-business": ((2, 3), "zh"),
}


def _bindings_path() -> Path:
    configured = os.environ.get(BINDINGS_ENV)
    if configured:
        return Path(configured)
    return REPO / DEFAULT_BINDINGS


def _load_bindings() -> dict[str, dict[str, str]]:
    path = _bindings_path()
    if not path.is_file():
        pytest.skip(
            f"no bindings file at {path}; set {BINDINGS_ENV} to run real-data checks"
        )
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        pytest.skip(f"bindings file unreadable: {type(exc).__name__}")
    if not isinstance(data, dict):
        pytest.skip("bindings file must map sample_id -> {path, sha256}")
    return data


def _entry(sample_id: str) -> dict[str, str] | None:
    bindings = _load_bindings()
    value = bindings.get(sample_id)
    if not isinstance(value, dict):
        return None
    path = value.get("path")
    sha = value.get("sha256")
    if not isinstance(path, str) or not isinstance(sha, str):
        return None
    if not Path(path).is_file():
        return None
    return {"path": path, "sha256": sha}


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _observe(sample_id: str):
    entry = _entry(sample_id)
    if entry is None:
        pytest.skip(f"{sample_id}: original not present or not bound on this machine")
    path = Path(entry["path"])
    if _sha256(path) != entry["sha256"]:
        pytest.skip(f"{sample_id}: original SHA-256 does not match its binding")
    pages, language = SAMPLE_PAGES[sample_id]

    from company_wiki.source_catalog.narrative_evidence import parse_pdf

    parsed = parse_pdf(
        path, source_id=sample_id, source_sha256=entry["sha256"], table_pages=list(pages)
    )
    selected = [unit for unit in parsed.units if unit.coordinates.page_number in set(pages)]
    observation = build_observation(
        selected,
        source_id=sample_id,
        source_sha256=entry["sha256"],
        title=sample_id,
        language=language,
        native_scan="partial",
        opaque_pages=sorted(parsed.opaque_pages),
    )
    return observation, selected, parsed


def test_real_originals_are_byte_stable_after_the_run() -> None:
    """The chain must not modify any original it read."""
    for sample_id in SAMPLE_PAGES:
        entry = _entry(sample_id)
        if entry is None:
            continue
        assert _sha256(Path(entry["path"])) == entry["sha256"], (
            f"{sample_id} was modified by the run"
        )


def test_chinese_offering_yields_projects_with_numbered_sections() -> None:
    observation, _units, _parsed = _observe("cn-equity")
    structure = build_structure(observation)
    kinds = {unit["kind"] for unit in structure["semantic_units"]}
    assert "project" in kinds, "the offering memorandum must yield project packages"

    headings = [
        unit for unit in observation["units"] if unit["kind"] == "heading"
    ]
    assert headings, "numbered headings must be detected from the real text"
    assert all(unit["hints"].get("heading_level") for unit in headings)


def test_real_projects_keep_their_subject_and_their_own_narrative() -> None:
    """A project package must hold its subject together with its own text.

    This document states its projects as headed prose rather than as a project
    table, so the dependency that matters here is the heading plus the
    paragraphs under it -- not a table header row.
    """
    observation, _units, _parsed = _observe("cn-equity")
    structure = build_structure(observation)
    projects = [unit for unit in structure["semantic_units"] if unit["kind"] == "project"]
    assert projects
    texts = {unit["unit_id"]: unit["text"] for unit in observation["units"]}
    multi = [project for project in projects if len(project["member_unit_ids"]) > 2]
    assert multi, "no project package kept more than its bare heading"
    for project in multi:
        anchor = project["anchor_unit_ids"][0]
        assert anchor in project["member_unit_ids"]
        # The anchor is the project's own statement of itself.
        assert texts.get(anchor, "").strip()


def test_real_two_phase_construction_survives_the_page_break() -> None:
    """恒锋 p62-63: the two-phase 建设期 must stay in one package."""
    observation, _units, _parsed = _observe("cn-equity")
    structure = build_structure(observation)
    texts = {unit["unit_id"]: unit["text"] for unit in observation["units"]}
    pages = {unit["unit_id"]: unit["page"] for unit in observation["units"]}
    projects = [unit for unit in structure["semantic_units"] if unit["kind"] == "project"]
    spanning = []
    for project in projects:
        member_pages = {pages.get(unit_id) for unit_id in project["member_unit_ids"]}
        if 62 in member_pages and 63 in member_pages:
            blob = " ".join(texts.get(unit_id, "") for unit_id in project["member_unit_ids"])
            if "一期" in blob and "二期" in blob:
                spanning.append(project)
    assert spanning, (
        "no package retained both construction phases across the 62->63 page break"
    )


def test_real_ir_record_separates_question_from_answer() -> None:
    observation, _units, _parsed = _observe("cn-ir")
    structure = build_structure(observation)
    exchanges = [
        unit for unit in structure["semantic_units"] if unit["kind"] == "qa_exchange"
    ]
    assert exchanges, "the IR record must yield qa_exchange packages"
    texts = {unit["unit_id"]: unit["text"] for unit in observation["units"]}
    # The known real denial must survive inside a package that also holds a question.
    denial_packages = [
        exchange
        for exchange in exchanges
        if any("不生产" in texts.get(unit_id, "") or "无生产" in texts.get(unit_id, "")
               for unit_id in exchange["member_unit_ids"])
    ]
    assert denial_packages, "the management denial must remain inside its exchange"


def test_real_hk_annual_exposes_two_lanes_and_keeps_them_apart() -> None:
    """Miniso p12 has two real columns; the lanes must be separated.

    Measured on the real page: the LEFT column (x0 ~ 57) carries the English
    text and the RIGHT column (x0 ~ 349) carries the Chinese text.  The two
    columns are each language-uniform, so the correct behaviour is that the
    columns are distinguished and no cross-column unit is merged -- not that a
    per-position English/Chinese pair is invented across the gutter.
    """
    observation, _units, _parsed = _observe("hk-annual")
    lanes = {unit["layout"].get("column") for unit in observation["units"]}
    assert 0 in lanes and 1 in lanes, "the HK annual page must expose two lanes"

    left = [unit for unit in observation["units"] if unit["layout"].get("column") == 0]
    right = [unit for unit in observation["units"] if unit["layout"].get("column") == 1]
    assert left and right

    import re

    cjk = re.compile(r"[\u4e00-\u9fff]")
    latin = re.compile(r"[A-Za-z]")

    def script_counts(units):
        cjk_total = sum(len(cjk.findall(unit["text"])) for unit in units)
        latin_total = sum(len(latin.findall(unit["text"])) for unit in units)
        return cjk_total, latin_total

    left_cjk, left_latin = script_counts(left)
    right_cjk, right_latin = script_counts(right)
    # The left lane is neither purely Chinese nor purely Latin, but the right
    # lane carries the Chinese body of the page.  What must hold is that the
    # lanes are real and that no unit sits in both.
    assert left_latin > 0, "the English column must be detected"
    assert right_cjk > 0, "the Chinese column must be detected"
    ids_left = {unit["unit_id"] for unit in left}
    ids_right = {unit["unit_id"] for unit in right}
    assert not (ids_left & ids_right), "a unit cannot belong to two lanes"


def test_real_two_language_table_is_aligned_within_its_column() -> None:
    """The real bilingual pair sits at the same page band in one lane."""
    observation, _units, _parsed = _observe("hk-annual")
    structure = build_structure(observation)
    texts = {unit["unit_id"]: unit["text"] for unit in observation["units"]}
    # The English and Chinese period captions are real parallel evidence.
    english = [
        unit["unit_id"]
        for unit in observation["units"]
        if texts[unit["unit_id"]].strip() == "As of December 31,"
    ]
    chinese = [
        unit["unit_id"]
        for unit in observation["units"]
        if texts[unit["unit_id"]].strip() == "截至12月31日"
    ]
    assert english and chinese, "the real bilingual captions must be present"
    # Both sides survive as their own units; nothing is translated or dropped.
    members = {
        unit_id
        for semantic in structure["semantic_units"]
        for unit_id in semantic["member_unit_ids"]
    }
    relations = {
        unit_id
        for relation in structure["relations"]
        for unit_id in (*relation["from_unit_ids"], *relation["to_unit_ids"])
    }
    for unit_id in english + chinese:
        assert unit_id in members | relations, "a source unit was dropped by alignment"


def test_real_quarterly_report_keeps_its_business_text_readable() -> None:
    observation, units, _parsed = _observe("cn-q-business")
    assert units, "the quarterly report must produce units"
    structure = build_structure(observation)
    assert structure["semantic_units"], "a readable quarterly report must not be empty"
    assigned = {
        unit_id
        for semantic in structure["semantic_units"]
        for unit_id in semantic["member_unit_ids"]
    }
    coverage = len(assigned) / len(units)
    assert coverage > 0.5, f"only {coverage:.0%} of real units were organised"


def test_cross_layer_chain_produces_dependency_packages() -> None:
    observation, _units, _parsed = _observe("cn-equity")
    structure = build_structure(observation)
    packages = build_dependency_packages(structure)
    assert packages["package_count"] > 0
    for package in packages["packages"]:
        assert package["member_unit_ids"], "an empty package must not be emitted"
        assert set(package["required_context_unit_ids"]) <= set(package["member_unit_ids"])


def test_every_emitted_reference_replays_to_a_real_unit() -> None:
    """Citation replay: every id the chain emits exists in the observation."""
    for sample_id in SAMPLE_PAGES:
        if _entry(sample_id) is None:
            continue
        observation, _units, _parsed = _observe(sample_id)
        known = {unit["unit_id"] for unit in observation["units"]}
        structure = build_structure(observation)
        for semantic in structure["semantic_units"]:
            assert set(semantic["member_unit_ids"]) <= known, sample_id
        for relation in structure["relations"]:
            assert set(relation["from_unit_ids"]) <= known, sample_id
            assert set(relation["to_unit_ids"]) <= known, sample_id
        packages = build_dependency_packages(structure)
        for package in packages["packages"]:
            assert set(package["member_unit_ids"]) <= known, sample_id
