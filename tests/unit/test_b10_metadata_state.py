"""B10 unit: the single chain's two halves share ONE parse implementation.

``store.metadata_object`` is the plain half (object or nothing);
``store.metadata_state`` is the reporting half (object + WHY it is not a usable object).
B10-3 converged the reporting callers onto the same parse, so the two halves must never
disagree about what the content is.
"""

from __future__ import annotations

from company_wiki.source_catalog.store import metadata_object, metadata_state

_CASES = [
    None,
    "",
    "{}",
    "[]",
    "123",
    '"a string"',
    "not json",
    '{"a": 1}',
    '{"a": ' + "[" * 200_000 + "]" * 200_000 + "}",  # deep nesting -> RecursionError
    b"\xff\xfe not utf-8",  # undecodable bytes
    {"already": "a dict"},
]


def test_metadata_object_and_state_agree_on_every_input() -> None:
    for raw in _CASES:
        obj = metadata_object(raw)
        state_obj, state = metadata_state(raw)
        assert obj == state_obj, f"halves disagree for {type(raw).__name__} input"
        assert obj == {} or isinstance(obj, dict)
        if obj:
            assert state is None, f"an object must have state None, got {state!r}"


def test_metadata_state_classifies() -> None:
    obj, state = metadata_state('{"k": "v"}')
    assert (obj, state) == ({"k": "v"}, None)
    obj, state = metadata_state("[1, 2]")
    assert (obj, state) == ({}, "not_object")
    obj, state = metadata_state("not json")
    assert (obj, state) == ({}, "unreadable")
    obj, state = metadata_state(None)
    assert (obj, state) == ({}, None)


def test_metadata_object_never_raises() -> None:
    for raw in _CASES:
        assert isinstance(metadata_object(raw), dict)


def test_metadata_object_normalizes_deep_nesting_to_empty() -> None:
    deep = '{"a": ' + "[" * 200_000 + "]" * 200_000 + "}"
    assert metadata_object(deep) == {}
    assert metadata_state(deep)[1] == "unreadable"
