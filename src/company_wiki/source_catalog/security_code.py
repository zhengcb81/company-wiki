"""Strict market-qualified code representation, not discovery alias matching.

Only documented code formatting is normalized. Observed unknown namespaces or
malformed values stay literal; punctuation, exchange suffixes and whitespace
are never removed. Source facts remain untouched by this read projection.
"""

from __future__ import annotations

import re

_NUMERIC_WIDTH = {"HK": 5, "CN": 6}
_US_CODE = re.compile(r"[A-Za-z0-9]+(?:[.\-][A-Za-z0-9]+)*", re.ASCII)


def canonical_security_code(value: str | None, market: str | None) -> str | None:
    """Return a market's code representation, preserving unsupported literals."""
    if not isinstance(value, str):
        return value
    width = _NUMERIC_WIDTH.get(market)
    if width is not None and re.fullmatch(r"[0-9]{1," + str(width) + "}", value):
        return value.zfill(width)
    if market == "US" and _US_CODE.fullmatch(value):
        return value.upper()
    return value


def security_codes_equivalent(
    left: str, right: str, *, left_market: str | None, right_market: str | None,
) -> bool:
    """Compare codes without borrowing a market from a request or other source."""
    if left_market and right_market and left_market != right_market:
        return False
    if left_market == right_market and left_market in {"CN", "HK", "US"}:
        return canonical_security_code(left, left_market) == canonical_security_code(right, right_market)
    return left == right
