from __future__ import annotations

import hashlib
import json
from pathlib import Path

from company_wiki.source_catalog.narrative_evidence import parse_pdf
from company_wiki.source_contract import source_id_for_sha256


ROOT = Path(__file__).resolve().parents[5]
SOURCE = ROOT / "companies/药明康德/raw/financial_reports/药明康德：2025年年度报告.pdf"
EXPECTED_SHA256 = "7f1431d66eae399d4b35639bb650e23287c7f52dacbb47b4b4a197fb5026d6a2"
PAGE = 235
RECEIPT = Path(__file__).with_name("replay-receipt.json")


def main() -> int:
    digest = hashlib.sha256(SOURCE.read_bytes()).hexdigest()
    if digest != EXPECTED_SHA256:
        raise RuntimeError(f"source SHA mismatch: {digest}")

    parsed = parse_pdf(
        SOURCE,
        source_id=source_id_for_sha256(digest),
        source_sha256=digest,
        selector_version="0.9.0",
        table_pages=[PAGE],
    )
    table_rows = [
        unit
        for unit in parsed.units
        if unit.coordinates.page_number == PAGE and unit.unit_kind == "pdf_table_row"
    ]
    if len(table_rows) != 4:
        raise RuntimeError(f"expected 4 table rows, received {len(table_rows)}")

    headers = tuple(table_rows[0].metadata.get("table_headers", ()))
    if len(headers) != 7 or not all(
        tuple(unit.metadata.get("table_headers", ())) == headers for unit in table_rows
    ):
        raise RuntimeError("expected one shared seven-column header across all rows")

    row_labels = [tuple(unit.metadata.get("row_cells", ()))[0] for unit in table_rows]
    if row_labels != ["项目", "WuXi ATU 业务", "WuXi Testing 部分业务", "合计"]:
        raise RuntimeError(f"unexpected table row labels: {row_labels!r}")

    page_text = [
        unit.raw_text
        for unit in parsed.units
        if unit.coordinates.page_number == PAGE and unit.unit_kind == "pdf_text_block"
    ]
    unit_currency_visible = any("单位：元" in text and "币种：人民币" in text for text in page_text)
    if not unit_currency_visible:
        raise RuntimeError("unit/currency context not found on the page")

    row_metadata = table_rows[0].metadata
    unit_currency_bound_to_rows = any(
        token in str(key).lower() for key in row_metadata for token in ("currency", "unit")
    )
    receipt = {
        "schema_version": "st-a02-pdf-table-source-check/1",
        "status": "PASS_STRUCTURED_TABLE_AVAILABLE_CONTEXT_SEPARATE",
        "source_sha256": digest,
        "physical_page": PAGE,
        "table_rows": len(table_rows),
        "header_columns": len(headers),
        "row_labels": row_labels,
        "page_unit_currency_context_visible": unit_currency_visible,
        "unit_currency_bound_to_table_row_metadata": unit_currency_bound_to_rows,
        "raw_financial_values_stored_in_receipt": False,
        "model_request_sent": False,
        "download_performed": False,
    }
    with RECEIPT.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(receipt, stream, ensure_ascii=False, indent=2)
        stream.write("\n")
    print(json.dumps(receipt, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
