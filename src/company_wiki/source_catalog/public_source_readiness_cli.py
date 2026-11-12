"""Public readiness CLI: one JSON response, no paths, no bytes.

stdout carries exactly one JSON readiness response (or nothing on a refused
request shape).  stderr is silent by contract.  The ``--config`` file is the
operator's trusted deployment input; the business JSON on stdin accepts only
a complete 6-field SourceRef plus an explicit mode — never a physical path,
root, SQL string or command.

Exit codes: 0 = response emitted (any readiness state), 2 = request refused
(invalid config/limits/JSON) with no stdout.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import NoReturn, Sequence

from .config import CatalogConfigError, load_catalog_config
from .public_source_readiness import (
    ASSESS_MODES,
    DEFAULT_MAX_VERIFY_BYTES,
    DEFAULT_VERIFY_DEADLINE_SECONDS,
    PublicSourceReadiness,
    parse_public_source_ref,
)
from .reader import CatalogReaderUnavailable
from .service import SourceCatalog
from .source_reader import SourceVersionReader


class _JsonArgumentParser(argparse.ArgumentParser):
    def error(self, message: str) -> NoReturn:
        raise ValueError(message)


def _load_request(raw: str) -> object:
    """Strict single-object JSON with duplicate-key rejection.

    Duplicate keys are a classic smuggling vector (last-key-wins), so the
    stdlib loader is wrapped with an object_pairs_hook that refuses them.
    NaN/Infinity literals are refused via parse_constant.
    """

    def _no_duplicates(pairs: list[tuple[str, object]]) -> dict[str, object]:
        seen: dict[str, object] = {}
        for key, value in pairs:
            if key in seen:
                raise ValueError("duplicate JSON key")
            seen[key] = value
        return seen

    def _reject_constant(name: str) -> object:
        raise ValueError(f"non-finite JSON constant: {name}")

    return json.loads(
        raw,
        object_pairs_hook=_no_duplicates,
        parse_constant=_reject_constant,
    )


def _int_option(
    raw: str | None,
    *,
    default: int,
    low: int,
    high: int,
) -> int:
    if raw is None:
        return default
    try:
        value = int(raw, 10)
    except ValueError:
        raise ValueError("limits must be integers") from None
    if not low <= value <= high:
        raise ValueError("limits out of range")
    return value


def _float_option(raw: str | None, *, default: float) -> float:
    if raw is None:
        return default
    try:
        value = float(raw)
    except ValueError:
        raise ValueError("deadline must be a number") from None
    if value != value or value in (float("inf"), float("-inf")) or value < 0:
        raise ValueError("deadline out of range")
    return value


def main(argv: Sequence[str] | None = None) -> int:
    parser = _JsonArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument(
        "--mode", required=True, choices=list(ASSESS_MODES),
    )
    parser.add_argument(
        "--byte-deadline-seconds", default=None,
        help=f"Verify deadline in seconds (default {DEFAULT_VERIFY_DEADLINE_SECONDS}).",
    )
    parser.add_argument(
        "--max-verify-bytes", default=None,
        help=f"Verify byte ceiling (default {DEFAULT_MAX_VERIFY_BYTES}).",
    )
    try:
        args = parser.parse_args(argv)
        deadline = _float_option(
            args.byte_deadline_seconds, default=DEFAULT_VERIFY_DEADLINE_SECONDS
        )
        max_bytes = _int_option(
            args.max_verify_bytes,
            default=DEFAULT_MAX_VERIFY_BYTES,
            low=1,
            high=2 * 1024 * 1024 * 1024,
        )
        request = _load_request(sys.stdin.read())
        # The CLI boundary accepts ONLY a complete 6-field SourceRef; anything
        # else (extra fields, smuggled paths, wrong shapes) is a refused
        # request with exit 2 and no stdout, before any catalog is opened.
        parse_public_source_ref(request)
        catalog: SourceCatalog | None = None
        try:
            config = load_catalog_config(args.config)
            catalog = SourceCatalog(config)
            readiness = PublicSourceReadiness(SourceVersionReader(catalog))
            response = readiness.assess(
                request,
                mode=args.mode,
                byte_deadline_seconds=deadline,
                max_verify_bytes=max_bytes,
            )
        finally:
            if catalog is not None:
                catalog.close()
    except (CatalogConfigError, CatalogReaderUnavailable, OSError, ValueError):
        return 2
    sys.stdout.write(
        json.dumps(response, ensure_ascii=True, sort_keys=True,
                   separators=(",", ":"), allow_nan=False) + "\n"
    )
    sys.stdout.flush()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
