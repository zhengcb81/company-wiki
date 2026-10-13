"""Regenerate the local bindings file from the survey manifest.

Local, uncommitted helper: the bindings it writes are machine-specific absolute
paths and must never be committed. It exists so a maintainer can rebuild the
bindings after the ROOT survey manifest changes.

The survey manifest mixes absolute paths with paths relative to the **main
company-wiki checkout**. This worktree is a sparse code checkout with no
``companies/`` directory, so a relative manifest path is resolved against the
manifest's own repository root (with ``--repo-root`` as a fallback), never
against the current working directory. When neither works, the sample is
reported MISSING and simply has no binding -- it is never guessed.

Usage::

    python -X utf8 -m tools.document_understanding_benchmark.make_bindings \
        --manifest <path>/sample_manifest.json \
        --out <local dir>/bindings.local.json \
        --repo-root C:/Users/<you>/Projects/company-wiki
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from .gold import sha256_file


def _candidate_paths(raw: str, repo_root: Path, extra_roots: list[Path]) -> list[Path]:
    path = Path(raw)
    if path.is_absolute():
        return [path]
    candidates = [repo_root / path]
    candidates.extend(root / path for root in extra_roots)
    return candidates


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build an uncommitted bindings file.")
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--repo-root", default=".")
    parser.add_argument(
        "--extra-root",
        action="append",
        default=[],
        help="additional root to resolve relative manifest paths against",
    )
    args = parser.parse_args(argv)

    repo_root = Path(args.repo_root).resolve()
    extra_roots = [Path(root).resolve() for root in args.extra_root]
    manifest = json.loads(Path(args.manifest).read_text(encoding="utf8"))

    bindings: dict[str, str] = {}
    rows: list[dict[str, object]] = []
    for sample in manifest["samples"]:
        located: Path | None = None
        state = "MISSING"
        for candidate in _candidate_paths(sample["path"], repo_root, extra_roots):
            if not candidate.is_file():
                continue
            if sha256_file(candidate) == sample["sha256"]:
                located = candidate
                state = "BOUND"
            else:
                state = "SHA_MISMATCH"
            break
        if located is not None:
            bindings[sample["id"]] = str(located)
        rows.append(
            {
                "sample_id": sample["id"],
                "state": state,
                "path": str(located or _candidate_paths(sample["path"], repo_root, extra_roots)[0]),
            }
        )

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(bindings, ensure_ascii=False, indent=2) + "\n", encoding="utf8")

    for row in rows:
        print(f"{row['sample_id']:<22} {row['state']:<13} {row['path']}")
    print(f"\nbound {len(bindings)}/{len(rows)} -> {out}")
    print("This file is machine-specific and must not be committed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
