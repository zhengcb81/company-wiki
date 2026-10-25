"""Neutral RED: pure normalization of frozen Sina responses (W19 A node).

Every expectation below is derived from the frozen fixtures byte-exact — not
from the implementation. Numbers/units/kinds are the ones the provider sent.
"""

from __future__ import annotations

import json

import pytest

from company_wiki.source_catalog.financial_statements import normalize

from . import fixtures


def _page(statement_source: str, page: int) -> bytes:
    return fixtures.fixture_bytes(
        f"sh688012-{statement_source}-type0-page{page}-num10.json.gz"
    )


class TestRealIncomeStatementPage:
    def test_period_metadata_is_preserved_verbatim(self):
        page = normalize.normalize_page(
            _page("lrb", 1), statement_type="income_statement", page_number=1
        )
        assert page.page_had_data is True
        assert page.report_count == 36
        report = page.report_by_period("20260630")
        assert report is not None
        assert report.statement_type == "income_statement"
        assert report.period_end == "2026-06-30"
        assert report.period_kind == "semi_annual"
        assert report.period_start is None
        assert report.consolidation == "consolidated"
        assert report.currency == "CNY"
        assert report.provider_rType == "合并期末"
        assert report.provider_publish_date == "20260820"
        assert report.provider_update_time == "1787134205"
        assert report.provider_is_audit == "未审计"
        assert report.provider_data_source == "定期报告"

    def test_rows_keep_original_order_labels_and_exact_decimals(self):
        page = normalize.normalize_page(
            _page("lrb", 1), statement_type="income_statement", page_number=1
        )
        report = page.report_by_period("20260630")
        assert len(report.rows) == 77
        first = report.rows[0]
        assert first.provider_field == "BIZTOTINCO"
        assert first.label == "营业总收入"
        assert first.raw_value == "6691287327.670000"
        assert first.value_decimal == "6691287327.670000"
        assert first.value_kind == "numeric"
        assert (
            first.json_pointer
            == "/result/data/report_list/20260630/data/0/item_value"
        )
        # BIZTOTINCO and BIZINCO stay two distinct rows (never merged).
        fields = [row.provider_field for row in report.rows[:2]]
        assert fields == ["BIZTOTINCO", "BIZINCO"]

    def test_null_value_is_not_zero_nor_empty(self):
        page = normalize.normalize_page(
            _page("lrb", 1), statement_type="income_statement", page_number=1
        )
        report = page.report_by_period("20260630")
        row = report.row_by_field("INTEINCO")
        assert row is not None
        assert row.raw_value is None
        assert row.value_decimal is None
        assert row.value_kind == "null"

    def test_eps_unit_evidence_and_precision_is_not_a_unit(self):
        page = normalize.normalize_page(
            _page("lrb", 1), statement_type="income_statement", page_number=1
        )
        report = page.report_by_period("20260630")
        eps = report.row_by_field("BASICEPS")
        assert eps.raw_value == "4.330000"
        assert eps.unit == "CNY/share"
        assert eps.scale == 1
        # f2/ps4 are display precision, not units: a CNY amount with ps4 keeps
        # unit unknown unless field evidence says otherwise (real MINYSHARINCO
        # appears with ps4 in other issuers' lrb).
        assert eps.provider_precision == "ps4"

    def test_card_pointer_example_resolves_to_real_value(self):
        merged = {}
        for page_no in (1, 2, 3, 4):
            page = normalize.normalize_page(
                _page("lrb", page_no),
                statement_type="income_statement",
                page_number=page_no,
            )
            for report in page.reports:
                merged.setdefault(report.period_end_compact, report)
        report = merged["20251231"]
        row = report.rows[7]
        assert row.provider_field == "BIZTOTCOST"
        assert row.raw_value == "11006675861.270000"
        assert (
            row.json_pointer
            == "/result/data/report_list/20251231/data/7/item_value"
        )
        # The pointer must resolve inside the frozen original bytes.
        original = fixtures.fixture_json("sh688012-lrb-type0-page1-num10.json.gz")
        node = original
        for segment in row.json_pointer.lstrip("/").split("/"):
            segment = int(segment) if isinstance(node, list) else segment
            node = node[segment]
        assert node == "11006675861.270000"

    def test_real_publish_date_anomaly_is_not_rewritten(self):
        # 2023-12-31 lrb carries publish_date=20250418 in the frozen snapshot.
        page = normalize.normalize_page(
            _page("lrb", 2), statement_type="income_statement", page_number=2
        )
        report = page.report_by_period("2023-12-31")
        assert report is not None
        assert report.provider_publish_date == "20250418"

    def test_report_hash_deterministic_and_sensitive_to_content(self):
        page_one = normalize.normalize_page(
            _page("lrb", 1), statement_type="income_statement", page_number=1
        )
        again = normalize.normalize_page(
            _page("lrb", 1), statement_type="income_statement", page_number=1
        )
        first = page_one.report_by_period("2026-06-30")
        second = again.report_by_period("2026-06-30")
        assert first.report_hash == second.report_hash
        mutated = json.loads(_page("lrb", 1).decode("utf-8"))
        mutated["result"]["data"]["report_list"]["20260630"]["data"][0][
            "item_value"
        ] = "1.00"
        changed = normalize.normalize_page(
            json.dumps(mutated, ensure_ascii=False).encode("utf-8"),
            statement_type="income_statement",
            page_number=1,
        ).report_by_period("2026-06-30")
        assert changed.report_hash != first.report_hash

    def test_update_time_is_not_business_identity(self):
        # A provider update_time bump alone must not mint a new business
        # version: the hash covers content/period/scope/revision metadata,
        # not HTTP-ish update timestamps.
        raw = json.loads(_page("lrb", 1).decode("utf-8"))
        entry = raw["result"]["data"]["report_list"]["20260630"]
        original_hash = normalize.normalize_page(
            json.dumps(raw, ensure_ascii=False).encode("utf-8"),
            statement_type="income_statement",
            page_number=1,
        ).report_by_period("2026-06-30").report_hash
        entry["update_time"] = 4102444800
        bumped_hash = normalize.normalize_page(
            json.dumps(raw, ensure_ascii=False).encode("utf-8"),
            statement_type="income_statement",
            page_number=1,
        ).report_by_period("2026-06-30").report_hash
        assert original_hash == bumped_hash

    def test_revision_metadata_changes_do_mint_new_hash(self):
        raw = json.loads(_page("lrb", 1).decode("utf-8"))
        entry = raw["result"]["data"]["report_list"]["20260630"]
        base = normalize.normalize_page(
            json.dumps(raw, ensure_ascii=False).encode("utf-8"),
            statement_type="income_statement",
            page_number=1,
        ).report_by_period("2026-06-30").report_hash
        entry["publish_date"] = "20261101"
        revised = normalize.normalize_page(
            json.dumps(raw, ensure_ascii=False).encode("utf-8"),
            statement_type="income_statement",
            page_number=1,
        ).report_by_period("2026-06-30").report_hash
        assert revised != base


