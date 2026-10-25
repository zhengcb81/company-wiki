"""Frozen producer deployment verification (H07).

The replay must import production code from an explicit producer repo at an
explicit commit. A dirty tree, a different HEAD, or an import that resolves
anywhere else refuses the run instead of silently measuring something else.
"""
from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Any

# Trees whose tracked state must be clean for the deploy to count as frozen.
_PRODUCER_TREES = ("src", "scripts", "tools", "config")


class ProducerError(RuntimeError):
    """The producer deploy does not match the requested frozen commit."""


def _git(producer_root: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", "-C", str(producer_root), *args],
        capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=60,
    )
    if result.returncode != 0:
        raise ProducerError(f"git {' '.join(args[:2])} failed: {result.stderr.strip()[:200]}")
    return result.stdout.strip()


def verify_producer(producer_root: Path, producer_commit: str) -> dict[str, Any]:
    """Verify HEAD == producer_commit and that production trees are clean."""
    root = Path(producer_root)
    if not (root / ".git").exists() and not root.joinpath(".git").is_file():
        raise ProducerError(f"{root} is not a git repository")
    head = _git(root, "rev-parse", "HEAD")
    if head != producer_commit:
        raise ProducerError(
            f"producer HEAD {head[:12]} != requested commit {producer_commit[:12]}"
        )
    dirty = []
    for tree in _PRODUCER_TREES:
        if not root.joinpath(tree).exists():
            continue
        status = _git(root, "status", "--porcelain", "--", tree)
        if status:
            dirty.extend(line for line in status.splitlines() if line.strip())
    if dirty:
        raise ProducerError(
            "producer tree has uncommitted changes in production paths: "
            + "; ".join(dirty[:5])
        )
    return {
        "producer_root": str(root.resolve()),
        "producer_commit": head,
        "branch": _git(root, "rev-parse", "--abbrev-ref", "HEAD"),
        "verified_clean_trees": [t for t in _PRODUCER_TREES if root.joinpath(t).exists()],
    }


def import_paths(producer_root: Path) -> list[Path]:
    """PYTHONPATH entries so company_wiki resolves from the producer repo."""
    root = Path(producer_root)
    paths = [root / "src", root, root / "scripts"]
    return [p for p in paths if p.exists()]


def record_import_roots(producer_root: Path) -> dict[str, str]:
    """Prove where production modules actually resolved from (worker side)."""
    import company_wiki  # noqa: PLC0415 - the point is to inspect the live import
    roots = {"company_wiki": str(Path(company_wiki.__file__).resolve())}
    try:
        from company_wiki import source_catalog  # noqa: F401
        roots["company_wiki.source_catalog"] = str(Path(source_catalog.__file__).resolve())
    except ImportError:  # pragma: no cover - defensive
        roots["company_wiki.source_catalog"] = ""
    try:
        import tools.document_understanding_benchmark as dub  # noqa: F401
        roots["tools.document_understanding_benchmark"] = str(Path(dub.__file__).resolve())
    except ImportError:  # pragma: no cover - defensive
        roots["tools.document_understanding_benchmark"] = ""
    return roots


def assert_imports_from_producer(roots: dict[str, str], producer_root: Path) -> None:
    root = str(Path(producer_root).resolve())
    for module, path in roots.items():
        if not path or not path.replace("\\", "/").startswith(root.replace("\\", "/") + "/"):
            raise ProducerError(
                f"{module} imported from {path or 'nowhere'}, expected under {root}"
            )
