"""Deterministic source-bundle fingerprints for worker reload verification."""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any


CORE_SOURCE_PATHS = (
    "src/company_wiki/source_catalog/code_identity.py",
    "src/company_wiki/source_catalog/worker.py",
    "src/company_wiki/source_catalog/lock.py",
    "src/company_wiki/source_catalog/store.py",
    "src/company_wiki/source_catalog/normalizer.py",
    "src/company_wiki/source_catalog/llm_summarizer.py",
    "src/company_wiki/source_catalog/llm_failure_policy.py",
    "src/company_wiki/source_catalog/service.py",
)


def source_bundle_fingerprint(project_root: Path) -> dict[str, Any]:
    root = Path(project_root).resolve(strict=False)
    files: list[dict[str, str]] = []
    digest = hashlib.sha256()
    for relative_path in CORE_SOURCE_PATHS:
        path = root / relative_path
        try:
            content = path.read_bytes()
        except OSError as exc:
            return {
                "fingerprint": None,
                "error": (
                    f"{type(exc).__name__}: required source file unavailable: "
                    f"{relative_path}"
                ),
                "files": [],
            }
        file_hash = hashlib.sha256(content).hexdigest()
        files.append({"path": relative_path, "sha256": file_hash})
        digest.update(relative_path.encode("utf-8"))
        digest.update(b"\0")
        digest.update(file_hash.encode("ascii"))
        digest.update(b"\n")
    return {"fingerprint": digest.hexdigest(), "error": None, "files": files}


__all__ = ["CORE_SOURCE_PATHS", "source_bundle_fingerprint"]
