"""ZR-603: asset ownership/consolidation timeline + geography hierarchy
contract for mining asset facts.

Composes with the ZR-602 additive ``basis`` key: ``ownership_basis``
declares HOW a revenue number relates to group ownership
(one_hundred_percent / equity_share / consolidated). This module provides
the timeline mechanics around that declaration:

  - effective-dated ownership fractions (acquisition effective dates
    change the applicable fraction; no implicit backwards inheritance
    before the first entry);
  - per-period fraction resolution (mid-period ownership changes are
    fail-closed by default; explicit ``allow_pro_rata`` resolves them
    with day-weighted averages — never silent averaging);
  - chain products (group 60% -> intermediate 70% -> mine == 0.42,
    computed in one pass);
  - apply-once share application (equity_share basis is rejected — the
    Kamoa/Porgera double-multiplication guard; consolidated basis is not
    equity-discounted at this layer);
  - additive asset geography {country, region?} validation plus a
    searchable country -> region -> asset index.

Independent revenue-side implementation of the registry contract (no
cross-repo import); wiring into segment documents is additive-only
(keys validated when present, legacy inputs unaffected, forecast
outputs unchanged).
"""

from __future__ import annotations

from datetime import date, timedelta
from typing import Any, Iterable, Mapping

from contracts.constants import ASSET_FACT_OWNERSHIP_BASES
from contracts.evidence import ForecastInputError, parse_iso_date, require

OWNERSHIP_TIMELINE_REQUIRED_KEYS = ("effective_date", "ownership_fraction")


def validate_ownership_timeline(timeline: Any) -> None:
    """Validate an effective-dated ownership timeline.

    Entries carry an ISO ``effective_date`` (unique) and an
    ``ownership_fraction`` in (0, 1]. An empty timeline fails closed.
    """
    require(
        isinstance(timeline, list) and bool(timeline),
        "ownership timeline must be a non-empty list",
    )
    seen: set[str] = set()
    for position, entry in enumerate(timeline):
        require(
            isinstance(entry, dict),
            f"ownership timeline entry {position} must be an object",
        )
        for key in OWNERSHIP_TIMELINE_REQUIRED_KEYS:
            require(
                key in entry,
                f"ownership timeline entry {position}.{key} is required",
            )
        stamp = entry["effective_date"]
        parse_iso_date(stamp, f"ownership timeline entry {position}.effective_date")
        require(stamp not in seen, f"duplicate effective_date: {stamp}")
        seen.add(stamp)
        fraction = entry["ownership_fraction"]
        require(
            isinstance(fraction, (int, float)) and not isinstance(fraction, bool),
            f"ownership_fraction must be numeric at {stamp}",
        )
        require(
            0.0 < float(fraction) <= 1.0,
            f"ownership_fraction must be in (0, 1] at {stamp}: {fraction}",
        )


def _fraction_on(timeline: list[dict[str, Any]], target: date) -> float:
    applicable = [
        entry
        for entry in timeline
        if parse_iso_date(entry["effective_date"], "effective_date") <= target
    ]
    require(
        bool(applicable),
        f"ownership timeline does not cover {_iso(target)} "
        f"(earliest effective_date: {timeline[0]['effective_date']})",
    )
    latest = max(applicable, key=lambda entry: entry["effective_date"])
    return float(latest["ownership_fraction"])


def _iso(value: date) -> str:
    return value.isoformat()


def ownership_fraction_on(timeline: Any, on_date: str) -> float:
    """Fraction applicable at ``on_date``: the latest entry whose
    effective_date is <= on_date. Fail-closed when the date precedes the
    first entry (no implicit backwards inheritance)."""
    validate_ownership_timeline(timeline)
    return _fraction_on(timeline, parse_iso_date(on_date, "on_date"))


def fraction_for_period(
    timeline: Any,
    start_date: str,
    end_date: str,
    *,
    allow_pro_rata: bool = False,
) -> float:
    """Fraction for a period [start_date, end_date] inclusive.

    When ownership changes inside the period the default is fail-closed
    (no silent averaging); explicit ``allow_pro_rata=True`` resolves it
    with a day-weighted average.
    """
    validate_ownership_timeline(timeline)
    start = parse_iso_date(start_date, "start_date")
    end = parse_iso_date(end_date, "end_date")
    require(start <= end, "period start must not be after period end")
    first = _fraction_on(timeline, start)
    last = _fraction_on(timeline, end)
    if first == last:
        return first
    require(
        allow_pro_rata,
        f"ownership changed within period {start_date}..{end_date}: "
        "explicit allow_pro_rata required (no silent averaging)",
    )
    return _day_weighted_fraction(timeline, start, end)


def _day_weighted_fraction(
    timeline: list[dict[str, Any]], start: date, end: date
) -> float:
    total_days = (end - start).days + 1
    weighted = 0.0
    day = start
    while day <= end:
        weighted += _fraction_on(timeline, day)
        day += timedelta(days=1)
    return weighted / total_days


