"""Produce causal inventory for the single reading catalog, without parsing.

The dependency lane canonicalizes this trace. This adapter owns which actual
source scopes and catalog decisions were involved; it is not a second freezer,
cache, registry, selector or task store.
"""
from __future__ import annotations

from collections.abc import Mapping, Sequence
from hashlib import sha256
import json
from typing import Any

from company_wiki.implementation_identity import code_sha256
from company_wiki.document_understanding.profiles import registry
from company_wiki.document_understanding.pipeline import PIPELINE_FEATURE_VERSION
from company_wiki.document_understanding.summary_input import SUMMARY_FEATURE_VERSION
from company_wiki.document_understanding.layout_hints import LAYOUT_HINTS_VERSION


def _digest(value: Any) -> str:
    return sha256(json.dumps(value, ensure_ascii=False, sort_keys=True,
                             separators=(",", ":")).encode()).hexdigest()


_NORMALIZED_MATERIAL_MATCHER = "company_wiki.document_normalization.replay"
_NARRATIVE_MATERIAL_MATCHER = "company_wiki.source_catalog.narrative_replay"
_MATERIAL_MATCHERS = frozenset({_NORMALIZED_MATERIAL_MATCHER, _NARRATIVE_MATERIAL_MATCHER})


def _source_usability_version(mime_type: str | None, material_matcher: str | None = None) -> str:
    """Bind the selector and the replay owner actually used for this carrier."""
    from .narrative_formats import NORMALIZED_MIME_TYPES
    from .narrative_selection import selection_algorithm_sha256

    if material_matcher is None:
        if mime_type in NORMALIZED_MIME_TYPES:
            material_matcher = _NORMALIZED_MATERIAL_MATCHER
        elif mime_type in {"application/pdf", "text/plain", "application/json"}:
            material_matcher = _NARRATIVE_MATERIAL_MATCHER
    hashes = {
        "company_wiki.source_catalog.narrative_selection": selection_algorithm_sha256(),
    }
    if material_matcher == _NORMALIZED_MATERIAL_MATCHER:
        from company_wiki.document_normalization.reading_identity import (
            normalized_parser_sha256, normalized_replay_sha256,
        )

        hashes[material_matcher] = normalized_replay_sha256()
        if mime_type in NORMALIZED_MIME_TYPES:
            hashes["normalized_carrier_parser"] = normalized_parser_sha256(mime_type)
    elif material_matcher == _NARRATIVE_MATERIAL_MATCHER:
        from .narrative_replay import replay_algorithm_sha256

        hashes[material_matcher] = replay_algorithm_sha256()
    elif material_matcher is not None:
        raise ValueError("unknown material matcher")
    return "source-usability/4+" + _digest(hashes)


def _pdf_versions() -> dict[str, str]:
    from company_wiki.document_normalization.layout_snapshots import FEATURE_VERSION
    from company_wiki.document_understanding.geometry_intent.reading import BRIDGE_VERSION
    from company_wiki.document_understanding.reading_identity import pdf_reading_algorithm_hashes
    from company_wiki.resource_budget import budget_algorithm_sha256
    from . import narrative_native_ranges, narrative_pdf_layout
    from .narrative_evidence import PDF_PROSE_LAYOUT_FEATURE_VERSION as PDF_PROSE_LAYOUT_FEATURE_VERSION
    from .narrative_evidence import evidence_algorithm_sha256
    from .narrative_pdf_candidates import pdf_candidate_algorithm_sha256
    from .narrative_pdf_intent import PDF_INTENT_EXECUTION_VERSION as PDF_INTENT_EXECUTION_VERSION
    from .narrative_pdf_intent import pdf_intent_algorithm_sha256

    # Capture remains historical. Recompute each owner identity before reuse.
    algorithms = pdf_reading_algorithm_hashes()
    algorithms.update({
        "company_wiki.source_catalog.narrative_evidence": evidence_algorithm_sha256(),
        "company_wiki.source_catalog.narrative_pdf_candidates": pdf_candidate_algorithm_sha256(),
        "company_wiki.source_catalog.narrative_pdf_intent": pdf_intent_algorithm_sha256(),
    })
    algorithms["company_wiki.resource_budget"] = budget_algorithm_sha256()
    return {
        "pdf_reading_bridge": BRIDGE_VERSION,
        "pdf_reading_algorithms": _digest(algorithms),
        "pdf_frontend": narrative_pdf_layout.PDF_READING_LAYOUT_FEATURE_VERSION,
        "pdf_native_prose": PDF_PROSE_LAYOUT_FEATURE_VERSION,
        "pdf_capture": narrative_pdf_layout.PDF_LAYOUT_CAPTURE_STRATEGY,
        "pdf_projection": FEATURE_VERSION,
        "pdf_native_range": narrative_native_ranges.NATIVE_PAGE_VIEW_FEATURE_VERSION,
        "pdf_native_range_parser": narrative_native_ranges.NATIVE_RANGE_CURRENT_PARSER_VERSION,
        "pdf_page_intent": PDF_INTENT_EXECUTION_VERSION,
    }


