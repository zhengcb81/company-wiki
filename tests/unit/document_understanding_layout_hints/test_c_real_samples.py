"""Node C: real-original spot checks (offline-opt-in) plus probe-pipeline guards.

The real cases are OFFLINE by default.  They run only when the operator sets
``CW_DU2_LAYOUT_REAL=1`` AND the uncommitted ``.planning/du2-layout/bindings.local.json``
maps sample ids to local originals.  A missing binding is reported as
UNAVAILABLE/SKIP and never counts as a real pass.

The probe pipeline itself is covered by offline tests so a wrong path can never
silently turn every real case into a skip.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

import real_probe
from checks import groups_of_kind

from company_wiki.document_understanding.layout_hints import derive_layout_hints

ROOT = Path(__file__).resolve().parents[3]
BINDINGS_PATH = ROOT / ".planning" / "du2-layout" / "bindings.local.json"
REAL_OPT_IN = os.environ.get("CW_DU2_LAYOUT_REAL") == "1"


def _real_bindings() -> dict:
    if not REAL_OPT_IN:
        pytest.skip("opt-in: real originals are not touched unless CW_DU2_LAYOUT_REAL=1")
    if not BINDINGS_PATH.is_file():
        pytest.skip(f"UNAVAILABLE: {BINDINGS_PATH} missing")
    data = json.loads(BINDINGS_PATH.read_text(encoding="utf8"))
    if not isinstance(data, dict):
        pytest.skip("UNAVAILABLE: bindings.local.json must map sample_id -> absolute path")
    return {str(k): str(v) for k, v in data.items()}


def _probe(bindings: dict, sample_id: str, mode: str) -> dict:
    result = real_probe.load_probe_input(bindings, sample_id, mode=mode)
    if result["status"] != "ok":
        pytest.skip(f"UNAVAILABLE: {result.get('reason')}")
    return result


def _units_by_text(observation: dict, text: str) -> list[dict]:
    return [
        unit
        for page in observation["pages"]
        for unit in page["units"]
        if unit["text"].strip() == text
    ]


def _row_with(result: dict, unit_id: str) -> list[dict]:
    return [
        row
        for row in groups_of_kind(result, "table_row")
        if unit_id in row["member_unit_ids"]
    ]


def _cell_of(row: dict, unit_id: str) -> dict | None:
    for cell in row["cells"]:
        if unit_id in cell["member_unit_ids"]:
            return cell
    return None


# ------------------------------------------------------------------ offline guards


def test_probe_pipeline_refuses_missing_or_mismatched_sources(tmp_path, monkeypatch) -> None:
    assert real_probe.load_probe_input({}, "hk-miniso-annual-store-table")["status"] == "unavailable"

    fake = tmp_path / "fake.pdf"
    fake.write_bytes(b"%PDF-1.4 fake original placeholder")
    bindings = {"hk-miniso-annual-store-table": str(fake)}
    refused = real_probe.load_probe_input(bindings, "hk-miniso-annual-store-table")
    assert refused["status"] == "unavailable"
    assert "sha mismatch" in refused["reason"]

    missing = real_probe.load_probe_input(
        {"hk-miniso-annual-store-table": str(tmp_path / "nope.pdf")},
        "hk-miniso-annual-store-table",
    )
    assert missing["status"] == "unavailable"
    assert "file not found" in missing["reason"]


def test_probe_units_carry_probe_ids_and_no_locator(tmp_path, monkeypatch) -> None:
    fitz = pytest.importorskip("fitz")
    pdf = tmp_path / "tiny.pdf"
    doc = fitz.open()
    page = doc.new_page(width=595, height=842)
    page.insert_text((70, 120), "2023 3,926 4,386", fontsize=11)
    page.insert_text((70, 160), "Header A Header B", fontsize=9)
    doc.save(pdf)
    doc.close()

    digest = real_probe.sha256_of(pdf)
    monkeypatch.setattr(
        real_probe,
        "PROBE_SAMPLES",
        (
            {
                "sample_id": "self-check-sample",
                "label": "self-check",
                "pages": [1],
                "sha256": digest,
            },
        ),
    )
    bindings = {"self-check-sample": str(pdf)}

    span = real_probe.load_probe_input(bindings, "self-check-sample", mode="span")
    assert span["status"] == "ok"
    units = span["observation"]["pages"][0]["units"]
    assert units and all(unit["locator"] is None for unit in units)
    assert all(unit["unit_id"].startswith("probe-self-check-sample-p1-") for unit in units)

    collapsed = real_probe.load_probe_input(bindings, "self-check-sample", mode="row_collapse")
    assert collapsed["status"] == "ok"
    collapsed_units = collapsed["observation"]["pages"][0]["units"]
    assert 0 < len(collapsed_units) <= len(units)  # rows merge spans together

    # probe ids must map back to page coordinates as evidence
    mapping = {item["unit_id"]: item for item in span["probe_mapping"]}
    assert set(mapping) == {unit["unit_id"] for unit in units}
    assert all(item["page"] == 1 and len(item["bbox"]) == 4 for item in mapping.values())


# ------------------------------------------------------- real samples (opt-in)


@pytest.mark.real_data
def test_miniso_store_table_keeps_columns_rows_and_context() -> None:
    bindings = _real_bindings()
    probe = _probe(bindings, "hk-miniso-annual-store-table", "span")
    result = derive_layout_hints(probe["observation"])

    total_row_units = _units_by_text(probe["observation"], "6,413") + _units_by_text(probe["observation"], "7,504")
    assert total_row_units, "probe sampling must find the MINISO total row"
    total_rows = _row_with(result, total_row_units[0]["unit_id"])
    assert total_rows, "the store-count total row must stay a table row (not a single degenerate cell)"

    mainland = _units_by_text(probe["observation"], "3,926")
    assert mainland, "probe sampling must find the mainland store count"
    row = _row_with(result, mainland[0]["unit_id"])
    assert row
    cell_2023 = _cell_of(row[0], mainland[0]["unit_id"])
    assert cell_2023 is not None and isinstance(cell_2023["column"], int)

    # 2023 and 2024 columns must remain two different quantities
    others = [uid for uid in row[0]["member_unit_ids"] if uid != mainland[0]["unit_id"]]
    columns = [cell_2023["column"]]
    for uid in others:
        cell = _cell_of(row[0], uid)
        if cell is not None and isinstance(cell["column"], int):
            columns.append(cell["column"])
    assert len(set(columns)) >= 2

    # no single-cell degeneration on sufficient input
    region_id = row[0]["parent_table_id"]
    rows = [r for r in groups_of_kind(result, "table_row") if r["parent_table_id"] == region_id]
    assert len(rows) >= 6
    assert all(r["cells"] for r in rows)

    # period/header context must travel with the quantity rows
    context_ids = set(row[0]["required_context_unit_ids"])
    assert context_ids
    context_text = " ".join(
        unit["text"]
        for page in probe["observation"]["pages"]
        for unit in page["units"]
        if unit["unit_id"] in context_ids
    )
    assert ("2023" in context_text) or ("2024" in context_text) or ("截至" in context_text) or ("As of" in context_text)

    codes = {diag["code"] for diag in result["diagnostics"]}
    assert "NEEDS_UPSTREAM_GRANULARITY" not in codes


@pytest.mark.real_data
def test_miniso_current_production_granularity_is_reported_not_faked() -> None:
    bindings = _real_bindings()
    probe = _probe(bindings, "hk-miniso-annual-store-table", "row_collapse")
    result = derive_layout_hints(probe["observation"])
    codes = {diag["code"] for diag in result["diagnostics"]}
    assert "NEEDS_UPSTREAM_GRANULARITY" in codes
    for row in groups_of_kind(result, "table_row"):
        assert row["cells"] == [] or all(cell["column"] is None for cell in row["cells"])


@pytest.mark.real_data
def test_hengfeng_cross_page_project_tables() -> None:
    bindings = _real_bindings()
    probe = _probe(bindings, "cn-hengfeng-offering-cross-page", "span")
    result = derive_layout_hints(probe["observation"])

    regions = groups_of_kind(result, "table_region")
    assert len(regions) >= 2, "overview table (p61) and investment table (p62) must both be found"

    # the p62 investment table keeps its unit line and header as context
    unit_line = _units_by_text(probe["observation"], "单位：万元")
    assert unit_line
    context_rels = [rel for rel in result["relations"] if rel["kind"] in {"caption_for", "header_for"}]
    assert context_rels

    # any claimed cross-page continuation must cite page gap and column/header evidence
    for rel in result["relations"]:
        if rel["kind"] == "continuation":
            assert any(b.startswith("page_gap=") for b in rel["basis"]), rel
            assert any(b.startswith(("column_alignment", "repeated_header")) for b in rel["basis"]), rel

    # quantities on the investment table keep separate columns
    amount = _units_by_text(probe["observation"], "29,779.00")
    assert amount
    rows: list[dict] = []
    matched_id = None
    for candidate in amount:
        found = _row_with(result, candidate["unit_id"])
        if found:
            rows = found
            matched_id = candidate["unit_id"]
            break
    assert rows, "the investment-table amount must stay a table row (the narrative mention is not a row)"
    cell = _cell_of(rows[0], matched_id)
    assert cell is not None and isinstance(cell["column"], int)


@pytest.mark.real_data
def test_jinhe_second_company_layout_generalizes() -> None:
    bindings = _real_bindings()
    probe = _probe(bindings, "cn-jinhe-convertible-tables", "span")
    result = derive_layout_hints(probe["observation"])

    # 6-column fundraising table: two amounts must land in different columns
    invest = _units_by_text(probe["observation"], "26,527.49")
    raised = _units_by_text(probe["observation"], "20,000.00")
    assert invest and raised
    row_invest = _row_with(result, invest[0]["unit_id"])
    row_raised = _row_with(result, raised[0]["unit_id"])
    assert row_invest and row_raised
    cell_a = _cell_of(row_invest[0], invest[0]["unit_id"])
    cell_b = _cell_of(row_raised[0], raised[0]["unit_id"])
    assert cell_a is not None and cell_b is not None
    assert cell_a["column"] != cell_b["column"]

    for rel in result["relations"]:
        if rel["kind"] == "continuation":
            assert any(b.startswith("page_gap=") for b in rel["basis"]), rel
            assert any(b.startswith(("column_alignment", "repeated_header")) for b in rel["basis"]), rel
            # the p224 continuation has no repeated header: its leading bands are
            # continuation rows, so no fresh header may be claimed for it
            if "repeated_header" not in rel["basis"]:
                target = rel["to_group_id"]
                assert not [
                    item
                    for item in result["relations"]
                    if item["kind"] == "header_for" and item["to_group_id"] == target
                ], "continued table without header evidence must not claim a fresh header"

    # at least one region on the second page shows the continuation problem honestly
    codes = {diag["code"] for diag in result["diagnostics"]}
    assert result["coverage"]["processed_unit_count"] > 0
    assert "WORK_BUDGET_EXCEEDED" not in codes


@pytest.mark.real_data
def test_amec_narrative_page_is_not_a_table() -> None:
    bindings = _real_bindings()
    probe = _probe(bindings, "cn-amec-annual-narrative", "span")
    result = derive_layout_hints(probe["observation"])
    assert groups_of_kind(result, "table_region") == [], "inline narrative numbers must not become a table"
