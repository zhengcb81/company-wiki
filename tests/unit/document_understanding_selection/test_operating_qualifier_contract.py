"""Public operating-state qualifier signals used by dependent layers."""

import pytest

from company_wiki.document_understanding.operating_states import (
    OperatingQualifiers,
    classify_qualifiers,
)


def test_qualifier_contract_returns_immutable_signals_without_exposing_patterns():
    result = classify_qualifiers(
        "The company plans expansion if the permit is approved, but does not operate the site."
    )

    assert result == OperatingQualifiers(planned=True, negated=True, conditional=True)
    with pytest.raises((AttributeError, TypeError)):
        result.planned = False


def test_qualifier_contract_is_neutral_when_no_qualifier_is_present():
    assert classify_qualifiers("The company operates a manufacturing site.") == OperatingQualifiers(
        planned=False, negated=False, conditional=False
    )


def test_qualifier_contract_rejects_non_text_input():
    with pytest.raises(TypeError, match="text"):
        classify_qualifiers(None)
