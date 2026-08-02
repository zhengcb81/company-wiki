"""Contracts for the path-scoped high-value source admission policy."""

from __future__ import annotations

import json
from pathlib import Path

from company_wiki.source_catalog import CatalogConfig, RootSpec, SourceCatalog
from company_wiki.source_catalog.admission import (
    FOCUS_RELATIVE_PREFIX,
    FOCUS_ROOT_ID,
    evaluate_admission,
    processing_priority,
)


def _decision(relative_path: str, metadata: dict[str, object] | None = None):
    return evaluate_admission(
        root_id=FOCUS_ROOT_ID,
        relative_path=relative_path,
        metadata=metadata or {},
    )


def _focus_catalog(tmp_path: Path) -> tuple[SourceCatalog, Path]:
    project = tmp_path / "project"
    root = tmp_path / "Dropbox" / "Stock"
    focus = root / FOCUS_RELATIVE_PREFIX
    focus.mkdir(parents=True)
    catalog = SourceCatalog(
        CatalogConfig(
            project_root=project,
            catalog_dir=project / ".source_catalog",
            roots=(RootSpec(FOCUS_ROOT_ID, root, "directory", priority=30),),
        )
    )
    return catalog, focus


def test_focus_policy_admits_only_the_five_requested_source_categories():
    cases = {
        "重点关注/Acme招股说明书.pdf": ("prospectus", 10),
        "重点关注/Acme 2025年度报告.pdf": ("annual_report", 20),
        "重点关注/Acme 2025年半年度报告.pdf": ("semi_annual_report", 21),
        "重点关注/Acme 2025年第三季度报告.pdf": ("quarterly_report", 22),
        "重点关注/Acme投资者关系活动记录.pdf": ("investor_relations", 30),
        "重点关注/Acme业绩电话会议纪要.pdf": ("investor_call_transcript", 40),
        "重点关注/中信证券-Acme-公司深度报告.pdf": ("broker_research", 50),
        "重点关注/Goldman Sachs Acme Equity Research Report.pdf": (
            "broker_research",
            50,
        ),
    }
    for relative_path, expected in cases.items():
        decision = _decision(relative_path)
        assert decision is not None
        assert decision.admitted is True
        assert (decision.document_kind, decision.priority) == expected
        assert decision.reason
        assert decision.evidence


def test_focus_policy_fails_closed_for_personal_material_and_weak_broker_signals():
    rejected = (
        "重点关注/投资笔记.docx",
        "重点关注/股票池.xlsx",
        "重点关注/筛选器_落难凤凰.csv",
        "重点关注/投资组合分析20260530.xlsx",
        "重点关注/IB statements/2024.pdf",
        "重点关注/水晶苍蝇拍点评/汇川技术.txt",
        "重点关注/公司研究框架.xlsx",
        "重点关注/优质低价_天风_选股20181027.csv",
        "重点关注/泛称研究报告.pdf",
    )
    for relative_path in rejected:
        decision = _decision(relative_path)
        assert decision is not None
        assert decision.admitted is False
        assert decision.document_kind is None
        assert decision.reason.startswith("focus_policy_")


def test_focus_policy_scope_is_an_exact_path_component_and_other_roots_are_untouched():
    assert evaluate_admission(
        root_id=FOCUS_ROOT_ID,
        relative_path="重点关注旧/投资笔记.docx",
        metadata={},
    ) is None
    assert evaluate_admission(
        root_id="company_raw",
        relative_path="重点关注/投资笔记.docx",
        metadata={},
    ) is None
    assert _decision("重点关注\\Acme招股说明书.pdf").admitted is True


def test_explicit_sidecar_kind_is_strong_but_three_identity_fields_are_not():
    explicit = _decision(
        "重点关注/opaque-name.pdf",
        {"document_kind": "broker_research", "source_title": "opaque-name"},
    )
    assert explicit is not None and explicit.admitted is True
    assert explicit.document_kind == "broker_research"

    identity_only = _decision(
        "重点关注/opaque-name.pdf",
        {
            "market": "HK",
            "security_id": "Unresolved (dropbox_stock)",
            "source_title": "opaque-name",
        },
    )
    assert identity_only is not None and identity_only.admitted is False


def test_processing_priority_is_stable_and_matches_requested_order():
    kinds = (
        "prospectus",
        "annual_report",
        "semi_annual_report",
        "quarterly_report",
        "investor_relations",
        "investor_call_transcript",
        "broker_research",
        "other",
    )
    assert [processing_priority(kind) for kind in kinds] == [
        10,
        20,
        21,
        22,
        30,
        40,
        50,
        1000,
    ]


