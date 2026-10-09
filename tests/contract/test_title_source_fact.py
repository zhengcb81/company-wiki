"""Titles are nullable source descriptions, not permissions or filename guesses."""

import pytest
from helpers.source_fact_fixture import (
    lake,
    html,
    imported,
    evidence,
    remove_capture_title,
    close,
)
from company_wiki.source_catalog.source_reader import SourceVersionReader


@pytest.fixture
def source(tmp_path):
    cat = lake(tmp_path)
    data = html(title="10-Q", form="10-Q", period="Q1", end="2025-09-30")
    ref, path = imported(cat, data, published="2026-07-30", declared_year=2026, document_kind="regulatory_filing")
    remove_capture_title(cat, ref)
    try:
        yield cat, ref, path, data
    finally:
        close(cat)


def test_title_correction_is_actual_source_text_append_only_and_idempotent(source):
    cat, ref, path, data = source
    reader = SourceVersionReader(cat)
    assert reader.describe_version(ref)["title"] is None
    prior = [
        dict(x)
        for x in cat.reader.fetchall(
            "SELECT * FROM source_metadata_assertions WHERE source_id=?",
            (ref.source_id,),
        )
    ]
    capture = cat.reader.fetchone(
        "SELECT metadata_json FROM documents WHERE document_id=?", (ref.document_id,)
    )[0]
    facts = {"title": "10-Q"}
    proof = evidence(ref, facts)
    first = cat.record_source_facts(ref=ref, facts=facts, evidence=proof)
    assert first["status"] == "recorded"
    assert reader.describe_version(ref)["title"] == "10-Q"
    assert (
        reader.open_version(ref, purpose="source_export").data
        == path.read_bytes()
        == data
    )
    assert (
        cat.reader.fetchone(
            "SELECT metadata_json FROM documents WHERE document_id=?",
            (ref.document_id,),
        )[0]
        == capture
    )
    assert [
        dict(x)
        for x in cat.reader.fetchall(
            "SELECT * FROM source_metadata_assertions WHERE source_id=? AND assertion_id!=?",
            (ref.source_id, first["assertion_id"]),
        )
    ] == prior
    proof["title"]["observed_at"] = "2026-10-09T01:00:00Z"
    assert cat.record_source_facts(ref=ref, facts=facts, evidence=proof) == {
        **first,
        "status": "unchanged",
    }


def test_title_and_form_projection_survives_explicit_registration(source):
    cat, ref, path, data = source
    facts = {"title": "10-Q", "form_type": "10-Q"}
    cat.record_source_facts(ref=ref, facts=facts, evidence=evidence(ref, facts))
    relative = path.relative_to(cat.config.roots[0].path).as_posix()
    cat.register_sources(root_id="company_raw", relative_paths={relative})
    manifest = SourceVersionReader(cat).describe_version(ref)
    assert (manifest["title"], manifest["form_type"]) == ("10-Q", "10-Q")
    assert (
        cat.reader.fetchone(
            "SELECT title FROM documents WHERE document_id=?", (ref.document_id,)
        )[0]
        == "10-Q"
    )
    assert path.read_bytes() == data


def test_explicit_unknown_title_remains_nullable_and_raw_readable(source):
    cat, ref, path, data = source
    for value in ("10-Q", None):
        facts = {"title": value}
        cat.record_source_facts(ref=ref, facts=facts, evidence=evidence(ref, facts))
    reader = SourceVersionReader(cat)
    assert reader.describe_version(ref)["title"] is None
    assert reader.open_version(ref, purpose="source_export").data == data
    assert (
        cat.reader.fetchone(
            "SELECT title FROM documents WHERE document_id=?", (ref.document_id,)
        )[0]
        is not None
    )


@pytest.mark.parametrize(
    "facts,proof",
    [
        ({"title": ""}, {"title": {"value": "", "locator": "html:title"}}),
        (
            {"title": " padded "},
            {"title": {"value": " padded ", "locator": "html:title"}},
        ),
        ({"title": "10-Q"}, {}),
        ({"title": "10-Q"}, {"title": {"value": "10-K", "locator": "html:title"}}),
    ],
)
def test_invalid_title_evidence_never_writes(source, facts, proof):
    cat, ref, path, data = source
    before = cat.reader.fetchone("SELECT COUNT(*) FROM source_metadata_assertions")[0]
    with pytest.raises(ValueError):
        cat.record_source_facts(ref=ref, facts=facts, evidence=proof)
    assert (
        cat.reader.fetchone("SELECT COUNT(*) FROM source_metadata_assertions")[0]
        == before
    )
    assert SourceVersionReader(cat).describe_version(ref)["title"] is None
    assert path.read_bytes() == data
