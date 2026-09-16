"""FC-1301: versioned reason-taxonomy audit gate.

Every reason literal emitted in production source must be registered in
``observability.REASONS`` (additive registry; codes are never removed, only
deprecated).  An unregistered literal is a taxonomy drift — this audit fails closed so
a new reason code forces a deliberate registry edit with a description.

WIDENED 2026-09-15, corrected 2026-09-16 (work package fc1301-taxonomy-coverage).  The
first version scanned three REGEX literal patterns (``reason="x"`` / ``"reason": "x"`` /
``_reject(..., "x")``), so a reason passed POSITIONALLY was invisible.  The AST version
that replaced it was WRONG in the same direction for one more round: it resolved callees
by bare name with first-definition-wins, so a positional reason in a module whose
``_reject``/``_result`` definition sorted later was still invisible - an independent
review (B.VR-fc1301, P0) proved a brand-new code at ``close_gap.py:256`` passed GREEN.
It now treats every definition of a name as a candidate (fail closed on ambiguity); the
second pass found 16 more never-registered codes in ``resolver.py``,
``security_identity.py`` and ``close_gap.py``, which are registered as well.

It also classifies values by SHAPE, because ``reason`` in this codebase means two
different things:

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
sys.path.insert(0, str(SRC.parents[1]))

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


def _signatures(root: Path) -> dict[str, list[list[str]]]:
    """function/method name -> ALL positional parameter lists found for that name.

    WHY ALL OF THEM (B-VR1301-01, P0): the first version kept only the first definition
    (``setdefault`` over sorted paths), so ``_reject`` resolved to
    ``artifact_handle.py``'s ``(artifact, reason)`` and a call like
    ``_reject("code", ...)`` in ``close_gap.py`` was mapped onto the WRONG parameter -
    the reason at index 0 was never looked at.  The reviewer proved the consequence: a
    brand-new positional code at ``close_gap.py:256`` left this gate GREEN.  A gate must
    fail CLOSED on ambiguity, so every definition of a name is a candidate and a
    position counts as a reason position if ANY of them names it so.
    """
    out: dict[str, list[list[str]]] = {}
    for path in sorted(root.rglob("*.py")):
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"))
        except (SyntaxError, UnicodeDecodeError):
            continue
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                out.setdefault(node.name, []).append(_param_names(node))
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
                    out.setdefault(node.name, []).append(fields)
    return out


def _is_reason_position(params_list: list[list[str]], index: int) -> bool:
    """True when ANY definition of the callee names that position a reason."""
    for params in params_list:
        if index < len(params) and _is_reason_param(params[index]):
            return True
    return False


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
            params_list = signatures.get(_callee_name(node.func))
            for keyword in node.keywords:
                if keyword.arg and _is_reason_param(keyword.arg):
                    value = _literal(keyword.value)
                    if value and CODE_LIKE.match(value):
                        found.setdefault(value, []).append(f"{path.name}:{node.lineno}")
            if not params_list:
                continue
            for index, arg in enumerate(node.args):
                if not _is_reason_position(params_list, index):
                    continue
                value = _literal(arg)
                if value and CODE_LIKE.match(value):
                    found.setdefault(value, []).append(f"{path.name}:{node.lineno}")
    return found


def test_taxonomy_version_is_the_frozen_n1_contract() -> None:
    """The flat taxonomy version is FROZEN, not bumped per code addition.

    Learned the hard way on 2026-09-16: this gate's first widening bumped 1.1 -> 1.2
    while adding the 15 previously invisible codes, and CI run 35130154115 went red on
    `tests/unit/test_stage_taxonomy.py`, which pins 1.1 as the N-1 compatibility
    contract ("N-1 compat: the v1.1 flat taxonomy constant is untouched") while the
    cross-repo event schema is `stage-taxonomy-2.0`.  Consumers key off this value, so
    a bump is a cross-repo contract decision; registering codes is additive and does
    not need one.  This case exists so the next author cannot repeat the mistake.
    """
    assert REASON_TAXONOMY_VERSION == "1.1", (
        "the flat reason taxonomy is the frozen N-1 contract (see "
        "tests/unit/test_stage_taxonomy.py); adding codes is additive and must NOT "
        "bump it - a bump is a cross-repo contract change"
    )


def test_the_newly_registered_codes_are_present() -> None:
    """The 15 codes that were invisible to the regex-era gate must stay registered
    (additive: a later edit may not quietly drop them)."""
    expected = {
        "focus_policy_explicit_document_kind", "focus_policy_explicit_kind_not_allowed",
        "focus_policy_announcement_or_notice", "focus_policy_prospectus_keyword",
        "focus_policy_call_transcript_keyword", "focus_policy_strict_broker_evidence",
        "focus_policy_commentary_without_broker_evidence", "focus_policy_regulatory_form",
        "focus_policy_semi_annual_keyword", "focus_policy_quarterly_keyword",
        "focus_policy_annual_keyword", "focus_policy_financial_report_keyword",
        "focus_policy_investor_relations_keyword", "v2_profile_admitted",
        "stale_gap_hash",
    }
    missing = sorted(code for code in expected if code not in REASONS)
    assert not missing, f"registered 2026-09-15 but now missing: {missing}"


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


def test_the_scan_handles_a_name_with_several_definitions() -> None:
    """REGRESSION for B-VR1301-01 (P0): callees were resolved by bare name with
    FIRST-DEFINITION-WINS, so `_reject` mapped onto whichever definition sorted first
    and a positional reason in another module was never examined - the reviewer proved
    a brand-new code at close_gap.py:256 passed GREEN.  Every definition of a name is a
    candidate now, so a position that is a reason in ANY of them must be scanned."""
    import tempfile

    with tempfile.TemporaryDirectory() as raw:
        root = Path(raw)
        (root / "a_first_by_path.py").write_text(
            "def _reject(artifact, reason):\n    return (artifact, reason)\n",
            encoding="utf-8",
        )
        (root / "z_second.py").write_text(
            "def _reject(reason):\n    return reason\n\n\n"
            "def go():\n    return _reject('brand_new_positional_code')\n",
            encoding="utf-8",
        )
        found = emitted_codes(root)
    assert "brand_new_positional_code" in found, (
        f"a positional reason whose callee has several definitions was missed: {found}"
    )


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


def test_the_registry_compared_against_is_this_repository_copy() -> None:
    """B-VR1301-04: the first version inserted `SRC.parent` (which holds no
    `company_wiki` package) into sys.path, so nothing guaranteed that the REASONS being
    compared against came from the tree under test - a copy-based verification silently
    validated the working repository's registry instead."""
    import company_wiki.source_catalog.observability as imported

    expected = SRC / "observability.py"
    assert Path(imported.__file__).resolve() == expected.resolve(), (
        f"the gate imported a DIFFERENT registry: {imported.__file__} != {expected}"
    )
    assert expected.is_file()


