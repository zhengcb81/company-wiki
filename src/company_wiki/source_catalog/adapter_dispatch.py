"""FC-302: production AdapterRegistry dispatch.

The scanner facade resolves the registered adapter for a root (by
``adapter_id`` — the effective route) and runs its enumerate().  The
adapter produces unified NormalizedCandidates; the dispatch converts them
to the scanner's internal _Candidate shape.  Unknown/missing adapter ids
fail closed.  The v1 scanner path is untouched (FC-305 cutover); this is
the production caller seam that gives SidecarFilingAdapter,
CompanyRawAdapter and DayuAdapter their production callers.
"""

from __future__ import annotations

from dataclasses import replace
from typing import Any

from .adapters.common import _ACQUISITION_SIDECAR_SUFFIX
from .adapters.company_raw import CompanyRawAdapter
from .adapters.dayu import DayuAdapter
from .adapters.interface import NormalizedCandidate
from .adapters.registry import registered_adapter
from .adapters.sidecar import SidecarFilingAdapter
from .models import RootSpec


class AdapterDispatchError(RuntimeError):
    """Raised when a root's adapter cannot be resolved or run."""


# adapter_id -> factory.  Only scanner-capable registered adapters appear.
_ADAPTER_FACTORIES = {
    "sidecar_filing_v1": lambda: SidecarFilingAdapter(),
    "company_raw_v1": lambda: CompanyRawAdapter(),
    "dayu_filing_v1": lambda: DayuAdapter(),
}


def adapter_for(root: RootSpec, *, relative_path: str | None = None):
    """Resolve the registered adapter for a root by its effective route
    (adapter_id).  Fail closed on unknown or missing ids."""
    if relative_path is not None:
        root = root.effective_root_for_path(relative_path)
    if root.adapter_id is None:
        raise AdapterDispatchError(
            f"root {root.root_id!r} has no adapter_id (2.x policy required)"
        )
    registered = registered_adapter(root.adapter_id)
    if registered is None:
        raise AdapterDispatchError(
            f"root {root.root_id!r} adapter {root.adapter_id!r} not registered"
        )
    factory = _ADAPTER_FACTORIES.get(root.adapter_id)
    if factory is None:
        raise AdapterDispatchError(
            f"root {root.root_id!r} adapter {root.adapter_id!r} has no "
            f"scanner adapter implementation"
        )
    return factory()


# Only old configs lacking an adapter need layout defaults. New roots use the
# configured adapter_id; no downstream reconcile branch knows their kind/id.
_LEGACY_ISSUER_FACTORIES = {
    "company_raw": CompanyRawAdapter,
    "dayu_portfolio": DayuAdapter,
}


def _configured_adapter_roots(root: RootSpec) -> list[RootSpec]:
    """Each configured adapter enumerates once; route order assigns ownership."""
    roots = [root] if root.adapter_id is not None else []
    seen = {root.adapter_id} if roots else set()
    for route in root.routes:
        if route.adapter_id is not None and route.adapter_id not in seen:
            roots.append(replace(root, adapter_id=route.adapter_id))
            seen.add(route.adapter_id)
    return roots


def discover_issuer_paths(root: RootSpec, **ports) -> set[str]:
    """Bounded discovery uses the same caller-owned ports across all adapters."""
    configured = _configured_adapter_roots(root)
    if not configured:
        factory = _LEGACY_ISSUER_FACTORIES.get(root.kind)
        if factory is None:
            return set()
        discover = getattr(factory(), "discover_issuer_paths", None)
        return discover(root.path, **ports) if callable(discover) else set()
    selected = set()
    for configured_root in configured:
        discover = getattr(adapter_for(configured_root), "discover_issuer_paths", None)
        if callable(discover):
            selected.update(path for path in discover(root.path, **ports)
                if root.effective_root_for_path(path).adapter_id == configured_root.adapter_id)
    return selected


