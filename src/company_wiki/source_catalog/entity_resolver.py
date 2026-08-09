"""WU-703: entity resolution independent of company_raw directories.

Identity comes from security_id + market via a controlled entity registry;
display_name is only a hint.  A company that never appears under
``companies/`` can still get an unbound or verified entity assertion.
Same-name different-market and reused tickers must resolve to ambiguous.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class EntityResolution:
    status: str  # exact | ambiguous | unresolved
    canonical_entity_id: str | None = None
    reason: str = ""


def resolve_entity(
    *,
    security_id: str | None,
    market: str | None,
    display_name: str | None,
    registry: dict[str, str],  # (security_id, market) -> canonical_entity_id
) -> EntityResolution:
    """Resolve via strong key first; name is a hint only."""
    if security_id and market:
        key = (security_id, market)
        if key in registry:
            return EntityResolution("exact", registry[key])
        # same security_id in a different market is ambiguous
        same_sec_other_market = [
            entry for (sec, _market), entry in registry.items()
            if sec == security_id and _market != market
        ]
        if same_sec_other_market:
            return EntityResolution(
                "ambiguous", None,
                f"security_id {security_id} exists in another market",
            )
        return EntityResolution("unresolved", None,
                                "new company: unbound assertion available")
    if display_name:
        matches = [
            entry for (sec, _m), entry in registry.items()
            if entry == display_name
        ]
        if len(matches) > 1:
            return EntityResolution("ambiguous", None,
                                    "display_name matches multiple entities")
        if len(matches) == 1:
            return EntityResolution("exact", matches[0], "name-only (weak)")
    return EntityResolution("unresolved", None, "no identity facts")


def name_conflict_detected(*, registry: dict[str, str], display_name: str) -> bool:
    """Same display name bound to two different canonical ids => conflict."""
    owners = {
        entry for (sec, _m), entry in registry.items()
        if entry == display_name
    }
    return len(owners) > 1
