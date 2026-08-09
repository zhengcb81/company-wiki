"""WU-804 RED/audit tests: resolver shadow diff gate (v1 vs v2)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))
from company_wiki.source_catalog.adapters.parity import run_parity  # noqa: E402


class _R:
    def __init__(self, path, reason="REUSED", status="active"):
        self.relative_path = path
        self.reason = reason
        self.source_status = status
        self.entity_name = None


def test_v2_never_relaxes_v1_selection():
    """v2 多放行一项（v1 rejected、v2 selected）是阻断缺陷。"""
    v1 = [_R("a.pdf")]
    v2 = [_R("a.pdf"), _R("b.pdf")]
    report = run_parity(v1, v2)
    assert not report.ok  # b.pdf presence diff is a blocker
    assert any(d.path == "b.pdf" for d in report.blockers)


def test_v2_rejecting_v1_admitted_is_safety_improvement():
    """v1 错误放行、v2 拒绝 → known_bad 分类（安全改进，不阻断）。"""
    v1 = [_R("a.pdf")]
    v2 = []
    report = run_parity(v1, v2, known_bad={("a.pdf", "presence"): "v1 admitted broker research"})
    assert report.ok


def test_reason_field_diff_blocker():
    v1 = [_R("a.pdf", reason="REUSED")]
    v2 = [_R("a.pdf", reason="MISSING")]
    report = run_parity(v1, v2)
    assert not report.ok
    assert any(d.field == "presence" or d.field == "reason" for d in report.blockers)
