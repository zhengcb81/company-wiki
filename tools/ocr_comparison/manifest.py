"""Run manifest: one JSON document pinning every identity axis of a run.

Records code identity (worktree branch/commit for tools/ocr_comparison),
render identity, per-arm backend identity (models/runtime/precision/prompt/
preprocess/postprocess), resource snapshot, deadline/output caps and cache
behaviour.  No company names, usernames or periods are hardcoded anywhere;
all document identity comes from the frozen sample manifest.
"""

from __future__ import annotations

import hashlib
import json
import platform
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path

CODE_FILES = [
    "tools/ocr_comparison/__init__.py",
    "tools/ocr_comparison/cache.py",
    "tools/ocr_comparison/compare.py",
    "tools/ocr_comparison/manifest.py",
    "tools/ocr_comparison/metrics.py",
    "tools/ocr_comparison/render_pages.py",
    "tools/ocr_comparison/run_comparison.py",
    "tools/ocr_comparison/runner.py",
    "tools/ocr_comparison/backends/__init__.py",
    "tools/ocr_comparison/backends/base.py",
    "tools/ocr_comparison/backends/rapidocr_r0.py",
    "tools/ocr_comparison/backends/xiaomi_x1.py",
    "tools/ocr_comparison/backends/native_n0.py",
]


def code_identity(repo: Path) -> dict:
    try:
        commit = subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=repo, capture_output=True, text=True,
            check=True, timeout=30,
        ).stdout.strip()
        dirty = subprocess.run(
            ["git", "status", "--porcelain"], cwd=repo, capture_output=True, text=True,
            check=True, timeout=30,
        ).stdout
    except (OSError, subprocess.SubprocessError):
        commit, dirty = None, ""
    file_shas = {}
    for rel in CODE_FILES:
        data = (repo / rel).read_bytes()
        file_shas[rel] = hashlib.sha256(data).hexdigest()
    return {
        "branch_commit": commit,
        "worktree_dirty_entries": len([line for line in dirty.splitlines() if line.strip()]),
        "code_file_sha256": file_shas,
        "python": sys.version.split()[0],
        "platform": platform.platform(),
    }


def runtime_identity() -> dict:
    import importlib.metadata as im

    packages = ("transformers", "torch", "pypdfium2", "rapidocr", "onnxruntime")
    versions = {}
    for name in packages:
        try:
            versions[name] = im.version(name)
        except im.PackageNotFoundError:
            versions[name] = None
    return {"package_versions": versions}


def resource_snapshot() -> dict:
    import ctypes

    class MEMORYSTATUSEX(ctypes.Structure):
        _fields_ = [
            ("dwLength", ctypes.c_ulong), ("dwMemoryLoad", ctypes.c_ulong),
            ("ullTotalPhys", ctypes.c_uint64), ("ullAvailPhys", ctypes.c_uint64),
            ("ullTotalPageFile", ctypes.c_uint64), ("ullAvailPageFile", ctypes.c_uint64),
            ("ullTotalVirtual", ctypes.c_uint64), ("ullAvailVirtual", ctypes.c_uint64),
            ("ullAvailExtendedVirtual", ctypes.c_uint64),
        ]

    if sys.platform != "win32":
        return {"note": "non-windows host"}
    stat = MEMORYSTATUSEX()
    stat.dwLength = ctypes.sizeof(MEMORYSTATUSEX)
    ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(stat))
    gb = 1024 ** 3
    return {
        "memory_load_pct": stat.dwMemoryLoad,
        "avail_phys_gb": round(stat.ullAvailPhys / gb, 2),
        "total_phys_gb": round(stat.ullTotalPhys / gb, 2),
        "avail_commit_gb": round(stat.ullAvailPageFile / gb, 2),
        "gpu_note": "no discrete GPU on this host; all arms CPU",
    }


def build_run_manifest(
    repo: Path,
    *,
    arms: dict,
    deadline_seconds: float,
    memory_cap_gb: float,
    cache_enabled: bool,
    sample_manifest_sha256: str,
    gold_sha256: str,
) -> dict:
    return {
        "schema_version": "cwp-ocr-comparison-run-manifest/1",
        "created_at_utc": datetime.now(UTC).isoformat(),
        "code": code_identity(repo),
        "runtime": runtime_identity(),
        "resources_at_start": resource_snapshot(),
        "limits": {
            "deadline_seconds_per_page": deadline_seconds,
            "process_memory_cap_gb": memory_cap_gb,
            "batch_concurrency": 1,
            "output_char_cap": 60000,
            "max_new_tokens": 2048,
        },
        "cache": {"enabled": cache_enabled, "key_axes": [
            "backend_identity", "page_image_sha256", "prompt_sha256", "params",
        ]},
        "arms": arms,
        "inputs": {
            "sample_manifest_sha256": sample_manifest_sha256,
            "gold_sha256": gold_sha256,
        },
    }


def sha256_file(path: str | Path) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()
