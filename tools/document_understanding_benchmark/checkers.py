"""Independent checkers over ``du-observed/1`` against ``du-gold/1``.

Design rules enforced here:

1. A fact is recalled only when the observation carries it through *replayable*
   original evidence: actual selected locator -> original text/coordinates.
   Flattened text and generated claims cannot prove their own provenance.
2. ``coverage.native_scan``/``opaque_pages`` gate recall. An unread page yields
   ``UNAVAILABLE`` (cannot prove either way), never ``FAIL`` and never ``PASS``.
3. ``coverage.complete``, schema validity and "a citation exists" never
   substitute for business recall or correctness.
4. Semantic entailment is ``NOT_EVALUATED`` unless an independent review is
   supplied; regex/numeric agreement is not entailment.
"""

from __future__ import annotations

import re
from collections.abc import Iterable, Mapping, Sequence
from typing import Any

from .schema import (
    CRITICAL,
    REQUIRED_BUSINESS,
    DISPOSITION_CONTEXT,
    CORRECTNESS_IF_EMITTED,
    FAIL,
    NOT_EVALUATED,
    PASS,
    PARTIAL,
    UNAVAILABLE,
    UNUSABLE_BLOCKS,
)
from .schema import (
    MAX_UNUSABLE_BLOCK_RATIO as _schema_max_unusable_ratio,
)
from .schema import (
    MIN_LEGIBILITY_CHARS as _schema_min_legibility_chars,
)
from .textutil import (
    anchor_matches,
    basis_contradiction,
    has_actual_marker,
    has_negation,
    has_plan_marker,
    looks_like_question,
    modality_conflicts,
    number_present,
    role_is_third_party,
    stage_regression,
    unit_matches_evidence,
)

# A claim whose evidence covers less than this share of its own length is
# treated as under-evidenced rather than fully evidenced.
MIN_EVIDENCE_COVERAGE = 0.5

# Legibility thresholds and the unusable-block list live in schema.py because the
# observer measures legibility over everything it parsed while this module judges
# it; both must use the same definition. See schema.UNUSABLE_BLOCKS for the
# measured control behind the numbers.
MAX_UNUSABLE_BLOCK_RATIO = _schema_max_unusable_ratio
MIN_LEGIBILITY_CHARS = _schema_min_legibility_chars


def _in_unusable_block(char: str) -> bool:
    code = ord(char)
    return any(low <= code <= high for low, high in UNUSABLE_BLOCKS)


def _check(
    check_id: str,
    status: str,
    *,
    expected: Any,
    observed: Any,
    evidence_refs: Sequence[str] = (),
    dimension: str = "",
    detail: str = "",
) -> dict[str, Any]:
    return {
        "check_id": check_id,
        "dimension": dimension,
        "status": status,
        "expected": expected,
        "observed": observed,
        "evidence_refs": list(evidence_refs),
        "detail": detail,
    }


# ---------------------------------------------------------------------------
# integrity
# ---------------------------------------------------------------------------


def check_source_identity(observed: Mapping[str, Any], gold: Mapping[str, Any]) -> dict[str, Any]:
    obs_sha = observed.get("source_sha256")
    gold_sha = gold.get("source_sha256")
    status = PASS if obs_sha == gold_sha else UNAVAILABLE
    return _check(
        "integrity.source_identity",
        status,
        expected=gold_sha,
        observed=obs_sha,
        dimension="observation_integrity",
        detail="" if status == PASS else "observed source is not the gold source",
    )


def _selected_locator_set(observed: Mapping[str, Any]) -> set[str]:
    return set(observed.get("selected_locators") or [])


def _claims(observed: Mapping[str, Any]) -> list[dict[str, Any]]:
    return list(observed.get("claims") or [])


def check_selected_source_material(observed: Mapping[str, Any], gold: Mapping[str, Any]) -> dict[str, Any]:
    rows = observed.get("selected_evidence")
    if rows is None:
        return _check("integrity.selected_source_material", NOT_EVALUATED,
                      expected="every selected locator carries original source text", observed=None,
                      dimension="observation_integrity", detail="legacy source mapping not provided")
    missing = sorted(_selected_locator_set(observed) - {row["locator"] for row in rows})
    return _check("integrity.selected_source_material", FAIL if missing else PASS,
                  expected="every selected locator carries original source text", observed=missing,
                  evidence_refs=missing, dimension="observation_integrity")


def check_unsupported_claims(observed: Mapping[str, Any], gold: Mapping[str, Any]) -> dict[str, Any]:
    """Claims whose every evidence locator was never selected are unsupported."""

    selected = _selected_locator_set(observed)
    unsupported: list[dict[str, Any]] = []
    for index, claim in enumerate(_claims(observed)):
        locators = list(claim.get("evidence_locators") or [])
        if not locators:
            unsupported.append({"claim_index": index, "reason": "no_evidence_locator"})
            continue
        if not selected.intersection(locators):
            unsupported.append({"claim_index": index, "reason": "locator_never_selected"})
    return _check(
        "integrity.unsupported_claims",
        FAIL if unsupported else PASS,
        expected="every claim cites at least one selected locator",
        observed=unsupported,
        evidence_refs=[loc for claim in _claims(observed) for loc in (claim.get("evidence_locators") or [])],
        dimension="observation_integrity",
    )


def check_replay(observed: Mapping[str, Any], gold: Mapping[str, Any]) -> dict[str, Any]:
    """Every claim citation must point at something the run actually selected."""

    selected = _selected_locator_set(observed)
    dangling: list[str] = []
    for claim in _claims(observed):
        for locator in claim.get("evidence_locators") or []:
            if locator not in selected:
                dangling.append(locator)
    for unit in observed.get("semantic_units") or []:
        for locator in unit.get("locators") or []:
            if locator not in selected:
                dangling.append(locator)
    return _check(
        "replay.evidence_locators",
        FAIL if dangling else PASS,
        expected="all cited locators were selected",
        observed=sorted(set(dangling)),
        evidence_refs=sorted(set(dangling)),
        dimension="citation_replay",
    )


