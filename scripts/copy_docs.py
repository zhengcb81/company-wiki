"""Retired legacy source utility; current documents use the source catalog.

No implicit company, physical-root copying or in-place text mutation remains.
"""
from __future__ import annotations


def main(argv=None) -> int:
    del argv
    print("LEGACY SOURCE TOOL RETIRED: use company-wiki-source-catalog register/query")
    return 78


if __name__ == "__main__":
    raise SystemExit(main())
