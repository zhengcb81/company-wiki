"""C-node probe: route the plan's real observed document shapes and report the outcome.

This script reads only the plan's own bounded observations (``sample_manifest.json`` +
``sample_observations.json.gz``) from the read-only main checkout. It builds ``du-input/1``
observations from the recorded titles, TOC lines, heading lines and short excerpts, then
prints what this package decided for each real sample.

It writes nothing and touches no original. Run it to reproduce the C-node table:

    python -X utf8 .planning/du-profiles/_cnode_probe.py
"""

from __future__ import annotations

import gzip
import json
import pathlib
import sys

PLAN = pathlib.Path(
    r"C:\Users\郑曾波\Projects\company-wiki\docs\plans\document-understanding-2026-10-13"
)
WORKTREE = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(WORKTREE / "src"))

from company_wiki.document_understanding.profiles import route_document  # noqa: E402

# The expected family for each real sample, stated by the plan's own manifest. Recorded
# here as an oracle so the probe reports agreement and disagreement honestly.
#
# Two manifest labels are deliberately corrected against the recorded body evidence, and
# the correction is the point of the probe rather than a convenience:
#
# * ``cn-ir-policy`` -- ``sample_manifest.json`` calls it ``ir_policy`` and the file name
#   says 投资者关系管理制度, but the observed body is an 投资者关系活动记录表 (a
#   ``业绩说明会`` Q&A record). ``findings.md`` records the same file as an activity
#   record, so the body wins and the expected family is ``investor_qa``.
# * ``cn-ipo-confirmation`` -- a single opaque page with empty native text; the title is
#   the only evidence, so ``administrative`` is the honest expectation.
EXPECTED = {
    "cn-h1": "interim",
    "cn-annual": "annual",
    "cn-ipo": "prospectus",
    "hk-release": "results_release",
    "hk-deck": "presentation",
    "us-release": "results_release",
    "cn-q-business": "quarterly",
    "cn-q-sparse": "quarterly",
    "cn-convertible": "offering",
    "cn-equity": "offering",
    "cn-ipo-confirmation": "administrative",
    "cn-ir": "investor_qa",
    "cn-ir-policy": "investor_qa",
    "hk-annual": "annual",
    "hk-interim": "interim",
    "hk-ipo": "prospectus",
    "us-10k": "annual",
    "us-10q": "quarterly",
    "us-20f": "annual",
    "us-txt": "earnings_call",
}


def units_from_sample(sample: dict) -> list[dict]:
    """Build du-input/1 units from the recorded bounded observations."""
    units: list[dict] = []
    ordinal = 0

    def add(text: str, kind: str, page: int | None) -> None:
        nonlocal ordinal
        if not isinstance(text, str) or not text.strip():
            return
        units.append(
            {
                "unit_id": f"u{ordinal + 1}",
                "ordinal": ordinal,
                "locator": f"opaque-locator-{ordinal + 1}",
                "page": page,
                "text": text,
                "kind": kind,
                "language": None,
                "role": None,
            }
        )
        ordinal += 1

    for entry in sample.get("toc") or []:
        if isinstance(entry, list) and len(entry) >= 2:
            add(str(entry[1]), "toc", None)
    for entry in sample.get("heading_pages") or []:
        page = entry.get("page") if isinstance(entry, dict) else None
        for heading in (entry.get("headings") or []) if isinstance(entry, dict) else []:
            add(str(heading), "heading", page)
    for entry in sample.get("read_pages") or []:
        if isinstance(entry, dict):
            add(str(entry.get("excerpt") or ""), "paragraph", entry.get("page"))
    for entry in sample.get("read_passages") or []:
        if isinstance(entry, dict):
            add(str(entry.get("excerpt") or ""), "paragraph", entry.get("page"))
    return units


def main() -> int:
    manifest = json.loads((PLAN / "sample_manifest.json").read_text(encoding="utf-8"))
    with gzip.open(PLAN / "sample_observations.json.gz", "rt", encoding="utf-8") as handle:
        observations = json.load(handle)
    by_id = {sample["id"]: sample for sample in observations["samples"]}

    print(f"{'sample':22} {'expected':16} {'profile':16} {'family':16} {'conf':8} disp")
    print("-" * 100)
    agree = 0
    rows = []
    for entry in manifest["samples"]:
        sample_id = entry["id"]
        sample = by_id.get(sample_id)
        if sample is None:
            print(f"{sample_id:22} MISSING OBSERVATION")
            continue
        units = units_from_sample(sample)
        observation = {
            "schema_version": "du-input/1",
            "source_ref": {
                "source_id": f"sample:{sample_id}",
                "source_sha256": sample.get("sha256") or "opaque",
            },
            "metadata": {
                "title": None,
                "declared_kind": sample.get("title_only_kind") or "unknown",
                "regime": "unknown",
                "form_type": None,
                "mime_type": "application/pdf",
                "language": None,
                "published_at": None,
                "period_end": None,
                "revision": None,
            },
            "coverage": {
                "native_scan": "unavailable"
                if (sample.get("native_text_empty_pages") or 0) and not units
                else "complete",
                "opaque_pages": [],
                "deferred_pages": [],
            },
            "units": units,
        }
        route = route_document(observation)
        expected = EXPECTED.get(sample_id, "?")
        ok = route["family"] == expected
        agree += ok
        rows.append((sample_id, expected, route, len(units), ok))
        print(
            f"{sample_id:22} {expected:16} {route['profile_id']:16} "
            f"{route['family']:16} {route['confidence']:8} {route['disposition_hint']}"
        )

    total = len(rows)
    print("-" * 100)
    print(f"family agreement: {agree}/{total}")
    print()
    print("disagreements and low-confidence rows:")
    for sample_id, expected, route, unit_count, ok in rows:
        if not ok or route["confidence"] in {"low", "unknown"}:
            codes = sorted({reason["code"] for reason in route["reasons"]})
            print(
                f"  {sample_id:22} units={unit_count:5} expected={expected:16} "
                f"got={route['family']:16} conf={route['confidence']:8} codes={codes}"
            )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