def test_directory_scanner_pairs_sidecar_and_excludes_rejected_focus_documents(
    tmp_path: Path,
):
    catalog, focus = _focus_catalog(tmp_path)
    allowed = focus / "Acme 2025年度报告.txt"
    allowed.write_text("Acme audited annual report", encoding="utf-8")
    sidecar = allowed.with_name(allowed.name + ".source.json")
    sidecar.write_text(
        json.dumps(
            {
                "market": "US",
                "security_id": "ACME",
                "source_title": "Acme 2025 Annual Report",
                "document_kind": "annual_report",
            }
        ),
        encoding="utf-8",
    )
    (focus / "Acme招股说明书.txt").write_text("prospectus", encoding="utf-8")
    (focus / "投资笔记.txt").write_text("private note", encoding="utf-8")
    (focus / "优质低价_天风_选股20181027.csv").write_text(
        "ticker,score\nACME,1\n", encoding="utf-8"
    )
    outside = focus.parent / "其他" / "投资笔记.txt"
    outside.parent.mkdir()
    outside.write_text("outside policy", encoding="utf-8")

    report = catalog.scan()
    rows = catalog.store.fetchall(
        """SELECT l.relative_path,l.role,l.document_id,d.document_kind
        FROM locations l JOIN documents d ON d.document_id=l.document_id
        ORDER BY l.relative_path"""
    )
    by_path = {row["relative_path"]: row for row in rows}

    assert "重点关注/投资笔记.txt" not in by_path
    assert "重点关注/优质低价_天风_选股20181027.csv" not in by_path
    assert by_path["重点关注/Acme 2025年度报告.txt"]["document_kind"] == (
        "annual_report"
    )
    assert by_path["重点关注/Acme 2025年度报告.txt.source.json"]["role"] == (
        "metadata"
    )
    assert (
        by_path["重点关注/Acme 2025年度报告.txt.source.json"]["document_id"]
        == by_path["重点关注/Acme 2025年度报告.txt"]["document_id"]
    )
    assert by_path["其他/投资笔记.txt"]["document_kind"] == "broker_research"
    assert report.policy_excluded == 2
    assert report.files_excluded >= report.policy_excluded


def test_normalize_limit_dispatches_prospectus_before_broker_research(tmp_path: Path):
    catalog, focus = _focus_catalog(tmp_path)
    (focus / "中信证券-Acme-公司深度报告.txt").write_text(
        "broker research body", encoding="utf-8"
    )
    (focus / "Acme招股说明书.txt").write_text(
        "prospectus body", encoding="utf-8"
    )
    catalog.scan()

    report = catalog.normalize(limit=1)

    assert report.completed == 1
    row = catalog.store.fetchone(
        """SELECT d.document_kind FROM artifacts a
        JOIN documents d ON d.document_id=a.document_id
        WHERE a.artifact_role='normalized'"""
    )
    assert row is not None and row["document_kind"] == "prospectus"


def test_fingerprint_batch_uses_the_same_requested_priority_order(tmp_path: Path):
    catalog, focus = _focus_catalog(tmp_path)
    for name in (
        "中信证券-Acme-公司深度报告.txt",
        "Acme业绩电话会议纪要.txt",
        "Acme投资者关系活动记录.txt",
        "Acme 2025年第三季度报告.txt",
        "Acme 2025年半年度报告.txt",
        "Acme 2025年度报告.txt",
        "Acme招股说明书.txt",
    ):
        (focus / name).write_text(name, encoding="utf-8")
    catalog.scan()

    batch = catalog.store.select_fingerprint_batch(
        limit=None, now_iso="2099-01-01T00:00:00Z"
    )
    kinds = [
        catalog.store.fetchone(
            "SELECT document_kind FROM documents WHERE document_id=?",
            (row["document_id"],),
        )["document_kind"]
        for row in batch
    ]
    assert kinds == [
        "prospectus",
        "annual_report",
        "semi_annual_report",
        "quarterly_report",
        "investor_relations",
        "investor_call_transcript",
        "broker_research",
    ]


