"""Named operating scope must not disappear behind generic recognition policy."""
from __future__ import annotations

from hashlib import sha256
import re

import pytest

from company_wiki.source_catalog import narrative_business_policy as policy
from company_wiki.source_catalog.narrative_document import DocumentStructure
from company_wiki.source_catalog.narrative_evidence import _make_unit, select_narrative_evidence
from company_wiki.source_contract import EvidenceCoordinates, source_id_for_sha256


SCOPED = (
    "本集团的测量仪器业务和设备维护服务的客户在本集团履约的同时取得并消耗经济利益，"
    "因此上述业务属于在某一时段内履行的履约义务。",
    "本公司的设备维护服务的客户在本公司履约时取得并消耗利益；"
    "或者客户控制履约形成的资产，因此上述业务属于在某一时段内履行的履约义务。",
    "本公司部分装配业务属于在某一时点履行的履约义务，在客户取得商品控制权时确认收入。",
    "Our instrument maintenance services are performance obligations satisfied over time "
    "because customers simultaneously receive and consume the benefits.",
    "The group's calibration services are performance obligations satisfied over time "
    "as the customer receives and consumes the benefits.",
    "本集团的部分测量业务、装配业务和维护服务的客户在本集团履约的同时取得并消耗经济利益；"
    "或本集团履约过程中所产出的商品具有不可替代用途，且本集团有权就累计完成部分收款，"
    "因此上述业务属于在某一时段内履行的履约义务。",
)


def source_fact(text):
    # The new reading use belongs to the actual 0.9 source projection. The
    # text-only compatibility detector is also used by legacy 0.8 selection.
    return policy.assess_reading_business_fact(text, {"relations": []})[0]


@pytest.mark.parametrize("text", SCOPED)
def test_explicit_operating_scope_has_a_distinct_recognition_reading_use(text):
    fact = source_fact(text)
    assert fact.eligible
    assert "business_revenue_recognition" in fact.topics
    assert "business_recognition_scope" in fact.topics
    assert policy.reading_material_value(fact) == "meaningful_fact"


@pytest.mark.parametrize("text", (
    "本集团部分业务属于在某一时段内履行的履约义务，客户同时取得并消耗经济利益。",
    "本集团的其他业务属于在某一时点履行的履约义务，在客户取得控制权时确认收入。",
    "Our services are performance obligations satisfied over time as customers consume benefits.",
    "Our certain businesses are performance obligations satisfied over time.",
    "Our other services are performance obligations satisfied over time.",
    "The supplier's instrument services are performance obligations satisfied over time.",
    "本集团检测业务正在拓展。客户在履约时取得利益，履约义务在某一时段内履行。",
    "Our device services are growing. Performance obligations are satisfied over time.",
    "本集团的仪器维护服务存在应收账款，按照金融资产预期信用损失模型计提减值。",
    "本集团的设备维护服务的客户在扩大生产；本集团其他业务的履约义务在某一时段内履行。",
    "本集团的设备维护服务的客户在履约时取得利益。其他业务的履约义务在某一时段内履行。",
    "本集团的设备维护服务的客户在本集团履约时取得并消耗利益；"
    "本集团其他业务属于在某一时段内履行的履约义务。",
    "本集团的主要业务属于在某一时段内履行的履约义务。",
    "The group's certain customer services are performance obligations satisfied over time.",
    "本集团客户的设备维护服务属于在某一时段内履行的履约义务。",
    "本集团供应商的设备维护服务属于在某一时段内履行的履约义务。",
    "本集团的设备维护服务的客户在本集团履约时取得并消耗利益；"
    "供应商的检测业务适用另一合同安排，因此上述业务属于在某一时段内履行的履约义务。",
    "本集团的主营业务属于在某一时段内履行的履约义务。",
    "本集团的核心业务属于在某一时段内履行的履约义务。",
    "Our core services are performance obligations satisfied over time.",
    "本集团的设备维护服务的客户在本集团履约时取得并消耗利益，而供应商的检测业务"
    "属于在某一时段内履行的履约义务。",
    "本集团的设备维护服务的客户在本集团履约时取得并消耗利益，供应商的检测业务"
    "属于在某一时段内履行的履约义务。",
    "Our instrument services are performance obligations, whereas the supplier's testing services "
    "are performance obligations satisfied over time.",
))
def test_generic_other_party_and_unrelated_finance_do_not_claim_named_scope(text):
    assert "business_recognition_scope" not in source_fact(text).topics


