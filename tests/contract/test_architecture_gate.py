"""CW-3 contract tests for the architecture gate."""


def test_source_catalog_does_not_import_prohibited_modules():
    from company_wiki.source_catalog.architecture_gate import (
        source_catalog_does_not_import_prohibited_modules,
    )

    ok, violations = source_catalog_does_not_import_prohibited_modules()
    assert ok, f"prohibited imports found: {violations}"


def test_rejected_stages_covers_all_investment_stages():
    from company_wiki.source_catalog.architecture_gate import (
        rejected_stages_covers_all_investment_stages,
    )

    ok, missing = rejected_stages_covers_all_investment_stages()
    assert ok, f"missing rejected stages: {missing}"


def test_scheduler_policy_blocks_valuation_and_research():
    from company_wiki.source_catalog.scheduler_policy import _FORBIDDEN_DISPATCH_TOKENS

    required = {
        "valuation",
        "research",
        "rating",
        "sell",
        "sotp",
        "stockwiki",
        "target_price",
        "wiki_writer",
    }
    assert required <= set(_FORBIDDEN_DISPATCH_TOKENS), (
        f"missing: {required - set(_FORBIDDEN_DISPATCH_TOKENS)}"
    )
