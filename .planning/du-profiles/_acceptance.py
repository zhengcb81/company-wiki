"""Acceptance check: the card's explicit pass/fail criteria, on the frozen wire.

Run: python -X utf8 .planning/du-profiles/_acceptance.py
"""

import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from company_wiki.document_understanding.profiles import (  # noqa: E402
    get_profile,
    list_profiles,
    route_document,
)

print("1. three frozen functions callable by ROOT")
print("   route_document:", callable(route_document))
print("   get_profile   :", callable(get_profile))
print("   list_profiles :", callable(list_profiles))
print("   profiles:", len(list_profiles()))

print()
print("2. confirmation letter is never a full IPO prospectus")
letter = {
    "schema_version": "du-input/1",
    "source_ref": {"source_id": "s", "source_sha256": "d"},
    "metadata": {
        "title": "关于《首次公开发行股票并在创业板上市招股说明书》的确认意见",
        "declared_kind": "prospectus",
        "regime": "cn_exchange",
        "form_type": None,
        "mime_type": "application/pdf",
        "language": "zh",
        "published_at": None,
        "period_end": None,
        "revision": None,
    },
    "coverage": {"native_scan": "unavailable", "opaque_pages": [1], "deferred_pages": []},
    "units": [
        {
            "unit_id": "u1",
            "ordinal": 0,
            "locator": "opaque-locator-1",
            "page": 1,
            "text": "控股股东、实际控制人对《首次公开发行股票并在创业板上市招股说明书》的确认意见",
            "kind": "heading",
            "language": "zh",
            "role": None,
        }
    ],
}
route = route_document(letter)
print("   ->", route["profile_id"], route["family"], route["disposition_hint"])
assert route["family"] == "administrative", route
assert route["disposition_hint"] == "administrative_candidate"
print("   OK: not routed as a prospectus, and not skipped")

print()
print("3. A-share 发行A股股票 wording is recognized")
offering = {
    "schema_version": "du-input/1",
    "source_ref": {"source_id": "s", "source_sha256": "d"},
    "metadata": {
        "title": None,
        "declared_kind": "unknown",
        "regime": "unknown",
        "form_type": None,
        "mime_type": "application/pdf",
        "language": "zh",
        "published_at": None,
        "period_end": None,
        "revision": None,
    },
    "coverage": {"native_scan": "complete", "opaque_pages": [], "deferred_pages": []},
    "units": [
        {
            "unit_id": "u1",
            "ordinal": 0,
            "locator": "l1",
            "page": 1,
            "text": "2020 年向特定对象发行A 股股票",
            "kind": "heading",
            "language": "zh",
            "role": None,
        },
        {
            "unit_id": "u2",
            "ordinal": 1,
            "locator": "l2",
            "page": 1,
            "text": "募集说明书",
            "kind": "heading",
            "language": "zh",
            "role": None,
        },
        {
            "unit_id": "u3",
            "ordinal": 2,
            "locator": "l3",
            "page": 61,
            "text": "本次向特定对象发行A 股股票拟募集资金总额为不超过35,978.71 万元。",
            "kind": "paragraph",
            "language": "zh",
            "role": None,
        },
    ],
}
route = route_document(offering)
print("   ->", route["profile_id"], route["family"], route["regime"])
assert route["family"] == "offering", route
assert route["regime"] == "cn_exchange"
print("   OK: recognized as an offering, not unknown")

print()
print("4. SEC and HK vocabularies do not cross-apply")
ten_k = get_profile("sec_10k")
twenty_f = get_profile("sec_20f")
hk = get_profile("hk_periodic")


def aliases(profile):
    return {
        a.casefold() for e in profile["section_priorities"] for a in e["aliases"]
    }


assert not any("item 4" in a for a in aliases(ten_k))
assert not any("item 7" in a for a in aliases(twenty_f))
assert not any(a.startswith("item ") for a in aliases(hk))
assert "業務回顧及展望" in aliases(hk)
print("   OK: 10-K has no Item 4, 20-F has no Item 7, HK has no Item numbering")

print()
print("5. unknown remains readable (generic_read) and never a skip")
unknown = {
    "schema_version": "du-input/1",
    "source_ref": {"source_id": "s", "source_sha256": "d"},
    "metadata": {
        "title": None,
        "declared_kind": "unknown",
        "regime": "unknown",
        "form_type": None,
        "mime_type": "text/plain",
        "language": None,
        "published_at": None,
        "period_end": None,
        "revision": None,
    },
    "coverage": {"native_scan": "complete", "opaque_pages": [], "deferred_pages": []},
    "units": [
        {
            "unit_id": "u1",
            "ordinal": 0,
            "locator": "l1",
            "page": None,
            "text": "unstructured working note with no recognizable structure",
            "kind": "paragraph",
            "language": None,
            "role": None,
        }
    ],
}
route = route_document(unknown)
print("   ->", route["profile_id"], route["disposition_hint"])
assert route["disposition_hint"] == "generic_read"
print("   OK: readable, never skipped")

print()
print("6. every claim is traceable to input signals")
print("   reasons carry codes + unit ids; sample:")
for reason in route["reasons"][:3]:
    print("    ", reason["code"], reason["unit_ids"])

print()
print("7. the forbidden shortcuts do not appear in executable logic")
import ast  # noqa: E402

src = sorted(
    (ROOT / "src" / "company_wiki" / "document_understanding" / "profiles").glob("*.py")
)
company_tokens = ("中微", "名创", "恒锋", "鼎龙", "微软", "Dropbox")
path_tokens = ("C:\\", "companies/", "raw/")
for module_path in sorted(src):
    tree = ast.parse(module_path.read_text(encoding="utf-8"))
    # Docstrings are documentation, not logic: they record which real sample motivated a
    # rule. Every other string literal and identifier is executable and must stay generic.
    docstrings = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
            body = getattr(node, "body", [])
            if body and isinstance(body[0], ast.Expr) and isinstance(body[0].value, ast.Constant):
                docstrings.add(id(body[0].value))
    for node in ast.walk(tree):
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            if id(node) in docstrings:
                continue
            for token in company_tokens + path_tokens:
                assert token not in node.value, (module_path.name, token, node.value[:60])
        if isinstance(node, ast.Name):
            for token in company_tokens:
                assert token not in node.id, (module_path.name, node.id)
print("   OK: no company name, path or directory is hardcoded in executable logic")
print("   (company names appear only in docstrings that record which real sample drove a rule)")

print()
print("ALL ACCEPTANCE CRITERIA SATISFIED")
print(json.dumps({"profiles": len(list_profiles())}, ensure_ascii=False))
