"""Current golden evolution preserves every source fact and verifies both parser eras."""
from copy import deepcopy
import json
from pathlib import Path

import pytest

from support.narrative_golden_evolution import (
    assert_reviewed_transcript_evolution,
    assert_reviewed_transcript_evolution_v2_to_v3,
)


ROOT = Path(__file__).resolve().parents[1] / "fixtures/narrative_transport_v1"


def _snapshots():
    return (json.loads((ROOT / "bundle.json").read_bytes()),
            json.loads((ROOT / "current-v2/bundle.json").read_bytes()))


def _current_snapshots():
    return (json.loads((ROOT / "current-v2/bundle.json").read_bytes()),
            json.loads((ROOT / "current-v3/bundle.json").read_bytes()))


def test_reviewed_current_generation_retains_exact_historical_source_facts_and_replays():
    assert_reviewed_transcript_evolution(*_snapshots())


def test_reviewed_v3_generation_adds_only_operating_tags_and_replays_both_parser_eras():
    assert_reviewed_transcript_evolution_v2_to_v3(*_current_snapshots())


@pytest.mark.parametrize("change", ["claim", "unit", "citation"])
def test_evolution_review_rejects_invented_fact_unit_or_unsupported_citation(change):
    old, current = _snapshots()
    damaged = deepcopy(current)
    claim = damaged["summary"]["draft"]["claims"][0]
    if change == "claim":
        claim["text"] += " Capacity increased 50 percent."
    elif change == "unit":
        damaged["evidence_spans"][0]["structured_value"]["unit"] = "million USD"
    else:
        claim["evidence_ids"] = [old["evidence_spans"][0]["span_id"]]
    with pytest.raises((AssertionError, ValueError)):
        assert_reviewed_transcript_evolution(old, damaged)


@pytest.mark.parametrize("change", ["claim", "topic", "reason"])
def test_v3_evolution_review_rejects_unreviewed_content_or_classification(change):
    old, current = _current_snapshots()
    damaged = deepcopy(current)
    span = damaged["evidence_spans"][0]
    if change == "claim":
        span["raw_text"] += " Revenue doubled."
    elif change == "topic":
        span["structured_value"]["topics"].append("market_leader")
    else:
        span["structured_value"]["selection_reasons"].append("external_validation")
    with pytest.raises((AssertionError, ValueError)):
        assert_reviewed_transcript_evolution_v2_to_v3(old, damaged)
