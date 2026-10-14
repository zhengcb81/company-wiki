"""Produce causal inventory for the single reading catalog, without parsing.

The dependency lane canonicalizes this trace. This adapter owns which actual
source scopes and catalog decisions were involved; it is not a second freezer,
cache, registry, selector or task store.
"""
from __future__ import annotations

from collections.abc import Mapping, Sequence
from hashlib import sha256
from importlib import import_module
import json
from typing import Any

from .profiles import registry
from .pipeline import PIPELINE_FEATURE_VERSION
from .summary_input import SUMMARY_FEATURE_VERSION
from .layout_hints import LAYOUT_HINTS_VERSION


def _digest(value: Any) -> str:
    return sha256(json.dumps(value, ensure_ascii=False, sort_keys=True,
                             separators=(",", ":")).encode()).hexdigest()


def _versions(*, pdf_frontend: bool = False) -> dict[str, str]:
    # Resolve the producer's current constant after package initialization.
    # This avoids making source_catalog's package imports depend on an
    # inventory module that is still being initialized.
    from company_wiki.source_catalog.narrative_business_policy import READING_BUSINESS_POLICY_VERSION
    from company_wiki.source_catalog.narrative_budget import READING_BUDGET_POLICY
    from .strategy_binding import STRATEGY_BINDING_VERSION
    from .observation_adapter import OBSERVATION_ADAPTER_VERSION
    from .narrative_continuity import NARRATIVE_CONTINUITY_FEATURE_VERSION

    versions = {"inventory": "1.2.0", "selector": "0.9.0", "budget": READING_BUDGET_POLICY,
            "business_policy": READING_BUSINESS_POLICY_VERSION,
            "strategy_binding": STRATEGY_BINDING_VERSION,
            "observation_adapter": OBSERVATION_ADAPTER_VERSION,
            "continuity": NARRATIVE_CONTINUITY_FEATURE_VERSION,
            "pipeline": PIPELINE_FEATURE_VERSION, "summary": SUMMARY_FEATURE_VERSION,
            "layout": LAYOUT_HINTS_VERSION}
    if pdf_frontend:
        for key, module_name, attribute in (
            ("pdf_frontend", "company_wiki.source_catalog.narrative_pdf_layout", "PDF_READING_LAYOUT_FEATURE_VERSION"),
            ("pdf_projection", "company_wiki.document_normalization.layout_snapshots", "FEATURE_VERSION"),
            ("pdf_native_range", "company_wiki.source_catalog.narrative_native_ranges", "NATIVE_PAGE_VIEW_FEATURE_VERSION"),
            ("pdf_native_range_parser", "company_wiki.source_catalog.narrative_native_ranges", "NATIVE_RANGE_PARSER_VERSION"),
        ):
            try:
                component = import_module(module_name)
            except ModuleNotFoundError as exc:
                if exc.name != module_name:
                    raise
                continue
            version = getattr(component, attribute, None)
            if isinstance(version, str) and 0 < len(version) <= 256:
                versions[key] = version
    return versions


def _inventory(scopes: Sequence[Mapping[str, Any]], bindings: Mapping[str, str],
               used_facets: set[str], *, complete: bool = True,
               carrier: str | None = None, actual_frontend: str | None = None) -> dict[str, Any]:
    components = []
    candidates = []
    if len(scopes) > 64:
        complete = False
        scopes = scopes[:64]
    for scope in scopes:
        sid = scope["scope_id"]
        binding = next((item for item in registry._CATALOG["legacy_bindings"]
                        if item["profile_id"] == bindings.get(sid)), None)
        if binding is None:
            complete = False
        else:
            identifier = "binding|" + sid + "|" + binding["profile_id"]
            components.append({"component_id": identifier, "version": "catalog-binding/1",
                "content_digest": _digest(binding), "matcher_digest": _digest(binding), "scope_ids": [sid]})
        for record in registry._CATALOG["families"]:
            applies = record["applies_to"]
            overlay = "lifecycle_overlay" in applies["purposes"]
            if applies["family"] != scope["family"] and not overlay:
                continue
            form = registry._base_form(scope["form_type"] if scope["form_type"] != "unknown" else "")
            forms = {registry._base_form(value) for value in applies["forms"]}
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
        fallback = registry._CATALOG["fallback"]
        identifier = "fallback|" + sid
        components.append({"component_id": identifier, "version": fallback["version"],
            "content_digest": _digest(fallback), "matcher_digest": _digest(fallback), "scope_ids": [sid]})
    if scopes:
        sid = scopes[0]["scope_id"]
        for facet in registry._CATALOG["facets"]:
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
    pdf_used = carrier == "application/pdf" and bool(actual_frontend)
    versions = _versions(pdf_frontend=pdf_used)
    if carrier == "application/pdf":
        if not pdf_used or not versions.get("pdf_projection") or versions.get("pdf_frontend") != actual_frontend:
            complete = False
        if actual_frontend:
            proof = _digest({"mime_type": carrier, "native_layout_frontend_version": actual_frontend})
            components.append({"component_id": "pdf-frontend-used|" + actual_frontend,
                "version": "native-frontend-use/1", "content_digest": proof, "matcher_digest": proof,
                "scope_ids": [scope["scope_id"] for scope in scopes]})
    return {"schema_version": "du-decision-trace/1", "scopes": list(scopes),
            "components": components, "candidates": candidates,
            "versions": versions,
            "inventory_complete": complete and bool(scopes) and bool(carrier)}


def build_decision_trace(pipeline: Mapping[str, Any], *, used_facet_ids: Sequence[str] = ()) -> dict[str, Any]:
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
    catalog_bindings = {row["profile_id"]: row for row in registry._CATALOG["legacy_bindings"]}

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
    return _inventory(scopes, bindings, set(used_facet_ids), complete=complete, carrier=carrier,
                      actual_frontend=frontend)


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
    return _inventory(frozen.get("scopes", ()), bindings, used,
                      complete=frozen.get("inventory_complete", frozen.get("status") == "complete"),
                      carrier=carrier, actual_frontend=actual_frontend)


__all__ = ["build_decision_trace", "current_decision_trace"]