def _versions(*, pdf_frontend: bool = False, mime_type: str | None = None,
              material_matcher: str | None = None,
              document_work_limit: int | None = None) -> dict[str, str]:
    # Resolve the producer's current constants after package initialization.
    from .narrative_business_policy import READING_BUSINESS_POLICY_VERSION
    from .narrative_budget import READING_BUDGET_POLICY
    from .reading_recipe import business_algorithm_hashes
    from company_wiki.document_understanding.strategy_binding import STRATEGY_BINDING_VERSION
    from company_wiki.document_understanding.observation_adapter import OBSERVATION_ADAPTER_VERSION
    from company_wiki.document_understanding.reading_context_contract import READING_CONTEXT_CONTRACT_FEATURE_VERSION
    from company_wiki.document_understanding.narrative_continuity import NARRATIVE_CONTINUITY_FEATURE_VERSION
    from company_wiki.document_understanding.structure import table_purpose
    from company_wiki.document_understanding.native_table_bridge import NATIVE_TABLE_BRIDGE_VERSION
    from company_wiki.document_understanding.reading_identity import continuity_algorithm_hashes
    from company_wiki.document_model.text_matching import SCRIPT_MATCHING_VERSION
    from company_wiki.resource_budget import load_budget_policy

    usability = _source_usability_version(
        mime_type or ("application/pdf" if pdf_frontend else None), material_matcher,
    )
    versions = {
        "inventory": "1.12.0",
        "inventory_algorithm": code_sha256(__file__),
        "context_policy": _digest(registry.context_policy_config()),
        "selector": "0.9.0",
        "budget": READING_BUDGET_POLICY,
        # The ceiling in force is an explicit input when the caller already
        # resolved it.  Only an unbound decision reads the policy file.
        "document_work_limit": str(
            load_budget_policy().document_work_limit
            if document_work_limit is None else document_work_limit
        ),
        "native_table_bridge": NATIVE_TABLE_BRIDGE_VERSION,
        "source_usability": usability,
        "business_policy": READING_BUSINESS_POLICY_VERSION,
        "business_algorithms": _digest(business_algorithm_hashes(pdf_frontend=pdf_frontend)),
        "strategy_binding": STRATEGY_BINDING_VERSION,
        "observation_adapter": OBSERVATION_ADAPTER_VERSION,
        "continuity": NARRATIVE_CONTINUITY_FEATURE_VERSION,
        "continuity_algorithms": _digest(continuity_algorithm_hashes()),
        "table_purpose": table_purpose.FEATURE_VERSION,
        "script_matching": SCRIPT_MATCHING_VERSION,
        "pipeline": PIPELINE_FEATURE_VERSION,
        "summary": SUMMARY_FEATURE_VERSION,
        "reading_context_contract": READING_CONTEXT_CONTRACT_FEATURE_VERSION,
        "layout": LAYOUT_HINTS_VERSION,
    }
    if pdf_frontend:
        versions.update(_pdf_versions())
    return versions


