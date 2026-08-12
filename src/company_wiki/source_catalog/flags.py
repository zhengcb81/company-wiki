"""WU-304/305: feature-flag state machine + cohort/circuit-breaker rules.

Independent flags (never one mega-switch):
  v2_scan_shadow / v2_persist_assertions / v2_resolve_shadow /
  v2_resolve_active / v2_bundle_active / legacy_bridge_enabled

Dependency rules (upstream must be accepted before downstream):
  v2_persist_assertions requires v2_scan_shadow
  v2_resolve_shadow requires v2_persist_assertions
  v2_resolve_active requires v2_resolve_shadow (and shadow diff == 0)
  v2_bundle_active requires v2_resolve_active
  legacy_bridge_enabled excludes v2_resolve_active (bridge is migration-only)

Illegal combinations fail fast at startup (FLAG-01..08); breakers only flip
version flags atomically, never mutate the catalog.
"""

from __future__ import annotations

FLAGS = (
    "v2_scan_shadow",
    "v2_persist_assertions",
    "v2_resolve_shadow",
    "v2_resolve_active",
    "v2_bundle_active",
    "legacy_bridge_enabled",
)

REQUIRES = {
    "v2_persist_assertions": ("v2_scan_shadow",),
    "v2_resolve_shadow": ("v2_persist_assertions",),
    "v2_resolve_active": ("v2_resolve_shadow",),
    "v2_bundle_active": ("v2_resolve_active",),
}

EXCLUDES = {
    "legacy_bridge_enabled": ("v2_resolve_active",),
}


def validate_flag_state(flags: dict[str, bool]) -> list[str]:
    """Return illegal-combination problems ([] = valid)."""
    problems: list[str] = []
    unknown = set(flags) - set(FLAGS)
    if unknown:
        problems.append(f"unknown flags: {sorted(unknown)}")
    for flag in FLAGS:
        if not flags.get(flag, False):
            continue
        for required in REQUIRES.get(flag, ()):
            if not flags.get(required, False):
                problems.append(f"{flag} requires {required} enabled")
        for excluded in EXCLUDES.get(flag, ()):
            if flags.get(excluded, False):
                problems.append(f"{flag} conflicts with {excluded} enabled")
    return problems


