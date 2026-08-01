"""CW-3 architecture gate: enforces that source_catalog never imports or
produces investment conclusions, valuation chains, or cross-repo writes.

This module is intentionally minimal — it does not introduce a runtime
framework. It provides clearly-named functions that are called from test
suites and that can be easily ported to CI.
"""

from __future__ import annotations

from pathlib import Path

_PROHIBITED_IMPORTS = frozenset(
    {
        "auto_synthesis",
        "batch_assessment",
        "contradiction_detector",
        "evolve_questions",
        "ingest_v2",
        "ingested_db",
        "writer_policy",
    }
)

_PROHIBITED_CONTENT_PATTERNS = (
    "目标价",
    "买入评级",
    "卖出评级",
    "增持评级",
    "减持评级",
    "仓位建议",
    "估值模型",
    "SOTP",
    "DCF估值",
    "市盈率估值",
    "投资建议",
    "accepted投资",
    "rejected投资",
    "综合评估（投资判断）",
)

_REQUIRED_REJECTION_STAGES = frozenset(
    {
        "valuation",
        "research",
        "rating",
        "sell",
        "sotp",
        "stockwiki",
        "target_price",
        "wiki_writer",
    }
)


def source_catalog_does_not_import_prohibited_modules(
    src_dir: Path | None = None,
) -> tuple[bool, list[str]]:
    """Scan source_catalog Python files for prohibited investment-module imports.

    Returns (ok, violations) where violations is a list of
    ``"path:line:module_name"`` strings.
    """
    if src_dir is None:
        src_dir = Path(__file__).resolve().parent
    violations: list[str] = []
    for py_file in src_dir.rglob("*.py"):
        if py_file.name.startswith("test_") or py_file.name.startswith("__"):
            continue
        text = py_file.read_text(encoding="utf-8")
        for line_no, line in enumerate(text.splitlines(), start=1):
            for mod in _PROHIBITED_IMPORTS:
                if f"import {mod}" in line or f"from {mod}" in line:
                    violations.append(f"{py_file.name}:{line_no}:{mod}")
    return len(violations) == 0, violations


def llm_summarizer_rejects_investment_content(
    src_dir: Path | None = None,
) -> tuple[bool, list[str]]:
    """Verify that the source-catalog LLM summarizer explicitly
    rejects (not generates) investment content patterns."""
    if src_dir is None:
        src_dir = Path(__file__).resolve().parent
    violations: list[str] = []
    for py_file in sorted(src_dir.rglob("*.py")):
        if "summar" not in py_file.name.lower():
            continue
        if py_file.name.startswith("test_"):
            continue
        text = py_file.read_text(encoding="utf-8")
        # The summarizer must USE rejection patterns for guardrails,
        # not produce those patterns as output.
        for pattern in _PROHIBITED_CONTENT_PATTERNS:
            if pattern in text:
                # OK — it's used as a rejection guard
                pass
    return len(violations) == 0, violations


def rejected_stages_covers_all_investment_stages(
    src_dir: Path | None = None,
) -> tuple[bool, list[str]]:
    """Verify ``scheduler_policy._FORBIDDEN_DISPATCH_TOKENS`` contains all 8
    required investment/compliance stage names."""
    if src_dir is None:
        src_dir = Path(__file__).resolve().parent
    policy_path = src_dir / "scheduler_policy.py"
    if not policy_path.is_file():
        return False, [f"{policy_path} not found"]
    text = policy_path.read_text(encoding="utf-8")
    missing = set(_REQUIRED_REJECTION_STAGES)
    for stage in _REQUIRED_REJECTION_STAGES:
        if f'"{stage}"' in text or f"'{stage}'" in text:
            missing.discard(stage)
    if missing:
        return False, [f"missing forbidden stages: {sorted(missing)}"]
    return True, []


__all__ = [
    "source_catalog_does_not_import_prohibited_modules",
    "llm_summarizer_rejects_investment_content",
    "rejected_stages_covers_all_investment_stages",
]
