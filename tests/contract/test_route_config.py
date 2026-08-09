"""WU-702 RED/audit tests: route-configured focus scope + future_root."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))
from company_wiki.source_catalog.config import load_catalog_config  # noqa: E402
from company_wiki.source_catalog.models import RouteSpec, RootSpec  # noqa: E402


def _root_with_routes() -> RootSpec:
    return RootSpec(
        root_id="dropbox_stock",
        path=Path("C:/unused"),
        kind="directory",
        adapter_id="sidecar_filing_v1",
        routes=(RouteSpec(include=("重点关注/**",)),),
    )


def test_route_matches_focus_subtree():
    root = _root_with_routes()
    assert root.route_matches("重点关注/新能源/2025年报.pdf")
    assert root.route_matches("重点关注")
    assert not root.route_matches("非重点/notes.pdf")
    assert not root.route_matches("互联网/哔哩哔哩/x.pdf")


def test_route_exclude_wins():
    root = RootSpec(
        root_id="r", path=Path("C:/x"), kind="directory",
        routes=(RouteSpec(include=("**/*.pdf",), exclude=("非重点/**",)),),
    )
    assert root.route_matches("重点/2025.pdf")
    assert not root.route_matches("非重点/2025.pdf")


def test_no_routes_legacy_false():
    root = RootSpec(root_id="r", path=Path("C:/x"), kind="directory")
    assert root.route_matches("anything") is False


def test_future_root_config_only(tmp_path):
    """FIX-03/WU-702: a second directory root with the same adapter/profile
    works via config only — no code special case."""
    import yaml

    payload = {
        "schema_version": "1.0",
        "catalog_dir": "${PROJECT_ROOT}/.source_catalog",
        "roots": [
            {"root_id": "dropbox_stock", "path": "${PROJECT_ROOT}/stock",
             "kind": "directory", "adapter_id": "sidecar_filing_v1",
             "read_only": True, "reusable_for_filing": True,
             "routes": [{"include": ["重点关注/**"], "adapter_id": "sidecar_filing_v1"}]},
            {"root_id": "future_root", "path": "${PROJECT_ROOT}/future",
             "kind": "directory", "adapter_id": "sidecar_filing_v1",
             "read_only": True, "reusable_for_filing": True,
             "routes": [{"include": ["重点关注/**"], "adapter_id": "sidecar_filing_v1"}]},
        ],
    }
    cfg = tmp_path / "source_catalog.yaml"
    cfg.write_text(yaml.safe_dump(payload, allow_unicode=True), encoding="utf-8")
    config = load_catalog_config(cfg, project_root=tmp_path)
    dropbox = next(r for r in config.roots if r.root_id == "dropbox_stock")
    future = next(r for r in config.roots if r.root_id == "future_root")
    assert dropbox.route_matches("重点关注/x.pdf")
    assert future.route_matches("重点关注/x.pdf")  # identical behavior
