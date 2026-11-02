"""Producer commit and actual loaded-code observations for holdout replay.

The replay must import production code from an explicit producer repo at an
explicit base commit. Worktree edits are recorded, not used as a global clean
permission. Wrong HEAD and imports from a different runtime remain errors.
"""
from __future__ import annotations

import subprocess
import hashlib
import sys
from pathlib import Path
from typing import Any

# Diagnostics only; the worker records the code files that actually loaded.
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
    """Verify the explicit base commit; report unrelated worktree edits."""
    root = Path(producer_root)
    if not (root / ".git").exists() and not root.joinpath(".git").is_file():
        raise ProducerError(f"{root} is not a git repository")
    head = _git(root, "rev-parse", "HEAD")
    if head != producer_commit:
        raise ProducerError(
            f"producer HEAD {head[:12]} != requested commit {producer_commit[:12]}"
        )
    try:
        status = _git(root, "status", "--porcelain", "--", *_PRODUCER_TREES)
        dirty = [line for line in status.splitlines() if line.strip()]
    except ProducerError:
        dirty = None  # Optional Git diagnostics cannot refuse a valid runtime.
    try:
        branch = _git(root, "rev-parse", "--abbrev-ref", "HEAD")
    except ProducerError:
        branch = None
    return {
        "producer_root": str(root.resolve()),
        "producer_commit": head,
        "branch": branch,
        "worktree_changes": dirty,
        "runtime_identity": "worker_records_loaded_files_after_execution",
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


def record_runtime_files(producer_root: Path) -> dict[str, dict[str, Any]]:
    """Observe actual loaded source files, without claiming worktree cleanliness.

    These are post-execution file identities, not a claim that HEAD alone
    represents WIP bytes. Sample/oracle freezing is independent of engine edits.
    """
    root = Path(producer_root).resolve()
    files = {}
    for name, module in tuple(sys.modules.items()):
        if not (name == "company_wiki" or name.startswith("company_wiki.")
                or name == "tools.document_understanding_benchmark"
                or name.startswith("tools.document_understanding_benchmark.")):
            continue
        filename = getattr(module, "__file__", None)
        if filename is None:
            continue  # Namespace packages do not contain a loaded code file.
        path = Path(filename).resolve()
        if not path.is_relative_to(root):
            raise ProducerError(f"{name} loaded outside the requested producer")
        try:
            data = path.read_bytes()
        except OSError as exc:
            raise ProducerError(f"cannot observe loaded code for {name}") from exc
        files[name] = {"relative_path": path.relative_to(root).as_posix(),
                       "sha256": hashlib.sha256(data).hexdigest(), "bytes": len(data)}
    return files
