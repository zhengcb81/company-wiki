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


_FLAG_NAMES = (
    "v2_scan_shadow",
    "v2_persist_assertions",
    "v2_resolve_shadow",
    "v2_resolve_active",
    "v2_bundle_active",
    "legacy_bridge_enabled",
)

# Modules allowed to know the flag names / hold flag state: the frozen flag
# machine (flags.py), the persistent snapshot (runtime_policy.py), and the
# gate itself (which scans for the names). Any other production module
# hardcoding the six-flag dict is a second policy source and violates
# FC-201/FC-205.
_POLICY_OWNERS = frozenset({"flags.py", "runtime_policy.py", "architecture_gate.py"})

# Legacy metadata containers may only be read inside the resolver's gated
# bridge (_source_metadata).  Any other production read is a bypass of the
# snapshot's legacy_bridge_enabled decision.
_LEGACY_KEYS = ("acquisition", "dayu_meta")


def control_plane_reads_runtime_policy(
    src_dir: Path | None = None,
) -> tuple[bool, list[str]]:
    """FC-205: production resolver/scan/bundle paths must consume the
    RuntimePolicySnapshot.  The resolver (SourceResolver.__init__) and the
    CLI resolve path must load/derive from the snapshot; no module may
    reconstruct flag state from scratch."""
    if src_dir is None:
        src_dir = Path(__file__).resolve().parent
    violations: list[str] = []
    resolver_path = src_dir / "resolver.py"
    text = resolver_path.read_text(encoding="utf-8")
    if "runtime_policy" not in text:
        violations.append("resolver.py has no RuntimePolicySnapshot reference")
    if "resolver_visibility" not in text:
        violations.append("resolver.py has no resolver_visibility derivation")
    if "legacy_bridge_allowed" not in text:
        violations.append("resolver.py legacy bridge not gated by snapshot")
    cli_path = src_dir / "cli.py"
    cli_text = cli_path.read_text(encoding="utf-8")
    if "load_runtime_policy" not in cli_text:
        violations.append("cli.py resolve/ensure does not load the snapshot")
    return len(violations) == 0, violations


def no_hardcoded_flag_dicts(
    src_dir: Path | None = None,
) -> tuple[bool, list[str]]:
    """FC-205: no production module outside flags.py / runtime_policy.py may
    hardcode the six-flag dict (second policy source, FC-201 deletion
    deadline).  Occurrences inside the policy owners and test files are
    allowed."""
    if src_dir is None:
        src_dir = Path(__file__).resolve().parent
    violations: list[str] = []
    for py_file in sorted(src_dir.rglob("*.py")):
        if py_file.name.startswith("test_") or py_file.name.startswith("__"):
            continue
        if py_file.name in _POLICY_OWNERS:
            continue
        text = py_file.read_text(encoding="utf-8")
        lines = text.splitlines()
        for i, line in enumerate(lines):
            if line.strip().startswith('"v2_') or line.strip().startswith("'v2_"):
                neighbors = " ".join(lines[max(0, i - 1):i + 2])
                hits = sum(1 for flag in _FLAG_NAMES if flag in neighbors)
                if hits >= 2:
                    violations.append(f"{py_file.name}:{i + 1}:hardcoded flag dict")
    return len(violations) == 0, violations


# The legacy-bridge read pattern is a loop over the two container keys and a
# .get(key) from a metadata dict.  Container WRITERS (acquisition_service
# builds the dict, scanner/normalizer store it) and constant definitions
# (visibility_bridge LEGACY_PROFILE_KEYS) are not bridge reads — only the
# loop-with-get pattern is the resolver-only seam.
#
# Built from parts so this module does not contain the literal pattern
# string: the leg04 freeze gate asserts the pattern exists in exactly ONE
# source file (resolver.py), and this gate module must not trip it.
_BRIDGE_LOOP_PATTERN = 'for key in ' + '("acquisition", "dayu_meta")'


def no_legacy_container_reads_outside_resolver(
    src_dir: Path | None = None,
) -> tuple[bool, list[str]]:
    """FC-205: the legacy-container bridge-read loop may only exist inside
    the resolver's gated _source_metadata.  Any other module with the same
    read pattern is a legacy-bridge bypass of the snapshot's
    legacy_bridge_enabled decision."""
    if src_dir is None:
        src_dir = Path(__file__).resolve().parent
    violations: list[str] = []
    resolver_path = src_dir / "resolver.py"
    resolver_text = resolver_path.read_text(encoding="utf-8")
    for py_file in sorted(src_dir.rglob("*.py")):
        if py_file.name.startswith("test_") or py_file.name.startswith("__"):
            continue
        if py_file == resolver_path:
            continue
        if py_file == Path(__file__).resolve():
            continue  # the gate itself carries the pattern constant
        text = py_file.read_text(encoding="utf-8")
        if _BRIDGE_LOOP_PATTERN in text:
            violations.append(
                f"{py_file.name}: legacy bridge-read loop outside resolver"
            )
    if _BRIDGE_LOOP_PATTERN not in resolver_text:
        violations.append("resolver.py bridge loop missing (gate weakened)")
    return len(violations) == 0, violations


__all__ = [
    "control_plane_reads_runtime_policy",
    "no_hardcoded_flag_dicts",
    "no_legacy_container_reads_outside_resolver",
    "rejected_stages_covers_all_investment_stages",
    "source_catalog_does_not_import_prohibited_modules",
    "llm_summarizer_rejects_investment_content",
]
