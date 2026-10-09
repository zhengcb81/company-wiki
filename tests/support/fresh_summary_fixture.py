"""Synthetic source bindings with small source-derived business passages.

The passages derive from the sealed fresh HK/US observations; fixture bytes/IDs
are synthetic and never masquerade as those original sources.
"""

from dataclasses import replace
from company_wiki.source_contract import EvidenceCoordinates, EvidenceSpan
from support.narrative_model_request_fixture import selection

HK_TEXT = (
    "金融科技及企業服務業務截至二零二五年十二月三十一日止年度的收入同比增長8%至人民幣2,294億元。",
    "金融科技服務收入同比以高個位數百分比增長，乃由於理財服務、消費貸款服務及商業支付活動的收入增加。",
    "企業服務收入同比增長接近20%，得益於國內及海外對雲服務的需求（包括對AI相關服務的需求）增加，以及",
    "由於微信小店交易額上升而帶動的商家技術服務費收入增長。",
    "董事會於本年度舉行四次會議。",
)
US_TEXT = (
    "· Microsoft 365 commercial cloud will now include GitHub cloud and other developer cloud services as well as Security Copilot which were",
    "previously reported in Azure",
    "· Microsoft 365 consumer cloud is unchanged",
)


def grouped_selection(
    texts=HK_TEXT,
    groups=("finance", "finance", "business", "business", None),
    *,
    language="zh",
    page=9,
    first_paragraph=32,
    flags=(),
):
    base = selection(len(texts))
    spans = tuple(
        EvidenceSpan.create(
            source_id=base.source_ref.source_id,
            coordinates=EvidenceCoordinates(
                page_number=page, paragraph_index=first_paragraph + i
            ),
            raw_text=text,
            structured_value={
                "source_role": "company_filing",
                "language": language,
                **({"selection_group_id": group} if group is not None else {}),
            },
            parser_name="synthetic-source-derived",
            parser_version="1.0.0",
            parse_status="parsed",
            quality_flags=flags,
        )
        for i, (text, group) in enumerate(zip(texts, groups, strict=True))
    )
    return replace(
        base,
        evidence_spans=spans,
        source_metadata=replace(base.source_metadata, language=language),
    )


def draft_for(selected, claims):
    return {
        "draft": {
            "source_id": selected.source_ref.source_id,
            "source_sha256": selected.source_ref.content_sha256,
            "language": selected.source_metadata.language,
            "claims": claims,
        }
    }


def claim(text, ids, groups=None, *, name="c1"):
    value = {
        "claim_id": name,
        "text": text,
        "evidence_ids": ids,
        "claim_type": "company_statement",
        "modality": "actual",
    }
    if groups is not None:
        value["evidence_group_ids"] = groups
    return value
