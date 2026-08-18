"""WU-303: single security-policy export consumed across repos.

company-wiki is the authoritative RootPolicy source.  ``export_policy``
produces a versioned canonical JSON snapshot (privacy-redacted: path tokens
stay as tokens, absolute paths are replaced) plus its sha256.  Consumers
(filing-fetch, revenue) read the snapshot or the policy hash from resolver
receipts; they never maintain their own allowlists (POL-01..03).
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

POLICY_SCHEMA_VERSION = "1.0"


def _redact_path(path: Path, project_root: Path) -> str:
    """Path tokens stay; absolute paths become ${PROJECT_ROOT}-relative."""
    try:
        relative = path.relative_to(project_root)
        return "${PROJECT_ROOT}/" + relative.as_posix()
    except ValueError:
        return "<redacted-absolute-path>"


def export_policy(config, *, project_root: Path | None = None) -> tuple[str, dict]:
    """Return (policy_sha256, canonical_policy_dict)."""
    root = project_root or config.project_root
    roots = []
    for spec in config.roots:
        roots.append(
            {
                "root_id": spec.root_id,
                "path": _redact_path(spec.path, root),
                "kind": spec.kind,
                "priority": spec.priority,
                "adapter_id": spec.adapter_id,
                "admission_profile_id": spec.admission_profile_id,
                "read_only": spec.read_only,
                # ZR-405: the export reflects the RESOLVER's effective
                # reusability — an unset per-root flag follows the kind-level
                # reusable_root_kinds allowance (the resolver's gate), so a
                # consumer containment check can never diverge from what the
                # wiki would actually reuse.
                "reusable_for_filing": _effective_reusable(spec, config),
                "routes": [
                    {
                        "include": list(route.include),
                        "exclude": list(route.exclude),
                        "adapter_id": route.adapter_id,
                    }
                    for route in spec.routes
                ],
            }
        )
    policy = {
        "schema_version": POLICY_SCHEMA_VERSION,
        "reusable_root_kinds": list(config.reusable_root_kinds),
        "roots": roots,
    }
    payload = json.dumps(policy, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest(), policy


def _effective_reusable(spec, config) -> bool:
    """Per-root reusable_for_filing if set, else the kind-level
    reusable_root_kinds allowance (resolver-consistent)."""
    if spec.reusable_for_filing is not None:
        return bool(spec.reusable_for_filing)
    return spec.kind in config.reusable_root_kinds


def validate_policy_hash(expected: str, actual: str) -> list[str]:
    if expected != actual:
        return [f"policy hash {actual[:12]} != expected {expected[:12]} (POL-02)"]
    return []


def policy_authorizes_root(policy: dict, root_id: str) -> bool:
    """POL-01: a consumer-local allowance can never widen the policy."""
    return any(
        r.get("root_id") == root_id and r.get("reusable_for_filing")
        for r in policy.get("roots", [])
    )
