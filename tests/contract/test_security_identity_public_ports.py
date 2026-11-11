"""Identity normalization is consumed through a stable owner port."""

from __future__ import annotations

import ast
from pathlib import Path

from company_wiki.source_catalog import (
    normalize_identity_text,
    security_listing_key,
)


SOURCE_ROOT = Path(__file__).resolve().parents[2] / "src" / "company_wiki" / "source_catalog"


def test_identity_normalizer_preserves_the_existing_canonical_rule():
    assert normalize_identity_text("Ａpple Inc.") == "appleinc"
    assert normalize_identity_text("ＭＳＦＴ １２３") == "msft123"
    assert normalize_identity_text("Élan Systems") == "élansystems"


def test_identity_consumers_do_not_import_private_security_identity_helpers():
    imports: list[str] = []
    for path in SOURCE_ROOT.rglob("*.py"):
        if path.name == "security_identity.py":
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if not isinstance(node, ast.ImportFrom):
                continue
            if node.module == "security_identity" and any(
                alias.name.startswith("_") for alias in node.names
            ):
                imports.append(f"{path.relative_to(SOURCE_ROOT)}:{node.lineno}")

    assert not imports, (
        "identity consumers must use the owner's public domain ports: "
        + ", ".join(imports)
    )


def test_listing_key_port_preserves_market_code_normalization():
    assert security_listing_key("5.HK", "HK") == "00005"
    assert security_listing_key("SH:600519", "CN") == "600519"


def test_identity_owner_lists_stable_helpers_in_its_public_exports():
    path = SOURCE_ROOT / "security_identity.py"
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    all_assignment = next(
        node
        for node in tree.body
        if isinstance(node, ast.Assign)
        and any(isinstance(target, ast.Name) and target.id == "__all__" for target in node.targets)
    )
    exported = set(ast.literal_eval(all_assignment.value))

    assert {
        "normalize_identity_text",
        "security_listing_key",
        "cross_market_issuer_link_ids",
    } <= exported