def decision_versions(*, pdf_frontend: bool = False, mime_type: str | None = None,
                      material_matcher: str | None = None) -> dict[str, str]:
    """Return the public version identity for reading-decision algorithms."""
    return _versions(
        pdf_frontend=pdf_frontend,
        mime_type=mime_type,
        material_matcher=material_matcher,
    )


def _inventory(scopes: Sequence[Mapping[str, Any]], bindings: Mapping[str, str],
               used_facets: set[str], *, complete: bool = True,
               carrier: str | None = None, actual_frontend: str | None = None,
               material_matcher: str | None = None, capture_digest: str | None = None,
               document_work_limit: int | None = None) -> dict[str, Any]:
    catalog = registry.decision_inventory_inputs()
    components = []
    candidates = []
    if len(scopes) > 64:
        complete = False
        scopes = scopes[:64]
    # Scope membership is a set. Canonicalize once, including the references in
    # carrier/frontend/capture components, before building the causal inventory.
    scopes = sorted(scopes, key=lambda scope: scope["scope_id"])
    for scope in scopes:
        sid = scope["scope_id"]
        binding = next((item for item in catalog["legacy_bindings"]
                        if item["profile_id"] == bindings.get(sid)), None)
        if binding is None:
            complete = False
        else:
            identifier = "binding|" + sid + "|" + binding["profile_id"]
            components.append({"component_id": identifier, "version": "catalog-binding/1",
                "content_digest": _digest(binding), "matcher_digest": _digest(binding), "scope_ids": [sid]})
        for record in catalog["families"]:
            applies = record["applies_to"]
            overlay = "lifecycle_overlay" in applies["purposes"]
            if applies["family"] != scope["family"] and not overlay:
                continue
            form = registry.normalize_form_type(scope["form_type"] if scope["form_type"] != "unknown" else "")
            forms = {registry.normalize_form_type(value) for value in applies["forms"]}
            eligible = ((scope["regime"] in {"unknown", None} or scope["regime"] in applies["regimes"])
                        and (not form or not forms or form in forms))
            identifier = "family|" + sid + "|" + record["id"]
            # Inapplicable content is not inspected. Its applicability matcher
            # remains causal: changing it can admit a formerly losing policy.
            relevant = record if eligible else {"applies_to": applies}
            components.append({"component_id": identifier, "version": "family-decision/1",
                "content_digest": _digest(relevant), "matcher_digest": _digest({
                    "applies_to": applies, **({"recognition": record["recognition"]} if eligible else {})}),
                "scope_ids": [sid]})
            candidates.append({"candidate_id": identifier, "scope_id": sid,
                               "component_ids": [identifier], "eligible": eligible})
        # Fallback is used for unresolved/ambiguous purpose and still affects
        # reading even if no nonempty candidate ultimately wins selection.
        fallback = catalog["fallback"]
        identifier = "fallback|" + sid
        components.append({"component_id": identifier, "version": fallback["version"],
            "content_digest": _digest(fallback), "matcher_digest": _digest(fallback), "scope_ids": [sid]})
    if scopes:
        # Facets belong to this whole source, not a particular parent or child
        # profile. Use a stable representative ID solely for the wire reference:
        # freeze canonicalizes scope order, so insertion-first changes on replay
        # for multi-scope documents (notably the appended PDF geometry scope).
        sid = min(scope["scope_id"] for scope in scopes)
        for facet in catalog["facets"]:
            identifier = "facet|" + facet["id"]
            matcher = facet["positive_evidence"]
            used = facet["id"] in used_facets
            components.append({"component_id": identifier, "version": "facet-decision/1",
                "content_digest": _digest(facet if used else {"positive_evidence": matcher}),
                "matcher_digest": _digest(matcher), "scope_ids": [sid]})
            candidates.append({"candidate_id": identifier, "scope_id": sid,
                               "component_ids": [identifier], "eligible": used})
    if carrier:
        proof = _digest({"mime_type": carrier})
        components.append({"component_id": "carrier|" + carrier, "version": "source-carrier/1",
            "content_digest": proof, "matcher_digest": proof,
            "scope_ids": [scope["scope_id"] for scope in scopes]})
    if material_matcher:
        proof = _digest({"material_matcher": material_matcher})
        components.append({"component_id": "source-matcher-used|" + material_matcher,
            "version": "parsed-material-matcher/1", "content_digest": proof, "matcher_digest": proof,
            "scope_ids": [scope["scope_id"] for scope in scopes]})
    pdf_used = carrier == "application/pdf" and bool(actual_frontend)
    try:
        versions = _versions(pdf_frontend=pdf_used, mime_type=carrier,
                             material_matcher=material_matcher,
                             document_work_limit=document_work_limit)
    except (ImportError, AttributeError, OSError, RuntimeError):
        if not pdf_used:
            raise
        # The already recorded frontend observation is still valid. Missing
        # PDF software cannot establish a complete current cache identity.
        versions = _versions(mime_type=carrier, material_matcher=material_matcher,
                             document_work_limit=document_work_limit)
        complete = False
    if carrier == "application/pdf":
        if not pdf_used or not versions.get("pdf_projection") or versions.get("pdf_frontend") != actual_frontend:
            complete = False
        if actual_frontend:
            proof = _digest({"mime_type": carrier, "native_layout_frontend_version": actual_frontend})
            components.append({"component_id": "pdf-frontend-used|" + actual_frontend,
                "version": "native-frontend-use/1", "content_digest": proof, "matcher_digest": proof,
                "scope_ids": [scope["scope_id"] for scope in scopes]})
        if capture_digest:
            components.append({'component_id': 'pdf-capture-used|' + capture_digest,
                'version': 'source-capture-use/1', 'content_digest': capture_digest,
                'matcher_digest': capture_digest,
                'scope_ids': [scope['scope_id'] for scope in scopes]})
    return {"schema_version": "du-decision-trace/1", "scopes": list(scopes),
            "components": components, "candidates": candidates,
            "versions": versions,
            "inventory_complete": complete and bool(scopes) and bool(carrier)}


