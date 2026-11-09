"""Public DU discourse observations keep regex implementation private."""

from dataclasses import FrozenInstanceError

import pytest

from company_wiki.document_understanding import (
    SourceDiscourseObservation,
    observe_source_discourse,
)


def test_courtesy_phrase_is_reported_as_a_bounded_observation():
    assert observe_source_discourse("Thank you for your attention.") == (
        SourceDiscourseObservation(courtesy_start=0, courtesy_only=True)
    )


def test_courtesy_prefix_does_not_hide_following_business_text():
    result = observe_source_discourse(
        "Thank you for your attention. We aim to grow."
    )
    assert result == SourceDiscourseObservation(courtesy_start=0, courtesy_only=False)


def test_non_courtesy_text_has_no_observed_marker():
    assert observe_source_discourse("The company operates a manufacturing site.") == (
        SourceDiscourseObservation(courtesy_start=None, courtesy_only=False)
    )


def test_observation_is_immutable_and_input_is_typed():
    result = observe_source_discourse("谢谢。")
    with pytest.raises(FrozenInstanceError):
        result.courtesy_only = False
    with pytest.raises(TypeError, match="text must be a string"):
        observe_source_discourse(None)
