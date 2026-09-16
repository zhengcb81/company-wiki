"""FC-1301: versioned reason-taxonomy audit gate.

Every reason literal emitted in production source must be registered in
``observability.REASONS`` (additive registry; codes are never removed, only
deprecated).  An unregistered literal is a taxonomy drift — this audit fails closed so
a new reason code forces a deliberate registry edit with a description.

WIDENED 2026-09-15 (work package fc1301-taxonomy-coverage, owner-approved).  The first
version scanned three REGEX literal patterns (``reason="x"`` / ``"reason": "x"`` /
``_reject(..., "x")``), so a reason passed POSITIONALLY was invisible: an inventory
found 17 code-like positional sites in production source and **15 codes that were
never registered** (13 ``focus_policy_*`` + ``stale_gap_hash`` + ``v2_profile_admitted``).
The scan is AST-based now — it maps positional and keyword arguments onto the callee's
parameter names — and it classifies values by SHAPE, because ``reason`` in this
codebase means two different things:

  * a taxonomy CODE (snake_case) -> must be in ``REASONS``;
  * a free-text explanation ("receipt reviewed_at is not ISO-8601 UTC") -> not a code,
    and requiring it to be registered would be nonsense.

Resolution limit, stated rather than hidden: a call whose callee is not defined inside
the scanned package cannot be mapped, so its positional literals are not checked.  The
count of such call sites is reported by the inventory tool
(``revenue-forecast/assurance/runs/2026-09-11_r4-phase-b/evidence/fc1301_reason_inventory.py``);
this gate does not pretend to be exhaustive.
"""

from __future__ import annotations

import ast
import re
import sys
from pathlib import Path

SRC = Path(__file__).resolve().parents[2] / "src" / "company_wiki" / "source_catalog"
sys.path.insert(0, str(SRC.parent))

from company_wiki.source_catalog.observability import (  # noqa: E402
    REASONS,
    REASON_TAXONOMY_VERSION,
)

#: snake_case => candidate taxonomy code; anything else is prose.
CODE_LIKE = re.compile(r"^[a-z][a-z0-9_]*$")
REASON_PARAM = "reason"


def _is_reason_param(name: str) -> bool:
    return name == REASON_PARAM or name.endswith("_reason")


def _param_names(node: ast.FunctionDef | ast.AsyncFunctionDef) -> list[str]:
    args = node.args
    names = [arg.arg for arg in (*args.posonlyargs, *args.args)]
    return names


def _signatures(root: Path) -> dict[str, list[str]]:
    """function/method name -> positional parameter names (dataclasses use fields)."""
    out: dict[str, list[str]] = {}
    for path in sorted(root.rglob("*.py")):
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"))
        except (SyntaxError, UnicodeDecodeError):
            continue
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                out.setdefault(node.name, _param_names(node))
            elif isinstance(node, ast.ClassDef):
                is_dataclass = any(
                    (isinstance(d, ast.Name) and d.id == "dataclass")
                    or (isinstance(d, ast.Attribute) and d.attr == "dataclass")
                    for d in node.decorator_list
                )
                fields = [
                    stmt.target.id for stmt in node.body
                    if isinstance(stmt, ast.AnnAssign) and isinstance(stmt.target, ast.Name)
                ]
                if is_dataclass and fields:
                    out.setdefault(node.name, fields)
    return out


def _callee_name(node: ast.AST) -> str:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        return node.attr
    return ""


def _literal(node: ast.AST) -> str | None:
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    return None


def emitted_codes(root: Path = SRC) -> dict[str, list[str]]:
    """code-like values emitted at reason positions, with ``file:line`` provenance."""
    signatures = _signatures(root)
    found: dict[str, list[str]] = {}
    for path in sorted(root.rglob("*.py")):
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"))
        except (SyntaxError, UnicodeDecodeError):
            continue
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            params = signatures.get(_callee_name(node.func))
            for keyword in node.keywords:
                if keyword.arg and _is_reason_param(keyword.arg):
                    value = _literal(keyword.value)
                    if value and CODE_LIKE.match(value):
                        found.setdefault(value, []).append(f"{path.name}:{node.lineno}")
            if params is None:
                continue
            for index, arg in enumerate(node.args):
                if index >= len(params) or not _is_reason_param(params[index]):
                    continue
                value = _literal(arg)
                if value and CODE_LIKE.match(value):
                    found.setdefault(value, []).append(f"{path.name}:{node.lineno}")
    return found


def test_taxonomy_version_current() -> None:
    assert REASON_TAXONOMY_VERSION == "1.2", (
        "taxonomy version must be bumped when codes are added (1.2 added the 15 "
        "focus/admission codes registered on 2026-09-15)"
    )


def test_every_emitted_reason_is_registered() -> None:
    emitted = emitted_codes()
    missing = sorted(code for code in emitted if code not in REASONS)
    assert not missing, (
        f"unregistered reason codes in production source: {missing} — "
        f"locations: { {code: emitted[code][:3] for code in missing} }; "
        f"register them in observability.REASONS (additive; never remove)"
    )


def test_the_scan_reaches_positional_reason_arguments() -> None:
    """NEGATIVE CASE for the widening: a code passed POSITIONALLY to a resolved callee
    must be found.  Without this, the regex-era blind spot could come back silently."""
    import tempfile

    with tempfile.TemporaryDirectory() as raw:
        root = Path(raw)
        (root / "mod.py").write_text(
            "def _decision(kind, reason, note):\n    return (kind, reason, note)\n\n\n"
            "def go():\n    return _decision('annual_report', 'never_registered_code', 'x')\n",
            encoding="utf-8",
        )
        (root / "kwargs.py").write_text(
            "def call(reason):\n    return reason\n\n\n"
            "def go():\n    return call(reason='also_never_registered')\n",
            encoding="utf-8",
        )
        found = emitted_codes(root)
    assert "never_registered_code" in found, f"positional reason not detected: {found}"
    assert "also_never_registered" in found, f"keyword reason not detected: {found}"


def test_free_text_reasons_are_not_treated_as_codes() -> None:
    """`reason` also carries human explanations; requiring those in the registry would
    be nonsense, so the shape test must exclude them."""
    import tempfile

    with tempfile.TemporaryDirectory() as raw:
        root = Path(raw)
        (root / "prose.py").write_text(
            "def _decision(kind, reason, note):\n    return (kind, reason, note)\n\n\n"
            "def go():\n"
            "    return _decision('x', 'receipt reviewed_at is not ISO-8601 UTC', 'y')\n",
            encoding="utf-8",
        )
        found = emitted_codes(root)
    assert not found, f"free text was treated as a code: {found}"


def test_registry_values_are_documented() -> None:
    for code, description in sorted(REASONS.items()):
        assert isinstance(description, str) and description.strip(), (
            f"reason {code!r} lacks a description"
        )


def test_every_registered_code_has_a_stage() -> None:
    """The stage map is what the collector groups by; a registered code without a
    stage would be emitted into a report that cannot place it."""
    from company_wiki.source_catalog.observability import STAGES_BY_REASON  # noqa: PLC0415

    missing = sorted(code for code in REASONS if code not in STAGES_BY_REASON)
    assert not missing, f"registered codes without a stage: {missing}"
