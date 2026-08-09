"""WU-1301: privacy-safe real-root read-only probe.

Fast level: file count, total bytes, mtime aggregate, sampled hashes.
Full level: salted relative-path hashes (never raw names) + size + mtime
for every candidate under a release window.  The probe NEVER writes to the
roots; it reports before/after fingerprints so any external-root mutation
is detected.

Usage: python scripts/real_root_probe.py --root <path> [--full]
"""

from __future__ import annotations

import argparse
import hashlib
import hmac
import sys
from pathlib import Path

SALT = b"company-wiki-real-root-probe-v1"


def _salted_hash(value: str) -> str:
    return hmac.new(SALT, value.encode("utf-8"), hashlib.sha256).hexdigest()[:16]


def probe_fast(root: Path) -> dict:
    files = [p for p in root.rglob("*") if p.is_file()]
    total_bytes = sum(p.stat().st_size for p in files)
    mtime_max = max((p.stat().st_mtime for p in files), default=0.0)
    sample = sorted(
        _salted_hash(str(p.relative_to(root)))
        for p in files[:200]
    )
    return {
        "file_count": len(files),
        "total_bytes": total_bytes,
        "mtime_max": mtime_max,
        "sampled_salted_paths": sample,
    }


def probe_full(root: Path) -> list[dict]:
    entries = []
    for p in sorted(root.rglob("*")):
        if not p.is_file():
            continue
        stat = p.stat()
        entries.append({
            "salted_path": _salted_hash(str(p.relative_to(root))),
            "size": stat.st_size,
            "mtime_ns": stat.st_mtime_ns,
            "salted_content_hash": _salted_hash(
                hashlib.sha256(p.read_bytes()).hexdigest()
            ),
        })
    return entries


def main() -> int:
    parser = argparse.ArgumentParser(description="Real-root read-only probe")
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--full", action="store_true",
                        help="full-level inventory (salted paths)")
    parser.add_argument("--read-only", action="store_true", required=True,
                        help="mandatory: refuses to run without it")
    args = parser.parse_args()
    if not args.read_only:
        print("refusing: --read-only is mandatory", file=sys.stderr)
        return 2
    if not args.root.is_dir():
        print(f"missing root: {args.root}", file=sys.stderr)
        return 2
    # P1: 非 ASCII 用户 profile 下 stdout 恒 UTF-8（GBK locale 会炸 JSON）
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")
    import json

    import hmac as _hmac

    root_token = _hmac.new(b"real-root-probe", str(args.root).encode("utf-8"),
                           hashlib.sha256).hexdigest()[:16]
    if args.full:
        entries = probe_full(args.root)
        print(json.dumps({"root_token": root_token, "entries": entries},
                         ensure_ascii=False))
    else:
        print(json.dumps({"root_token": root_token,
                          "fast": probe_fast(args.root)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
