"""FC-906-b RED/GREEN: role-applicability contract (markdown / consumer_analysis).

FC-906-a proved the 3 registered producers now emit v2-bindable artifacts.
This contract pins the other half of the FC-906 role matrix: the catalog side
has NO producer for ``markdown`` (redundant with ``normalized``, which is
already text/markdown) and ``consumer_analysis`` (consumer-side provenance
contract per E2E-D06) — both documented in
``assurance/fc/FC-906/03_change_contract_fc906b.md`` and never written by
catalog producers.  The role contract document itself is the RED target
(missing -> test fails), then the guard pins the invariant forever.
"""

from __future__ import annotations

from pathlib import Path

from company_wiki.source_catalog.source_bundle import GENERATOR_REGISTRY

PRODUCER_ROLE_VALUES = {
    "normalized": "source_catalog_normalizer",
    "summary": "source_catalog_llm_summary",
    "sections": "source_catalog_section_extractor",
}

# Roles that MUST never gain a catalog producer while this contract holds.
NON_CATALOG_ROLES = ("markdown", "consumer_analysis")

# Roles declared in the frozen ROLE_DEPENDENCIES contract.
KNOWN_ROLES = {"normalized", "markdown", "summary", "sections",
               "consumer_analysis"}

CONTRACT_REL = "assurance/fc/FC-906/03_change_contract_fc906b.md"
CONTRACT_TOP = "FC-906-b Change Contract"
CONTRACT_FIELDS = ("角色", "裁决", "consumer 归属")


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def test_catalog_producers_write_only_registered_roles():
    """Guard: the 3 catalog producers write exactly normalized/summary/sections.

    This pins the invariant that no catalog producer path exists for
    ``markdown`` or ``consumer_analysis``.  If someone adds such a producer,
    they must (a) register its generator in GENERATOR_REGISTRY AND (b) amend
    this test + the role contract — never silently.
    """
    # Registry is the single source of truth for producers (FC-902).
    assert set(GENERATOR_REGISTRY) == set(PRODUCER_ROLE_VALUES.values()), (
        "GENERATOR_REGISTRY drift: registered generators no longer match the "
        f"known producer set {sorted(PRODUCER_ROLE_VALUES.values())}"
    )
    # The registry contains no generator for the non-catalog roles — binding
    # gate (validate_artifact) would fail them closed anyway.
    for role in NON_CATALOG_ROLES:
        assert not any(role in name for name in GENERATOR_REGISTRY), (
            f"catalog producer for non-catalog role {role!r} must not exist"
        )
    # Producer INSERT role values (source of truth in the producer modules) are
    # exactly the three registered roles.
    producer_modules = {
        "normalizer.py": ("normalized", "source_catalog_normalizer"),
        "llm_summarizer.py": ("summary", "source_catalog_llm_summary"),
        "section_extractor.py": ("sections", "source_catalog_section_extractor"),
    }
    src = _repo_root() / "src" / "company_wiki" / "source_catalog"
    for module, (role, generator) in producer_modules.items():
        text = (src / module).read_text(encoding="utf-8")
        # The role appears as a literal in INSERT position or in the role
        # constant (section_extractor uses SECTION_ARTIFACT_ROLE = "sections").
        assert f'"{role}"' in text, f"{module} must declare role {role!r}"
        assert generator in text, f"{module} must declare generator {generator!r}"
        for banned in NON_CATALOG_ROLES:
            # A role literal in INSERT/artifact-role position is the smoking
            # gun of an unregistered write path.  We match the artifact_role
            # parameter shape (`"role",` in the INSERT tuple or
            # `"artifact_role": "role"`), NOT any incidental word — e.g.
            # mime_type "text/markdown" or a docstring mention must not trip.
            assert f'"{banned}",' not in text and (
                f'"artifact_role": "{banned}"' not in text
            ), f"{module} writes non-catalog role {banned!r}"


def test_role_contract_document_is_valid():
    """RED target (FC-906-b): the role-applicability contract exists & is valid.

    Documents the applicability ruling for markdown / consumer_analysis, so a
    future reader can distinguish 'deliberately not produced' from 'missing'.
    """
    contract = _repo_root() / CONTRACT_REL
    assert contract.is_file(), f"role contract missing: {CONTRACT_REL}"
    text = contract.read_text(encoding="utf-8")
    assert CONTRACT_TOP in text
    # Every non-catalog role must have a RULING — a section heading carrying
    # the applicability verdict ("不适用") and a consumer attribution — not
    # merely a mention of the role name (a role name in §1 body text would
    # pass a weak check while its ruling was deleted — M2 proved this).
    for role in NON_CATALOG_ROLES:
        assert f"`{role}` 角色 — 不适用" in text, (
            f"contract must carry an applicability ruling for {role!r} "
            "(`<role>` 角色 — 不适用)"
        )
        assert "consumer" in text.lower() or "Consumer" in text, (
            f"contract must attribute a consumer for {role!r}"
        )
    for field in CONTRACT_FIELDS:
        assert field in text, f"contract must carry field {field!r}"
    # The contract must name both the binding-gate consequence and the
    # GENERATOR_REGISTRY consequence (fail-closed story, not silent absence).
    assert "GENERATOR_REGISTRY" in text
    assert "artifact_generator_unregistered" in text
    assert "E2E-D06" in text or "consumer" in text.lower()


def test_role_matrix_is_complete():
    """The frozen role set and the non-catalog exclusion are consistent."""
    assert set(PRODUCER_ROLE_VALUES) | set(NON_CATALOG_ROLES) == KNOWN_ROLES, (
        "role matrix drift: producer roles + non-catalog roles must cover the "
        f"frozen DAG roles {sorted(KNOWN_ROLES)}"
    )
    assert KNOWN_ROLES == {
        "normalized", "markdown", "summary", "sections", "consumer_analysis"
    }
