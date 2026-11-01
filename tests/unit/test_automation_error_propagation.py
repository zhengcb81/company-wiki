"""Structured automation failures must obey Python's exception protocol."""
from contextlib import contextmanager

import pytest

from company_wiki.automation.models import HandlerMetrics, HandlerOutcome
from company_wiki.automation.narrative_model_caller import NarrativeBudgetCallError
from company_wiki.automation.narrative_select import _SelectFailure
from company_wiki.automation.narrative_summarize import _SummaryFailure
from company_wiki.automation.narrative_verify import _VerifyFailure


@pytest.mark.parametrize("kind", [NarrativeBudgetCallError, _SelectFailure, _SummaryFailure, _VerifyFailure])
def test_structured_failure_survives_context_cleanup_with_original_identity(kind):
    if kind is NarrativeBudgetCallError:
        error = kind("SYNTHETIC_FAILURE", HandlerOutcome.RETRYABLE, HandlerMetrics(0, 0.0, 0))
    else:
        error = kind("SYNTHETIC_FAILURE", HandlerOutcome.RETRYABLE, "synthetic detail")
    original_cause = OSError("synthetic storage fault")
    cleaned = []

    @contextmanager
    def resource_scope():
        try:
            yield
        finally:
            cleaned.append(True)

    with pytest.raises(kind) as caught:
        with resource_scope():
            raise error from original_cause
    assert caught.value is error
    assert caught.value.__cause__ is original_cause
    assert caught.value.code == "SYNTHETIC_FAILURE"
    assert caught.value.outcome is HandlerOutcome.RETRYABLE
    assert caught.value.__traceback__ is not None
    assert cleaned == [True]
