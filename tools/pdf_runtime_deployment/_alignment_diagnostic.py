"""Real-proposal alignment audit for the deployed runtime.

Child mode (deployed interpreter): one real offline SDK conversion of a
synthetic PDF, dumping the actual docling items. No mocks, no threshold
changes. Parent mode (repo interpreter): the production
``proposals_from_items``/``align_paragraphs`` consume those real items, and
every rejected proposal is classified against the real native structure.

This exists to answer one question honestly: does a real SDK proposal ever
pass the existing alignment on a normal wrapped-prose fixture, and if not,
which binding exactly fails.
"""
from __future__ import annotations

from argparse import ArgumentParser
from pathlib import Path
import json
import sys


def child_main(artifacts: str, pdf_path: Path) -> None:
    """Real SDK conversion, exactly the production converter shape."""
    from io import BytesIO

    from docling.document_converter import DocumentConverter, PdfFormatOption  # type: ignore[import-not-found]
    from docling.datamodel.base_models import InputFormat, DocumentStream  # type: ignore[import-not-found]
    from docling.datamodel.pipeline_options import PdfPipelineOptions  # type: ignore[import-not-found]
    from docling.datamodel.accelerator_options import AcceleratorOptions, AcceleratorDevice  # type: ignore[import-not-found]

    data = pdf_path.read_bytes()
    options = PdfPipelineOptions(do_ocr=False, do_table_structure=False, do_code_enrichment=False,
        do_formula_enrichment=False, generate_page_images=False, generate_picture_images=False,
        generate_parsed_pages=False, enable_remote_services=False, artifacts_path=Path(artifacts),
        document_timeout=120, accelerator_options=AcceleratorOptions(device=AcceleratorDevice.CPU, num_threads=4))
    converter = DocumentConverter(allowed_formats=[InputFormat.PDF],
        format_options={InputFormat.PDF: PdfFormatOption(pipeline_options=options)})
    items = []
    for page in (1, 2):
        converted = converter.convert(DocumentStream(name="source.pdf", stream=BytesIO(data)),
            page_range=(page, page), max_file_size=len(data), raises_on_error=False)
        if str(converted.status) != "ConversionStatus.SUCCESS":
            raise SystemExit(f"conversion failed on page {page}: {converted.status}")
        for item, _ in converted.document.iterate_items():
            if str(item.label) in {"text", "list_item"}:
                items.append({"page": page, "label": str(item.label), "text": getattr(item, "text", ""),
                              "provenance": [p.model_dump(mode="json") for p in getattr(item, "prov", [])]})
    print(json.dumps({"items": items, "docling_version": __import__("importlib.metadata",
                      fromlist=["version"]).version("docling")}, ensure_ascii=True))


