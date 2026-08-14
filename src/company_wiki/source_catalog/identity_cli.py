"""Standalone console entry point for read-only listed-company identification."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Sequence

from .security_identity import (
    IdentityStatus,
    OfficialSecurityMasterRefresher,
    SECURITY_MARKETS,
    SecurityIdentityResolver,
    SecurityMasterStore,
    load_identity_master,
)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="company-wiki-identify",
        description="Resolve a company name, alias, or ticker to a verified listed security.",
    )
    parser.add_argument("query", help="company name, alias, or ticker")
    parser.add_argument(
        "--cache-dir",
        type=Path,
        default=Path(".source_catalog/security_master"),
        help="versioned per-market security-master cache directory",
    )
    parser.add_argument("--market", choices=SECURITY_MARKETS)
    parser.add_argument("--exchange")
    parser.add_argument(
        "--refresh",
        action="store_true",
        help="refresh official snapshots before resolving; failures keep stale snapshots",
    )
    parser.add_argument("--pretty", action="store_true")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    args = _parser().parse_args(argv)
    try:
        store = SecurityMasterStore(args.cache_dir)
        refresh = None
        if args.refresh:
            refresh_markets = (args.market,) if args.market else SECURITY_MARKETS
            refresh = OfficialSecurityMasterRefresher(store).refresh(
                markets=refresh_markets
            )
        result = SecurityIdentityResolver(
            load_identity_master(store, market=args.market)
        ).identify(
            args.query,
            market=args.market,
            exchange=args.exchange,
        )
        payload = result.to_dict()
        if refresh is not None:
            payload["refresh"] = refresh
    except Exception as exc:
        # ZR-204: unified error taxonomy emission (canonical code + retryable).
        from .error_taxonomy import structured_error

        print(
            json.dumps(structured_error(exc), ensure_ascii=False, sort_keys=True),
            file=sys.stderr,
        )
        return 1
    print(
        json.dumps(
            payload,
            ensure_ascii=False,
            indent=2 if args.pretty else None,
            sort_keys=True,
        )
    )
    return 0 if result.status is IdentityStatus.RESOLVED else 2


if __name__ == "__main__":
    raise SystemExit(main())


__all__ = ["main"]
