"""Metadata-only fingerprint of the selected PDF runtime dependency closure.

The resolver follows the distributions selected by importlib.metadata, which
uses interpreter search-path precedence. It never enumerates the environment,
imports an SDK, installs a package, or searches for model artifacts.
"""
from __future__ import annotations

from collections.abc import Callable, Iterable, Mapping
from hashlib import sha256
from importlib import metadata
import json
from typing import Any

ENVIRONMENT_ALGORITHM = "pdf-runtime-closure/2"
LEGACY_ENVIRONMENT_ALGORITHM = "pdf-installed-distributions/1"


def configured_runtime_roots(runtime_versions: Mapping[str, str]) -> tuple[str, ...]:
    """The configured SDKs are roots; Requires-Dist owns their transitives."""
    return tuple(sorted({"docling", *(name for name in runtime_versions if name != "python")}))


def describe_environment(roots: Iterable[str], *,
                         distribution_lookup: Callable[[str], Any] | None = None,
                         marker_environment: Mapping[str, str] | None = None) -> dict[str, Any]:
    # packaging is a declared dependency of the optional Docling deployment.
    # Keep native-only reading and v1 history free of this optional import.
    from packaging.markers import default_environment
    from packaging.requirements import InvalidRequirement, Requirement
    from packaging.utils import canonicalize_name
    from packaging.version import InvalidVersion, Version

    lookup = distribution_lookup or metadata.distribution
    environment = default_environment()
    if marker_environment is not None:
        environment.update(marker_environment)
    environment.pop("extra", None)  # extras are per-node, never caller-global
    selected: dict[str, Any] = {}
    active_extras: dict[str, set[str]] = {}
    declarations: dict[str, set[str]] = {}
    pending: list[str] = []
    processed: dict[str, frozenset[str]] = {}

    def parse(value: str):
        try:
            requirement = Requirement(value)
        except InvalidRequirement as exc:
            raise ValueError("invalid PDF runtime dependency metadata") from exc
        return requirement

    def activate(requirement) -> None:
        if requirement.url:
            # Installed metadata cannot prove which direct-URL bytes are active.
            # Inactive optional URLs never reach this gate.
            raise ValueError("PDF runtime direct URL dependency identity is unsupported")
        name = canonicalize_name(requirement.name)
        if name not in selected:
            try:
                dist = lookup(name)
            except metadata.PackageNotFoundError as exc:
                raise ValueError(f"PDF runtime dependency metadata missing: {name}") from exc
            try:
                raw_name, raw_version = dist.metadata["Name"], dist.version
            except (KeyError, AttributeError, TypeError) as exc:
                raise ValueError(f"PDF runtime dependency metadata incomplete: {name}") from exc
            if (not isinstance(raw_name, str) or not raw_name.strip()
                    or canonicalize_name(raw_name) != name
                    or not isinstance(raw_version, str) or not raw_version.strip()):
                raise ValueError(f"PDF runtime dependency metadata incomplete: {name}")
            try:
                Version(raw_version)
            except InvalidVersion as exc:
                raise ValueError(f"PDF runtime dependency version invalid: {name}") from exc
            selected[name], active_extras[name] = dist, set()
            declarations[name] = set()
        dist = selected[name]
        if requirement.specifier and not requirement.specifier.contains(dist.version, prereleases=True):
            raise ValueError(f"PDF runtime dependency version does not satisfy metadata: {name}")
        extras = {canonicalize_name(extra) for extra in requirement.extras}
        declared = {canonicalize_name(extra) for extra in (dist.metadata.get_all("Provides-Extra") or ())}
        if not extras <= declared:
            raise ValueError(f"PDF runtime dependency extra metadata missing: {name}")
        active_extras[name].update(extras)
        if processed.get(name) != frozenset(active_extras[name]):
            pending.append(name)

    normalized_roots = set()
    for value in roots:
        requirement = parse(value)
        if requirement.marker is not None:
            raise ValueError("PDF runtime roots must be explicit, without markers")
        normalized_roots.add(str(requirement))
        activate(requirement)
    if not normalized_roots:
        raise ValueError("PDF runtime dependency roots are empty")
    while pending:
        name = pending.pop(0)
        extras = frozenset(active_extras[name])
        if processed.get(name) == extras:
            continue
        processed[name] = extras
        for raw in selected[name].requires or ():
            requirement = parse(raw)
            if requirement.marker is not None and not any(
                requirement.marker.evaluate({**environment, "extra": extra}) for extra in ("", *sorted(extras))
            ):
                continue
            declarations[name].add(str(requirement))
            activate(requirement)
    payload = {
        "algorithm": ENVIRONMENT_ALGORITHM,
        "roots": sorted(normalized_roots),
        "marker_environment": dict(sorted(environment.items())),
        "distributions": [{"name": name, "version": selected[name].version,
                           "extras": sorted(active_extras[name]),
                           "requires": sorted(declarations[name])} for name in sorted(selected)],
    }
    digest = sha256(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    return {"schema_version": "pdf-paragraph-environment/2", "environment_algorithm": ENVIRONMENT_ALGORITHM,
            "environment_sha256": digest, **payload}
