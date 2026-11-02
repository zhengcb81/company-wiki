"""Small original-ID fixtures, not correct-section or heading-hint injections.

These are synthetic parser observations, not byte-attested PDF originals. Native
geometry and character offsets are reproducible from each declared block. The
real H1 source and downstream citation/model checks remain separate acceptance.
"""
from __future__ import annotations

from dataclasses import dataclass, replace
from hashlib import sha256

from company_wiki.document_understanding.observation_adapter import build_observation
from company_wiki.document_understanding.pipeline import understand_units
from company_wiki.resource_budget import WorkBudget
from company_wiki.source_catalog.narrative_document import DocumentStructure
from company_wiki.source_catalog.narrative_evidence import _make_unit
from company_wiki.source_catalog.narrative_native_ranges import build_native_page_view
from company_wiki.source_catalog.narrative_pdf_paragraphs import ParagraphProposal, align_paragraphs
from company_wiki.source_contract import EvidenceCoordinates, source_id_for_sha256


@dataclass(frozen=True)
class Row:
    key: str
    text: str
    page: int = 1
    block: int | None = None
    box: tuple[float, float, float, float] | None = None
    kind: str = "pdf_text_block"
    table_index: int | None = None


def source(rows: tuple[Row, ...], *, geometry=True, column=0):
    assert len({row.key for row in rows}) == len(rows)
    digest = sha256("\n".join(row.text for row in rows).encode("utf-8")).hexdigest()
    sid = source_id_for_sha256(digest)
    positions, prepared, blocks = {}, [], {}
    for row in rows:
        position = positions.get(row.page, 0)
        positions[row.page] = position + 1
        block = position if row.block is None else row.block
        box = row.box or (72., 80. + 60. * position, 528., 108. + 60. * position)
        prepared.append((row, position, block, box))
        key = row.page, block
        if key in blocks:
            assert blocks[key][0] == box, "fragments of one block keep its observed box"
            blocks[key][1].append(row.text)
        else:
            blocks[key] = (box, [row.text])
    views = {
        page: build_native_page_view([
            (block, box, "\n".join(texts))
            for (actual_page, block), (box, texts) in blocks.items() if actual_page == page
        ]) for page in positions
    }
    offsets, units, owned = {}, [], {}
    for row, position, block, box in prepared:
        key = row.page, block
        block_text = "\n".join(blocks[key][1])
        start = offsets.get(key, 0)
        metadata = {
            "pdf_block": block,
            "block_sha256": sha256(block_text.encode("utf-8")).hexdigest(),
            "block_char_start": start,
            "block_char_end": start + len(row.text),
            "native_source_view": views[row.page],
        }
        if row.table_index is not None:
            assert row.kind.startswith("html_"), "HTML association is metadata, not a second locator kind"
            metadata["table_index"] = row.table_index
        if geometry:
            layout = {"bbox": list(box), "page_width": 600, "page_height": 800,
                      "coordinate_frame": "dict", "rotation": 0}
            if column is not None:
                layout["column"] = column
            metadata["reading_layout"] = {"layout": layout, "upstream_hints": {"font_runs": [{
                "char_start": 0, "char_end": len(row.text), "font_size": 12,
                "font_weight": "regular", "coordinate_frame": "dict",
                "source": "pdf_native_single_textpage", "char_alignment": "exact",
            }]}}
        unit = _make_unit(
            source_id=sid, parser_version="0.1.1",
            coordinates=EvidenceCoordinates(page_number=row.page, paragraph_index=position),
            raw_text=row.text, unit_kind=row.kind, source_role="company_filing",
            language="zh", metadata=metadata,
        )
        assert unit.raw_text == row.text
        assert "heading_level" not in unit.metadata and "heading_like" not in unit.metadata
        units.append(unit)
        owned[row.key] = unit
        offsets[key] = start + len(row.text) + 1
    pages = max(positions)
    return DocumentStructure(sid, digest, "zh", tuple(units), page_count=pages,
                             pages_read=pages, mime_type="application/pdf"), owned


def snapshot(parsed):
    return tuple((unit.unit_id, unit.source_id, unit.raw_text, unit.text_sha256,
                  unit.coordinates, unit.coordinates.locator(), repr(unit.metadata))
                 for unit in parsed.units)


def observation(parsed):
    before = snapshot(parsed)
    result = build_observation(parsed.units, source_id=parsed.source_id,
                               source_sha256=parsed.source_sha256, language="zh",
                               declared_kind="semi_annual_report", mime_type=parsed.mime_type)
    assert snapshot(parsed) == before
    return result


def run_pipeline(parsed, *, deferred_pages=(), budget=None):
    before = snapshot(parsed)
    contexts = {}
    result = understand_units(
        parsed.units, source_id=parsed.source_id, source_sha256=parsed.source_sha256,
        title="中性半年报", declared_kind="semi_annual_report", mime_type=parsed.mime_type or "text/plain",
        language=parsed.language, native_scan="complete", deferred_pages=deferred_pages,
        work_budget=budget if budget is not None else WorkBudget(16_000_000),
        _native_contexts=contexts,
    )
    assert snapshot(parsed) == before, "source text, IDs, locators and metadata are immutable"
    assert result["source_ref"]["source_id"] == parsed.source_id
    known = {unit.unit_id for unit in parsed.units}
    for section in result.get("structure", {}).get("sections", ()):
        assert set(section["heading_unit_ids"]) | set(section["body_unit_ids"]) <= known
    return result, contexts


def inherited_heading_ids(result, target):
    """Inspect actual section ancestry; not a downstream citation-view claim."""
    sections = result["structure"]["sections"]
    matches = [section for section in sections if target.unit_id in section["body_unit_ids"]]
    assert len(matches) == 1, "the original body must remain addressable in one real section"
    index = {section["section_id"]: section for section in sections}
    current, visited, context = matches[0], set(), set()
    while current is not None:
        assert current["section_id"] not in visited, "section ancestry must be acyclic"
        visited.add(current["section_id"])
        context.update(current["heading_unit_ids"])
        parent = current.get("parent_id")
        assert parent is None or parent in index
        current = index.get(parent)
    return context


def aligned_source_members_without_geometry():
    """Generate existing membership proof via its actual producer, then omit boxes."""
    parsed, _owned = source((
        Row("intro", "备注18：乙方关于产品服务范围的说明："),
        Row("body", "“1、乙方的检测平台已完成升级。”"),
    ))
    proposal = ParagraphProposal(
        source_id=parsed.source_id, source_sha256=parsed.source_sha256, page=1,
        text=" ".join(unit.raw_text for unit in parsed.units), bbox=(72., 80., 528., 168.),
        page_width=600, page_height=800,
    )
    aligned = align_paragraphs(parsed, (proposal,), work_budget=WorkBudget(100_000))
    assert aligned.accepted_groups == 1, "the fixture must have real producer-validated members"
    stripped = tuple(replace(unit, metadata={
        **{key: value for key, value in unit.metadata.items() if key != "native_source_view"}, "reading_layout": {
        "paragraph_membership": unit.metadata["reading_layout"]["paragraph_membership"],
    }}) for unit in aligned.parsed.units)
    for unit in stripped:
        assert "layout" not in unit.metadata["reading_layout"]
    without_geometry = replace(aligned.parsed, units=stripped)
    assert tuple(row[:6] for row in snapshot(without_geometry)) == tuple(
        row[:6] for row in snapshot(parsed))
    return without_geometry, dict(zip(("intro", "body"), stripped, strict=True))
