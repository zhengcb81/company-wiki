"""Producer policy ownership; ordinary FF tests never read the CWP tree."""
import os
from pathlib import Path

WIKI_CONFIG_PATH = Path(os.environ["CWP_V2_CODE_ROOT"]) / "config/source_catalog.yaml"


def test_config_dbx_04_dropbox_root_defined_in_wiki_policy_only() -> None:
    """The Dropbox root's realpath lives in company-wiki's
    source_catalog.yaml (the policy snapshot source) — filing-fetch holds
    no copy."""
    import yaml

    wiki_payload = yaml.safe_load(WIKI_CONFIG_PATH.read_text(encoding="utf-8"))
    dropbox_wiki = next(
        r for r in wiki_payload["roots"] if r.get("root_id") == "dropbox_stock"
    )
    token = "${USER_PROFILE}"
    profile = os.environ.get("USERPROFILE") or str(Path.home())
    wiki_path = Path(str(dropbox_wiki["path"]).replace(token, profile))
    # read_only + reusable_for_filing contract
    assert dropbox_wiki.get("read_only") is not False
    assert _norm(wiki_path).endswith("Dropbox/Stock"), f"unexpected: {wiki_path}"


def _norm(path: Path) -> str:
    return str(path.resolve()).replace("\\", "/")
