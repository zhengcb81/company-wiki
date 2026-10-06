"""Path-only classification and retention buckets for the storage footprint.

Rules are mutually exclusive and evaluated top-down on the root-relative POSIX
path of a file; the first matching rule wins. Business originals are never
classified as waste by file extension — anything without provable path
evidence falls through to ``unknown``.
"""

from __future__ import annotations

CATEGORIES = [
    "raw_originals",
    "curated_final_summaries",
    "databases",
    "auto_recovery_materials",
    "tmp_test_cache",
    "plans_reports",
    "git_code",
    "unknown",
]

CATEGORY_LABELS = {
    "raw_originals": "raw/原始TXT/来源侧录",
    "curated_final_summaries": "精选/最终摘要",
    "databases": "数据库/WAL/SHM",
    "auto_recovery_materials": "恢复中的AUTO任务材料",
    "tmp_test_cache": "tmp/测试/缓存",
    "plans_reports": "计划/报告",
    "git_code": "Git与已跟踪代码",
    "unknown": "未知",
}

BUCKETS = ["keep_now", "separate_disposal_review", "undetermined"]

BUCKET_LABELS = {
    "keep_now": "现在保留",
    "separate_disposal_review": "可另开处置",
    "undetermined": "无法判断",
}

BUCKET_REASONS = {
    "keep_now": (
        "原件/来源侧录、精选final、计划报告与仓库代码属读取与审计材料；"
        "本工具零删除，不提出释放"
    ),
    "separate_disposal_review": (
        "逻辑字节仅是可另开处置的候选上界：需独立处置审批与重建/可用性评估；"
        "本工具不执行 purge/hardlink/delete"
    ),
    "undetermined": (
        "active/retry/prepared/未ACK 或类别无法只读证实终态，不凭 mtime 判断；"
        "原件永不进入删除建议"
    ),
}

_TMP_COMPONENTS = frozenset(
    {
        "tmp",
        ".tmp",
        ".tmp-e2e",
        "__pycache__",
        ".pytest_cache",
        ".ruff_cache",
        ".mypy_cache",
        ".venv",
        "node_modules",
        "build",
        "dist",
        ".codegraph",
        ".mimocode",
    }
)
_RAW_COMPONENTS = frozenset(
    {
        "companies",
        "sectors",
        "themes",
        "future_lake",
        "source_manifests",
        "source_provenance",
    }
)
_PLANNING_COMPONENTS = frozenset({".planning", "docs"})
_GOVERNANCE_COMPONENTS = frozenset({"artifacts", "assurance", "control", "drills"})
_CODE_COMPONENTS = frozenset(
    {
        ".git",
        ".githooks",
        ".github",
        "src",
        "scripts",
        "tests",
        "tools",
        "web",
        "config",
        "configs",
        "examples",
        "benchmarks",
    }
)

_DB_SUFFIXES = (".sqlite", ".sqlite3", ".db")
_DB_SIDECAR_SUFFIXES = (
    ".sqlite-wal",
    ".sqlite-shm",
    ".sqlite-journal",
    ".sqlite3-wal",
    ".sqlite3-shm",
    ".sqlite3-journal",
    ".db-wal",
    ".db-shm",
    ".db-journal",
)
_ROOT_PLAN_TOKENS = ("task_plan", "report", "plan")
_ROOT_PLAN_NAMES = frozenset(
    {
        "findings.md",
        "progress.md",
        "review_plan.md",
        "review_queue.md",
        "planning_status.md",
    }
)


def is_db_basename(name: str) -> bool:
    lowered = name.lower()
    if lowered.endswith(_DB_SIDECAR_SUFFIXES):
        return True
    return lowered.endswith(_DB_SUFFIXES)


def _has_tmp_component(rel: str) -> bool:
    parts = rel.split("/")
    if any(part in _TMP_COMPONENTS for part in parts):
        return True
    name = parts[-1]
    return name == ".coverage" or name.startswith("pytest-")


def _inside_auto_dir(rel: str, auto_dirs: set[str]) -> bool:
    for directory in auto_dirs:
        if directory == "":
            return True
        if rel == directory or rel.startswith(directory + "/"):
            return True
    return False


def classify_file(rel: str, *, auto_dirs: set[str]) -> tuple[str, str]:
    """Return ``(category, rule_id)`` for a root-relative POSIX file path."""
    parts = rel.split("/")
    name = parts[-1]
    first = parts[0]
    if _inside_auto_dir(rel, auto_dirs):
        return "auto_recovery_materials", "auto_store_material"
    if is_db_basename(name):
        return "databases", "db_file"
    if _has_tmp_component(rel):
        return "tmp_test_cache", "tmp_tree"
    if len(parts) == 1 and name.startswith(".tmp"):
        return "tmp_test_cache", "derived_index_sidecar"
    if (
        len(parts) == 1
        and name.startswith(".")
        and (name.endswith("_index.json") or name.endswith("_db.json"))
    ):
        return "tmp_test_cache", "derived_index_sidecar"
    if "wiki" in parts:
        return "curated_final_summaries", "wiki_pages"
    if rel.startswith(".source_catalog/derived/") or rel.startswith(
        ".source_catalog/artifacts/"
    ):
        return "curated_final_summaries", "catalog_final_artifacts"
    if first in _RAW_COMPONENTS:
        return "raw_originals", "raw_tree"
    if rel.startswith(".source_catalog/staging/"):
        return "raw_originals", "acquisition_staging"
    if first in _PLANNING_COMPONENTS:
        return "plans_reports", "planning_docs_tree"
    if first == "logs" or name.endswith(".log") or name.endswith(".jsonl"):
        return "plans_reports", "operational_logs"
    if "receipt" in name.lower():
        return "plans_reports", "plan_report_files"
    if first in _GOVERNANCE_COMPONENTS:
        return "plans_reports", "governance_evidence_dirs"
    if len(parts) == 1:
        lowered = name.lower()
        if lowered in _ROOT_PLAN_NAMES or any(
            token in lowered for token in _ROOT_PLAN_TOKENS
        ):
            return "plans_reports", "plan_report_files"
        if lowered.startswith("log") or "_log." in lowered:
            return "plans_reports", "operational_logs"
        return "git_code", "repo_root_file"
    if first in _CODE_COMPONENTS:
        return "git_code", "repo_code_tree"
    return "unknown", "unmatched"


def retention_bucket(category: str, rel: str) -> str:
    """Disposition suggestion bucket; never an executed action."""
    if category in {"auto_recovery_materials", "unknown"}:
        return "undetermined"
    if category == "tmp_test_cache":
        return "separate_disposal_review"
    if category == "databases":
        if _has_tmp_component(rel):
            return "separate_disposal_review"
        return "keep_now"
    return "keep_now"
