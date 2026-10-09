"""Transcript parser identities stay replayable without reinterpreting old locators."""
from __future__ import annotations

from copy import deepcopy
from dataclasses import replace
import hashlib
from pathlib import Path

import pytest

from company_wiki.automation.narrative_formats import parser_component
from company_wiki.source_catalog.narrative_evidence import (
    parse_transcript_text, select_narrative_evidence, verify_transcript_evidence_spans,
    NARRATIVE_SELECTOR_NAME, NARRATIVE_SELECTOR_VERSION,
)
from company_wiki.source_catalog.narrative_retrieval import (
    NARRATIVE_EVIDENCE_BUNDLE_SCHEMA_VERSION, NARRATIVE_REPLAY_CONTRACT_SCHEMA_VERSION,
    NarrativeEvidenceResolver, NarrativeEvidenceResolveError, NarrativeEvidenceSearch,
)
from company_wiki.source_catalog.transcript_text_extract import extract_transcript_material
from company_wiki.source_contract import source_id_for_sha256


SENTENCE = "We launched a new product and expanded overseas capacity."
LEGACY = f"Full Conference Call Transcript\nCEO: {SENTENCE}\n"
NATURAL = f"Transcript\nAcme Q3 Earnings Call\nJANE DOE:\n{SENTENCE}\nEND\n"


def transcript_bundle(raw_path: Path, *, version: str, source_format="transcript_txt"):
    original = raw_path.read_bytes()
    digest = hashlib.sha256(original).hexdigest()
    source_id = source_id_for_sha256(digest)
    mime_type = {"transcript_txt": "text/plain", "transcript_html": "text/html"}[source_format]
    if source_format == "transcript_txt":
        text = original.decode("utf-8-sig")
    else:
        material = extract_transcript_material(original, mime_type=mime_type)
        material.verify(original)
        text = material.text_utf8
    parser_name, parser_version = parser_component(mime_type, "transcript", parser_version=version)
    parsed = parse_transcript_text(text, source_id=source_id, source_sha256=digest,
                                   language="en", parser_version=parser_version)
    selected = select_narrative_evidence(parsed, title="Acme earnings call",
                                         existing_kind="investor_call_transcript")
    bundle = {
        "schema_version": NARRATIVE_EVIDENCE_BUNDLE_SCHEMA_VERSION,
        "sources": [{
            "title": "Acme earnings call", "selection_status": selected.status,
            "coverage_complete": selected.coverage_complete,
            "summary_input": selected.summary_input(),
            "replay_contract": {
                "schema_version": NARRATIVE_REPLAY_CONTRACT_SCHEMA_VERSION,
                "source_format": source_format, "language": "en",
                "existing_kind": "investor_call_transcript",
                "parser_name": parser_name, "parser_version": parser_version,
                "parser_options": {}, "selector_name": NARRATIVE_SELECTOR_NAME,
                "selector_version": NARRATIVE_SELECTOR_VERSION,
                "max_selected": selected.selection_limit,
            },
        }],
    }
    return bundle, parsed, selected, text


@pytest.mark.parametrize("version", ["0.1.0", "0.1.1", "0.2.0"])
def test_legacy_and_current_packages_replay_original_words_and_locators(tmp_path, version):
    raw = tmp_path / "call.txt"
    raw.write_bytes(LEGACY.encode("utf-8"))
    bundle, parsed, selected, text = transcript_bundle(raw, version=version)
    span = next(span for span in selected.evidence_spans if span.raw_text == SENTENCE)
    assert span.parser_version == version
    assert span.coordinates.paragraph_index == 1
    assert (span.coordinates.char_start, span.coordinates.char_end) == (0, len(SENTENCE))
    assert span.structured_value["source_role"] == "management"
    verified, failed = verify_transcript_evidence_spans(
        text, source_id=parsed.source_id, source_sha256=parsed.source_sha256,
        evidence_spans=selected.evidence_spans,
    )
    assert verified == tuple(span.span_id for span in selected.evidence_spans)
    assert not failed
    hit = NarrativeEvidenceSearch(bundle).search("expanded overseas")[0]
    resolved = NarrativeEvidenceResolver(bundle, raw_paths_by_source_id={hit.source_id: raw}).resolve(hit)
    assert resolved.raw_text == SENTENCE
    assert resolved.parser_version == version
    assert resolved.evidence_ids == hit.evidence_ids
    assert resolved.locators == hit.locators == (span.locator,)