def effective_group_share(chain: Any, on_date: str) -> float:
    """Effective group share along an ownership chain, one pass.

    E.g. group 60% of an intermediate that holds 70% of a mine ==
    0.42 — the product is applied exactly once per level.
    """
    require(
        isinstance(chain, list) and bool(chain),
        "ownership chain must be a non-empty list of timelines",
    )
    target = parse_iso_date(on_date, "on_date")
    share = 1.0
    for level, timeline in enumerate(chain):
        validate_ownership_timeline(timeline)
        share *= _fraction_on(timeline, target)
    require(0.0 < share <= 1.0, f"effective group share out of range: {share}")
    return share


def apply_ownership_share(
    annual_revenue: Mapping[str, Any],
    basis: str,
    chain: Any,
    period_dates: Mapping[str, tuple[str, str]],
) -> dict[str, float]:
    """Apply the effective group share exactly once to 100%-basis revenue.

    ``basis`` must be a ZR-602 ownership basis value:
      - one_hundred_percent: revenue * effective share (group attributable);
      - equity_share: rejected — the share is already applied, multiplying
        again double-counts (Kamoa/Porgera guard);
      - consolidated: rejected — consolidated revenue is not
        equity-discounted at this layer.
    """
    require(
        isinstance(basis, str) and basis in ASSET_FACT_OWNERSHIP_BASES,
        f"unsupported ownership basis: {basis}",
    )
    if basis == "equity_share":
        raise ForecastInputError(
            "ownership share already applied to equity_share basis revenue "
            "(double multiplication rejected)"
        )
    if basis == "consolidated":
        raise ForecastInputError(
            "consolidated basis revenue is not equity-discounted at this layer"
        )
    attributed: dict[str, float] = {}
    for period_key, (start_date, end_date) in period_dates.items():
        require(
            period_key in annual_revenue,
            f"annual_revenue is missing period {period_key}",
        )
        value = annual_revenue[period_key]
        require(
            isinstance(value, (int, float)) and not isinstance(value, bool),
            f"annual_revenue[{period_key}] must be numeric",
        )
        share = effective_group_share(chain, end_date)
        attributed[period_key] = float(value) * share
    return attributed


def validate_geography(geography: Any) -> None:
    """Validate an additive asset geography ``{country, region?}``.

    ``None`` passes (additive contract — assets without geography are
    unaffected); when present, country is a non-empty string and region,
    when present, is a non-empty string.
    """
    if geography is None:
        return
    require(isinstance(geography, dict), "geography must be an object")
    country = geography.get("country")
    require(
        isinstance(country, str) and country.strip(),
        "geography.country is required",
    )
    region = geography.get("region")
    require(
        region is None
        or (isinstance(region, str) and region.strip()),
        "geography.region must be a non-empty string when present",
    )


def geography_index(
    assets: Any,
) -> dict[str, dict[str | None, list[str]]]:
    """Build the searchable country -> (region|None) -> [asset names]
    hierarchy index. Assets without geography fail closed (not silently
    omitted)."""
    require(
        isinstance(assets, Iterable) and not isinstance(assets, (str, bytes)),
        "geography_index requires an iterable of asset objects",
    )
    index: dict[str, dict[str | None, list[str]]] = {}
    for asset in assets:
        require(
            isinstance(asset, Mapping),
            "indexed assets must be objects (name/geography)",
        )
        name = asset.get("name")
        require(
            isinstance(name, str) and name.strip(),
            "indexed asset requires a name",
        )
        geography = asset.get("geography")
        validate_geography(geography)
        require(geography is not None, f"asset {name} has no geography to index")
        region = geography.get("region")
        region_key = region.strip() if isinstance(region, str) else None
        by_region = index.setdefault(geography["country"].strip(), {})
        by_region.setdefault(region_key, []).append(name)
    return index


def validate_segment_ownership(name: str, ownership: Any) -> None:
    """Segment-level additive ``ownership`` key: a chain of timelines.

    ``None`` passes (additive); a present key must be a non-empty list
    of valid timelines."""
    if ownership is None:
        return
    require(
        isinstance(ownership, list) and bool(ownership),
        f"{name}.ownership must be a non-empty list of timelines",
    )
    for level, timeline in enumerate(ownership):
        try:
            validate_ownership_timeline(timeline)
        except ForecastInputError as exc:
            raise ForecastInputError(f"{name}.ownership[{level}]: {exc}") from exc


def validate_segment_geography(name: str, geography: Any) -> None:
    """Segment-level additive ``geography`` key (None passes)."""
    if geography is None:
        return
    try:
        validate_geography(geography)
    except ForecastInputError as exc:
        raise ForecastInputError(f"{name}.geography: {exc}") from exc
