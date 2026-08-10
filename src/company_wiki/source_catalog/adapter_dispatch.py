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

from typing import Any

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


def adapter_for(root: RootSpec):
    """Resolve the registered adapter for a root by its effective route
    (adapter_id).  Fail closed on unknown or missing ids."""
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
) -> list[Any]:
    """Run the root's registered adapter and return scanner candidates.

    This is the production caller for the three registered adapters
    (FC-302 CodeGraph gate: caller>=1 each).  Adapter candidates are
    converted to the scanner's internal _Candidate shape; the v1 scanner
    path is unchanged.
    """
    adapter = adapter_for(root)
    candidates = adapter.enumerate(root.path)
    converted = []
    for item in candidates:
        if not isinstance(item, NormalizedCandidate):
            converted.append(item)
            continue
        converted.append(_to_scanner_candidate(root, item, company_names))
    return converted


__all__ = [
    "AdapterDispatchError",
    "adapter_for",
    "scan_root_via_adapter",
]