class TestBalanceSheetSpecifics:
    def test_group_rows_are_classified_not_misaligned(self):
        page = normalize.normalize_page(
            _page("fzb", 1), statement_type="balance_sheet", page_number=1
        )
        assert page.report_count == 33
        report = page.reports[0]
        assert len(report.rows) == 141
        group_rows = [row for row in report.rows if row.value_kind == "group"]
        assert len(group_rows) == 5
        first_group = group_rows[0]
        assert first_group.provider_field == ""
        assert first_group.label == "流动资产"
        assert first_group.raw_value == ""
        assert first_group.value_decimal is None
        # A numeric row right after group rows keeps its own field/value pair.
        numeric = next(
            row for row in report.rows if row.value_kind == "numeric"
        )
        assert numeric.provider_field and numeric.raw_value is not None

    def test_balance_sheet_period_kind_and_statement_semantics(self):
        page = normalize.normalize_page(
            _page("fzb", 1), statement_type="balance_sheet", page_number=1
        )
        report = page.report_by_period("2026-06-30")
        assert report.period_kind == "semi_annual"
        # Instant vs duration semantics live in the report contract:
        assert report.statement_type == "balance_sheet"


class TestValueKindsAndDiagnostics:
    def test_invalid_numeric_keeps_raw_and_flags(self):
        raw = json.loads(_page("lrb", 1).decode("utf-8"))
        raw["result"]["data"]["report_list"]["20260630"]["data"][0]["item_value"] = (
            "1,234.5元"
        )
        page = normalize.normalize_page(
            json.dumps(raw, ensure_ascii=False).encode("utf-8"),
            statement_type="income_statement",
            page_number=1,
        )
        row = page.report_by_period("2026-06-30").rows[0]
        assert row.raw_value == "1,234.5元"
        assert row.value_decimal is None
        assert row.value_kind == "non_numeric"
        assert "invalid_numeric_value" in row.quality_flags

    def test_empty_string_value_is_distinct_from_null(self):
        raw = json.loads(_page("lrb", 1).decode("utf-8"))
        raw["result"]["data"]["report_list"]["20260630"]["data"][0]["item_value"] = ""
        page = normalize.normalize_page(
            json.dumps(raw, ensure_ascii=False).encode("utf-8"),
            statement_type="income_statement",
            page_number=1,
        )
        row = page.report_by_period("2026-06-30").rows[0]
        assert row.raw_value == ""
        assert row.value_decimal is None
        assert row.value_kind == "empty"

    def test_scientific_notation_parses_as_exact_decimal(self):
        raw = json.loads(_page("lrb", 1).decode("utf-8"))
        raw["result"]["data"]["report_list"]["20260630"]["data"][0]["item_value"] = (
            "-1.05E+3"
        )
        page = normalize.normalize_page(
            json.dumps(raw, ensure_ascii=False).encode("utf-8"),
            statement_type="income_statement",
            page_number=1,
        )
        row = page.report_by_period("2026-06-30").rows[0]
        assert row.value_kind == "numeric"
        assert row.value_decimal == "-1050"

    def test_null_data_page_is_reported_not_raised(self):
        empty = fixtures.fixture_bytes("sh688012-lrb-type0-page5-num10.json.gz")
        page = normalize.normalize_page(
            empty, statement_type="income_statement", page_number=5
        )
        assert page.page_had_data is False
        assert page.reports == ()

    def test_protocol_error_when_data_lacks_report_list(self):
        with pytest.raises(normalize.NormalizeProtocolError):
            normalize.normalize_page(
                b'{"result": {"status": {"code": 0}, "data": {"report_count": "5"}}}',
                statement_type="income_statement",
                page_number=1,
            )

    def test_nonzero_status_code_is_protocol_error(self):
        with pytest.raises(normalize.NormalizeProtocolError):
            normalize.normalize_page(
                b'{"result": {"status": {"code": 1}, "data": null}}',
                statement_type="income_statement",
                page_number=1,
            )


class TestPeriodKindMatrix:
    @pytest.mark.parametrize(
        ("compact", "kind"),
        [
            ("20251231", "annual"),
            ("20250930", "q3"),
            ("20250630", "semi_annual"),
            ("20250331", "q1"),
        ],
    )
    def test_period_kind_from_month_day(self, compact: str, kind: str):
        assert normalize.parse_period_kind(compact) == kind

    def test_unknown_month_day_is_reported(self):
        with pytest.raises(normalize.NormalizeProtocolError):
            normalize.parse_period_kind("20250115")


class TestConsolidation:
    def test_rtype_mapping(self):
        assert normalize.parse_consolidation("合并期末") == "consolidated"
        assert normalize.parse_consolidation("母公司期末") == "parent"
        assert normalize.parse_consolidation("") == "unknown"
        assert normalize.parse_consolidation(None) == "unknown"
