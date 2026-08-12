"""FC-1201 RED/acceptance tests: root/source hardcode gate ratchet + cleanup.

SCENARIO: EX-08

Interpretation A (user decision 2026-08-12): the FC-304
``no_root_specific_hardcode`` gate is turned into a *frozen ratchet* — the
allowlist of legacy/root-specific owners is pinned to a baseline so no NEW
file can join it without a deliberate, reviewed test update.  The v1 scanner
branches stay allowlisted as the bounded R9 cutover backlog (plan §3 step7:
delete legacy code only after the legacy bridge is off).  Files whose only
token mention was a comment/docstring are cleaned so they can leave the
allowlist (real shrink, zero behavior change).

This FC does NOT touch the v1 scanner, the production config loader, the
write path, or production yaml (canonical_writer/cli refactors are deferred
to an FC-1201 follow-up — they require a loader change, out of scope for a
"safe cleanup" FC).
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))


# FC-1201 frozen baseline for the root-hardcode allowlist.  This is the
# bounded set of files permitted to reference root tokens:
#   - policy modules (own the tokens by contract)
#   - adapters (know the root layout they serve)
#   - the gate itself (carries the token list)
#   - v1 / loader-blocked backlog (R9 cutover / follow-up; documented in the
#     FC-1201 WU card).
# Adding a file requires updating this baseline (= deliberate review).
# Shrinking is encouraged: remove a file from the allowlist AND here.
FC_1201_FROZEN_ALLOWLIST = frozenset(
    {
        # policy modules — own the tokens
        "registry.py",
        "policy_2x.py",
        "config.py",
        "adapter_dispatch.py",
        # adapters — know the root layout they serve
        "company_raw.py",
        "dayu.py",
        "sidecar.py",
        # the gate itself carries the token list
        "architecture_gate.py",
        # v1 / loader-blocked backlog (R9 cutover or FC-1201 follow-up)
        "scanner.py",
        "models.py",
        "canonical_writer.py",
        "portfolio_promoter.py",
        "admission.py",
        "focus_cleanup.py",
        "backfill_v2.py",
        "cli.py",
    }
)


def test_fc1201_allowlist_ratchet_frozen():
    """Ratchet: the allowlist must equal the FC-1201 frozen baseline.

    Any addition (new file tolerated) or removal (file cleaned up) changes
    the set and trips this test, forcing a deliberate baseline update.
    """
    from company_wiki.source_catalog.architecture_gate import (
        _ROOT_HARDCODE_ALLOWED_FILES,
    )

    current = frozenset(_ROOT_HARDCODE_ALLOWED_FILES)
    assert current == FC_1201_FROZEN_ALLOWLIST, (
        "root-hardcode allowlist drifted from FC-1201 frozen baseline — "
        f"added={sorted(current - FC_1201_FROZEN_ALLOWLIST)}, "
        f"removed={sorted(FC_1201_FROZEN_ALLOWLIST - current)}"
    )


def test_fc1201_comment_only_files_left_allowlist():
    """Files whose only token mention was a comment/docstring must be cleaned
    and removed from the allowlist (resolver/observability/entity_resolver)."""
    from company_wiki.source_catalog.architecture_gate import (
        _ROOT_HARDCODE_ALLOWED_FILES,
    )

    for cleaned in ("resolver.py", "observability.py", "entity_resolver.py"):
        assert cleaned not in _ROOT_HARDCODE_ALLOWED_FILES, (
            f"{cleaned} should have left the allowlist after FC-1201 cleanup"
        )


def test_fc1201_cleaned_files_are_token_free():
    """The files removed from the allowlist must actually contain none of the
    four root tokens — otherwise the gate would (correctly) flag them."""
    from company_wiki.source_catalog import architecture_gate as gate

    src_dir = Path(gate.__file__).resolve().parent
    # entity_resolver.py was DELETED in FC-1203 (dead module) — deletion is
    # the strongest form of token-free; only surviving files are read here.
    for cleaned in ("resolver.py", "observability.py"):
        text = (src_dir / cleaned).read_text(encoding="utf-8")
        for token in gate._ROOT_HARDCODE_TOKENS:
            assert token not in text, (
                f"{cleaned} still contains root token {token!r} after cleanup"
            )


def test_fc1201_gate_green_after_cleanup():
    """Integration: the gate stays green once the comment-only files are
    cleaned and leave the allowlist (no new violations introduced)."""
    from company_wiki.source_catalog.architecture_gate import (
        no_root_specific_hardcode,
    )

    ok, violations = no_root_specific_hardcode()
    assert ok, f"root-specific hardcodes flagged: {violations}"


def test_fc1201_gate_still_detects_new_hardcode(tmp_path):
    """Adversarial: a NEW module hardcoding a root token must still trip the
    gate — the ratchet shrinks the allowlist, it does not weaken detection."""
    from company_wiki.source_catalog.architecture_gate import (
        no_root_specific_hardcode,
    )

    (tmp_path / "new_owner.py").write_text(
        'if root_id == "dayu_portfolio":\n    pass\n', encoding="utf-8"
    )
    ok, violations = no_root_specific_hardcode(tmp_path)
    assert not ok
    assert any("dayu_portfolio" in v for v in violations)
