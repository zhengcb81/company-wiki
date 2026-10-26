"""Verify six frozen annual-report facts against original Sina page values.

This is a source-validation tool, not a production financial-table extractor.
PDF material is an existing PdfReading observation bound to an immutable local
SourceRef; the financial dataset remains supplied by its API/normalizer owner.
"""
import argparse
from decimal import Decimal
import gzip
import hashlib
import json
from pathlib import Path
import re
import sys


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cwp-root", type=Path, required=True)
    parser.add_argument("--observation", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise FileExistsError("choose a new receipt filename")
    sys.path.insert(0, str(args.cwp_root.resolve() / "src"))
    from company_wiki.source_catalog.financial_statements.normalize import normalize_page
    original = json.loads(gzip.decompress(args.observation.read_bytes()))
    metadata = original["metadata"]
    if not (metadata["security_id"] == "688012" and metadata["fiscal_year"] == 2025
            and metadata["period_end"] == "2025-12-31" and original["config_unchanged"]):
        raise RuntimeError("official source identity/period not proven")
    def page_text(page):
        return "\n".join(u["text"] for u in original["extracted_pages"][str(page)])
    for page, heading in [(138, "合并资产负债表"), (142, "合并利润表"), (146, "合并现金流量表")]:
        header = re.sub(r"\s+", "", page_text(page))
        if not all(text in header for text in (heading, "2025", "单位：元", "币种：人民币")):
            raise RuntimeError("consolidation/currency/scale/column-year header not established")
    golden = [
        ("lrb", "income_statement", "BIZTOTINCO", "营业总收入", 142, "12384638268.11"),
        ("lrb", "income_statement", "BIZTOTCOST", "营业总成本", 143, "11006675861.27"),
        ("fzb", "balance_sheet", "CURFDS", "货币资金", 138, "7951400258.31"),
        ("fzb", "balance_sheet", "TOTASSET", "资产总计", 139, "29846018981.43"),
        ("llb", "cash_flow", "LABORGETCASH", "销售商品、提供劳务收到的现金", 146, "14122161977.48"),
        ("llb", "cash_flow", "MANANETR", "经营活动产生的现金流量净额", 147, "2295352919.08"),
    ]
    capture = args.cwp_root / "docs/plans/w19-sina-statements-2026-10-25/inputs/research/capture"
    checks = []
    for source, kind, field, label, page, expected in golden:
        amount = f"{Decimal(expected):,.2f}"
        matches = [u for u in original["extracted_pages"][str(page)]
                   if label in re.sub(r"\s+", "", u["text"]) and amount in u["text"]]
        if len(matches) != 1:
            raise RuntimeError(f"frozen official oracle not unique for {field}")
        raw = gzip.decompress((capture / f"sh688012-{source}-type0-page1-num10.json.gz").read_bytes())
        report = next(r for r in normalize_page(raw, statement_type=kind, page_number=1).reports
                      if r.period_end == "2025-12-31" and r.consolidation == "consolidated")
        row = next(r for r in report.rows if r.provider_field == field)
        if not (Decimal(row.value_decimal) == Decimal(expected) and report.currency == "CNY"
                and row.unit is None and row.scale is None):
            raise RuntimeError(f"value/currency or unknown-unit contract mismatch for {field}")
        at = re.sub(r"\s+", "", matches[0]["text"]).index(label)
        excerpt = re.sub(r"\s+", "", matches[0]["text"])[at:at + len(label) + 65]
        checks.append({"statement_type": kind, "provider_field": field, "label": label,
            "expected_official": expected, "actual_sina": row.value_decimal,
            "currency": report.currency, "api_unit": row.unit, "api_scale": row.scale,
            "official_unit": "CNY", "official_scale": 1,
            "unit_validation": "exact numeric magnitude equals official yuan amounts in these six samples; provider per-row unit remains unspecified",
            "period_end": report.period_end, "consolidation": report.consolidation,
            "period_semantics": "instant" if kind == "balance_sheet" else "annual_duration",
            "official_locator": matches[0]["coordinates"], "official_unit_id": matches[0]["unit_id"],
            "official_excerpt": excerpt, "sina_page_sha256": hashlib.sha256(raw).hexdigest(),
            "sina_json_pointer": row.json_pointer, "pass": True})
    receipt = {"schema_version": "w19-official-six-values/1", "passed": True,
        "official_source_ref": original["source_ref"], "official_metadata": metadata,
        "reading_recipe": original["recipe"],
        "native_observation_gzip_sha256": hashlib.sha256(args.observation.read_bytes()).hexdigest(),
        "checks": checks, "new_downloads": 0, "new_paid_calls": 0,
        "unit_limit": "Do not generalize per-row units from display precision or these samples; production preserves None for unproven units/scales.",
        "scope": "independent original six-value validation; not RF adoption or arbitrary historical PIT"}
    with args.output.open("x", encoding="utf-8") as stream:
        json.dump(receipt, stream, ensure_ascii=False, indent=2)
        stream.write("\n")
    print(json.dumps({"passed": True, "checks": len(checks), "new_downloads": 0}))


if __name__ == "__main__":
    main()