@pytest.mark.parametrize("version", ["0.1.0", "0.1.1"])
def test_old_versions_do_not_reinterpret_current_natural_body(version):
    digest = hashlib.sha256(NATURAL.encode()).hexdigest()
    parsed = parse_transcript_text(NATURAL, source_id=source_id_for_sha256(digest),
                                   source_sha256=digest, parser_version=version)
    assert parsed.errors == ("transcript_start_missing",)
    assert parsed.units == ()


def test_current_official_html_package_replays_hashed_original_bytes(tmp_path):
    raw = tmp_path / "call.html"
    original = ("<html><body><h2>Transcript</h2><p>Acme Q3 Earnings Call</p>"
                f"<p>JANE DOE:</p><p>{SENTENCE}</p><p>AMY ROE: Thank you.</p><p>END</p>"
                "<footer>We launched a new retail website.</footer></body></html>").encode()
    raw.write_bytes(original)
    bundle, _, selected, _ = transcript_bundle(raw, version="0.2.0", source_format="transcript_html")
    assert selected.coverage_complete
    assert all("retail" not in span.raw_text for span in selected.evidence_spans)
    hit = NarrativeEvidenceSearch(bundle).search("expanded overseas")[0]
    resolved = NarrativeEvidenceResolver(bundle, raw_paths_by_source_id={hit.source_id: raw}).resolve(hit)
    assert resolved.raw_text == SENTENCE
    assert resolved.parser_version == "0.2.0"
    assert raw.read_bytes() == original


@pytest.mark.parametrize("mutation,message", [
    ("unknown", "unsupported transcript parser version"),
    ("wrong_declared", "parser metadata"),
    ("forged_text", "package evidence text hash"),
    ("forged_text_and_sha", "replayed package raw_text_sha256"),
    ("forged_locator", "selected evidence set"),
    ("wrong_format", "file extension"),
])
def test_version_text_hash_locator_and_format_guards_remain_closed(tmp_path, mutation, message):
    raw = tmp_path / "call.txt"
    raw.write_bytes(LEGACY.encode())
    original, _, _, _ = transcript_bundle(raw, version="0.2.0")
    bundle = deepcopy(original)
    record = bundle["sources"][0]
    row = record["summary_input"]["evidence"][0]
    if mutation == "unknown":
        record["replay_contract"]["parser_version"] = "9.9.9"
        row["parser_version"] = "9.9.9"
    elif mutation == "wrong_declared":
        record["replay_contract"]["parser_version"] = "0.1.1"
    elif mutation.startswith("forged_text"):
        row["raw_text"] = "We launched a forged overseas product."
        if mutation == "forged_text_and_sha":
            row["raw_text_sha256"] = hashlib.sha256(row["raw_text"].encode()).hexdigest()
    elif mutation == "forged_locator":
        row["locators"] = ["loc:v1/paragraph:999/char:0:4"]
        row["locator"] = row["locators"][0]
    else:
        record["replay_contract"]["source_format"] = "transcript_html"
    hit = NarrativeEvidenceSearch(bundle).search("overseas")[0]
    resolver = NarrativeEvidenceResolver(bundle, raw_paths_by_source_id={hit.source_id: raw})
    with pytest.raises(NarrativeEvidenceResolveError, match=message):
        resolver.resolve(hit)
    # A forged hit cannot bypass package-group matching either.
    with pytest.raises(NarrativeEvidenceResolveError, match="exact package group"):
        resolver.resolve(replace(hit, locators=("loc:v1/paragraph:800/char:0:4",)))


