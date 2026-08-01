"""RED contracts for classification trust-order and published-date rules.

CW-2.24 Phase 1: these tests MUST fail against current code before any fix.
"""

from __future__ import annotations

import importlib
from pathlib import Path



def _cls():
    """Import _classification from scanner module."""
    mod = importlib.import_module("company_wiki.source_catalog.scanner")
    return mod._classification


def _pub_date():
    """Import _published_date from scanner module."""
    mod = importlib.import_module("company_wiki.source_catalog.scanner")
    return mod._published_date


# ---------------------------------------------------------------------------
# RED 1: broker research vs annual report
# ---------------------------------------------------------------------------

class TestBrokerResearchVsAnnualReport:
    """券商'年报点评'必须是 broker_research，不能是 annual_report。"""

    def test_annual_review_commentary_is_broker_research(self):
        classify = _cls()
        path = Path("中信证券-贵州茅台-2025年报点评.pdf")
        kind, source_type = classify(path, root_kind="directory", metadata={})
        assert kind == "broker_research"
        assert source_type.value == "broker_research"

    def test_deep_report_is_broker_research(self):
        classify = _cls()
        path = Path("国泰君安-宁德时代-深度报告.pdf")
        kind, source_type = classify(path, root_kind="directory", metadata={})
        assert kind == "broker_research"

    def test_actual_annual_report_still_works(self):
        classify = _cls()
        path = Path("贵州茅台-2025年度报告.pdf")
        kind, source_type = classify(path, root_kind="company_raw", metadata={})
        assert kind == "annual_report"
        assert source_type.value == "regulatory_filing"

    def test_annual_report_chinese_short(self):
        classify = _cls()
        path = Path("贵州茅台：2025年年报.pdf")
        kind, _ = classify(path, root_kind="company_raw", metadata={})
        assert kind == "annual_report"

    def test_broker_research_title_with_annual_report_keyword(self):
        """标题含'年报'但实为研报的，必须识别为 broker_research。"""
        classify = _cls()
        path = Path("海通证券-比亚迪-2024年报点评.pdf")
        kind, _ = classify(path, root_kind="directory", metadata={})
        assert kind == "broker_research"


# ---------------------------------------------------------------------------
# RED 2: regulatory filings (10-K, 20-F, 40-F)
# ---------------------------------------------------------------------------

class TestRegulatoryFilings:
    """受信 form_type 或明确文件名必须识别为 regulatory filing。"""

    def test_10k_by_form_type(self):
        classify = _cls()
        path = Path("ACME-annual-report.pdf")
        kind, source_type = classify(
            path, root_kind="directory", metadata={"form_type": "10-K"}
        )
        assert kind == "annual_report"
        assert source_type.value == "regulatory_filing"

    def test_20f_by_form_type(self):
        classify = _cls()
        path = Path("issuer-20F-2025.pdf")
        kind, source_type = classify(
            path, root_kind="directory", metadata={"form_type": "20-F"}
        )
        assert kind == "annual_report"

    def test_40f_by_form_type(self):
        classify = _cls()
        path = Path("annual-filing.pdf")
        kind, _ = classify(
            path, root_kind="directory", metadata={"form_type": "40-F"}
        )
        assert kind == "annual_report"

    def test_20f_in_filename(self):
        """文件名含 20-F 也应识别。"""
        classify = _cls()
        path = Path("company-20F-2025.pdf")
        kind, _ = classify(path, root_kind="directory", metadata={})
        assert kind == "annual_report"


# ---------------------------------------------------------------------------
# RED 3: sidecar metadata priority over weak filename
# ---------------------------------------------------------------------------

class TestSidecarPriority:
    """sidecar document_kind/form_type 必须覆盖弱文件名信号。"""

    def test_sidecar_broker_research_overrides_weak_filename(self):
        """即使文件名含'年报'，sidecar 标为 broker_research 时应尊重。"""
        classify = _cls()
        path = Path("中信证券-2025年报点评.pdf")
        # sidecar 明确标为 broker_research
        kind, _ = classify(
            path, root_kind="directory",
            metadata={"document_kind": "broker_research"}
        )
        assert kind == "broker_research"

    def test_sidecar_form_type_dominates(self):
        """sidecar form_type=10-K 应覆盖文件名无信号。"""
        classify = _cls()
        path = Path("random-name.pdf")
        kind, _ = classify(
            path, root_kind="directory",
            metadata={"form_type": "10-K"}
        )
        assert kind == "annual_report"

    def test_sidecar_conflict_must_not_silently_guess(self):
        """sidecar document_kind 与 form_type 冲突时不能静默猜测。
        当前实现不处理冲突，此测试记录期望行为。"""
        classify = _cls()
        path = Path("some-doc.pdf")
        # form_type=10-K 但 document_kind=broker_research — 冲突
        kind, _ = classify(
            path, root_kind="directory",
            metadata={"form_type": "10-K", "document_kind": "broker_research"}
        )
        # sidecar document_kind 应优先，或进入 quality flag
        # 当前实现不检查冲突，先标记此 RED
        assert kind == "broker_research" or "quality_flag" in str(kind)


