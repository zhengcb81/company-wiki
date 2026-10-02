"""JSON originals replay from encoded provider bytes, without translation."""

import base64
import hashlib
import json
from dataclasses import replace
from pathlib import Path

import pytest

from company_wiki.source_catalog.transcript_material import (
    TranscriptMaterialError,
    extract_transcript_material,
    load_transcript_material,
)


def test_fmp_producer_golden_replays_without_rewriting_original():
    golden = json.loads((Path(__file__).parents[1] / 'fixtures/transcript_fmp/fmp_v2.fetched.json').read_text(encoding='utf-8'))
    original = base64.b64decode(golden['provider_payload_base64'])
    material = extract_transcript_material(original, mime_type='application/json')
    assert material.original_sha256 == golden['provider_payload_sha256']
    assert hashlib.sha256(material.text_utf8.rstrip('\n').encode()).hexdigest() == golden['canonical_content_sha256']
    material.verify(original)
    assert load_transcript_material(material.lineage_dict(), original=original,
        text_utf8=material.text_utf8.encode(), expected_mime_type='application/json') == material


@pytest.mark.parametrize('ensure_ascii', [False, True])
def test_json_escaped_newlines_quotes_unicode_and_literal_backslashes(ensure_ascii):
    text = 'CEO: 海外业务 😀 "growth"\r\nAnalyst: literal \\n and &amp;\nCEO: planned, not completed.\u2028Final line'
    original = json.dumps([{'symbol': 'MSFT', 'content': text}], ensure_ascii=ensure_ascii).encode('utf-8')
    material = extract_transcript_material(original, mime_type='application/json')
    assert material.text_utf8.splitlines() == [
        'CEO: 海外业务 😀 "growth"', 'Analyst: literal \\n and &amp;',
        'CEO: planned, not completed.', 'Final line',
    ]
    assert material.extractor_version != 'transcript-original-text/1.0.0'
    for text_line, span in zip(material.text_utf8.splitlines(), material.lines, strict=True):
        encoded = original[span.source_byte_start:span.source_byte_end].decode('utf-8')
        assert ' '.join(json.loads('"' + encoded + '"').split()) == text_line
    material.verify(original)
    assert load_transcript_material(material.lineage_dict(), original=original,
        text_utf8=material.text_utf8.encode(), expected_mime_type='application/json') == material
    with pytest.raises(TranscriptMaterialError, match='original bytes changed'):
        material.verify(original + b' ')
    bad_span = replace(material.lines[0], source_byte_start=0)
    with pytest.raises(TranscriptMaterialError):
        replace(material, lines=(bad_span, *material.lines[1:])).verify(original)


@pytest.mark.parametrize('original', [
    b'[{"content":"one","content":"two"}]',
    b'[{"content":"truncated}',
    b'[{"content":"one"},{"content":"two"}]',
    b'[{"content":42}]',
    b'[{"content":"\\ud800"}]',
    b'[{"content":"text","x":NaN}]',
    b'[{"content":"text","nested":{"content":"another"}}]',
])
def test_json_ambiguous_or_invalid_original_is_rejected(original):
    with pytest.raises(TranscriptMaterialError):
        extract_transcript_material(original, mime_type='application/json')


def test_legacy_plain_extractor_version_is_preserved():
    material = extract_transcript_material(b'CEO: English text\n', mime_type='text/plain')
    assert material.extractor_version == 'transcript-original-text/1.0.0'


def test_json_line_budget_counts_nonempty_lines(monkeypatch):
    import company_wiki.source_catalog.transcript_text_extract as extractor

    monkeypatch.setattr(extractor, 'MAX_TRANSCRIPT_LINES', 2)
    bounded = json.dumps([{'content': 'first\n\nsecond\n'}]).encode()
    assert len(extract_transcript_material(bounded, mime_type='application/json').lines) == 2
    oversized = json.dumps([{'content': 'first\nsecond\nthird'}]).encode()
    with pytest.raises(TranscriptMaterialError, match='line limit'):
        extract_transcript_material(oversized, mime_type='application/json')