def test_registry_values_are_documented() -> None:
    for code, description in sorted(REASONS.items()):
        assert isinstance(description, str) and description.strip(), (
            f"reason {code!r} lacks a description"
        )


def test_the_newly_registered_codes_have_stages() -> None:
    """Registration alone is not enough: the collector groups events by stage and drops
    mismatched ones fail-closed, so every code added here needs a stage.  (The
    every-code-has-a-stage property is already pinned by
    tests/unit/test_stage_taxonomy.py:126 - this case covers the NEW codes.)"""
    from company_wiki.source_catalog.observability import STAGES_BY_REASON  # noqa: PLC0415

    new_codes = (
        "one_verified_exact_identity",
        "multiple_verified_exact_identities",
        "exact_identity_conflicts_with_market_or_exchange_hint",
        "no_verified_identity_candidate",
        "one_unique_strong_fuzzy_identity",
        "fuzzy_candidates_require_user_selection",
        "identity_mismatch_market_or_security_id",
        "one_existing_source_matches_provider_identity",
        "latest_existing_source_matches_provider_identity",
        "multiple_existing_sources_match_provider_identity",
        "one_existing_source_satisfies_semantic_request",
        "latest_existing_source_satisfies_semantic_request",
        "multiple_existing_sources_match_semantic_request",
        "matching_sources_have_unknown_published_date",
        "no_runtime_policy",
        "stale_policy_hash",
    )
    missing = sorted(code for code in new_codes if code not in STAGES_BY_REASON)
    assert not missing, f"newly registered codes without a stage: {missing}"
