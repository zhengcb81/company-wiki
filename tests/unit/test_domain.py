"""Tests for src/company_wiki/domain.py"""


import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from company_wiki.domain import (
    Company, Sector, Theme, Question, SourceRecord, Claim,
    EvidenceSpan, KnowledgePatch, EntityType, SourceKind,
    ClaimType, AnswerState,
)


class TestEntityTypes:
    def test_company_type(self):
        c = Company(id="SZSE:002371", name="北方华创", ticker="002371", exchange="SZSE")
        assert c.entity_type == EntityType.COMPANY

    def test_sector_type(self):
        s = Sector(id="sector:半导体设备", name="半导体设备")
        assert s.entity_type == EntityType.SECTOR

    def test_theme_type(self):
        t = Theme(id="theme:国产替代", name="国产替代")
        assert t.entity_type == EntityType.THEME


class TestSourceRecord:
    def test_create(self):
        s = SourceRecord(
            source_id="abc123",
            path="/path/to/file.pdf",
            source_kind=SourceKind.REGULATORY,
        )
        assert s.source_id == "abc123"
        assert s.source_kind == SourceKind.REGULATORY

    def test_source_kinds(self):
        assert SourceKind.REGULATORY.value == "regulatory"
        assert SourceKind.BROKER_RESEARCH.value == "broker_research"


class TestClaim:
    def test_create(self):
        c = Claim(
            claim_id="claim-001",
            claim_type=ClaimType.FACT,
            text="营收同比增长32%",
            entity_id="SZSE:002371",
        )
        assert c.claim_type == ClaimType.FACT
        assert c.confidence == 0.5

    def test_with_evidence(self):
        span = EvidenceSpan(source_id="abc123", page=5)
        c = Claim(
            claim_id="claim-002",
            claim_type=ClaimType.FACT,
            text="净利润增长28%",
            entity_id="SZSE:002371",
            evidence=[span],
        )
        assert len(c.evidence) == 1
        assert c.evidence[0].page == 5


class TestQuestion:
    def test_create(self):
        q = Question(
            id="Q001",
            text="北方华创2025年订单增速？",
            owner="北方华创",
            priority="high",
        )
        assert q.answer_state == AnswerState.UNANSWERED
        assert q.status == "active"


class TestKnowledgePatch:
    def test_create(self):
        p = KnowledgePatch(
            patch_id="patch-001",
            source_id="abc123",
            targets=["SZSE:002371"],
            risk_level="medium",
        )
        assert len(p.targets) == 1
        assert p.validation_result == ""