def _to_scanner_candidate(root: RootSpec, item: NormalizedCandidate, company_names):
    """Convert a NormalizedCandidate to the scanner's internal _Candidate.

    The adapter emits relative paths, group keys, roles and normalized
    metadata; entity_name is inferred the same way the v1 scanner does
    (from the company directory name embedded in the relative path).
    """
    from .scanner import _Candidate, _infer_company

    path = root.path / item.relative_path
    return _Candidate(
        root=root,
        path=path,
        relative_path=item.relative_path,
        group_key=item.group_key,
        role=item.role,
        entity_name=_infer_company(item.relative_path, company_names),
        group_metadata=dict(item.normalized or {}),
        source_status="active",
    )


def scan_root_via_adapter(
    root: RootSpec,
    company_names: tuple[str, ...],
    *,
    progress: Any = None,
    relative_paths: set[str] | None = None,
    metadata_reader=None, file_walker=None,
) -> list[Any]:
    """Run the root's registered adapter and return scanner candidates.

    This is the production caller for the three registered adapters
    (FC-302 CodeGraph gate: caller>=1 each).  Adapter candidates are
    converted to the scanner's internal _Candidate shape; the v1 scanner
    path is unchanged.
    """
    configured = _configured_adapter_roots(root)
    if not configured:
        adapter_for(root)  # retain the explicit missing-adapter failure
    groups = []
    for configured_root in configured:
        adapter = adapter_for(configured_root)
        # One shared metadata/walker port retains aggregate caller limits.
        options = {}
        if metadata_reader is not None:
            options["metadata_reader"] = metadata_reader
        if file_walker is not None and isinstance(adapter, DayuAdapter):
            options["file_walker"] = file_walker
        scoped_paths = relative_paths
        if root.routes:
            def owned(relative, *, adapter_id=configured_root.adapter_id):
                primary = relative.removesuffix(_ACQUISITION_SIDECAR_SUFFIX)
                return root.effective_root_for_path(primary).adapter_id == adapter_id
            options["primary_filter"] = owned
            if relative_paths is not None:
                scoped_paths = {path for path in relative_paths if owned(path)}
                if not scoped_paths:
                    continue
        candidates = adapter.enumerate(root.path, relative_paths=scoped_paths,
                                       compute_hash=False, **options)
        primaries = {item.group_key: item.relative_path for item in candidates
                     if isinstance(item, NormalizedCandidate)
                     and item.role in {"original_primary", "indexed_only"}}
        groups.append((configured_root, candidates, primaries))
    attachment_owners = {}
    for configured_root, candidates, primaries in groups:
        for item in candidates:
            if not isinstance(item, NormalizedCandidate) or item.role in {"original_primary", "indexed_only"}:
                continue
            effective = root.effective_root_for_path(primaries.get(item.group_key, item.group_key))
            if effective.adapter_id == configured_root.adapter_id:
                previous = attachment_owners.get(item.relative_path)
                if previous is not None and previous != effective:
                    raise AdapterDispatchError("source attachment has conflicting route owners")
                attachment_owners[item.relative_path] = effective
    converted = []
    seen = set()
    for configured_root, candidates, primaries in groups:
        for item in candidates:
            if not isinstance(item, NormalizedCandidate):
                if root.routes:
                    raise AdapterDispatchError("routed adapter returned an invalid candidate")
                converted.append(item)
                continue
            # Group membership from the owning adapter outranks another
            # layout's attempt to treat that metadata file as a new original.
            effective = attachment_owners.get(item.relative_path)
            if effective is None:
                effective = root.effective_root_for_path(primaries.get(item.group_key, item.group_key))
            if effective.adapter_id == configured_root.adapter_id:
                if root.routes and item.relative_path in seen:
                    raise AdapterDispatchError("routed adapter emitted duplicate source path")
                converted.append(_to_scanner_candidate(effective, item, company_names))
                seen.add(item.relative_path)
    return converted


__all__ = [
    "AdapterDispatchError",
    "adapter_for",
    "scan_root_via_adapter",
    "discover_issuer_paths",
]
