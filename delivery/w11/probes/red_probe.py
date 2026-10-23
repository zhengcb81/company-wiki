"""Reconstruct the base discovery module and reproduce the three W11 defects.

This is retained RED evidence for the W11 lane. It reads the pre-fix module
from git (commit ``0d7ada21``), builds a throwaway package, and runs the same
neutral probes against the base and the current working-tree module.

Run from the workspace root:

    python -X utf8 -B delivery/w11/probes/red_probe.py

Outputs JSON: base blob SHA-256, per-probe base/current candidates. No
network, no model, no production catalog, no workspace writes.
"""

from __future__ import annotations

import hashlib
import importlib
import json
import subprocess
import sys
import tempfile
from pathlib import Path

BASE_COMMIT = "0d7ada21"
BASE_MODULE = "src/company_wiki/source_catalog/official_discovery.py"
ROUTING = "src/company_wiki/source_catalog/narrative_routing.py"
WORKSPACE = Path(__file__).resolve().parents[3]

# Sealed faa5bf discover result (result_receipt, 2839 B); the titles of its
# three candidates are the derived minimal fixture used by probe D2.
SEALED_RESULT_SHA256 = (
    "1c33f18b24354c5a30e1d71258cf09c89ad23baec43bc42111082bc2fe7e7f52"
)

PROBES = {
    "D1-earnings-release-is-not-a-transcript": (
        '<a href="/er.pdf">Q2 2026 Earnings Release</a>'
        '<a href="/ep.pdf">Q2 2026 Earnings Presentation</a>'
        '<a href="/t.pdf">Q2 2026 Earnings Call Transcript</a>'
    ),
    "D2-legal-navigation-is-not-a-material": (
        '<a href="/privacy.pdf">隐私声明</a>'
        '<a href="/terms.pdf">使用条款</a>'
        '<a href="/privacy2.pdf">|  隐私声明</a>'
    ),
    "D3-generic-navigation-is-not-a-material": (
        '<a href="/c.html">Conference</a>'
        '<a href="/b.html">Business</a>'
        '<a href="/i.html">Investor</a>'
        '<a href="/ci.pdf">Contact Information</a>'
    ),
}


def _git_show(path: str) -> bytes:
    return subprocess.run(
        ["git", "-C", str(WORKSPACE), "show", f"{BASE_COMMIT}:{path}"],
        check=True,
        capture_output=True,
    ).stdout


def _build_base_package(root: Path) -> Path:
    package = root / "company_wiki" / "source_catalog"
    package.mkdir(parents=True)
    (root / "company_wiki" / "__init__.py").write_bytes(b"")
    (package / "__init__.py").write_bytes(b"")
    (package / "narrative_routing.py").write_bytes(_git_show(ROUTING))
    (package / "official_discovery.py").write_bytes(_git_show(BASE_MODULE))
    return root


def _probe(module, html: bytes):
    result = module.discover_official_documents(
        [
            {
                "url": "https://ir.example/ir",
                "original": html,
                "mime_type": "text/html",
                "capture_id": "red-probe",
            }
        ],
        entity="Neutral Instruments",
        as_of_date="2026-10-21",
        start_date="2026-01-01",
    )
    return [
        {
            "title": candidate["title"],
            "kind": candidate["document_kind"],
            "url": candidate["source_url"],
        }
        for candidate in result["candidates"]
    ]


def main() -> int:
    base_sha = hashlib.sha256(_git_show(BASE_MODULE)).hexdigest()
    with tempfile.TemporaryDirectory(prefix="w11-red-probe-") as folder:
        root = _build_base_package(Path(folder))
        sys.path.insert(0, str(root))
        for name in list(sys.modules):
            if name == "company_wiki" or name.startswith("company_wiki."):
                del sys.modules[name]
        base = importlib.import_module(
            "company_wiki.source_catalog.official_discovery"
        )
        base_probe = {
            name: _probe(base, html.encode("utf-8"))
            for name, html in PROBES.items()
        }
        sys.path.pop(0)
        for name in list(sys.modules):
            if name == "company_wiki" or name.startswith("company_wiki."):
                del sys.modules[name]
    sys.path.insert(0, str(WORKSPACE / "src"))
    current = importlib.import_module(
        "company_wiki.source_catalog.official_discovery"
    )
    current_probe = {
        name: _probe(current, html.encode("utf-8"))
        for name, html in PROBES.items()
    }
    print(
        json.dumps(
            {
                "schema_version": "w11-red-probe/1",
                "base_commit": BASE_COMMIT,
                "base_module_sha256": base_sha,
                "sealed_result_sha256": SEALED_RESULT_SHA256,
                "derived_minimal_fixture": True,
                "original_page_replay": False,
                "probes": {
                    name: {
                        "input_title_only": PROBES[name],
                        "base_candidates": base_probe[name],
                        "current_candidates": current_probe[name],
                    }
                    for name in PROBES
                },
            },
            ensure_ascii=False,
            indent=1,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
