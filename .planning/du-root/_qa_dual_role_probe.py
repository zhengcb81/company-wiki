"""Diagnose the QA dual-role-set question (DU-S-ADAPT-5) on a real original.

The parser emits every text fragment on a Q&A page twice:

* flat ``pdf_text_block`` units whose ``source_role`` is ``qa_text_shadow`` (the text layer);
* structured role units (``investor_question`` / ``management``) built from the detected Q&A
  structure.

Production selection already excludes ``qa_text_shadow`` from candidates
(``narrative_candidates._EXCLUDED_ROLES``), so the convention is "structured roles win, the
shadow is the duplicate". This script checks what the new layer actually does with both
copies: whether they reach the observation, whether structure pairs them, and whether the
packages double-count.

Run: python -X utf8 .planning/du-root/_qa_dual_role_probe.py
"""

from __future__ import annotations

import hashlib
import json
import pathlib
import sys
from collections import Counter

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from company_wiki.document_understanding import understand_units  # noqa: E402
from company_wiki.source_catalog.narrative_evidence import parse_pdf  # noqa: E402

BINDINGS = ROOT / ".planning" / "du-root" / "bindings.local.json"
SAMPLE = "cn-ir"


def main() -> int:
    bindings = json.loads(BINDINGS.read_text(encoding="utf-8"))
    entry = bindings[SAMPLE]
    path = pathlib.Path(entry["path"])
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    print(f"original      : {path.name}")
    print(f"sha256 match  : {digest == entry['sha256']}")

    parsed = parse_pdf(path, source_id=f"probe:{SAMPLE}", source_sha256=digest)
    units = list(parsed.units)
    print(f"parsed units  : {len(units)}")
    print(f"role counts   : {dict(Counter(u.source_role for u in units))}")

    result = understand_units(
        units,
        source_id=f"probe:{SAMPLE}",
        source_sha256=digest,
        title="投资者关系活动记录表",
        declared_kind="investor_relations",
        language="zh",
    )

    route = result["route"]
    print(f"route         : {route['profile_id']} / {route['family']} / {route['confidence']}")

    observation = result["observation"]
    wire_roles = Counter(u.get("role") for u in observation["units"])
    print(f"wire roles    : {dict(wire_roles)}")

    semantic = result["structure"]["semantic_units"]
    kinds = Counter(u["kind"] for u in semantic)
    print(f"semantic kinds: {dict(kinds)}")

    qa_units = [u for u in semantic if u["kind"] == "qa_exchange"]
    print(f"qa_exchange   : {len(qa_units)}")
    for unit in qa_units[:3]:
        members = unit["member_unit_ids"]
        roles = [
            next(
                (w.get("role") for w in observation["units"] if w["unit_id"] == member),
                None,
            )
            for member in members
        ]
        print(f"   {unit['semantic_id']} completeness={unit['completeness']} roles={roles}")

    # The real question: does the shadow copy produce its own competing packages?
    packages = result["packages"]["packages"]
    print(f"packages      : {len(packages)}")
    pkg_kinds = Counter(p["kind"] for p in packages)
    print(f"package kinds : {dict(pkg_kinds)}")

    unit_role = {u["unit_id"]: u.get("role") for u in observation["units"]}
    shadow_only = [
        p
        for p in packages
        if p["member_unit_ids"]
        and all(unit_role.get(m) == "qa_text_shadow" for m in p["member_unit_ids"])
    ]
    structured_only = [
        p
        for p in packages
        if p["member_unit_ids"]
        and all(
            unit_role.get(m) in {"investor_question", "management"} for m in p["member_unit_ids"]
        )
    ]
    mixed = [
        p
        for p in packages
        if p["member_unit_ids"]
        and p not in shadow_only
        and p not in structured_only
    ]
    print(f"packages: all-shadow={len(shadow_only)} all-structured={len(structured_only)} mixed={len(mixed)}")

    # Do shadow and structured copies hold identical text (a true duplicate)?
    text_by_role: dict[str, set[str]] = {"qa_text_shadow": set(), "structured": set()}
    for unit in observation["units"]:
        role = unit.get("role")
        if role == "qa_text_shadow":
            text_by_role["qa_text_shadow"].add(unit["text"].strip())
        elif role in {"investor_question", "management"}:
            text_by_role["structured"].add(unit["text"].strip())
    shared = text_by_role["qa_text_shadow"] & text_by_role["structured"]
    print(
        "text overlap  : "
        f"shadow={len(text_by_role['qa_text_shadow'])} "
        f"structured={len(text_by_role['structured'])} "
        f"identical={len(shared)}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
