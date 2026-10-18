"""One JSON-encoding layer from a transport is decoded, not accepted blindly."""
from company_wiki.automation.narrative_model_scoped import _clause_object


def test_a_json_encoded_clause_object_is_decoded():
    raw = '{"text": "x", "basis_parts": ["p1"], "modality": "actual"}'
    assert _clause_object(raw) == {"text": "x", "basis_parts": ["p1"], "modality": "actual"}


def test_other_strings_remain_contract_errors():
    assert _clause_object("not json") is None
    assert _clause_object("[1, 2]") is None
    assert _clause_object(3) is None
