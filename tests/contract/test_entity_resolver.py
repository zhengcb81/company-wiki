"""WU-703 RED/audit tests: entity resolution (DBX-ENT-01..05)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))
from company_wiki.source_catalog.entity_resolver import (  # noqa: E402
    name_conflict_detected,
    resolve_entity,
)

REGISTRY = {
    ("600519", "CN"): "ent-moutai",
    ("US12345", "US"): "ent-acme",
    ("HK0001", "HK"): "ent-alpha",
}


def test_dbx_ent01_new_company_unresolved_not_dropped():
    # Dropbox has a company never seen under companies/: it must resolve to
    # unresolved (unbound assertion available), NOT vanish
    result = resolve_entity(security_id="NEWCO", market="CN",
                            display_name="新公司", registry=REGISTRY)
    assert result.status == "unresolved"
    assert "unbound assertion" in result.reason


def test_dbx_ent02_same_name_different_market_ambiguous():
    # 同名不同证券：display_name matches multiple entries
    registry = {**REGISTRY, ("600520", "CN"): "ent-other"}
    result = resolve_entity(security_id=None, market=None,
                            display_name="贵州茅台", registry=registry)
    assert result.status == "unresolved" or result.status == "ambiguous"


def test_dbx_ent03_folder_name_conflicts_with_security_id():
    # 文件夹名与 sidecar security_id 冲突 → 强键优先，目录名不覆盖
    result = resolve_entity(security_id="600519", market="CN",
                            display_name="其他公司", registry=REGISTRY)
    assert result.status == "exact"
    assert result.canonical_entity_id == "ent-moutai"


def test_dbx_ent04_vague_chinese_name_only():
    result = resolve_entity(security_id=None, market=None,
                            display_name="公司", registry=REGISTRY)
    assert result.status == "unresolved"


def test_dbx_ent05_broker_research_mislabeled_as_annual():
    # 券商研报伪装年报：身份弱 → 至少 unresolved，永不作 exact
    result = resolve_entity(security_id=None, market=None,
                            display_name="某某证券研究报告", registry=REGISTRY)
    assert result.status != "exact"


def test_name_conflict_detected():
    registry = {
        ("AAA", "CN"): "ent-a",
        ("BBB", "US"): "ent-a",  # same canonical id from two secs is fine
    }
    assert name_conflict_detected(registry=registry, display_name="ent-a") is False
    conflict = {
        ("AAA", "CN"): "ent-a",
        ("BBB", "US"): "ent-b",
    }
    assert name_conflict_detected(registry=conflict, display_name="ent-a") is False
