"""Source-information A: actual local bindings, never a stage/reason proxy.

Small synthetic sources use real operating/session owners. No document IO,
network, source catalog, SDK or model is involved.
"""
from hashlib import sha256

from company_wiki.resource_budget import new_document_work_budget
from company_wiki.source_catalog.narrative_document import NarrativeUnit
from company_wiki.source_contract import EvidenceCoordinates, source_id_for_sha256
from company_wiki.source_catalog.narrative_operating_relations import SourceOperatingSession
from company_wiki.source_catalog.narrative_business_policy import project_reading_business_fact
from company_wiki.source_catalog.narrative_support_use import source_support_use


FINANCIAL_BACKGROUND = (
    "有鑒於此，管理層在評估本集團是否有足夠的財務資源持續經營時，"
    "已審慎考慮本集團的未來流動資金及表現以及其可用融資來源。"
    "本集團擁有現金、現金等價物以及受限制現金。"
    "此外，本集團擁有銀行及其他金融機構的現有信貸融資，"
    "為本集團日後的營運及資本開支提供資金。")


def unit_id(index):
    return "urn:company-wiki:narrative-unit:sha256:" + sha256(str(index).encode()).hexdigest()


def session_for(texts):
    units = {}
    for index, text in enumerate(texts):
        digest = sha256(text.encode()).hexdigest()
        uid = unit_id(index)
        units[uid] = NarrativeUnit(uid, source_id_for_sha256(digest),
            "source-information-regression", "1",
            EvidenceCoordinates(page_number=1, paragraph_index=index), text,
            "html_paragraph", "company_filing", "mixed")
    budget = new_document_work_budget()
    return SourceOperatingSession(units, work_budget=budget), budget


def observed_use(session, uid):
    fact = session.fact(uid)
    return source_support_use(session.source_text(uid), fact=fact,
        financial_only=session.financial_only(uid),
        source_roles=session.source_assertions(uid))


def test_financial_current_state_does_not_manufacture_business_support():
    session, _ = session_for([FINANCIAL_BACKGROUND])
    fact = session.fact(unit_id(0))
    assert not fact.financial_exempt
    assert observed_use(session, unit_id(0))[0] == "context_only"


def test_actual_financing_terms_and_operating_resources_stay_supported():
    texts = [
        "本集团签订固定利率贷款协议，并以电子设备作为抵押。",
        "Our manufacturing facilities assemble medical devices.",
        "本公司的设备尚未完成客户认证。",
        "未来公司计划建设新的服务平台。",
    ]
    for text in texts:
        session, _ = session_for([text])
        assert observed_use(session, unit_id(0))[0] == "support", text


def test_typed_binding_is_per_relation_and_cached_without_more_work():
    session, budget = session_for([
        FINANCIAL_BACKGROUND,
        "本公司的设备已完成客户认证。",
    ])
    for uid in (unit_id(0), unit_id(1)):
        result = session.relations(uid)
        proofs = session.engine.relation_bindings(uid)
        assert len(proofs) == len(result["relations"])
        if uid == unit_id(0):
            assert not any(proofs)
        else:
            assert any(proofs)
    before = budget.used
    assert session.engine.relation_bindings(unit_id(1))
    assert budget.used == before
    assert observed_use(session, unit_id(0))[0] == "context_only"


def test_serialized_refs_alone_cannot_supply_typed_operating_proof():
    session, _ = session_for(["本公司的设备已完成客户认证。"])
    result = session.relations(unit_id(0))
    assert result["relations"]
    fact = project_reading_business_fact(session.source_text(unit_id(0)), result,
                                         include_description=False)
    assert not fact.eligible


def test_mixed_source_does_not_donate_binding_to_financial_relations():
    session, _ = session_for([
        "本公司的设备已完成客户认证。 " + FINANCIAL_BACKGROUND])
    result = session.relations(unit_id(0))
    bindings = session.engine.relation_bindings(unit_id(0))
    assert any(bindings) and not all(bindings)
    assert len(bindings) == len(result["relations"])
    for relation, bound in zip(result["relations"], bindings):
        if bound:
            continue
        projected = project_reading_business_fact(session.source_text(unit_id(0)),
            {**result, "relations": [relation]}, include_description=False,
            relation_bindings=(bound,))
        assert not projected.eligible


def test_actual_contract_and_partner_bindings_need_no_product_head():
    for text in (
        "本公司已与客户签订供货合同。",
        "We signed a supply agreement with Northwind.",
        "公司计划与渠道合作伙伴建立合作关系。",
    ):
        session, _ = session_for([text])
        assert observed_use(session, unit_id(0))[0] == "support", text
        assert any(session.engine.relation_bindings(unit_id(0)))


def test_signing_arbitrary_text_does_not_create_a_business_relationship_proof():
    session, _ = session_for(["We signed the financial statements."])
    assert observed_use(session, unit_id(0))[0] == "context_only"
    assert not any(session.engine.relation_bindings(unit_id(0)))