def build_decision_trace(pipeline: Mapping[str, Any], *, used_facet_ids: Sequence[str] = (),
                         source_parser_names: Sequence[str] | None = None,
                         document_work_limit: int | None = None) -> dict[str, Any]:
    route = pipeline["route"]
    metadata = pipeline.get("observation", {}).get("metadata", {})
    source = pipeline["source_ref"]["source_id"]
    scopes = []
    bindings = {}
    complete = True
    # Used-profile rows are compact identities, not the resolved strategy. A
    # compatibility ID can serve multiple actual families (hk_periodic serves
    # annual and interim). Index the already resolved unit views once and keep
    # each real child reading key separate from its parent.
    observed: dict[tuple[str, str | None], dict[str, set[str]]] = {}
    for view in pipeline["reading_plan"].get("unit_profiles", {}).values():
        pid = view.get("profile_id")
        if not isinstance(pid, str):
            continue
        observed_key = (pid, view.get("reading_profile_key") or None)
        values = observed.setdefault(observed_key, {"family": set(), "regime": set(), "form_type": set()})
        for name in values:
            actual = view.get(name)
            if isinstance(actual, str) and actual:
                values[name].add(actual)
    root_profile = pipeline.get("profile") or {}
    children = pipeline.get("child_profiles") or {}
    catalog_bindings = {
        row["profile_id"]: row for row in registry.decision_inventory_inputs()["legacy_bindings"]
    }

    def field(name: str, resolved: Mapping[str, Any], actual: Mapping[str, set[str]],
              fallback: Any = "unknown") -> str:
        nonlocal complete
        value = resolved.get(name)
        choices = actual.get(name, set())
        if isinstance(value, str) and value:
            if choices and choices != {value}:
                complete = False
            return value
        if len(choices) == 1:
            return next(iter(choices))
        if len(choices) > 1:
            # Contradictory actual scope data cannot become a reusable decision
            # by arbitrarily picking the first unit or a legacy default.
            complete = False
            return "unknown"
        return str(fallback or "unknown")

    for used in pipeline["reading_plan"].get("used_profiles", ()):
        profile_id = used["profile_id"]
        key = used.get("reading_profile_key") or None
        sid = source + "|" + str(key or "root")
        actual = observed.get((profile_id, key), {})
        if key is None:
            resolved = root_profile if root_profile.get("profile_id") == profile_id else {}
            family = field("family", resolved, actual, route.get("family"))
            if not (resolved.get("family") or actual.get("family") or route.get("family")):
                complete = False
            regime = field("regime", resolved, actual, route.get("regime"))
            form = field("form_type", resolved, actual,
                         route.get("form_type") if "form_type" in route else metadata.get("form_type"))
        else:
            resolved = children.get(key, {})
            child_route: Mapping[str, Any] = next((row for row in route.get("child_routes", ())
                                                  if row.get("reading_profile_key") == key), {})
            family = field("family", resolved, actual, child_route.get("family"))
            if not (resolved.get("family") or actual.get("family") or child_route.get("family")):
                complete = False
            # The production child resolver clears the parent's title/form
            # and obtains its market from its own base profile. Only this
            # market fallback reflects that actual operation; its legacy
            # family is never substituted for the resolved child family.
            binding = catalog_bindings.get(profile_id, {})
            regime = field("regime", resolved, actual,
                           child_route.get("regime", binding.get("regime")))
            form = field("form_type", resolved, actual, child_route.get("form_type"))
        scopes.append({"scope_id": sid, "family": family, "regime": regime,
                       "form_type": form, "purpose": family})
        bindings[sid] = profile_id
    carrier = metadata.get("mime_type")
    carrier = carrier if isinstance(carrier, str) and 0 < len(carrier) <= 256 else None
    frontend = metadata.get("native_layout_frontend_version")
    frontend = frontend if isinstance(frontend, str) and 0 < len(frontend) <= 256 else None
    material_matcher = None
    if source_parser_names:
        from company_wiki.document_normalization.units import PARSER_NAME
        # The source owner's material check uses this exact branch. HTML MIME,
        # document purpose and profile cannot distinguish DOM from call text.
        material_matcher = (_NORMALIZED_MATERIAL_MATCHER
                            if all(name == PARSER_NAME for name in source_parser_names)
                            else _NARRATIVE_MATERIAL_MATCHER)
    capture = (pipeline.get('native_layout_frontend') or {}).get('capture')
    planning = (pipeline.get('native_layout_frontend') or {}).get('planning')
    if isinstance(planning, Mapping) and isinstance(planning.get('profile_scope'), Mapping):
        actual = planning['profile_scope']
        sid = source + '|pdf-native-intent'
        scopes.append({'scope_id': sid, 'family': actual.get('family', 'unknown'),
                       'regime': actual.get('regime', 'unknown'),
                       'form_type': actual.get('form_type') or 'unknown',
                       'purpose': actual.get('family', 'unknown')})
        bindings[sid] = actual.get('profile_id', 'generic')
    return _inventory(scopes, bindings, set(used_facet_ids), complete=complete, carrier=carrier,
                      actual_frontend=frontend, material_matcher=material_matcher,
                      capture_digest=_digest(capture) if isinstance(capture, Mapping) else None,
                      document_work_limit=document_work_limit)


