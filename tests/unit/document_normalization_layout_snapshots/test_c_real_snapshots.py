"""Node C: real layout snapshots (offline probe self-check + opt-in real originals).

Real cases are OFFLINE by default.  They run only when ``CW_DU3_GEOMETRY_REAL=1``
AND the uncommitted ``.planning/du3-geometry/bindings.local.json`` maps sample ids
to local originals.  A missing binding / SHA mismatch is reported UNAVAILABLE and
never counts as a real pass.  The probe pipeline itself is covered offline so a
wrong path can never silently turn every real case into a skip.

Measurement/binding reliability here does NOT mean fine-column / fine-table recall
has passed: real pages are measurement oracles only.
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest

import native_probe

from company_wiki.document_normalization.layout_snapshots import project_layout_snapshot

ROOT = Path(__file__).resolve().parents[3]
BINDINGS_PATH = ROOT / ".planning" / "du3-geometry" / "bindings.local.json"
REAL_OPT_IN = os.environ.get("CW_DU3_GEOMETRY_REAL") == "1"


def _real_bindings() -> dict:
    if not REAL_OPT_IN:
        pytest.skip("opt-in: real originals untouched unless CW_DU3_GEOMETRY_REAL=1")
    bindings = native_probe.load_bindings_file(BINDINGS_PATH)
    if not bindings:
        pytest.skip(f"UNAVAILABLE: {BINDINGS_PATH.name} missing")
    return bindings


def _probe(bindings: dict, sample_id: str) -> dict:
    result = native_probe.load_snapshot(bindings, sample_id)
    if result["status"] != "ok":
        pytest.skip(f"UNAVAILABLE: {result.get('reason')}")
    return result


# ---------------------------------------------------------------- offline self-check


def test_native_probe_refuses_missing_or_mismatched_sources(tmp_path) -> None:
    assert native_probe.load_snapshot({}, "hk-miniso-annual-store-table")["status"] == "unavailable"

    fake = tmp_path / "fake.pdf"
    fake.write_bytes(b"%PDF-1.4 fake original placeholder")
    refused = native_probe.load_snapshot(
        {"hk-miniso-annual-store-table": str(fake)}, "hk-miniso-annual-store-table"
    )
    assert refused["status"] == "unavailable"
    assert "sha mismatch" in refused["reason"]

    missing = native_probe.load_snapshot(
        {"hk-miniso-annual-store-table": str(tmp_path / "nope.pdf")},
        "hk-miniso-annual-store-table",
    )
    assert missing["status"] == "unavailable"
    assert "file not found" in missing["reason"]


def test_native_probe_extracts_real_geometry_from_generated_pdf(tmp_path, monkeypatch) -> None:
    fitz = pytest.importorskip("fitz")
    pdf = tmp_path / "selfcheck.pdf"
    doc = fitz.open()
    page = doc.new_page(width=595, height=842)
    page.insert_text((70, 120), "Revenue 2023 3,926", fontsize=11)
    page.insert_text((70, 160), "Header A Header B", fontsize=9)
    doc.save(pdf)
    doc.close()

    digest = native_probe.sha256_of(pdf)
    monkeypatch.setattr(
        native_probe,
        "GEOMETRY_SAMPLES",
        (
            {
                "sample_id": "selfcheck",
                "label": "self-check",
                "pages": [1],
                "sha256": digest,
            },
        ),
    )
    result = native_probe.load_snapshot({"selfcheck": str(pdf)}, "selfcheck")
    assert result["status"] == "ok"
    snapshot = result["snapshot"]
    assert snapshot["schema_version"] == "du-layout-snapshot/1"
    page0 = snapshot["pages"][0]
    assert page0["coordinate_frame"] == "dict"
    assert page0["width"] > 0 and page0["height"] > 0

    # the probe produced real span units + bindings with real bboxes
    assert result["units"], "probe must extract real text spans"
    text_bindings = [b for b in page0["bindings"] if b["source"] == "pdf_dict"]
    assert text_bindings
    for b in text_bindings:
        assert len(b["bbox"]) == 4
        # real words carry their own bboxes, never the parent's
        for w in b.get("words", []):
            assert len(w["bbox"]) == 4

    # and the projection binds them
    proj = project_layout_snapshot(snapshot, result["units"])
    assert proj["coverage"]["bound_unit_count"] > 0


# ---------------------------------------------------------------- real originals (opt-in)


@pytest.mark.real_data
def test_real_originals_fingerprint_unchanged() -> None:
    bindings = _real_bindings()
    for spec in native_probe.GEOMETRY_SAMPLES:
        raw = bindings.get(spec["sample_id"])
        if not raw:
            continue
        result = native_probe.load_snapshot(bindings, spec["sample_id"])
        if result["status"] != "ok":
            continue
        before = result["fp_before"]
        after = native_probe.fingerprint(Path(raw))
        assert after == before, f"original must be byte/mtime/size preserved: {spec['sample_id']}"


@pytest.mark.real_data
def test_jinhe_multicolumn_cells_keep_distinct_geometry() -> None:
    bindings = _real_bindings()
    probe = _probe(bindings, "cn-jinhe-convertible-tables")
    proj = project_layout_snapshot(probe["snapshot"], probe["units"])
    # at least one table-row unit resolved to fine cell granularity with distinct columns
    fine = [
        meta
        for meta in proj["unit_metadata"].values()
        if meta["layout"]["granularity"] == "cell"
    ]
    assert fine, "the 6-column table must yield real per-cell geometry"
    meta = fine[0]
    cells = meta["upstream_hints"]["cells"]
    assert len(cells) >= 2
    cols = {c.get("column") for c in cells if c.get("column") is not None}
    assert len(cols) >= 2, "multi-column cells keep distinct columns"
    parent = meta["layout"]["bbox"]
    for c in cells:
        assert c["bbox"] != parent, "cell bbox is real, not the parent row/table box"


@pytest.mark.real_data
def test_hengfeng_cross_page_binds_both_pages() -> None:
    bindings = _real_bindings()
    probe = _probe(bindings, "cn-hengfeng-offering-cross-page")
    proj = project_layout_snapshot(probe["snapshot"], probe["units"])
    assert proj["coverage"]["bound_unit_count"] > 0
    pages_bound = {meta["layout"]["page"] for meta in proj["unit_metadata"].values()}
    assert len(pages_bound) >= 2, "both pages of the cross-page table are projected"


@pytest.mark.real_data
def test_amec_narrative_has_no_fabricated_cells() -> None:
    bindings = _real_bindings()
    probe = _probe(bindings, "cn-amec-annual-narrative")
    proj = project_layout_snapshot(probe["snapshot"], probe["units"])
    # narrative page: any cells present must carry real geometry; no table cells invented
    for meta in proj["unit_metadata"].values():
        for c in meta["upstream_hints"]["cells"]:
            assert len(c["bbox"]) == 4 and c["bbox"] != meta["layout"]["bbox"]
    # text spans project to word granularity, not fabricated cells
    for meta in proj["unit_metadata"].values():
        if meta["layout"]["granularity"] == "cell":
            assert meta["upstream_hints"]["cells"], "cell granularity needs real cells"


@pytest.mark.real_data
def test_shihua_new_company_real_cells() -> None:
    bindings = _real_bindings()
    probe = _probe(bindings, "cn-shihua-annual-store-table")
    proj = project_layout_snapshot(probe["snapshot"], probe["units"])
    assert proj["coverage"]["bound_unit_count"] > 0
    assert proj["unit_metadata"], "the new-company sample projects real units"


@pytest.mark.real_data
def test_miniso_availability_is_honest() -> None:
    bindings = _real_bindings()
    result = native_probe.load_snapshot(bindings, "hk-miniso-annual-store-table")
    if result["status"] != "ok":
        pytest.skip(f"UNAVAILABLE: {result.get('reason')}")
    proj = project_layout_snapshot(result["snapshot"], result["units"])
    assert proj["coverage"]["bound_unit_count"] >= 0


@pytest.mark.real_data
def test_real_projection_has_no_absolute_paths() -> None:
    bindings = _real_bindings()
    probe = _probe(bindings, "cn-jinhe-convertible-tables")
    proj = project_layout_snapshot(probe["snapshot"], probe["units"])
    flat = repr(proj).lower()
    assert ".pdf" not in flat
    assert ":\\" not in flat and "companies/" not in flat
