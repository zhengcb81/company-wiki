"""Read-only snapshot of the *real* installed reading catalog, for the C-node replay.

Boundary, stated once and kept:

* **Real.** ``reading_catalog.json`` is the single installed reading-policy catalog
  shipped in this tree. The component ids, versions, applies-to tuples and recognition
  payloads below are read from that file, and its SHA-256 is recorded so the receipt can
  show exactly which catalog the replay ran against.
* **Synthetic.** The decision *domain* -- which scopes a source entered, which components
  the router actually inspected, and which candidates took part and lost -- is not
  observable from the catalog. The real instrumentation belongs to ROOT's router and
  selector. Everything shaped here is a legal ``du-decision-trace/1`` built from real
  catalog identities, and it is labelled synthetic wherever it is reported.

Nothing here writes to the catalog, reads a company original, calls a model, or touches
the network. The catalog is loaded read-only and its byte digest is checked unchanged.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from .builders import content_digest, scope, trace

#: ``<worktree>/src/company_wiki/document_understanding`` — the parent of this package.
_PACKAGE_PARENT = Path(__file__).resolve().parents[3] / "src" / "company_wiki" / "document_understanding"
CATALOG_PATH = _PACKAGE_PARENT / "profiles" / "reading_catalog.json"

ALGORITHM_VERSIONS: dict[str, Any] = {
    "router": "0.8.0",
    "selector": "1.0.0",
    "structure": "du-structure/1",
    "reading_catalog": "du-reading-catalog/1",
}


def load_catalog(path: Path = CATALOG_PATH) -> tuple[dict[str, Any], str]:
    """Return ``(parsed_catalog, sha256_of_file_bytes)``. Read-only, no side effects."""
    raw = Path(path).read_bytes()
    return json.loads(raw.decode("utf-8")), hashlib.sha256(raw).hexdigest()


def _applies_rows(record: dict[str, Any]) -> list[dict[str, Any]]:
    applies = record["applies_to"]
    regimes = applies.get("regimes") or ["unknown"]
    purposes = applies.get("purposes") or ["unknown"]
    forms = applies.get("forms") or [None]
    rows = []
    for regime in regimes:
        for purpose in purposes:
            for form in forms:
                rows.append(
                    {
                        "regime": regime,
                        "family": applies.get("family", "unknown"),
                        "form_type": form,
                        "purpose": purpose,
                    }
                )
    return rows


def scope_id_for(row: dict[str, Any]) -> str:
    return f"scope:{row['regime']}:{row['family']}:{row['purpose']}"


def build_snapshot(catalog: dict[str, Any], file_sha256: str) -> dict[str, Any]:
    """A bounded snapshot: identities only, never the policy bodies themselves."""
    families = []
    for record in catalog["families"]:
        families.append(
            {
                "component_id": f"family:{record['id']}",
                "version": record["version"],
                "content_digest": content_digest(record),
                "matcher_digest": content_digest(record.get("recognition", {})),
                "applies": _applies_rows(record),
            }
        )
    facets = []
    for record in catalog["facets"]:
        facets.append(
            {
                "component_id": f"facet:{record['id']}",
                "version": record["version"],
                "content_digest": content_digest(record),
                "matcher_digest": content_digest(record.get("positive_evidence", [])),
            }
        )
    bindings = [
        {
            "profile_id": binding["profile_id"],
            "family_ids": list(binding["family_ids"]),
            "regime": binding["regime"],
            "family": binding["family"],
        }
        for binding in catalog["legacy_bindings"]
    ]
    return {
        "snapshot_schema": "du3-dependencies-catalog-snapshot/1",
        "catalog_file": "src/company_wiki/document_understanding/profiles/reading_catalog.json",
        "catalog_sha256": file_sha256,
        "schema_version": catalog.get("schema_version"),
        "families": families,
        "facets": facets,
        "bindings": bindings,
    }


def load_snapshot(path: Path = CATALOG_PATH) -> tuple[dict[str, Any], str]:
    catalog, digest = load_catalog(path)
    return build_snapshot(catalog, digest), digest


# --- synthetic but legal decision domains -------------------------------------------


def source_domain(
    snapshot: dict[str, Any],
    *,
    profile_id: str = "cn_annual",
    include_child_scope: bool = True,
    winners: tuple[str, ...] = (),
) -> dict[str, Any]:
    """One source's decision domain, built from real catalog identities.

    ``profile_id`` picks which legacy binding this source is. The *scope* is the one this
    source actually entered; the *components* are every family/facet the matcher would
    have had to look at inside that scope -- including the ones that matched and lost;
    the *candidates* are the bindings that were weighed.
    """
    bindings = {item["profile_id"]: item for item in snapshot["bindings"]}
    families = {item["component_id"]: item for item in snapshot["families"]}
    facets = list(snapshot["facets"])

    chosen = bindings[profile_id]
    primary = families[f"family:{chosen['family_ids'][0]}"]
    base_row = primary["applies"][0]
    parent_id = scope_id_for(base_row)
    child_id = f"{parent_id}:business_review"

    scopes = [scope(parent_id, **base_row)]
    if include_child_scope:
        scopes.append(scope(child_id, **{**base_row, "purpose": "business_review"}))

    # Everything the matcher had to inspect inside this source's scope. Recognition
    # signals are tested against the document before a family is chosen, so every family
    # declared for this market had to be looked at -- including the ones that matched and
    # lost. That is exactly the population the decision identity has to cover.
    inspected = [
        item
        for item in snapshot["families"]
        if any(row["regime"] == base_row["regime"] for row in item["applies"])
    ]
    components = [
        {
            "component_id": item["component_id"],
            "version": item["version"],
            "content_digest": item["content_digest"],
            "matcher_digest": item["matcher_digest"],
            "scope_ids": [parent_id],
        }
        for item in inspected
    ]
    for item in facets:
        components.append(
            {
                "component_id": item["component_id"],
                "version": item["version"],
                "content_digest": item["content_digest"],
                "matcher_digest": item["matcher_digest"],
                "scope_ids": [child_id if include_child_scope else parent_id],
            }
        )

    inspected_ids = {item["component_id"] for item in inspected}
    winners = winners or tuple(chosen["family_ids"])
    candidates = []
    for binding in sorted(snapshot["bindings"], key=lambda item: item["profile_id"]):
        # Only the components this domain actually inspected belong here. A binding may
        # span several markets (a "prospectus" covers cn/hk/us families); the parts this
        # source never looked at are outside its decision domain by construction.
        member_ids = [
            f"family:{fid}" for fid in binding["family_ids"] if f"family:{fid}" in inspected_ids
        ]
        if not member_ids:
            continue
        is_winner = binding["profile_id"] == profile_id
        candidates.append(
            {
                "candidate_id": f"candidate:{binding['profile_id']}",
                "scope_id": parent_id,
                "component_ids": member_ids,
                "eligible": is_winner or binding["profile_id"] in winners,
            }
        )

    return trace(
        scopes=scopes,
        components=components,
        candidates=candidates,
        versions=dict(ALGORITHM_VERSIONS),
    )


def whole_catalog_domain(snapshot: dict[str, Any]) -> dict[str, Any]:
    """The naive anti-pattern: the entire catalog as one decision domain.

    Kept so the C-node replay can show, with the real catalog, why the dependency unit
    has to be the *source-local* decision domain rather than a whole-catalog hash.
    """
    scopes: list[dict[str, Any]] = []
    seen: set[str] = set()
    for item in snapshot["families"]:
        for row in item["applies"]:
            identifier = scope_id_for(row)
            if identifier in seen:
                continue
            seen.add(identifier)
            scopes.append(scope(identifier, **row))
    components = [
        {
            "component_id": item["component_id"],
            "version": item["version"],
            "content_digest": item["content_digest"],
            "matcher_digest": item["matcher_digest"],
            "scope_ids": [scopes[0]["scope_id"]],
        }
        for item in snapshot["families"] + snapshot["facets"]
    ]
    candidates = [
        {
            "candidate_id": f"candidate:{item['profile_id']}",
            "scope_id": scopes[0]["scope_id"],
            "component_ids": [f"family:{fid}" for fid in item["family_ids"]],
            "eligible": True,
        }
        for item in snapshot["bindings"]
    ]
    return trace(
        scopes=scopes,
        components=components,
        candidates=candidates,
        versions=dict(ALGORITHM_VERSIONS),
    )


def distinctive_phrase(catalog: dict[str, Any]) -> str:
    """A short string that only exists in the catalog's *policy text*.

    Used to prove the manifest stores identity, never the policy body. The phrase is read
    from the catalog at test time and is not persisted anywhere.
    """
    for record in catalog["families"]:
        for question in record.get("reading_questions", ()):
            if isinstance(question, str) and len(question) >= 6:
                return question
    for record in catalog["families"]:
        for section in record.get("sections", ()):
            for alias in section.get("aliases", ()):
                if isinstance(alias, str) and len(alias) >= 4:
                    return alias
    raise AssertionError("the catalog carries no readable policy text to probe with")
