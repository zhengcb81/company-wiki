"""Model usage is optional, paired, typed and independent of output decoding."""

import pytest

from company_wiki.automation.narrative_model import (
    ModelResponseError,
    NarrativeModelResponse,
)


def test_replay_four_positional_fields_remain_compatible():
    response = NarrativeModelResponse("replay", "fixture", "1.0", b"{}")
    assert (response.input_tokens, response.output_tokens, response.duration_ms) == (None, None, 0)


def test_usage_can_be_zero_and_survives_invalid_draft_json():
    response = NarrativeModelResponse(
        "http", "real-model", "1.0", b"invalid-json", 100, 0, 25,
    )
    assert response.input_tokens == 100
    assert response.output_tokens == 0
    assert response.duration_ms == 25


@pytest.mark.parametrize("tokens", [(-1, 1), (1, -1), (True, 1), (1, False), (1.5, 1), (1, "2"), (None, 1), (1, None)])
def test_invalid_or_partial_usage_is_rejected(tokens):
    with pytest.raises(ModelResponseError, match="usage"):
        NarrativeModelResponse("http", "model", "1.0", b"{}", *tokens)


@pytest.mark.parametrize("duration", [-1, True, 1.5, "2", None])
def test_duration_must_be_nonnegative_integer(duration):
    with pytest.raises(ModelResponseError, match="duration"):
        NarrativeModelResponse("http", "model", "1.0", b"{}", duration_ms=duration)