def current_decision_trace(frozen: Mapping[str, Any]) -> dict[str, Any]:
    """Inspect relevant current inventory without rerouting or rereading text.

    Changed matchers invalidate the cached decision rather than being tested on
    obsolete snippets. Unrelated families and unused facet instructions are not
    forced into this source's dependency content.
    """
    bindings = {}
    for component in frozen.get("components", ()):
        identifier = component["component_id"]
        if identifier.startswith("binding|"):
            sid, profile_id = identifier.removeprefix("binding|").rsplit("|", 1)
            bindings[sid] = profile_id
    used = {row["candidate_id"].removeprefix("facet|") for row in frozen.get("candidates", ())
            if row["candidate_id"].startswith("facet|") and row["eligible"]}
    # The actual observation carrier is persisted as a causal component. A
    # source filename, market family or old global version cannot prove that
    # this source used the PDF frontend; absent/conflicting proof stays partial.
    proofs = [component for component in frozen.get("components", ())
              if component["component_id"].startswith("carrier|")]
    carrier = None
    if len(proofs) == 1:
        proof = proofs[0]
        observed = proof["component_id"].removeprefix("carrier|")
        digest = _digest({"mime_type": observed})
        scope_ids = {scope["scope_id"] for scope in frozen.get("scopes", ())}
        if (0 < len(observed) <= 256 and proof.get("version") == "source-carrier/1"
                and proof.get("content_digest") == digest and proof.get("matcher_digest") == digest
                and set(proof.get("scope_ids", ())) == scope_ids):
            carrier = observed
    native_proofs = [component for component in frozen.get("components", ())
                     if component["component_id"].startswith("pdf-frontend-used|")]
    actual_frontend = None
    if carrier == "application/pdf" and len(native_proofs) == 1:
        proof = native_proofs[0]
        actual = proof["component_id"].removeprefix("pdf-frontend-used|")
        digest = _digest({"mime_type": carrier, "native_layout_frontend_version": actual})
        if (0 < len(actual) <= 256 and proof.get("version") == "native-frontend-use/1"
                and proof.get("content_digest") == digest and proof.get("matcher_digest") == digest
                and set(proof.get("scope_ids", ())) == {scope["scope_id"] for scope in frozen.get("scopes", ())}):
            actual_frontend = actual
    matcher_proofs = [component for component in frozen.get("components", ())
                      if component["component_id"].startswith("source-matcher-used|")]
    material_matcher = None
    matcher_complete = not matcher_proofs  # Compatibility traces have no actual parser argument.
    if len(matcher_proofs) == 1:
        proof = matcher_proofs[0]
        actual = proof["component_id"].removeprefix("source-matcher-used|")
        digest = _digest({"material_matcher": actual})
        if (actual in _MATERIAL_MATCHERS and proof.get("version") == "parsed-material-matcher/1"
                and proof.get("content_digest") == digest and proof.get("matcher_digest") == digest
                and set(proof.get("scope_ids", ())) == {scope["scope_id"] for scope in frozen.get("scopes", ())}):
            material_matcher = actual
            matcher_complete = True
    # This is the immutable source attempt's actual coverage, not a prediction
    # of what a new parse would capture. Current algorithm versions still cause
    # invalidation; replay does not reread an original just to recreate a digest.
    capture_proofs = [row for row in frozen.get('components', ())
                      if row['component_id'].startswith('pdf-capture-used|')]
    capture_digest = None
    capture_complete = not capture_proofs
    if len(capture_proofs) == 1 and carrier == 'application/pdf':
        proof = capture_proofs[0]
        actual = proof['component_id'].removeprefix('pdf-capture-used|')
        if (len(actual) == 64 and all(c in '0123456789abcdef' for c in actual)
                and proof.get('version') == 'source-capture-use/1'
                and proof.get('content_digest') == proof.get('matcher_digest') == actual
                and set(proof.get('scope_ids', ())) == {s['scope_id'] for s in frozen.get('scopes', ())}):
            capture_digest, capture_complete = actual, True
    return _inventory(frozen.get("scopes", ()), bindings, used,
                      complete=frozen.get("inventory_complete", frozen.get("status") == "complete")
                      and matcher_complete and capture_complete,
                      carrier=carrier, actual_frontend=actual_frontend, material_matcher=material_matcher,
                      capture_digest=capture_digest)


__all__ = ["build_decision_trace", "current_decision_trace", "decision_versions"]