def parent_main(receipts: Path, config_path: Path) -> None:
    sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))
    import subprocess
    import tempfile

    from company_wiki.resource_budget import WorkBudget
    from company_wiki.source_contract import source_id_for_sha256
    from company_wiki.source_catalog import narrative_evidence as native
    from company_wiki.source_catalog.narrative_pdf_paragraphs import align_paragraphs
    from company_wiki.source_catalog.narrative_pdf_enhancement import proposals_from_items
    from company_wiki.document_understanding.geometry_intent.reading import PdfReadingContext

    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from _synthetic_pdf import build_two_page_wrapped_prose_pdf  # type: ignore[import-not-found]

    config = json.loads(config_path.read_text(encoding="utf-8-sig"))
    scratch = Path(tempfile.mkdtemp(prefix="w22-align-"))
    try:
        data, digest = build_two_page_wrapped_prose_pdf(scratch / "synthetic.pdf")
        completed = subprocess.run([config["python"], "-I", "-X", "utf8", str(Path(__file__).resolve()),
                                    "--mode", "child", "--artifacts", config["artifacts"],
                                    "--pdf", str(scratch / "synthetic.pdf")],
                                   stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=300)
        if completed.returncode != 0:
            raise RuntimeError(completed.stderr.decode("utf-8", "replace")[-2000:])
        child = json.loads(completed.stdout.decode("utf-8"))
        source_id = source_id_for_sha256(digest)
        # Same parser arguments as the production 0.9.0 reading path: the
        # reading_layout projection is attached by the parser under this
        # selector, and alignment/triage consume exactly that projection.
        parsed = native.parse_pdf_bytes(data, source_id=source_id, source_sha256=digest,
                                        language="zh", selector_version="0.9.0",
                                        work_budget=WorkBudget(10_000_000), layout_max_seconds=15,
                                        reading_context=PdfReadingContext("合成验收样张", "annual_report", "zh"))
        proposals = proposals_from_items(parsed, child["items"], (1, 2))
        aligned = align_paragraphs(parsed, proposals, work_budget=WorkBudget(10_000_000))
        native_rows = []
        for unit in parsed.units:
            layout = dict(unit.metadata.get("reading_layout", {}).get("layout", {}))
            native_rows.append({"page": unit.coordinates.page_number,
                                "paragraph_index": unit.coordinates.paragraph_index,
                                "text": unit.raw_text, "bbox": layout.get("bbox"),
                                "font_size": layout.get("font_size"),
                                "page_size": (layout.get("page_width"), layout.get("page_height")),
                                "frame": layout.get("coordinate_frame")})
        proposal_rows = []
        for proposal in proposals:
            layout = dict(next(u for u in parsed.units if u.coordinates.page_number == proposal.page)
                          .metadata.get("reading_layout", {}).get("layout", {}))
            members = [u for u in parsed.units if u.coordinates.page_number == proposal.page
                       and u.unit_kind == "pdf_text_block"]
            cx_within = []
            for unit in members:
                box = unit.metadata.get("reading_layout", {}).get("layout", {}).get("bbox")
                if box:
                    cx, cy = (box[0] + box[2]) / 2, (box[1] + box[3]) / 2
                    cx_within.append({"text": unit.raw_text[:18], "center": (cx, cy),
                                      "inside_xy": (proposal.bbox[0] - 2 <= cx <= proposal.bbox[2] + 2,
                                                    proposal.bbox[1] - 2 <= cy <= proposal.bbox[3] + 2)})
            size = layout.get("font_size")
            tolerance = min(3., max(2., 0.25 * size)) if isinstance(size, (int, float)) and size > 0 else 2.
            joined = "".join("".join(unit.raw_text.split()) for unit in members)
            proposal_rows.append({
                "page": proposal.page, "text": proposal.text, "bbox": list(proposal.bbox),
                "page_size": (proposal.page_width, proposal.page_height),
                "frame": proposal.coordinate_frame,
                "joined_native_matches": joined == "".join("".join(proposal.text.split())),
                "centers": cx_within, "tolerance": tolerance})
        receipt = {"pdf_sha256": digest, "docling_version": child["docling_version"],
                   "native_units": native_rows, "sdk_items": child["items"],
                   "proposals": proposal_rows,
                   "accepted_groups": aligned.accepted_groups, "rejected_groups": aligned.rejected_groups,
                   "aligned_units": [unit.metadata.get("reading_layout", {}).get("paragraph_membership")
                                     for unit in aligned.parsed.units]}
    finally:
        import shutil
        shutil.rmtree(scratch, ignore_errors=True)
    receipts.mkdir(parents=True, exist_ok=True)
    (receipts / "w22-alignment-diagnostic.json").write_text(
        json.dumps(receipt, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"accepted_groups": receipt["accepted_groups"],
                      "rejected_groups": receipt["rejected_groups"],
                      "proposals": len(proposal_rows),
                      "receipt": str(receipts / "w22-alignment-diagnostic.json")}, ensure_ascii=True))


def main() -> None:
    arguments = dict(zip(sys.argv[1::2], sys.argv[2::2]))
    if arguments.get("--mode") == "child":
        child_main(arguments["--artifacts"], Path(arguments["--pdf"]))
        return
    parser = ArgumentParser(description=__doc__)
    parser.add_argument("--receipts", type=Path, required=True)
    parser.add_argument("--config", type=Path, required=True)
    options = parser.parse_args()
    parent_main(options.receipts, options.config)


if __name__ == "__main__":
    main()