def test_unknown_version_rejected_at_parser_and_generation_boundary():
    with pytest.raises(ValueError, match="unsupported transcript parser version"):
        parser_component("text/plain", "transcript", parser_version="0.2.1")
    digest = hashlib.sha256(LEGACY.encode()).hexdigest()
    with pytest.raises(ValueError, match="unsupported transcript parser version"):
        parse_transcript_text(LEGACY, source_id=source_id_for_sha256(digest),
                              source_sha256=digest, parser_version="0.2.1")


@pytest.mark.parametrize("mutation,message", [
    ("contract", "unsupported transcript parser version"),
    ("evidence", "package evidence text hash"),
    ("locator", "exact package group"),
    ("evidence_sha", "replayed package raw_text_sha256"),
    ("source_sha", "search hit identity"),
])
def test_resolver_owns_construction_snapshot_and_reuses_parse_cache(
    tmp_path, monkeypatch, mutation, message,
):
    raw = tmp_path / "call.txt"
    raw.write_bytes(LEGACY.encode())
    bundle, _, _, _ = transcript_bundle(raw, version="0.2.0")
    hit = NarrativeEvidenceSearch(bundle).search("expanded overseas")[0]
    paths = {hit.source_id: raw}
    resolver = NarrativeEvidenceResolver(bundle, raw_paths_by_source_id=paths)
    from company_wiki.source_catalog import narrative_evidence
    original_parse = narrative_evidence.parse_transcript_text
    parse_calls = []

    def counted_parse(*args, **kwargs):
        parse_calls.append(kwargs["parser_version"])
        return original_parse(*args, **kwargs)

    monkeypatch.setattr(narrative_evidence, "parse_transcript_text", counted_parse)
    first = resolver.resolve(hit)
    assert first.raw_text == SENTENCE and parse_calls == ["0.2.0"]
    record = bundle["sources"][0]
    row = record["summary_input"]["evidence"][0]
    if mutation == "contract":
        record["replay_contract"]["parser_version"] = "9.9.9"
    elif mutation == "evidence":
        row["raw_text"] = "We launched a forged overseas product."
    elif mutation == "locator":
        row["locators"][0] = "loc:v1/paragraph:999/char:0:4"
    elif mutation == "evidence_sha":
        row["raw_text"] = "We launched a forged overseas product."
        row["raw_text_sha256"] = hashlib.sha256(row["raw_text"].encode()).hexdigest()
    else:
        record["summary_input"]["source_sha256"] = "0" * 64
    # This reader owns the original construction snapshot. The external bundle
    # is input for future readers, not a mutable control channel for this one.
    assert resolver.resolve(hit) == first
    assert resolver.resolve_group(source_id=hit.source_id,
                                  evidence_group_id=hit.evidence_group_id) == first
    assert parse_calls == ["0.2.0"]
    fresh = NarrativeEvidenceResolver(bundle, raw_paths_by_source_id=paths)
    with pytest.raises(NarrativeEvidenceResolveError, match=message):
        fresh.resolve(hit)


def test_resolver_snapshot_is_taken_before_first_read_and_keeps_path_mapping(tmp_path):
    raw = tmp_path / "call.txt"
    raw.write_bytes(LEGACY.encode())
    bundle, _, _, _ = transcript_bundle(raw, version="0.1.1")
    hit = NarrativeEvidenceSearch(bundle).search("expanded overseas")[0]
    paths = {hit.source_id: raw}
    resolver = NarrativeEvidenceResolver(bundle, raw_paths_by_source_id=paths)
    bundle["sources"][0]["replay_contract"]["parser_version"] = "9.9.9"
    paths.clear()
    resolved = resolver.resolve(hit)
    assert resolved.raw_text == SENTENCE and resolved.parser_version == "0.1.1"
    assert resolved.locators == hit.locators
    with pytest.raises(NarrativeEvidenceResolveError, match="unsupported transcript parser version"):
        NarrativeEvidenceResolver(bundle, raw_paths_by_source_id={hit.source_id: raw}).resolve(hit)