# ---------------------------------------------------------------------------
# RED 4: semi-annual / quarterly vs commentary
# ---------------------------------------------------------------------------

class TestSemiAnnualQuarterly:
    """半年报/季报 vs 点评的区分。"""

    def test_semi_annual_report(self):
        classify = _cls()
        path = Path("贵州茅台-2025年半年度报告.pdf")
        kind, source_type = classify(path, root_kind="company_raw", metadata={})
        assert kind == "semi_annual_report"
        assert source_type.value == "regulatory_filing"

    def test_quarterly_report_q1(self):
        classify = _cls()
        path = Path("贵州茅台-2025年一季度报告.pdf")
        kind, source_type = classify(path, root_kind="company_raw", metadata={})
        assert kind == "quarterly_report"

    def test_quarterly_report_q3(self):
        classify = _cls()
        path = Path("贵州茅台-2025年三季度报告.pdf")
        kind, _ = classify(path, root_kind="company_raw", metadata={})
        assert kind == "quarterly_report"

    def test_semi_annual_commentary_is_broker_research(self):
        """'半年报点评'不是半年报，是研报。"""
        classify = _cls()
        path = Path("中信证券-贵州茅台-2025半年报点评.pdf")
        kind, _ = classify(path, root_kind="directory", metadata={})
        assert kind == "broker_research"

    def test_quarterly_commentary_is_broker_research(self):
        """'季报点评'不是季报，是研报。"""
        classify = _cls()
        path = Path("国泰君安-宁德时代-2025一季报点评.pdf")
        kind, _ = classify(path, root_kind="directory", metadata={})
        assert kind == "broker_research"

    def test_form_10q_is_quarterly(self):
        classify = _cls()
        path = Path("quarterly-report.pdf")
        kind, _ = classify(
            path, root_kind="directory", metadata={"form_type": "10-Q"}
        )
        assert kind == "quarterly_report"


# ---------------------------------------------------------------------------
# RED 5: published_date rules
# ---------------------------------------------------------------------------

class TestPublishedDate:
    """published_date 只来自可信字段；只有 fiscal_year 时保持 null。"""

    def test_fiscal_year_only_returns_none(self):
        """只有 fiscal_year 时不得伪造 published_date。"""
        pub = _pub_date()
        assert pub("ACME-FY2025-annual.pdf") is None

    def test_explicit_date_in_filename(self):
        """文件名有明确日期时提取。"""
        pub = _pub_date()
        assert pub("report-2026-02-20.pdf") == "2026-02-20"

    def test_chinese_date_format(self):
        pub = _pub_date()
        assert pub("报告2025年03月15日.pdf") == "2025-03-15"

    def test_no_date_returns_none(self):
        pub = _pub_date()
        assert pub("random-filename.pdf") is None

    def test_partial_date_returns_none(self):
        """只有年份没有月日时不得伪造。"""
        pub = _pub_date()
        assert pub("report-2025.pdf") is None


# ---------------------------------------------------------------------------
# RED 6: same SHA multiple locations — stable classification
# ---------------------------------------------------------------------------

class TestSameShaClassification:
    """同 SHA 多 location 不因路径不同产生不同 document kind。
    这是 scanner 层面的集成测试。"""

    def test_same_metadata_same_kind(self):
        """相同 metadata 在不同路径调用 _classification 应返回相同结果。"""
        classify = _cls()
        metadata = {"form_type": "20-F"}
        kind1, st1 = classify(
            Path("dropbox/ACME-20F.pdf"),
            root_kind="directory",
            metadata=metadata,
        )
        kind2, st2 = classify(
            Path("dayu/ACME/filings/20F.pdf"),
            root_kind="dayu_portfolio",
            metadata=metadata,
        )
        assert kind1 == kind2

    def test_strong_metadata_stable_across_roots(self):
        """有强 metadata 时，不同 root 的分类结果应一致。"""
        classify = _cls()
        metadata = {"form_type": "10-K"}
        kind1, _ = classify(Path("a.pdf"), root_kind="company_raw", metadata=metadata)
        kind2, _ = classify(Path("b.pdf"), root_kind="directory", metadata=metadata)
        assert kind1 == kind2


# ---------------------------------------------------------------------------
# RED 7: dayu_portfolio default must not override strong signals
# ---------------------------------------------------------------------------

class TestDayuPortfolioDefault:
    """dayu_portfolio 的默认分类不应覆盖明确信号。"""

    def test_dayu_portfolio_default_is_regulatory(self):
        """dayu_portfolio 无信号时默认 regulatory_filing。"""
        classify = _cls()
        path = Path("ACME/random-doc.pdf")
        kind, _ = classify(path, root_kind="dayu_portfolio", metadata={})
        assert kind == "regulatory_filing"

    def test_dayu_portfolio_with_form_type(self):
        """dayu_portfolio 有 form_type 时应使用精确分类。"""
        classify = _cls()
        path = Path("ACME/annual.htm")
        kind, _ = classify(
            path, root_kind="dayu_portfolio", metadata={"form_type": "10-K"}
        )
        assert kind == "annual_report"