def test_both_summary_queues_dispatch_prospectus_first(tmp_path: Path):
    catalog, focus = _focus_catalog(tmp_path)
    (focus / "中信证券-Acme-公司深度报告.txt").write_text(
        "broker source with enough factual content for a deterministic summary.",
        encoding="utf-8",
    )
    (focus / "Acme招股说明书.txt").write_text(
        "prospectus source with enough factual content for a deterministic summary.",
        encoding="utf-8",
    )
    catalog.scan()
    catalog.normalize()

    report = catalog.summarize(limit=1)
    assert report.completed + report.partial == 1
    extractive = catalog.store.fetchone(
        """SELECT d.document_kind FROM artifacts a
        JOIN documents d ON d.document_id=a.document_id
        WHERE a.artifact_role='summary'
        AND a.generator_name='source_catalog_extractive_summary'"""
    )
    assert extractive is not None and extractive["document_kind"] == "prospectus"

    prompts: list[str] = []

    class _Response:
        success = True
        provider = "test"
        model = "test-model"
        usage: dict[str, int] = {}
        content = json.dumps(
            {
                "overview": "招股资料概述",
                "key_facts": ["这是可核对的招股资料事实。"],
                "topics": ["招股资料"],
                "limitations": [],
            },
            ensure_ascii=False,
        )

    class _Client:
        provider = "test"
        model = "test-model"

        def generate(self, prompt: str, **_kwargs):
            prompts.append(prompt)
            return _Response()

    llm_report = catalog.summarize_with_llm(
        limit=1,
        llm_client_factory=_Client,
        max_input_chars=10_000,
        max_output_tokens=500,
    )
    assert llm_report.completed == 1
    assert len(prompts) == 1
    assert "文档类型：prospectus" in prompts[0]


def test_control_panel_exposes_policy_exclusions_separately():
    project_root = Path(__file__).resolve().parents[2]
    script = (project_root / "scripts" / "source_catalog_control.ps1").read_text(
        encoding="utf-8"
    )
    assert "$Scan.policy_excluded" in script


# --- Rollout blocker regression contracts (Preflight 1) ---


def test_regulatory_filing_explicit_kind_requires_financial_secondary_evidence():
    # Blocker 1: sidecar declaring generic regulatory_filing without financial
    # form/title evidence must NOT be admitted unconditionally.
    generic = _decision(
        "重点关注/opaque-name.pdf", {"document_kind": "regulatory_filing"}
    )
    assert generic is not None and generic.admitted is False

    with_form = _decision(
        "重点关注/opaque.pdf",
        {"document_kind": "regulatory_filing", "form_type": "10-K"},
    )
    assert with_form is not None and with_form.admitted is True
    assert with_form.document_kind == "annual_report"

    with_title = _decision(
        "重点关注/opaque.pdf",
        {
            "document_kind": "regulatory_filing",
            "source_title": "XX公司2025年度财务报告",
        },
    )
    assert with_title is not None and with_title.admitted is True
    assert with_title.document_kind == "regulatory_filing"


def test_announcements_and_regulatory_notices_fail_closed():
    for name in (
        "重点关注/XX公司关于召开股东大会的公告.pdf",
        "重点关注/XX公司监管问询函.pdf",
        "重点关注/XX公司权益变动公告.pdf",
        "重点关注/XX公司减持计划公告.pdf",
    ):
        decision = _decision(name)
        assert decision is not None and decision.admitted is False, name
        assert decision.reason.startswith("focus_policy_")


def test_commentary_without_broker_evidence_fails_closed():
    # Blocker 2: 年报点评/半年报解读/季报复盘/财报摘要 must not fall through
    # to annual/semi/quarterly keywords without strict broker evidence.
    for name in (
        "重点关注/XX公司年报点评.pdf",
        "重点关注/XX公司半年报解读.pdf",
        "重点关注/XX公司季报复盘.pdf",
        "重点关注/XX公司财报摘要.pdf",
    ):
        decision = _decision(name)
        assert decision is not None and decision.admitted is False, name
        assert decision.reason.startswith("focus_policy_")


def test_commentary_with_strict_broker_evidence_is_broker_research():
    decision = _decision("重点关注/中信证券-XX公司年报点评.pdf")
    assert decision is not None and decision.admitted is True
    assert decision.document_kind == "broker_research"


def test_directory_scanner_sidecar_pairing_is_scoped_to_focus_subtree(
    tmp_path: Path,
):
    # Blocker 3: sidecar pairing must only change 重点关注; other directories
    # under the same dropbox_stock root keep legacy standalone behavior.
    catalog, focus = _focus_catalog(tmp_path)
    outside = focus.parent / "其他"
    outside.mkdir()
    for base in (
        focus / "Acme 2025年度报告.txt",
        outside / "notes.txt",
    ):
        base.write_text("content", encoding="utf-8")
        base.with_name(base.name + ".source.json").write_text(
            json.dumps({"source_title": "t"}), encoding="utf-8"
        )
    catalog.scan()
    rows = catalog.store.fetchall(
        "SELECT relative_path, role FROM locations WHERE root_id='dropbox_stock'"
    )
    by_path = {row["relative_path"]: row["role"] for row in rows}
    assert by_path["重点关注/Acme 2025年度报告.txt.source.json"] == "metadata"
    assert by_path["其他/notes.txt.source.json"] == "original_primary"
