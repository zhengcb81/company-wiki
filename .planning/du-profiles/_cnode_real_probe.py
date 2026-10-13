"""C-node probe over REAL originals: what does ``route_document`` actually decide?

This is the C-node companion to ``_cnode_probe.py``. Where that script replays the plan's
own *recorded* bounded observations, this one opens the real originals listed in
``docs/plans/document-understanding-2026-10-13/sample_manifest.json`` in the read-only main
CWP checkout, parses them with the EXISTING production parser, and reports the route.

Rules this script obeys:

* originals are opened read-only and are NEVER copied into this worktree;
* the only thing written is the bounded C-node evidence under
  ``.planning/du-profiles/c-evidence/``;
* evidence excerpts are truncated to ``MAX_EVIDENCE_CHARS_PER_DOC`` (8 KiB) per document;
* every original's SHA-256 is verified against the manifest expectation BEFORE parsing, and
  a document whose SHA does not match is reported ``UNAVAILABLE`` rather than parsed;
* a document that cannot be read at all is reported ``UNAVAILABLE``, never ``PASS``.

Run::

    python -X utf8 .planning/du-profiles/_cnode_real_probe.py

Exit code 0 means the probe ran to completion (including honest UNAVAILABLE rows). It is
not a PASS/FAIL gate on the router: the point is to record what really happens.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import sys
import time
from typing import Any

WORKTREE = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(WORKTREE / "src"))

MAIN_CWP = pathlib.Path(r"C:\Users\郑曾波\Projects\company-wiki")
OUT_DIR = WORKTREE / ".planning" / "du-profiles" / "c-evidence"

#: Hard cap on how much original text may appear in the evidence file, per document.
MAX_EVIDENCE_CHARS_PER_DOC = 8 * 1024

#: Cap on how many bounded excerpts we keep per document.
MAX_EXCERPTS_PER_DOC = 24

#: Cap on a single excerpt's length.
MAX_EXCERPT_CHARS = 400

#: Bounded unit count fed to the router so the C-node run stays cheap on a 246-page PDF.
MAX_UNITS_FOR_ROUTE = 4000


# --------------------------------------------------------------------------------------
# The real originals, with the SHA-256 the plan's manifest records for them.
#
# ``expect_*`` fields record what the CARD says the correct answer is, so a disagreement
# is visible rather than silently normalised away.
# --------------------------------------------------------------------------------------

REAL_ORIGINALS: tuple[dict[str, Any], ...] = (
    {
        "sample_id": "cn-ipo-confirmation-dinglong",
        "path": r"companies\鼎龙股份\raw\prospectus"
        r"\鼎龙股份：控股股东、实际控制人对《湖北鼎龙化学股份有限公司首次公开发行股票并在创业板上市招股说明书》的确认意见.pdf",
        "sha256": "0829538f0707650db99852c5e269abe9e0d7e558d54d93e0a2c0be15fe0d0fa7",
        "carrier": "pdf",
        "metadata_title": "鼎龙股份：控股股东、实际控制人对《湖北鼎龙化学股份有限公司首次公开发行股票并在创业板上市招股说明书》的确认意见",
        # The legacy title-regex router -- the defect this lane exists to fix -- labels this
        # ``prospectus`` purely from 招股说明书 in the title, even though it is a one-page
        # scanned confirmation letter with zero native text.
        "legacy_title_only_kind": "prospectus",
        "expect_family": "administrative",
        "expect_not_family": "prospectus",
        "headline": "defect-a: confirmation letter mistyped as prospectus from its title",
    },
    {
        "sample_id": "cn-equity-offering-hengfeng",
        "path": r"companies\恒锋工具\raw\research"
        r"\恒锋工具：2020年向特定对象发行A股股票募集说明书（注册稿）.PDF",
        "sha256": "37f7c62de54b33eb8f978c3ee5525471c9c7150b9cbaedc10901aa8280550d2e",
        "carrier": "pdf",
        "metadata_title": "恒锋工具：2020年向特定对象发行A股股票募集说明书（注册稿）",
        # The legacy title regex looks for 发行股票; 发行A股股票 does not match, so the
        # legacy router fell through to ``unknown``.
        "legacy_title_only_kind": "unknown",
        "expect_family": "offering",
        "expect_not_family": None,
        "headline": "defect-b: 发行A股股票募集说明书 routed to unknown from the title alone",
    },
    {
        "sample_id": "hk-annual-miniso-2024",
        "path": r"C:\Users\郑曾波\Dropbox\Stock\消费品\名创优品\2024年度报告（港股）.pdf",
        "absolute": True,
        "sha256": "07f4937e0558fc31189a56236313ad93c1cef4182adb10ebaf4f355acb9bf1cf",
        "carrier": "pdf",
        "metadata_title": "名创优品 2024年度报告（港股）",
        "legacy_title_only_kind": "annual_report",
        "expect_family": "annual",
        "expect_not_family": None,
        "headline": "HK bilingual annual report; must never be routed by SEC item numbering",
    },
    {
        "sample_id": "cn-ir-wanrun-20260515",
        "path": r"companies\万润股份\raw\research\万润股份：投资者关系活动记录表20260515.pdf",
        "sha256": "221467c15a24180205a8226f96fea9bda0262c866d5ba8aa31889ec96e6466d7",
        "carrier": "pdf",
        "metadata_title": "万润股份：投资者关系活动记录表20260515",
        "legacy_title_only_kind": "unknown",
        "expect_family": "investor_qa",
        "expect_not_family": None,
        "headline": "IR activity record with a real negation in a Q&A pair",
    },
    {
        "sample_id": "cn-quarterly-amec-2026q1",
        "path": r"companies\中微公司\raw\financial_reports\中微公司：2026年第一季度报告.pdf",
        "sha256": "ab7bb0076b2a3fb42ebca7b54d1b167a790221e394613ce544e275b249eb3268",
        "carrier": "pdf",
        "metadata_title": "中微公司：2026年第一季度报告",
        "legacy_title_only_kind": "quarterly_report",
        "expect_family": "quarterly",
        "expect_not_family": "annual",
        "headline": "A-share quarterly with real product narrative; must not be skipped as a whole",
    },
    {
        "sample_id": "us-10k-msft-2025",
        "path": r"companies\微软\raw\financial_reports\annual\微软_10-K_2025.htm",
        "sha256": "99d693f6c1544144ebeee92954f151a85bc62111837530a42855953bc01d0bbe",
        "carrier": "html",
        "metadata_title": "微软_10-K_2025",
        "legacy_title_only_kind": "annual_report",
        "expect_family": "annual",
        "expect_not_family": None,
        "headline": "SEC 10-K HTML: SEC item numbering, never HK/A-share section vocabulary",
    },
    {
        "sample_id": "us-earnings-call-msft-q4fy26",
        "path": r"companies\Microsoft\raw\transcripts\MSFT_Q4_2026_earnings_call.txt",
        "sha256": "4ac3b4f0fa1be928b56b4ef9775cac694a1712d46785bb1fa28d2a6a68d7852a",
        "carrier": "txt",
        "metadata_title": "MSFT_Q4_2026_earnings_call",
        "legacy_title_only_kind": "investor_call_transcript",
        "expect_family": "earnings_call",
        "expect_not_family": None,
        "headline": "TXT transcript: speaker turns, analyst questions vs management answers",
    },
)


def sha256_of(path: pathlib.Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def resolve(entry: dict[str, Any]) -> pathlib.Path:
    if entry.get("absolute"):
        return pathlib.Path(entry["path"])
    return MAIN_CWP / entry["path"]


# --------------------------------------------------------------------------------------
# Carriers -> du-input/1 units using the EXISTING production parsers only.
# --------------------------------------------------------------------------------------


def units_from_pdf(path: pathlib.Path, sha: str, source_id: str) -> tuple[list[dict], dict]:
    """Parse a real PDF with the existing narrative parser. No new parser is written."""
    from company_wiki.source_catalog.narrative_evidence import parse_pdf

    started = time.perf_counter()
    result = parse_pdf(path, source_id=source_id, source_sha256=sha)
    elapsed = time.perf_counter() - started

    units: list[dict] = []
    for index, unit in enumerate(result.units):
        text = unit.raw_text or ""
        if index >= MAX_UNITS_FOR_ROUTE:
            break
        units.append(
            {
                "unit_id": f"u{index + 1}",
                "ordinal": index,
                "locator": str(getattr(unit, "unit_id", None) or unit.coordinates.locator()),
                "page": getattr(unit.coordinates, "page_number", None),
                "text": text,
                "kind": _map_unit_kind(unit.unit_kind),
                "language": getattr(unit, "language", None),
                "role": getattr(unit, "source_role", None),
            }
        )

    facts = {
        "parser": "company_wiki.source_catalog.narrative_evidence.parse_pdf",
        "parse_seconds": round(elapsed, 3),
        "page_count": result.page_count,
        "pages_read": result.pages_read,
        "opaque_pages": list(result.opaque_pages),
        "total_units": len(result.units),
        "units_fed": len(units),
        "native_scan": "unavailable" if not units else ("partial" if result.opaque_pages else "complete"),
        "errors": [str(error) for error in result.errors][:10],
    }
    return units, facts


def _map_unit_kind(kind: str) -> str:
    """Map production unit kinds onto the frozen du-input kind hints (hints only)."""
    if kind in {"pdf_text_block"}:
        return "paragraph"
    if kind in {"pdf_table_row", "pdf_table_qa_fragment"}:
        return "table_row"
    return kind or "paragraph"


def units_from_html(path: pathlib.Path, sha: str, source_id: str) -> tuple[list[dict], dict]:
    """Parse real HTML with the existing normalizer; DOM order is preserved."""
    from company_wiki.document_normalization import NormalizationLimits, normalize_document

    data = path.read_bytes()
    started = time.perf_counter()
    document = normalize_document(
        data,
        source_id=source_id,
        source_sha256=sha,
        mime_type="text/html",
        limits=NormalizationLimits(),
    )
    elapsed = time.perf_counter() - started

    units: list[dict] = []
    for index, unit in enumerate(document.units):
        if index >= MAX_UNITS_FOR_ROUTE:
            break
        # ``NormalizedDocument.units`` yields the same ``NarrativeUnit`` shape the PDF
        # parser yields: text lives on ``raw_text``, chapter hints on ``metadata``.
        hints = unit.metadata if isinstance(unit.metadata, dict) else {}
        units.append(
            {
                "unit_id": f"u{index + 1}",
                "ordinal": index,
                "locator": str(getattr(unit, "unit_id", None) or unit.coordinates.locator()),
                "page": getattr(unit.coordinates, "page_number", None),
                "text": getattr(unit, "raw_text", "") or "",
                "kind": _map_html_kind(getattr(unit, "unit_kind", None)),
                "language": getattr(unit, "language", None),
                "role": getattr(unit, "source_role", None),
                "hints": {
                    "dom_path": hints.get("dom_path"),
                    "heading_level": _heading_level_from_metadata(hints),
                },
            }
        )

    facts = {
        "parser": "company_wiki.document_normalization.normalize_document(text/html)",
        "parse_seconds": round(elapsed, 3),
        "page_count": None,
        "total_units": len(document.units),
        "units_fed": len(units),
        "native_scan": "unavailable" if not units else "complete",
        "errors": [str(error) for error in getattr(document, "errors", ())][:10],
    }
    return units, facts


def _map_html_kind(kind: Any) -> str:
    text = str(kind or "")
    if "heading" in text:
        return "heading"
    if "table" in text:
        return "table_row"
    if "list" in text:
        return "list_item"
    return "paragraph"


def _heading_level_from_metadata(metadata: dict) -> int | None:
    """Surface a real DOM heading level when the normalizer recorded one."""
    for key in ("heading_level", "headingLevel", "level"):
        value = metadata.get(key)
        if isinstance(value, int) and not isinstance(value, bool):
            return value
    tag = metadata.get("tag_name") or metadata.get("tag")
    if isinstance(tag, str) and len(tag) == 2 and tag[0].lower() == "h" and tag[1].isdigit():
        return int(tag[1])
    return None


def units_from_txt(path: pathlib.Path) -> tuple[list[dict], dict]:
    """Split a real transcript TXT on blank lines; one physical block per unit."""
    started = time.perf_counter()
    text = path.read_text(encoding="utf-8", errors="replace")
    elapsed = time.perf_counter() - started

    blocks = [block.strip() for block in text.replace("\r\n", "\n").split("\n\n")]
    blocks = [block for block in blocks if block]
    units: list[dict] = []
    for index, block in enumerate(blocks):
        if index >= MAX_UNITS_FOR_ROUTE:
            break
        units.append(
            {
                "unit_id": f"u{index + 1}",
                "ordinal": index,
                "locator": f"line:{index + 1}",
                "page": None,
                "text": block,
                "kind": "paragraph",
                "language": "en",
                "role": None,
            }
        )

    facts = {
        "parser": "utf-8 read + blank-line blocking (carrier read only, no new parser)",
        "parse_seconds": round(elapsed, 3),
        "page_count": None,
        "total_units": len(units),
        "units_fed": len(units),
        "native_scan": "unavailable" if not units else "complete",
        "errors": [],
    }
    return units, facts


# --------------------------------------------------------------------------------------
# Bounded evidence excerpts
# --------------------------------------------------------------------------------------


def bounded_excerpts(units: list[dict]) -> tuple[list[dict], int]:
    """Keep a bounded, spread-out sample of the parsed text for the evidence file.

    Excerpts are chosen across the document span (head / middle / tail) so the evidence
    file shows what the router actually saw without copying the document.
    """
    non_blank = [unit for unit in units if unit["text"].strip()]
    if not non_blank:
        return [], 0

    count = min(MAX_EXCERPTS_PER_DOC, len(non_blank))
    step = len(non_blank) / count
    chosen: list[dict] = []
    seen: set[str] = set()
    for index in range(count):
        unit = non_blank[min(int(index * step), len(non_blank) - 1)]
        if unit["unit_id"] in seen:
            continue
        seen.add(unit["unit_id"])
        chosen.append(
            {
                "unit_id": unit["unit_id"],
                "page": unit["page"],
                "locator": unit["locator"],
                "kind": unit["kind"],
                "excerpt": unit["text"].strip()[:MAX_EXCERPT_CHARS],
            }
        )

    budget = MAX_EVIDENCE_CHARS_PER_DOC
    kept: list[dict] = []
    used = 0
    for entry in chosen:
        cost = len(entry["excerpt"]) + len(entry["unit_id"]) + 32
        if used + cost > budget:
            break
        used += cost
        kept.append(entry)
    return kept, used


# --------------------------------------------------------------------------------------
# Routing
# --------------------------------------------------------------------------------------


def build_observation(
    entry: dict[str, Any],
    sha: str,
    units: list[dict],
    facts: dict,
) -> dict:
    return {
        "schema_version": "du-input/1",
        "source_ref": {"source_id": entry["sample_id"], "source_sha256": sha},
        "metadata": {
            "title": entry["metadata_title"],
            "declared_kind": entry["legacy_title_only_kind"],
            "regime": "unknown",
            "form_type": None,
            "mime_type": {
                "pdf": "application/pdf",
                "html": "text/html",
                "txt": "text/plain",
            }[entry["carrier"]],
            "language": None,
            "published_at": None,
            "period_end": None,
            "revision": None,
        },
        "coverage": {
            "native_scan": facts["native_scan"],
            "opaque_pages": facts.get("opaque_pages") or [],
            "deferred_pages": [],
        },
        "units": units,
    }


def legacy_title_route(entry: dict[str, Any]) -> str:
    """What the EXISTING production title router says -- the baseline being fixed."""
    from company_wiki.source_catalog.narrative_evidence import classify_document_kind

    return classify_document_kind(entry["metadata_title"])


def probe_entry(entry: dict[str, Any], router) -> dict:
    path = resolve(entry)
    row: dict[str, Any] = {
        "sample_id": entry["sample_id"],
        "carrier": entry["carrier"],
        "headline": entry["headline"],
        "expected_family": entry["expect_family"],
        "expected_not_family": entry["expect_not_family"],
        "manifest_sha256": entry["sha256"],
    }

    if not path.exists():
        row["status"] = "UNAVAILABLE"
        row["unavailable_reason"] = "original not present at the recorded path"
        row["path"] = str(path)
        return row

    actual_sha = sha256_of(path)
    row["actual_sha256"] = actual_sha
    row["sha_matches_manifest"] = actual_sha == entry["sha256"]
    if not row["sha_matches_manifest"]:
        row["status"] = "UNAVAILABLE"
        row["unavailable_reason"] = (
            "SHA-256 does not match the plan manifest; refusing to parse a changed original"
        )
        return row

    row["path"] = str(path)
    row["bytes"] = path.stat().st_size
    row["mtime_utc"] = path.stat().st_mtime

    try:
        if entry["carrier"] == "pdf":
            units, facts = units_from_pdf(path, actual_sha, entry["sample_id"])
        elif entry["carrier"] == "html":
            units, facts = units_from_html(path, actual_sha, entry["sample_id"])
        else:
            units, facts = units_from_txt(path)
    except Exception as error:  # honest failure, never a fake PASS
        row["status"] = "UNAVAILABLE"
        row["unavailable_reason"] = f"parse failed: {type(error).__name__}: {error}"
        return row

    row["parse"] = facts
    non_blank = sum(1 for unit in units if unit["text"].strip())
    row["units_total"] = len(units)
    row["units_non_blank"] = non_blank
    row["native_text_empty"] = non_blank == 0

    # What the legacy title-only router says vs what this package says.
    try:
        row["legacy_title_route"] = legacy_title_route(entry)
    except Exception as error:
        row["legacy_title_route"] = f"UNAVAILABLE: {type(error).__name__}: {error}"

    observation = build_observation(entry, actual_sha, units, facts)
    started = time.perf_counter()
    route = router(observation)
    row["route_seconds"] = round(time.perf_counter() - started, 4)
    row["route"] = route

    family = route["family"]
    row["family_matches_expected"] = family == entry["expect_family"]
    row["mislabels_expected_not_family"] = (
        entry["expect_not_family"] is not None and family == entry["expect_not_family"]
    )
    row["status"] = "OBSERVED"

    excerpts, used = bounded_excerpts(units)
    row["evidence_excerpts"] = excerpts
    row["evidence_excerpt_chars"] = used
    return row


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", default=None, help="evidence JSON output path")
    args = parser.parse_args()

    from company_wiki.document_understanding.profiles import route_document

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    output = pathlib.Path(args.output) if args.output else OUT_DIR / "c-node-real-originals.json"

    started = time.perf_counter()
    rows = [probe_entry(entry, route_document) for entry in REAL_ORIGINALS]
    elapsed = round(time.perf_counter() - started, 3)

    observed = [row for row in rows if row["status"] == "OBSERVED"]
    unavailable = [row for row in rows if row["status"] == "UNAVAILABLE"]
    agree = [row for row in observed if row["family_matches_expected"]]
    wrong = [row for row in observed if not row["family_matches_expected"]]
    forbidden = [row for row in observed if row["mislabels_expected_not_family"]]

    summary = {
        "documents_probed": len(rows),
        "observed": len(observed),
        "unavailable": len(unavailable),
        "family_agreement": len(agree),
        "family_disagreement": len(wrong),
        "headline_defect_regressions": len(forbidden),
        "elapsed_seconds": elapsed,
        "max_evidence_chars_per_doc": MAX_EVIDENCE_CHARS_PER_DOC,
        "originals_copied_into_worktree": 0,
    }

    payload = {
        "schema_version": "du-cnode-evidence/1",
        "generated_by": ".planning/du-profiles/_cnode_real_probe.py",
        "worktree": str(WORKTREE),
        "note": (
            "Real-original C-node evidence. Excerpts are bounded to "
            f"{MAX_EVIDENCE_CHARS_PER_DOC} bytes per document; no original was copied into "
            "this worktree. UNAVAILABLE rows mean the original could not be read, never PASS."
        ),
        "summary": summary,
        "documents": rows,
    }
    output.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    # --- console report -----------------------------------------------------------
    print(f"{'sample':34} {'legacy':18} {'got family':16} {'conf':8} {'disp':24} ok")
    print("-" * 120)
    for row in rows:
        if row["status"] != "OBSERVED":
            print(f"{row['sample_id']:34} UNAVAILABLE -- {row['unavailable_reason']}")
            continue
        legacy = str(row["legacy_title_route"])[:17]
        mark = "OK" if row["family_matches_expected"] else "**"
        if row["mislabels_expected_not_family"]:
            mark = "!!"
        print(
            f"{row['sample_id']:34} {legacy:18} {row['route']['family']:16} "
            f"{row['route']['confidence']:8} {row['route']['disposition_hint']:24} {mark}"
        )
    print("-" * 120)
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    print(f"\nevidence -> {output}")
    if unavailable:
        print("\nUNAVAILABLE (not PASS):")
        for row in unavailable:
            print(f"  {row['sample_id']}: {row['unavailable_reason']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