# ---------------------------------------------------------------------------
# route
# ---------------------------------------------------------------------------


def check_route(observed: Mapping[str, Any], gold: Mapping[str, Any]) -> dict[str, Any]:
    expected = list(gold.get("expected_route_families") or [])
    route = observed.get("route")
    if not expected:
        return _check(
            "route.family",
            NOT_EVALUATED,
            expected=[],
            observed=None,
            dimension="route_type",
            detail="gold declares no expected route family",
        )
    if not route:
        return _check(
            "route.family",
            NOT_EVALUATED,
            expected=expected,
            observed=None,
            dimension="route_type",
            detail="observation carries no route; baseline has no new router",
        )
    actual = route.get("family") or route.get("document_kind")
    status = PASS if actual in expected else FAIL
    return _check(
        "route.family",
        status,
        expected=expected,
        observed=actual,
        dimension="route_type",
    )


# ---------------------------------------------------------------------------
# recall
# ---------------------------------------------------------------------------


def _unescaped_pages(observed: Mapping[str, Any]) -> set[int]:
    coverage = observed.get("coverage") or {}
    pages: set[int] = set()
    for page in coverage.get("opaque_pages") or []:
        try:
            pages.add(int(page))
        except (TypeError, ValueError):
            continue
    return pages


def _selected_source_rows(observed: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    selected = _selected_locator_set(observed)
    return [row for row in observed.get("selected_evidence") or []
            if row.get("locator") in selected]


def _anchor_location_matches(anchor: Mapping[str, Any], row: Mapping[str, Any]) -> bool:
    # Gold locators may be hand-labelled table hints; actual page/line coordinates
    # are authoritative. No generated claim or flattened text can supply them.
    if anchor.get("location_kind") == "document":
        return True
    if anchor.get("page") is not None and row.get("page") != anchor["page"]:
        return False
    if anchor.get("line") is not None:
        start = row.get("line")
        end = row.get("line_end") or start
        if start is None or not start <= anchor["line"] <= end:
            return False
    return True


def _support_set_status(support_set: Sequence[Mapping[str, Any]], observed: Mapping[str, Any],
                        *, require_same_scope: bool = False,
                        context: bool = False) -> tuple[str, list[str]]:
    rows = list(observed.get("context_evidence") or []) if context else _selected_source_rows(observed)
    candidates = []
    missing_position = False
    for anchor in support_set:
        matches = [row for row in rows if _anchor_location_matches(anchor, row)
                   and anchor_matches(anchor.get("exact_quote") or "", row.get("text") or "")]
        if not matches:
            if any(anchor_matches(anchor.get("exact_quote") or "", row.get("text") or "")
                   and ((anchor.get("page") is not None and row.get("page") is None)
                        or (anchor.get("line") is not None and row.get("line") is None)) for row in rows):
                missing_position = True
            return (NOT_EVALUATED if missing_position else FAIL), []
        known = [row for row in matches if all(not anchor.get(key) or row.get(key) == anchor[key]
                                             for key in ("scope_id", "source_role", "period"))]
        if not known:
            unknown = any(any(anchor.get(key) and row.get(key) is None
                              for key in ("scope_id", "source_role", "period")) for row in matches)
            return (NOT_EVALUATED if unknown else FAIL), []
        candidates.append(known)
    if require_same_scope:
        shared = set.intersection(*[{row.get("scope_id") for row in group if row.get("scope_id")}
                                    for group in candidates])
        if not shared:
            if any(any(not row.get("scope_id") for row in group) for group in candidates):
                return NOT_EVALUATED, []
            return FAIL, []
        scope = sorted(shared)[0]
        candidates = [[row for row in group if row.get("scope_id") == scope] for group in candidates]
    return PASS, sorted({row["locator"] for group in candidates for row in group})


def _group_unread(support_set: Sequence[Mapping[str, Any]], observed: Mapping[str, Any]) -> bool:
    coverage = observed.get("coverage") or {}
    opaque = _unescaped_pages(observed)
    read_pages = coverage.get("read_pages")
    return any(anchor.get("location_kind") != "document" and
               (anchor.get("page") in opaque or
                (read_pages is not None and anchor.get("page") is not None
                 and anchor["page"] not in read_pages)) for anchor in support_set)


def check_recall_fact(fact: Mapping[str, Any], observed: Mapping[str, Any]) -> dict[str, Any]:
    target = fact.get("target_kind", REQUIRED_BUSINESS)
    dimension = "disposition_context" if target == DISPOSITION_CONTEXT else "critical_fact_recall"
    base = dict(expected="fact present with source-bound selected evidence", dimension=dimension)
    if target == CORRECTNESS_IF_EMITTED:
        return _check(f"recall.{fact['id']}", NOT_EVALUATED, observed="optional output",
                      detail="ordinary financial/context numbers are not mandatory business extraction", **base)
    if (observed.get("coverage") or {}).get("native_scan") == "unavailable":
        return _check(f"recall.{fact['id']}", UNAVAILABLE, observed="no native scan", **base)
    field = "context_evidence" if target == DISPOSITION_CONTEXT else "selected_evidence"
    if observed.get(field) is None:
        return _check(f"recall.{fact['id']}", NOT_EVALUATED, observed="no source-bound mapping",
                      detail=f"{field} absent; legacy flat text and claims are not source evidence", **base)
    outcomes = []
    for group in fact.get("any_support_sets") or []:
        if _group_unread(group, observed):
            outcomes.append(UNAVAILABLE)
            continue
        status, refs = _support_set_status(group, observed,
                                           require_same_scope=bool(fact.get("require_same_scope")),
                                           context=target == DISPOSITION_CONTEXT)
        if status == PASS:
            return _check(f"recall.{fact['id']}", PASS, observed="recalled", evidence_refs=refs, **base)
        outcomes.append(status)
    if FAIL in outcomes:
        status = FAIL if is_critical(fact) else PARTIAL
    elif NOT_EVALUATED in outcomes:
        status = NOT_EVALUATED
    else:
        status = UNAVAILABLE
    return _check(f"recall.{fact['id']}", status, observed="absent or unread",
                  detail=fact.get("reason") or "", **base)


# ---------------------------------------------------------------------------
# basis: role / modality / quantity / must_not_assert
# ---------------------------------------------------------------------------


def _distinctive_tokens(fact: Mapping[str, Any]) -> list[str]:
    """Tokens that identify the fact's subject independently of its anchor wording.

    A mutation that rewrites a claim destroys the anchor quote but usually keeps
    the subject word or the number. Without this, "总投资为28,000万元" rewritten
    as "项目收入28,000万元" would escape the basis check entirely.
    """

    tokens: list[str] = []
    for token in fact.get("must_preserve") or []:
        text = str(token).strip()
        if len(text) >= 2:
            tokens.append(text)
    for support_set in fact.get("any_support_sets") or []:
        for anchor in support_set:
            quote = anchor.get("exact_quote") or ""
            for chunk in re.split(r"[\s,，、。；;：:（）()\[\]《》\"']+", quote):
                chunk = chunk.strip()
                if len(chunk) >= 2 and not chunk.replace(".", "").isdigit():
                    tokens.append(chunk)
    # Preserve order, drop duplicates and pure numbers.
    seen: set[str] = set()
    ordered: list[str] = []
    for token in tokens:
        if token in seen:
            continue
        seen.add(token)
        ordered.append(token)
    return ordered


def _claim_relates_to_fact(fact: Mapping[str, Any], claim: Mapping[str, Any]) -> bool:
    """True when a claim is about this fact, even if its wording was rewritten."""

    text = claim.get("text") or ""
    if not text:
        return False
    quotes = [
        anchor.get("exact_quote") or ""
        for support_set in fact.get("any_support_sets") or []
        for anchor in support_set
    ]
    if any(anchor_matches(quote, text) for quote in quotes if quote):
        return True
    if _mentions_fact_number(fact, text):
        return True
    # Subject-word overlap: require a reasonably distinctive token so that a
    # generic word like "公司" cannot associate unrelated claims.
    for token in _distinctive_tokens(fact):
        if token.replace(".", "").replace(",", "").isdigit():
            continue
        if len(token) >= 3 and anchor_matches(token, text):
            return True
    return False


def _related_claims(fact: Mapping[str, Any], observed: Mapping[str, Any]) -> list[dict[str, Any]]:
    """All claims about this fact, whether or not the anchor wording survived.

    This supersedes anchor-only matching: a mutation that rewrites a claim
    destroys the anchor quote, and an anchor-only lookup would then miss the
    basis violation entirely.
    """

    return [claim for claim in _claims(observed) if _claim_relates_to_fact(fact, claim)]


def _modalities_conflict(gold_modality: str, declared: str) -> bool:
    """True when an observation's modality cannot describe the gold fact.

    Only hard contradictions count. ``plan`` and ``conditional`` are not
    treated as conflicting with each other, and ``third_party`` is a role
    concern handled separately.
    """

    incompatible = {
        "actual": {"plan", "negation"},
        "plan": {"actual", "negation"},
        "negation": {"actual", "plan"},
        "question": {"actual", "plan"},
        "conditional": {"actual"},
    }
    return declared in incompatible.get(gold_modality, set())


def _bases_conflict(fact_basis: str, declared_basis: str) -> bool:
    """True when an observation's declared basis cannot describe the gold fact.

    Only *known* incompatibilities count. Related-but-different bases (a
    ``total`` fact carried by a ``count`` claim) are left alone, because the
    oracle cannot prove those wrong.
    """

    incompatible = {
        "total": {"incremental", "period_flow", "capacity_new", "projected_output"},
        "incremental": {"total", "capacity_total"},
        "investment": {"period_flow", "projected_output"},
        "period_flow": {"total", "incremental", "investment"},
        "capacity_total": {"incremental", "capacity_new"},
        "capacity_new": {"total", "capacity_total"},
        "projected_output": {"total", "period_flow", "investment"},
    }
    return declared_basis in incompatible.get(fact_basis, set())


def _fact_is_negation(fact: Mapping[str, Any]) -> bool:
    for token in fact.get("must_preserve") or []:
        if has_negation(str(token)):
            return True
    for support_set in fact.get("any_support_sets") or []:
        for anchor in support_set:
            if has_negation(anchor.get("exact_quote") or ""):
                return True
    return False


def _fact_is_plan(fact: Mapping[str, Any]) -> bool:
    """A fact whose own wording is forward-looking.

    ``quantity_basis == "projected_output"`` is the gold's explicit marker for
    "this is a plan number", so a claim that states it as an accomplished fact
    is a basis violation.
    """

    if (fact.get("quantity_basis") or "") == "projected_output":
        return True
    for support_set in fact.get("any_support_sets") or []:
        for anchor in support_set:
            quote = anchor.get("exact_quote") or ""
            if has_plan_marker(quote) and not has_actual_marker(quote):
                return True
    return False


def _fact_is_question(fact: Mapping[str, Any]) -> bool:
    for support_set in fact.get("any_support_sets") or []:
        for anchor in support_set:
            if looks_like_question(anchor.get("exact_quote") or ""):
                return True
    return False


def _shares_fact_subject(fact: Mapping[str, Any], text: str) -> bool:
    """True when a claim is about the same subject as the fact.

    Subject sharing is derived from the fact's own preserved tokens, with the
    negation marker stripped so that "不生产VC" matches a claim about "VC".
    Word-boundary languages fall back to the distinctive ASCII token.
    """

    if not text:
        return False
    for token in fact.get("must_preserve") or []:
        stripped = str(token)
        for marker in ("不", "未", "没有", "无", "非", "尚未"):
            if stripped.startswith(marker) and len(stripped) > len(marker):
                stripped = stripped[len(marker) :]
                break
        stripped = stripped.strip()
        if not stripped:
            continue
        if len(stripped) >= 2 and anchor_matches(stripped, text):
            return True
        # Latin/technical subject terms survive translation-shaped rewording.
        for chunk in _SUBJECT_TOKEN_RE.findall(stripped):
            if len(chunk) >= 2 and anchor_matches(chunk, text):
                return True
    return False


_SUBJECT_TOKEN_RE = re.compile(r"[A-Za-z][A-Za-z0-9&\-]{1,}")
# Named actors that must survive: controllers, regulators, brands. Swapping one
# for another changes who did what, which is a factual error even when the
# predicate and the number survive unchanged.
_SUBJECT_PATTERNS: tuple[tuple[str, str], ...] = (
    ("中国节能", "中国节能"),
    ("控股股东", "控股股东"),
    ("宁德时代", "宁德时代"),
    ("九目化学", "九目化学"),
    ("中微公司", "中微公司"),
    ("恒锋工具", "恒锋工具"),
    ("名创优品", "名创优品"),
    ("TOP TOY", "TOP TOY"),
    ("MINISO", "MINISO"),
    ("Verisk", "Verisk"),
    ("TAL", "TAL"),
    ("Microsoft", "Microsoft"),
)


def _fact_subject(fact: Mapping[str, Any]) -> str | None:
    """The named actor a fact is about, when the gold names one explicitly."""

    corpus = " ".join(
        [str(token) for token in fact.get("must_preserve") or []]
        + [
            anchor.get("exact_quote") or ""
            for support_set in fact.get("any_support_sets") or []
            for anchor in support_set
        ]
    )
    lowered = corpus.casefold()
    for pattern, label in _SUBJECT_PATTERNS:
        if pattern.casefold() in lowered:
            return label
    return None


def _has_foreign_subject(text: str, subject: str) -> bool:
    """True when a claim swaps the fact's named subject for a different actor."""

    lowered = text.casefold()
    if subject.casefold() in lowered:
        return False
    for pattern, _label in _SUBJECT_PATTERNS:
        if pattern.casefold() == subject.casefold():
            continue
        if pattern.casefold() in lowered:
            return True
    return False


def _mentions_fact_number(fact: Mapping[str, Any], text: str) -> bool:
    """True when a claim repeats the fact's number even if it reworded the anchor."""

    for token in fact.get("must_preserve") or []:
        stripped = str(token).replace(",", "").strip()
        if stripped.replace(".", "").isdigit() and number_present(stripped, text):
            return True
    return False


def _token_preserved(token: str, haystack: str) -> bool:
    """A required token survives literally, or as the same number at any scale."""

    if anchor_matches(token, haystack):
        return True
    stripped = token.replace(",", "").strip()
    if stripped.replace(".", "").isdigit() and number_present(stripped, haystack):
        return True
    return False


def check_basis_fact(fact: Mapping[str, Any], observed: Mapping[str, Any]) -> dict[str, Any]:
    check_id = f"basis.{fact['id']}"
    recall = check_recall_fact(fact, observed)
    related = _related_claims(fact, observed)
    if fact.get("target_kind") == CORRECTNESS_IF_EMITTED and not related:
        return _check(check_id, NOT_EVALUATED, expected="correct if emitted", observed="not emitted",
                      dimension="role_modality_quantity", detail="optional fact was not output")
    if recall["status"] != PASS and not related:
        return _check(
            check_id,
            NOT_EVALUATED,
            expected="fact carried with correct role/modality/quantity basis",
            observed=recall["observed"],
            dimension="role_modality_quantity",
            detail="not recalled, so basis is not assessable",
        )

    problems: list[str] = []
    # Claims that are about this fact even when a mutation rewrote the anchor
    # wording (a question premise echoed as a company statement, or a total
    # restated as an increment). Basis violations live here, so they must not
    # be missed just because the anchor quote no longer matches.
    related = _related_claims(fact, observed)

    for claim in related:
        conflict = modality_conflicts(claim.get("modality") or "unknown", claim.get("text") or "")
        if conflict:
            problems.append(conflict)
        role = claim.get("role") or "unknown"
        declared = claim.get("modality") or "unknown"
        if role_is_third_party(role) and declared in {"actual", "plan"}:
            problems.append(f"third_party_role_asserted_as_company_fact:{role}")
        if declared == "question" and not looks_like_question(claim.get("text") or ""):
            problems.append("question_modality_without_question_form")

    # must_preserve tokens must survive somewhere in the replayable material.
    fact_rows = [row for row in _selected_source_rows(observed)
                 if any(_anchor_location_matches(anchor, row)
                        for group in fact.get("any_support_sets") or [] for anchor in group)]
    replayable = "\n".join(row.get("text") or "" for row in fact_rows)
    for token in fact.get("must_preserve") or []:
        if _token_preserved(token, replayable):
            continue
        problems.append(f"missing_required_token:{token}")

    # must_not_assert violations are searched across all claims, not only the
    # matching ones, because the typical hallucination is a *new* claim.
    all_text = "\n".join(claim.get("text") or "" for claim in _claims(observed))
    for forbidden in fact.get("must_not_assert") or []:
        for claim in _claims(observed):
            if _token_preserved(forbidden, claim.get("text") or ""):
                problems.append(f"must_not_assert_violated:{forbidden}")
                break
        else:
            if anchor_matches(forbidden, all_text):
                problems.append(f"must_not_assert_violated:{forbidden}")

    # Paraphrases a literal token cannot catch: the same number restated under
    # a different quantity basis (total -> net addition, investment -> revenue).
    basis = fact.get("quantity_basis") or "unknown"
    if basis != "unknown":
        for claim in related:
            contradiction = basis_contradiction(basis, claim.get("text") or "")
            if contradiction:
                problems.append(f"basis_contradiction:{contradiction}")
            # The observation's own declared basis must agree with the gold's.
            # A claim that declares `incremental` while carrying a `total` fact
            # contradicts itself even when its wording still says "总数".
            for quantity in claim.get("quantities") or []:
                declared_basis = quantity.get("basis") or "unknown"
                if declared_basis == "unknown":
                    continue
                if _bases_conflict(basis, declared_basis):
                    problems.append(f"declared_basis_conflicts:{declared_basis}")

    # Modality-vs-modality: a fact that is a plan must not be restated as a
    # completed action by any related claim.
    if _fact_is_plan(fact):
        for claim in related:
            if (claim.get("modality") or "unknown") == "actual" and has_actual_marker(
                claim.get("text") or ""
            ):
                problems.append("plan_restated_as_actual")
            elif (claim.get("modality") or "unknown") == "actual" and not has_plan_marker(
                claim.get("text") or ""
            ):
                problems.append("plan_modality_dropped")

    # Product/project lifecycle: a claim must not assert a later stage than
    # its own evidence ('量产验证阶段' restated as '已量产').
    for claim in related:
        for support_set in fact.get("any_support_sets") or []:
            for anchor in support_set:
                regression = stage_regression(
                    anchor.get("exact_quote") or "", claim.get("text") or ""
                )
                if regression:
                    problems.append(regression)
                    break

    # Subject fidelity: a fact whose subject is a named party must not be
    # restated with a different subject. Attributing a controller's or an
    # affiliate's action to the listed company (or deleting the actor) changes
    # who did what, which is a factual error even when the predicate survives.
    subject = _fact_subject(fact)
    if subject:
        for claim in related:
            text = claim.get("text") or ""
            if _has_foreign_subject(text, subject):
                problems.append(f"subject_rewritten:{subject}")

    # A question is not a company statement: a fact whose only support is a
    # question must not be carried by a company-role affirmative claim.
    if _fact_is_question(fact):
        for claim in related:
            role = claim.get("role") or "unknown"
            declared = claim.get("modality") or "unknown"
            if declared in {"actual", "plan"} and role in {
                "company_filing",
                "company_statement",
                "management_answer",
                "management_prepared",
            }:
                problems.append(f"question_carried_as_company_fact:{role}")

    # Quantity basis: a declared quantity whose basis contradicts the fact.
    for claim in related:
        for quantity in claim.get("quantities") or []:
            basis = quantity.get("basis") or "unknown"
            if basis == "unknown":
                continue
            if basis in {"period_flow", "incremental"} and fact.get("id") == "f-project-capex":
                problems.append(f"quantity_basis_mismatch:{basis}")
    # Modality must agree with what the gold says the fact *is*. This is the
    # authoritative check: a plan restated as actual, or a negation restated as
    # positive, is a basis violation regardless of the claim's wording.
    gold_modality = fact.get("modality") or "unknown"
    if gold_modality != "unknown":
        for claim in related:
            declared = claim.get("modality") or "unknown"
            if declared == "unknown":
                continue
            if _modalities_conflict(gold_modality, declared):
                problems.append(f"modality_conflicts:{gold_modality}->{declared}")

    # A number asserted inside a matching claim must appear in the replayable
    # evidence *with the same unit basis*; otherwise the number was restated
    # (万元 -> 元, 万 -> 亿) or invented outright.
    for claim in related:
        for quantity in claim.get("quantities") or []:
            value = quantity.get("value")
            if value is None:
                continue
            if not number_present(value, replayable):
                problems.append(f"quantity_not_in_evidence:{value}")
            elif not unit_matches_evidence(value, quantity.get("unit"), replayable):
                problems.append(f"quantity_unit_mismatch:{value}:{quantity.get('unit')}")

    # A gold fact whose truth is a negation must not be contradicted by an
    # affirmative claim, whoever the speaker is. A question premise or an
    # analyst assertion restated as fact is exactly this failure.
    if _fact_is_negation(fact):
        for claim in _claims(observed):
            text = claim.get("text") or ""
            if not _shares_fact_subject(fact, text):
                continue
            if has_negation(text):
                continue
            declared = claim.get("modality") or "unknown"
            role = claim.get("role") or "unknown"
            if declared in {"actual", "plan"} or role_is_third_party(role):
                problems.append(f"negation_contradicted:{role}:{declared}")
            elif declared == "question" and _shares_fact_subject(fact, text):
                problems.append(f"question_premise_carried_as_claim:{role}")

    status = FAIL if problems else PASS if fact_rows else NOT_EVALUATED
    return _check(
        check_id,
        status,
        expected="role/modality/quantity basis preserved",
        observed=sorted(set(problems)),
        dimension="role_modality_quantity",
        detail="" if not problems else "; ".join(sorted(set(problems))),
    )


# ---------------------------------------------------------------------------
# context completeness
# ---------------------------------------------------------------------------


def check_context(observed: Mapping[str, Any], gold: Mapping[str, Any]) -> dict[str, Any]:
    """Semantic units must carry their members and required context together."""

    units = list(observed.get("semantic_units") or [])
    if not units:
        return _check(
            "context.semantic_units",
            NOT_EVALUATED,
            expected="semantic units with complete member sets",
            observed=None,
            dimension="context_completeness",
            detail="baseline has no new structure; context completeness unmeasurable",
        )
    selected = _selected_locator_set(observed)
    bound = {row["locator"] for row in _selected_source_rows(observed)}
    incomplete = [unit.get("semantic_id") for unit in units
                  if unit.get("completeness") not in {None, "unknown", "complete"}]
    missing: dict[str, list[str]] = {}
    unknown = []
    for unit in units:
        required = unit.get("required_locators")
        members = set(unit.get("locators") or [])
        if not members:
            missing[unit["semantic_id"]] = ["semantic unit has no original members"]
        if not members.issubset(selected):
            missing[unit["semantic_id"]] = sorted(members - selected)
        if required is None or unit.get("dependencies_resolved") is not True:
            unknown.append(unit["semantic_id"])
            continue
        required_set = members | set(required)
        absent = required_set - (selected & bound)
        if absent:
            missing[unit["semantic_id"]] = sorted(absent)
    status = FAIL if incomplete or missing else NOT_EVALUATED if unknown else PASS
    return _check("context.semantic_units", status,
                  expected="all members and resolved required context have selected source text",
                  observed={"incomplete_units": incomplete, "missing_context": missing,
                            "dependency_observation_missing": unknown},
                  dimension="context_completeness")


# ---------------------------------------------------------------------------
# bilingual redundancy
# ---------------------------------------------------------------------------


def _language_of(claim: Mapping[str, Any]) -> str | None:
    value = claim.get("language")
    return value if isinstance(value, str) and value else None


def check_bilingual(observed: Mapping[str, Any], gold: Mapping[str, Any]) -> dict[str, Any]:
    """The same fact must not be summarised twice in two languages."""

    claims = _claims(observed)
    languages = {_language_of(claim) for claim in claims} - {None}
    if len(languages) < 2:
        return _check(
            "bilingual.duplicate_summary",
            PASS,
            expected="no duplicated fact across languages",
            observed=sorted(languages),
            dimension="bilingual_redundancy",
            detail="single language lane in observation",
        )
    duplicates: list[dict[str, Any]] = []
    for index, claim in enumerate(claims):
        text = claim.get("text") or ""
        if not text:
            continue
        locators = set(claim.get("evidence_locators") or [])
        for other_index in range(index + 1, len(claims)):
            other = claims[other_index]
            if _language_of(claim) == _language_of(other):
                continue
            other_text = other.get("text") or ""
            if not other_text:
                continue
            other_locators = set(other.get("evidence_locators") or [])
            if not other_locators:
                continue
            # The same fact summarised in two languages shows up as an
            # identical numeric/identifier payload carried by the same
            # evidence, or as the two claims sharing their *entire* evidence
            # set. Sharing one locator out of several is normal
            # cross-referencing, not duplication.
            shared = _shared_payloads(text, other_text)
            same_evidence = locators == other_locators
            if (shared and locators.intersection(other_locators)) or same_evidence:
                duplicates.append(
                    {
                        "first": index,
                        "second": other_index,
                        "shared_payloads": sorted(shared),
                        "shared_locators": sorted(locators.intersection(other_locators)),
                    }
                )
    return _check(
        "bilingual.duplicate_summary",
        FAIL if duplicates else PASS,
        expected="each fact summarised once across language lanes",
        observed=duplicates,
        dimension="bilingual_redundancy",
    )


def _shared_payloads(left: str, right: str) -> set[str]:
    from .textutil import quantities_from_scales

    left_numbers = {f"{value:g}" for value, _unit in quantities_from_scales(left)}
    right_numbers = {f"{value:g}" for value, _unit in quantities_from_scales(right)}
    shared = left_numbers.intersection(right_numbers) - {"", "0"}
    # A bare 1/2/3 shared between languages is noise; require >= 3 digits.
    return {value for value in shared if len(value.replace(".", "")) >= 3}


# ---------------------------------------------------------------------------
# derived space / resources
# ---------------------------------------------------------------------------

DEFAULT_LIMITS: dict[str, Any] = {
    "max_derived_bytes": 200 * 1024,
    "max_gold_quote_bytes_per_document": 8 * 1024,
    "max_elapsed_seconds": 900.0,
}


def check_derived_space(
    observed: Mapping[str, Any], gold: Mapping[str, Any], limits: Mapping[str, Any]
) -> dict[str, Any]:
    metrics = observed.get("metrics") or {}
    limit = int(limits.get("max_derived_bytes", DEFAULT_LIMITS["max_derived_bytes"]))
    derived = metrics.get("derived_bytes")
    if derived is None:
        return _check(
            "derived_space.budget",
            NOT_EVALUATED,
            expected=f"derived_bytes <= {limit}",
            observed=None,
            dimension="derived_space",
            detail="observation reports no derived size",
        )
    status = PASS if int(derived) <= limit else FAIL
    return _check(
        "derived_space.budget",
        status,
        expected=f"derived_bytes <= {limit}",
        observed=int(derived),
        dimension="derived_space",
    )


def check_resource(
    observed: Mapping[str, Any], gold: Mapping[str, Any], limits: Mapping[str, Any]
) -> dict[str, Any]:
    execution = observed.get("execution") or {}
    limit = float(limits.get("max_elapsed_seconds", DEFAULT_LIMITS["max_elapsed_seconds"]))
    elapsed = execution.get("elapsed_seconds")
    if elapsed is None:
        return _check(
            "resource.elapsed",
            NOT_EVALUATED,
            expected=f"elapsed_seconds <= {limit}",
            observed=None,
            dimension="time_resource",
            detail="observation reports no elapsed time",
        )
    status = PASS if float(elapsed) <= limit else FAIL
    return _check(
        "resource.elapsed",
        status,
        expected=f"elapsed_seconds <= {limit}",
        observed=float(elapsed),
        dimension="time_resource",
        detail="elapsed is reported, not a throughput claim",
    )


# ---------------------------------------------------------------------------
# semantics (never auto-PASS)
# ---------------------------------------------------------------------------


def check_coverage_honesty(
    observed: Mapping[str, Any], gold: Mapping[str, Any]
) -> dict[str, Any]:
    """`coverage.complete` must not be asserted over pages that were not read.

    Claiming structural completeness while pages are opaque/deferred is a
    false-completeness defect: it makes the run look finished and hides the
    gap. This is distinct from recall, which is simply unprovable for those
    pages.
    """

    coverage = observed.get("coverage") or {}
    complete = coverage.get("complete")
    if complete is None:
        return _check(
            "coverage.no_false_complete",
            NOT_EVALUATED,
            expected="coverage.complete consistent with opaque/deferred pages",
            observed=None,
            dimension="context_completeness",
            detail="observation reports no structural completeness flag",
        )
    opaque = list(coverage.get("opaque_pages") or [])
    deferred = list(coverage.get("deferred_unit_ids") or [])
    unassigned = list(coverage.get("unassigned_unit_ids") or [])
    native_scan = coverage.get("native_scan")
    false_complete = bool(complete) and bool(opaque or deferred)
    if bool(complete) and native_scan == "partial" and not opaque and not deferred:
        # A partial native scan with no named gap cannot justify "complete".
        false_complete = True
    return _check(
        "coverage.no_false_complete",
        FAIL if false_complete else PASS,
        expected="complete only when no page/unit is unread",
        observed={
            "complete": complete,
            "native_scan": native_scan,
            "opaque_pages": opaque,
            "deferred_unit_ids": deferred,
            "unassigned_unit_ids": unassigned,
        },
        dimension="context_completeness",
    )


def check_quantity_provenance(
    observed: Mapping[str, Any], gold: Mapping[str, Any]
) -> dict[str, Any]:
    """Every claimed quantity must carry its period and unit basis.

    A number stripped of the column it came from (period, unit) cannot be
    checked against the original and is not replayable evidence, so dropping
    the table header is a real defect rather than a stylistic one.
    """

    stripped: list[dict[str, Any]] = []
    total = 0
    for index, claim in enumerate(_claims(observed)):
        for quantity in claim.get("quantities") or []:
            if quantity.get("value") is None:
                continue
            total += 1
            basis = quantity.get("basis") or "unknown"
            # A ratio/count needs no unit; everything else does.
            needs_unit = basis not in {"ratio", "count", "unknown"}
            if needs_unit and not (quantity.get("unit") or quantity.get("currency")):
                stripped.append({"claim_index": index, "value": quantity.get("value"), "missing": "unit"})
            if needs_unit and not quantity.get("period"):
                stripped.append({"claim_index": index, "value": quantity.get("value"), "missing": "period"})
    if total == 0:
        return _check(
            "basis.quantity_provenance",
            NOT_EVALUATED,
            expected="each quantity carries unit and period",
            observed=None,
            dimension="role_modality_quantity",
            detail="observation reports no quantities",
        )
    return _check(
        "basis.quantity_provenance",
        FAIL if stripped else PASS,
        expected="each quantity carries unit and period",
        observed=stripped,
        dimension="role_modality_quantity",
    )


def check_text_legibility(
    observed: Mapping[str, Any], gold: Mapping[str, Any]
) -> dict[str, Any]:
    """Is the text actually readable, or is it a broken font mapping?

    A PDF whose text layer uses an unmapped CID font yields characters that are
    not the document's content. The parser reports no error for this: it emits
    units and the selector picks spans, so a 100%-garbled document can look like
    a clean parse. Measured on a real one: 415 pages, 0 pages of readable
    Chinese, yet 9,618 units, zero quality flags and zero errors, and the
    selector picked plain mojibake as narrative evidence.

    The signal is the share of characters in blocks that legitimate prose never
    uses (CJK radicals, Kangxi radicals, CJK strokes, control pictures, private
    use, hexagrams, box drawing). Thresholds come from the measured control
    documented at ``UNUSABLE_BLOCKS``.

    Reports ``NOT_EVALUATED`` unless the gold declares a language and there is
    enough text to judge, because a short or numeric-only selection is not
    evidence of a broken text layer.
    """

    language = (gold.get("language") or "").casefold()
    if not language:
        return _check(
            "integrity.text_legibility",
            NOT_EVALUATED,
            expected="text is readable rather than a broken font mapping",
            observed=None,
            dimension="observation_integrity",
            detail="gold declares no language, so legibility is not judged",
        )

    # Prefer the observer's measurement over everything it parsed. Judging only
    # the selection is not enough: a garbled document can have hundreds of
    # thousands of unusable characters while the selector retains a couple of
    # hundred, and the threshold would never fire.
    metrics = observed.get("metrics") or {}
    full_ratio = metrics.get("unusable_block_ratio")
    if isinstance(full_ratio, (int, float)):
        dense_chars = metrics.get("read_text_dense_chars") or 0
        if dense_chars < MIN_LEGIBILITY_CHARS:
            return _check(
                "integrity.text_legibility",
                NOT_EVALUATED,
                expected=f"unusable-block ratio < {MAX_UNUSABLE_BLOCK_RATIO}",
                observed={"dense_chars": dense_chars, "basis": "parsed_text"},
                dimension="observation_integrity",
                detail=f"fewer than {MIN_LEGIBILITY_CHARS} parsed characters to judge",
            )
        status = FAIL if float(full_ratio) >= MAX_UNUSABLE_BLOCK_RATIO else PASS
        return _check(
            "integrity.text_legibility",
            status,
            expected=f"unusable-block ratio < {MAX_UNUSABLE_BLOCK_RATIO}",
            observed={
                "unusable_block_ratio": round(float(full_ratio), 5),
                "dense_chars": dense_chars,
                "basis": "parsed_text",
            },
            dimension="observation_integrity",
            detail=(
                ""
                if status == PASS
                else "the parsed text is dominated by characters from blocks legitimate "
                "prose never uses, so the text layer is a broken font mapping; any fact "
                "read from it would be fabricated"
            ),
        )

    text = observed.get("selected_text") or ""
    dense = [char for char in text if not char.isspace()]
    if len(dense) < MIN_LEGIBILITY_CHARS:
        return _check(
            "integrity.text_legibility",
            NOT_EVALUATED,
            expected=f"unusable-block ratio < {MAX_UNUSABLE_BLOCK_RATIO}",
            observed={"dense_chars": len(dense), "basis": "selected_text"},
            dimension="observation_integrity",
            detail=(
                f"fewer than {MIN_LEGIBILITY_CHARS} non-space selected characters to "
                "judge, and the observation reports no parsed-text measurement"
            ),
        )

    unusable = sum(1 for char in dense if _in_unusable_block(char))
    ratio = unusable / len(dense)
    status = FAIL if ratio >= MAX_UNUSABLE_BLOCK_RATIO else PASS
    return _check(
        "integrity.text_legibility",
        status,
        expected=f"unusable-block ratio < {MAX_UNUSABLE_BLOCK_RATIO}",
        observed={
            "unusable_block_ratio": round(ratio, 5),
            "unusable_chars": unusable,
            "dense_chars": len(dense),
            "basis": "selected_text",
        },
        dimension="observation_integrity",
        detail=(
            ""
            if status == PASS
            else "selected text contains characters from blocks legitimate prose never "
            "uses, so the text layer is probably a broken font mapping; any fact read "
            "from it would be fabricated"
        ),
    )


def check_semantics_entailment(
    observed: Mapping[str, Any], gold: Mapping[str, Any], review: Mapping[str, Any] | None
) -> dict[str, Any]:
    """Entailment requires independent review. Regex/numeric agreement is not it.

    Three outcomes are kept distinct:

    - no review at all -> ``NOT_EVALUATED`` (the honest default);
    - a review whose verdicts are all entailed -> ``PASS``;
    - a review that found an unsupported claim -> ``FAIL``;
    - a review that could not decide every claim -> ``PARTIAL``, because "the
      reviewer was unsure" is not the same as "the claim is wrong".
    """

    if not review:
        return _check(
            "semantics.entailment",
            NOT_EVALUATED,
            expected="independent semantic review of each claim against its evidence",
            observed=None,
            dimension="untested_semantics",
            detail="no independent review supplied; deterministic checks cannot prove entailment",
        )

    from .review import ENTAILED_VERDICTS, UNDECIDED_VERDICTS, UNSUPPORTED_VERDICTS

    reviewed = list(review.get("claims") or [])
    indices = [row.get("claim_index") for row in reviewed]
    expected_indices = set(range(len(_claims(observed))))
    valid_indices = [index for index in indices if type(index) is int and index in expected_indices]
    missing_review = sorted(expected_indices - set(valid_indices))
    invalid_indices = [index for index in indices if type(index) is not int or index not in expected_indices]
    duplicates = sorted({index for index in valid_indices if valid_indices.count(index) > 1})
    wrong_sample = review.get("sample_id") not in (None, gold.get("sample_id"))
    unsupported = [row for row in reviewed if row["verdict"] in UNSUPPORTED_VERDICTS]
    undecided = [row for row in reviewed if row["verdict"] in UNDECIDED_VERDICTS]
    unknown = [
        row
        for row in reviewed
        if row["verdict"] not in ENTAILED_VERDICTS
        and row["verdict"] not in UNSUPPORTED_VERDICTS
        and row["verdict"] not in UNDECIDED_VERDICTS
    ]

    if wrong_sample:
        status = PARTIAL
    elif unsupported:
        status = FAIL
    elif undecided or unknown or missing_review or invalid_indices or duplicates:
        status = PARTIAL
    else:
        status = PASS

    return _check(
        "semantics.entailment",
        status,
        expected="every reviewed claim entailed by its evidence",
        observed={
            "reviewed": len(reviewed),
            "unsupported": unsupported,
            "undecided": undecided,
            "unrecognized_verdicts": unknown,
            "missing_claim_reviews": missing_review,
            "invalid_claim_indices": invalid_indices,
            "duplicate_claim_indices": duplicates,
            "wrong_sample": wrong_sample,
        },
        evidence_refs=[
            locator
            for row in unsupported
            for locator in (row.get("evidence_locators") or [])
        ],
        dimension="untested_semantics",
    )


def spot_read_list(observed: Mapping[str, Any], gold: Mapping[str, Any]) -> list[dict[str, Any]]:
    """Rows handed to ROOT for the independent large-node semantic review."""

    facts = {fact["id"]: fact for fact in gold.get("facts") or []}
    rows: list[dict[str, Any]] = []
    for claim in _claims(observed):
        text = claim.get("text") or ""
        matched = [
            fact_id
            for fact_id, fact in facts.items()
            if any(
                anchor_matches(anchor.get("exact_quote") or "", text)
                for support_set in fact.get("any_support_sets") or []
                for anchor in support_set
            )
        ]
        rows.append(
            {
                "claim_text": text,
                "role": claim.get("role"),
                "modality": claim.get("modality"),
                "evidence_locators": list(claim.get("evidence_locators") or []),
                "gold_fact_ids": matched,
                "review_question": "does the evidence entail the claim text as written?",
            }
        )
    return rows


def collect_recall_facts(gold: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    return [fact for fact in gold.get("facts") or []
            if fact.get("target_kind", REQUIRED_BUSINESS) == REQUIRED_BUSINESS]


def is_critical(fact: Mapping[str, Any]) -> bool:
    return (fact.get("importance") or CRITICAL) == CRITICAL


def summarize_dimensions(checks: Iterable[Mapping[str, Any]]) -> dict[str, Any]:
    by_dimension: dict[str, list[str]] = {}
    for row in checks:
        by_dimension.setdefault(row.get("dimension") or "other", []).append(row["status"])
    return {
        dimension: {
            "checks": len(statuses),
            "pass": statuses.count(PASS),
            "fail": statuses.count(FAIL),
            "partial": statuses.count(PARTIAL),
            "unavailable": statuses.count(UNAVAILABLE),
            "not_evaluated": statuses.count(NOT_EVALUATED),
        }
        for dimension, statuses in sorted(by_dimension.items())
    }
