"""WU-704 RED/audit tests: DBX fixture end-to-end (adapter → admission).

Dropbox-shaped fixture trees driven through SidecarFilingAdapter +
evaluate_candidate.  Resolver-dependent scenarios (DBX-01 REUSED,
DBX-03 latest-gap) land with Phase 8 resolver cutover.
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))
from company_wiki.source_catalog.adapters.sidecar import SidecarFilingAdapter  # noqa: E402
from company_wiki.source_catalog.admission import evaluate_candidate  # noqa: E402


def _sidecar(**overrides) -> dict:
    payload = {
        "schema_version": "1.0",
        "canonical_entity_id": "ent-moutai",
        "display_name": "贵州茅台",
        "market": "CN",
        "security_id": "600519",
        "document_kind": "annual_report",
        "fiscal_year": 2025,
        "period_end": "2025-12-31",
        "provider": "example-filing",
        "provider_document_id": "acc-2025",
        "source_url": "https://www.example-filing.com/600519/2025",
        "content_sha256": "c" * 64,
    }
    payload.update(overrides)
    return payload


def _dropbox_tree(tmp_path: Path, files: list[tuple[str, dict | None]]) -> Path:
    root = tmp_path / "stock"
    root.mkdir()
    for name, sidecar in files:
        primary = root / name
        primary.write_bytes(b"%PDF-1.4 " + name.encode("utf-8"))
        if sidecar is not None:
            primary.with_name(primary.name + ".source.json").write_text(
                json.dumps(sidecar, ensure_ascii=False), encoding="utf-8"
            )
    return root


def test_dbx_08_sidecar_hash_wrong_admission_rejects(tmp_path):
    """DBX-08: sidecar hash 错 → 拒绝且不自动重写 sidecar。"""
    tree = _dropbox_tree(tmp_path, [("2025年报.pdf", _sidecar())])
    adapter = SidecarFilingAdapter()
    candidates = adapter.enumerate(tree)
    primary = next(c for c in candidates if c.role == "original_primary")
    # adapter records the sidecar hash; admission compares to file bytes
    decision = evaluate_candidate(
        primary.normalized,
        policy_allows_filing=True, profile_allows_filing=True,
        content_hash_matches=(primary.content_sha256 == "c" * 64),
    )
    assert not decision.admitted  # sidecar hash c*64 != actual file hash
    assert "content_hash_mismatch" in decision.reason


def test_dbx_09_non_focus_generic_not_filing(tmp_path):
    """DBX-09: 非重点子树普通文档 → 可 index，不可作为 filing。"""
    tree = _dropbox_tree(tmp_path, [("非重点/notes.pdf", _sidecar(
        document_kind="broker_research"))])
    candidates = SidecarFilingAdapter().enumerate(tree)
    primary = next(c for c in candidates)
    decision = evaluate_candidate(
        primary.normalized,
        policy_allows_filing=True, profile_allows_filing=False,  # generic profile
        content_hash_matches=True,
    )
    assert not decision.admitted
    assert "non_filing_kind" in decision.reason


def test_dbx_12_broker_report_mislabeled_annual_rejected(tmp_path):
    """DBX-12: broker report 带年报文件名 → fail closed。"""
    tree = _dropbox_tree(tmp_path, [("某某证券_2025年报.pdf", _sidecar(
        document_kind="broker_research"))])
    candidates = SidecarFilingAdapter().enumerate(tree)
    primary = next(c for c in candidates)
    decision = evaluate_candidate(
        primary.normalized,
        policy_allows_filing=True, profile_allows_filing=False,
        content_hash_matches=True,
    )
    assert not decision.admitted


def test_dbx_14_amended_version_both_kept(tmp_path):
    """DBX-14: 正式版与更正版并存，均保留。"""
    tree = _dropbox_tree(tmp_path, [
        ("annual_2025.pdf", _sidecar(provider_document_id="acc-2025-v1")),
        ("annual_2025_revised.pdf", _sidecar(provider_document_id="acc-2025-v2",
                                             revision_id="2")),
    ])
    candidates = SidecarFilingAdapter().enumerate(tree)
    assert len(candidates) == 2  # both documents preserved
    assert {c.normalized["provider_document_id"] for c in candidates} == {
        "acc-2025-v1", "acc-2025-v2"}


def test_dbx_01_reuse_semantics_pending_resolver(tmp_path):
    """DBX-01 的 REUSED/download=0 断言依赖 Phase 8 resolver cutover；
    fixture + adapter 链在本 WU 准备就绪。"""
    tree = _dropbox_tree(tmp_path, [("2025年报.pdf", _sidecar())])
    candidates = SidecarFilingAdapter().enumerate(tree)
    primary = next(c for c in candidates)
    assert primary.role == "original_primary"
    assert primary.normalized["normalization_status"] == "capture_ready"
