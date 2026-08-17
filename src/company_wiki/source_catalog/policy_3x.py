"""ZR-401: RootPolicy 3.0 — strict loader + versioned snapshot export.

3.0 removes every implicit permission expansion the 2.x loader tolerated:

- schema_version MUST be "3.0" (an N-1 1.x/2.x config is rejected with a
  migration hint — never silently upgraded);
- ``privacy_class`` is REQUIRED per root (no default): an external root
  (kind != company_raw) must be ``private_user``; a company_raw root must
  be ``public`` — a private company root or a public external root is a
  config error (load fails);
- external roots can never be a canonical write target (kind !=
  company_raw + canonical_write_target -> load fails);
- unknown root fields fail closed (strict allowlist);
- reusable external roots must be read_only.

``export_root_policy_3x`` produces a versioned, privacy-redacted snapshot
(paths become tokens; sha256 over the canonical JSON) — the single hash
ZR-404 envelopes bind against.

N/N-1: 3.0 loader accepts ONLY schema_version "3.0"; the 2.x loader and
the legacy config loader are unchanged for existing consumers.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import yaml

from .config import CatalogConfigError, _expand_path, _unresolved_variables
from .models import ROOT_KINDS, CatalogConfig, RootSpec
from .policy_2x import (
    ALLOWED_ROOT_FIELDS_2X,
    _WRITABLE_KINDS,
    load_root_policy_2x,
)

ROOT_POLICY_3X_SCHEMA_VERSION = "3.0"
ROOT_POLICY_3X_SCHEMA = "root-policy-3.0"

# 3.0 allowlist = 2.x fields + privacy_class (required) + symlink/max/sidecar
# (already in 2.x).  We reuse the 2.x allowlist so the field vocabulary is
# single-sourced, and enforce 3.0-specific rules on top.
ALLOWED_ROOT_FIELDS_3X = ALLOWED_ROOT_FIELDS_2X | {"privacy_class"}

# External roots must be private; company_raw is the only public root kind.
_PUBLIC_KIND = "company_raw"
_PRIVATE_PRIVACY = "private_user"
_PUBLIC_PRIVACY = "public"


def _privacy_rule(kind: str, privacy: str) -> str | None:
    """Return a violation message for a (kind, privacy) pair, or None."""
    if kind == _PUBLIC_KIND:
        if privacy != _PUBLIC_PRIVACY:
            return (
                f"company_raw root must be privacy_class='public' "
                f"(got {privacy!r})"
            )
        return None
    if privacy != _PRIVATE_PRIVACY:
        return (
            f"external root (kind={kind!r}) must be privacy_class="
            f"'private_user' (got {privacy!r}) — no implicit public"
        )
    return None


def load_root_policy_3x(
    path: Path, *, project_root: Path | None = None
) -> CatalogConfig:
    """Strict RootPolicy 3.0 loader.

    Loads via the 2.x loader (which enforces the shared field/vocabulary
    checks: unknown fields, duplicate roots, external write targets,
    unknown adapter/profile, widening routes) and then applies the 3.0
    schema/privacy gates on top.  Any violation raises CatalogConfigError.
    """
    if not isinstance(path, Path):
        raise TypeError("path must be pathlib.Path")
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    data = payload if isinstance(payload, dict) else {}
    schema = str(data.get("schema_version", ""))
    if schema != ROOT_POLICY_3X_SCHEMA_VERSION:
        raise CatalogConfigError(
            f"RootPolicy schema_version must be {ROOT_POLICY_3X_SCHEMA_VERSION!r} "
            f"(got {schema!r}); 1.x/2.x configs are not auto-upgraded — "
            f"migrate to 3.0 explicitly"
        )
    # Run the 2.x loader first: it validates the shared surface (unknown
    # fields, duplicate roots, external write targets, unknown
    # adapter/profile, widening routes) under the 3.0 YAML schema marker.
    config = load_root_policy_2x(
        path, project_root=project_root,
        yaml_schema_version=ROOT_POLICY_3X_SCHEMA_VERSION,
    )
    # 3.0 privacy gates (no implicit permission expansion).
    for spec in config.roots:
        privacy = getattr(spec, "privacy_class", None)
        if privacy is None or not privacy:
            raise CatalogConfigError(
                f"roots[{spec.root_id}] privacy_class is required in 3.0 "
                f"(no implicit default)"
            )
        violation = _privacy_rule(spec.kind, privacy)
        if violation is not None:
            raise CatalogConfigError(f"roots[{spec.root_id}] {violation}")
    return config


def export_root_policy_3x(
    config: CatalogConfig, *, project_root: Path | None = None
) -> tuple[str, dict[str, Any]]:
    """RootPolicySnapshot 3.0 canonical export + sha256.

    Privacy-redacted: absolute paths become ``${PROJECT_ROOT}/...`` tokens
    (never emitted verbatim).  The returned sha256 is the envelope-binding
    hash (ZR-404); consumers verify it, never re-derive policy.
    """
    root = project_root or config.project_root
    roots = []
    for spec in config.roots:
        path_ref = str(spec.path)
        try:
            relative = Path(path_ref).resolve(strict=False).relative_to(
                root.resolve(strict=False)
            )
            path_token = "${PROJECT_ROOT}/" + relative.as_posix()
        except ValueError:
            path_token = "<redacted-absolute-path>"
        roots.append({
            "root_id": spec.root_id,
            "path_ref": path_token,
            "kind": spec.kind,
            "adapter_id": spec.adapter_id,
            "admission_profile_id": spec.admission_profile_id,
            "read_only": spec.read_only,
            "reusable_for_filing": spec.reusable_for_filing,
            "allowed_document_kinds": list(spec.allowed_document_kinds),
            "canonical_write_target": getattr(spec, "canonical_write_target", None),
            "priority": spec.priority,
            "cohort": getattr(spec, "cohort", None),
            "privacy_class": getattr(spec, "privacy_class", None),
        })
    policy = {
        "schema_version": ROOT_POLICY_3X_SCHEMA_VERSION,
        "schema": ROOT_POLICY_3X_SCHEMA,
        "reusable_root_kinds": list(config.reusable_root_kinds),
        "roots": roots,
    }
    payload = json.dumps(policy, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest(), policy


__all__ = [
    "ALLOWED_ROOT_FIELDS_3X",
    "ROOT_POLICY_3X_SCHEMA",
    "ROOT_POLICY_3X_SCHEMA_VERSION",
    "export_root_policy_3x",
    "load_root_policy_3x",
]
