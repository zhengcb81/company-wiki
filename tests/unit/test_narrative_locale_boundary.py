"""Catalog locale tags cross the real batch boundary without changing sources."""

import hashlib
import json
from types import SimpleNamespace

import pytest

from company_wiki.automation.narrative_batch import build_batch_events
from company_wiki.automation.narrative_batch_request import NarrativeBatchRequest
from company_wiki.automation.narrative_contracts import (
    NarrativeContractError,
    SourceMetadataValue,
    SourceRevisionEventPayload,
)
from company_wiki.source_catalog.narrative_language import NarrativeLanguageError
from company_wiki.source_catalog.source_reader import SourceRef
from company_wiki.source_contract.source_manifest import source_id_for_sha256


class CatalogReader:
    def __init__(self, language, *, company="Different issuer", body=None):
        self.body = body or (
            "公司新产品已进入海外市场，客户验证和新业务产能正在持续推进。"
        ).encode("utf-8")
        digest = hashlib.sha256(self.body).hexdigest()
        self.ref = SourceRef("locale-source", source_id_for_sha256(digest), digest,
                             len(self.body), "text/plain")
        self.metadata = {"title": company + " business update", "document_kind": "investor_call_transcript",
                         "language": language}
        self.opens = 0

    def query_ref(self, *identity):
        assert identity == (self.ref.document_id, self.ref.source_id, self.ref.content_sha256)
        return self.ref

    def describe_version(self, ref):
        assert ref == self.ref
        return dict(self.metadata)

    def read_policy_sha256(self, ref):
        assert ref == self.ref
        return "b" * 64

    def open_version(self, ref, *, purpose, expected_read_policy_sha256):
        assert purpose == "narrative_derivation"
        self.opens += 1
        return SimpleNamespace(document_id=ref.document_id, source_id=ref.source_id,
                               content_sha256=hashlib.sha256(self.body).hexdigest(),
                               byte_size=len(self.body), data=self.body,
                               source_read_policy_sha256=expected_read_policy_sha256)


def prepare(reader):
    request = NarrativeBatchRequest.from_dict({
        "schema_version": "narrative-batch-request/1", "run_id": "locale-preflight",
        "sources": [{"schema_version": "2.0", **reader.ref.__dict__}],
        "profile": "P2", "max_seconds": 30, "max_tokens": 100_000, "max_cost_usd": "0.1",
        "model": {"model_id": "fixture", "endpoint": "https://example.invalid/v1/chat/completions",
                  "api_key_env": "LOCALE_TEST_KEY"},
        "pricing": {"version": "test/1", "input_micro_usd_per_million_tokens": 300_000,
                    "output_micro_usd_per_million_tokens": 1_200_000},
    })
    return build_batch_events(request, reader, now="2026-10-09T10:00:00Z")


@pytest.mark.parametrize("tag,family", [
    ("zh-CN", "zh"), ("zh-TW", "zh"), ("zh-Hant", "zh"), ("zh-Hans-CN", "zh"),
    ("en-US", "en"), ("en-GB", "en"), ("en-Latn-US", "en"), ("ZH-hant-HK", "zh"),
])
def test_locale_preflight_preserves_declared_tag_and_resolves_worker_family(tag, family):
    reader = CatalogReader(tag)
    original = dict(reader.metadata)
    batch = prepare(reader)
    payload = json.loads(batch.events[0].payload_json)
    metadata = payload["source_metadata"]
    assert metadata["language"] == family
    assert metadata["declared_language"] == tag
    assert reader.metadata == original
    assert reader.opens == 0  # Locale normalization needs no parser/model call.
    assert SourceRevisionEventPayload.from_dict(payload).to_dict() == payload
    assert prepare(reader).input_hash == batch.input_hash


@pytest.mark.parametrize("tag", ["zh", "en", "mixed"])
def test_existing_family_wire_and_generation_identity_remain_unchanged(tag):
    reader = CatalogReader(tag)
    payload = json.loads(prepare(reader).events[0].payload_json)
    assert payload["source_metadata"] == {**reader.metadata, "source_class": "transcript"}


@pytest.mark.parametrize("tag", ["fr-FR", "zh-Latn", "en-Cyrl", "zh-../../secret", "zh-CN-extra"])
def test_unsupported_declared_tags_fail_with_a_safe_reason_before_model_work(tag):
    reader = CatalogReader(tag)
    with pytest.raises(NarrativeLanguageError, match="^SOURCE_LANGUAGE_UNSUPPORTED_TAG$"):
        prepare(reader)
    assert reader.opens == 0


def test_unknown_mixed_language_uses_verified_bytes_without_company_guessing():
    reader = CatalogReader(None, company="Another issuer", body=(
        "海外新业务已经进入规模化发展阶段，国内客户仍在完成订单验收和产品验证。\n"
        "The international product launch and domestic customer acceptance remain separate drivers."
    ).encode("utf-8"))
    payload = json.loads(prepare(reader).events[0].payload_json)
    assert payload["source_metadata"]["language"] == "mixed"
    assert "declared_language" not in payload["source_metadata"]
    assert reader.metadata["language"] is None
    assert reader.opens == 1


def test_unclassifiable_unknown_source_remains_an_extraction_failure():
    reader = CatalogReader(None, body=b"123 456 789")
    with pytest.raises(NarrativeLanguageError, match="^SOURCE_LANGUAGE_UNDETERMINED$"):
        prepare(reader)
    assert reader.opens == 1


def test_wire_cannot_claim_an_effective_family_unrelated_to_declared_tag():
    with pytest.raises(NarrativeContractError):
        SourceMetadataValue.from_dict({"source_class": "filing", "title": None,
                                       "document_kind": "annual_report", "language": "en",
                                       "declared_language": "zh-CN"})