@pytest.mark.parametrize("language", ("zh", "en"))
def test_scope_is_retained_under_the_existing_finite_source_budget(language):
    if language == "zh":
        generic = "本集团的履约义务在某一时段内履行，客户在履约时取得并消耗经济利益。"
        scoped = SCOPED[0]
    else:
        generic = "Our performance obligations are satisfied over time as customers consume benefits."
        scoped = SCOPED[2]
    texts = [generic + (f" 注释{i}。" if language == "zh" else f" Note {i}.") for i in range(18)]
    texts.append(scoped)
    digest = sha256(b"neutral-business-scope-recognition").hexdigest()
    source = source_id_for_sha256(digest)
    units = tuple(_make_unit(
        source_id=source, parser_version="1.0.0",
        coordinates=EvidenceCoordinates(paragraph_index=index), raw_text=text,
        unit_kind="html_paragraph", source_role="company_filing", language=language,
        metadata={"source_locator": f"cwp-html-dom/1|n=0.{index}"},
    ) for index, text in enumerate(texts))
    parsed = DocumentStructure(source, digest, language, units, line_count=len(units),
                               mime_type="text/html")
    result = select_narrative_evidence(
        parsed, title="Annual report", existing_kind="annual_report",
        selector_version="0.9.0", max_selected=6,
    )
    assert scoped in {span.raw_text for span in result.evidence_spans}
    assert len(result.evidence_spans) <= 6
    assert sum(len(span.raw_text or "") for span in result.evidence_spans) <= 48000


@pytest.mark.parametrize("scope", ("其他业务", "仪器维护服务"))
def test_repeated_conditions_do_not_rescan_the_remaining_paragraph(monkeypatch, scope):
    """Actual regex input work must fit the helper's charged scan envelope."""
    from company_wiki.source_catalog import narrative_recognition_scope as owner

    scanned = 0

    class CountedPattern:
        def __init__(self, pattern):
            self.pattern = pattern

        def __getattr__(self, method):
            def call(text, *args, **kwargs):
                nonlocal scanned
                scanned += len(text)
                return getattr(self.pattern, method)(text, *args, **kwargs)
            return call

    for name, pattern in tuple(vars(owner).items()):
        if isinstance(pattern, re.Pattern):
            monkeypatch.setattr(owner, name, CountedPattern(pattern))
    text = (f"本集团的{scope}的客户在本集团履约时取得并消耗利益；" * 80
            + "本集团其他业务属于在某一时段内履行的履约义务。")
    assert owner.named_recognition_scope(text) is False
    assert scanned <= owner.READING_RECOGNITION_SCOPE_SCAN_PASSES * len(text)


@pytest.mark.parametrize("version", ("0.6.0", "0.7.0", "0.7.1", "0.8.0"))
def test_legacy_selection_does_not_call_new_scope_semantics_or_change_span_identity(monkeypatch, version):
    text = "本公司的仪器维护服务属于在某一时段内履行的履约义务。"
    digest = sha256(b"legacy-recognition-scope-boundary").hexdigest()
    source = source_id_for_sha256(digest)
    unit = _make_unit(
        source_id=source, parser_version="1.0.0",
        coordinates=EvidenceCoordinates(paragraph_index=0), raw_text=text,
        unit_kind="html_paragraph", source_role="company_filing", language="zh",
        metadata={"source_locator": "cwp-html-dom/1|n=0.0"},
    )
    document = DocumentStructure(source, digest, "zh", (unit,), line_count=1, mime_type="text/html")
    with monkeypatch.context() as patch:
        patch.setattr(policy, "named_recognition_scope", lambda _text: False)
        baseline = select_narrative_evidence(document, title="Annual report",
            existing_kind="annual_report", selector_version=version)

    def forbidden(_text):
        raise AssertionError(f"legacy selector {version} invoked new scope semantics")
    monkeypatch.setattr(policy, "named_recognition_scope", forbidden)
    actual = select_narrative_evidence(document, title="Annual report",
        existing_kind="annual_report", selector_version=version)
    assert [span.to_dict() for span in actual.evidence_spans] == [
        span.to_dict() for span in baseline.evidence_spans]
