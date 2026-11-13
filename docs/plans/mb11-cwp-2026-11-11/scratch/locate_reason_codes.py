"""Scratch probe: locate emission sites of this card's reason codes."""
import re
from pathlib import Path

SRC = Path(r"C:\Users\郑曾波\Projects\mb11-cwp\src\company_wiki\source_catalog")

MINE = [
    "canonical_browse_unavailable",
    "stream_consumer_gone",
    "ambiguous",
    "available",
    "conflict",
    "not_found",
    "unavailable",
    "legacy_source_current_version_verified",
    "legacy_source_multiple_versions",
    "legacy_source_not_registered",
    "legacy_source_size_changed",
    "registered_location_budget_exceeded",
    "registered_location_deadline",
]

# Files this card added or changed inside source_catalog.
CHANGED = {
    "public_canonical_browser.py",
    "public_canonical_browser_cli.py",
    "public_legacy_source_link.py",
    "public_legacy_source_link_cli.py",
    "public_legacy_source_recovery.py",
    "public_legacy_source_recovery_cli.py",
    "public_source_readiness.py",
    "public_source_readiness_cli.py",
    "source_stream_cli.py",
    "cn_primary_issuer.py",
}

for code in MINE:
    hits = []
    for path in sorted(SRC.rglob("*.py")):
        if path.name not in CHANGED and path.parent == SRC:
            continue
        if path.name not in CHANGED:
            continue
        for number, line in enumerate(
            path.read_text(encoding="utf-8").splitlines(), 1
        ):
            if re.search(rf'["\']{re.escape(code)}["\']', line):
                hits.append(f"{path.name}:{number}: {line.strip()[:100]}")
    print(f"\n{code} ({len(hits)}):")
    for hit in hits[:4]:
        print("   ", hit)
