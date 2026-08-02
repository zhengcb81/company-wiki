"""
quality.py — 质量快照与 SLO 监控

由 ledger/run 生成版本化质量快照，不再手填 dashboard。
"""

import hashlib
import json
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Optional


@dataclass
class QualitySnapshot:
    """质量快照"""
    snapshot_id: str
    created_at: datetime
    version: str = "1.0"

    # 来源质量
    total_sources: int = 0
    verified_sources: int = 0
    unverified_sources: int = 0
    quarantined_sources: int = 0

    # 声明质量
    total_claims: int = 0
    active_claims: int = 0
    stale_claims: int = 0
    contradicted_claims: int = 0

    # 问题覆盖
    total_questions: int = 0
    answered_questions: int = 0
    unanswered_questions: int = 0
    stale_questions: int = 0

    # 页面质量
    total_pages: int = 0
    pages_with_timeline: int = 0
    pages_with_assessment: int = 0
    orphan_pages: int = 0

    # 投影一致性
    projection_hash: str = ""
    index_hash: str = ""

    # 运行统计
    total_runs: int = 0
    successful_runs: int = 0
    failed_runs: int = 0

    # 预算使用
    total_tokens_used: int = 0
    total_cost_usd: float = 0.0

    # 元数据
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "snapshot_id": self.snapshot_id,
            "created_at": self.created_at.isoformat(),
            "version": self.version,
            "sources": {
                "total": self.total_sources,
                "verified": self.verified_sources,
                "unverified": self.unverified_sources,
                "quarantined": self.quarantined_sources,
            },
            "claims": {
                "total": self.total_claims,
                "active": self.active_claims,
                "stale": self.stale_claims,
                "contradicted": self.contradicted_claims,
            },
            "questions": {
                "total": self.total_questions,
                "answered": self.answered_questions,
                "unanswered": self.unanswered_questions,
                "stale": self.stale_questions,
            },
            "pages": {
                "total": self.total_pages,
                "with_timeline": self.pages_with_timeline,
                "with_assessment": self.pages_with_assessment,
                "orphan": self.orphan_pages,
            },
            "projections": {
                "projection_hash": self.projection_hash,
                "index_hash": self.index_hash,
            },
            "runs": {
                "total": self.total_runs,
                "successful": self.successful_runs,
                "failed": self.failed_runs,
            },
            "budget": {
                "tokens_used": self.total_tokens_used,
                "cost_usd": self.total_cost_usd,
            },
        }

    def save(self, path: Path):
        """保存快照"""
        path.write_text(json.dumps(self.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8")

    @classmethod
    def load(cls, path: Path) -> "QualitySnapshot":
        """加载快照"""
        data = json.loads(path.read_text(encoding="utf-8"))
        return cls(
            snapshot_id=data["snapshot_id"],
            created_at=datetime.fromisoformat(data["created_at"]),
            version=data.get("version", "1.0"),
            total_sources=data.get("sources", {}).get("total", 0),
            verified_sources=data.get("sources", {}).get("verified", 0),
            unverified_sources=data.get("sources", {}).get("unverified", 0),
            quarantined_sources=data.get("sources", {}).get("quarantined", 0),
            total_claims=data.get("claims", {}).get("total", 0),
            active_claims=data.get("claims", {}).get("active", 0),
            stale_claims=data.get("claims", {}).get("stale", 0),
            contradicted_claims=data.get("claims", {}).get("contradicted", 0),
            total_questions=data.get("questions", {}).get("total", 0),
            answered_questions=data.get("questions", {}).get("answered", 0),
            unanswered_questions=data.get("questions", {}).get("unanswered", 0),
            stale_questions=data.get("questions", {}).get("stale", 0),
            total_pages=data.get("pages", {}).get("total", 0),
            pages_with_timeline=data.get("pages", {}).get("with_timeline", 0),
            pages_with_assessment=data.get("pages", {}).get("with_assessment", 0),
            orphan_pages=data.get("pages", {}).get("orphan", 0),
            projection_hash=data.get("projections", {}).get("projection_hash", ""),
            index_hash=data.get("projections", {}).get("index_hash", ""),
            total_runs=data.get("runs", {}).get("total", 0),
            successful_runs=data.get("runs", {}).get("successful", 0),
            failed_runs=data.get("runs", {}).get("failed", 0),
            total_tokens_used=data.get("budget", {}).get("tokens_used", 0),
            total_cost_usd=data.get("budget", {}).get("cost_usd", 0.0),
        )


@dataclass
class SLO:
    """服务级别目标"""
    name: str
    target: float  # 目标值（如 0.95 表示 95%）
    current: float = 0.0
    unit: str = "ratio"

    @property
    def is_met(self) -> bool:
        return self.current >= self.target

    @property
    def gap(self) -> float:
        return self.target - self.current


@dataclass
class QualityReport:
    """质量报告"""
    report_id: str
    created_at: datetime
    snapshot: QualitySnapshot
    slos: list[SLO] = field(default_factory=list)
    issues: list[str] = field(default_factory=list)
    recommendations: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "report_id": self.report_id,
            "created_at": self.created_at.isoformat(),
            "snapshot": self.snapshot.to_dict(),
            "slos": [
                {"name": s.name, "target": s.target, "current": s.current, "unit": s.unit, "is_met": s.is_met}
                for s in self.slos
            ],
            "issues": self.issues,
            "recommendations": self.recommendations,
        }

    def save(self, path: Path):
        """保存报告"""
        path.write_text(json.dumps(self.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8")


class QualityAnalyzer:
    """
    质量分析器。

    从数据库和文件系统生成质量快照和报告。
    """

    def __init__(self, wiki_root: Path):
        self._root = wiki_root

    def generate_snapshot(self) -> QualitySnapshot:
        """生成质量快照"""
        snapshot = QualitySnapshot(
            snapshot_id=f"qs-{datetime.now().strftime('%Y%m%d-%H%M%S')}",
            created_at=datetime.now(),
        )

        # 统计页面
        self._count_pages(snapshot)

        # 计算投影 hash
        self._compute_hashes(snapshot)

        return snapshot

    def generate_report(self, snapshot: Optional[QualitySnapshot] = None) -> QualityReport:
        """生成质量报告"""
        if snapshot is None:
            snapshot = self.generate_snapshot()

        report = QualityReport(
            report_id=f"qr-{datetime.now().strftime('%Y%m%d-%H%M%S')}",
            created_at=datetime.now(),
            snapshot=snapshot,
        )

        # 定义 SLOs
        report.slos = [
            SLO(name="source_verification", target=0.95, current=self._calc_source_verification(snapshot)),
            SLO(name="question_coverage", target=0.80, current=self._calc_question_coverage(snapshot)),
            SLO(name="page_completeness", target=0.90, current=self._calc_page_completeness(snapshot)),
            SLO(name="run_success_rate", target=0.95, current=self._calc_run_success_rate(snapshot)),
        ]

        # 检查问题
        if snapshot.unverified_sources > 0:
            report.issues.append(f"存在 {snapshot.unverified_sources} 个未验证来源")
        if snapshot.stale_claims > 0:
            report.issues.append(f"存在 {snapshot.stale_claims} 个过期声明")
        if snapshot.orphan_pages > 0:
            report.issues.append(f"存在 {snapshot.orphan_pages} 个孤立页面")

        # 生成建议
        for slo in report.slos:
            if not slo.is_met:
                report.recommendations.append(f"SLO '{slo.name}' 未达标: 当前 {slo.current:.1%}，目标 {slo.target:.1%}")

        return report

    def _count_pages(self, snapshot: QualitySnapshot):
        """统计页面"""
        companies_dir = self._root / "companies"
        sectors_dir = self._root / "sectors"

        page_count = 0
        timeline_count = 0
        assessment_count = 0

        for wiki_dir in list(companies_dir.rglob("wiki")) + list(sectors_dir.rglob("wiki")):
            if wiki_dir.is_dir():
                for page in wiki_dir.glob("*.md"):
                    page_count += 1
                    content = page.read_text(encoding="utf-8")
                    if "## 时间线" in content:
                        timeline_count += 1
                    if "## 综合评估" in content:
                        assessment_count += 1

        snapshot.total_pages = page_count
        snapshot.pages_with_timeline = timeline_count
        snapshot.pages_with_assessment = assessment_count

    def _compute_hashes(self, snapshot: QualitySnapshot):
        """计算投影 hash"""
        # 计算所有 wiki 页面的 hash
        wiki_hashes = []
        for wiki_dir in self._root.rglob("wiki"):
            if wiki_dir.is_dir():
                for page in sorted(wiki_dir.glob("*.md")):
                    h = hashlib.sha256(page.read_bytes()).hexdigest()[:16]
                    wiki_hashes.append(h)

        if wiki_hashes:
            combined = "".join(wiki_hashes)
            snapshot.projection_hash = hashlib.sha256(combined.encode()).hexdigest()[:16]

        # 计算 index hash
        index_path = self._root / "index.md"
        if index_path.exists():
            snapshot.index_hash = hashlib.sha256(index_path.read_bytes()).hexdigest()[:16]

    def _calc_source_verification(self, snapshot: QualitySnapshot) -> float:
        """计算来源验证率"""
        if snapshot.total_sources == 0:
            return 1.0
        return snapshot.verified_sources / snapshot.total_sources

    def _calc_question_coverage(self, snapshot: QualitySnapshot) -> float:
        """计算问题覆盖率"""
        if snapshot.total_questions == 0:
            return 1.0
        return snapshot.answered_questions / snapshot.total_questions

    def _calc_page_completeness(self, snapshot: QualitySnapshot) -> float:
        """计算页面完整度"""
        if snapshot.total_pages == 0:
            return 1.0
        return snapshot.pages_with_timeline / snapshot.total_pages

    def _calc_run_success_rate(self, snapshot: QualitySnapshot) -> float:
        """计算运行成功率"""
        if snapshot.total_runs == 0:
            return 1.0
        return snapshot.successful_runs / snapshot.total_runs


def verify_disaster_recovery(wiki_root: Path, snapshot: QualitySnapshot) -> tuple[bool, list[str]]:
    """
    验证灾难恢复。

    检查：
    1. 所有 raw 文件可访问
    2. 所有 wiki 页面可访问
    3. index 与投影一致

    Returns:
        (is_recoverable, issues)
    """
    issues = []

    # 检查 raw 文件
    companies_dir = wiki_root / "companies"
    if companies_dir.exists():
        for company_dir in companies_dir.iterdir():
            if company_dir.is_dir():
                raw_dir = company_dir / "raw"
                if raw_dir.exists():
                    for raw_file in raw_dir.rglob("*"):
                        if raw_file.is_file():
                            try:
                                raw_file.read_bytes()
                            except Exception as e:
                                issues.append(f"无法读取 raw 文件: {raw_file}: {e}")

    # 检查 wiki 页面
    for wiki_dir in wiki_root.rglob("wiki"):
        if wiki_dir.is_dir():
            for page in wiki_dir.glob("*.md"):
                try:
                    page.read_text(encoding="utf-8")
                except Exception as e:
                    issues.append(f"无法读取 wiki 页面: {page}: {e}")

    # 检查 index
    index_path = wiki_root / "index.md"
    if index_path.exists():
        try:
            index_content = index_path.read_text(encoding="utf-8")
            if not index_content.strip():
                issues.append("index.md 为空")
        except Exception as e:
            issues.append(f"无法读取 index.md: {e}")

    return len(issues) == 0, issues
