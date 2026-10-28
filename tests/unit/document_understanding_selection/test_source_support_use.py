"""Source-owned support capability, before model packet or scarce selection."""
from __future__ import annotations

from dataclasses import replace

import pytest

from company_wiki.source_catalog import narrative_reading as reading
from unit.document_understanding_selection.test_reading_native_carriers import source_fixture, selected


@pytest.mark.parametrize("text", (
    "9  Example Holdings Limited", "11  示例控股有限公司", "2025 Interim Report  14",
    "截至六月三十日止六個月", "For the six months ended June 30",
    "（除股數和每股數據外，所有金額以千計）", "All amounts in thousands except per share data",
    "非公", "非公認", "認會計準則毛利為人民幣678百萬元。",
    "Cash and cash equivalents were USD 42 million at period end.",
    "截至六月三十日，我們的現金及現金等價物為人民幣42百萬元。",
    "毛利為人民幣37百萬元，毛利率為15.2%。",
    "We remain committed to sustainable high-quality development and creating value.",
    "我們繼續堅持高質量、可持續發展的原則。",
    "Our employee share incentive scheme aims to attract staff and remains valid for ten years.",
    "本集團股權激勵計劃旨在吸引及挽留員工，計劃有效期為十年。",
    "Equity investments are measured at cost less impairment plus observable price changes.",
    "對於不易確定公平值的股權投資，按成本減減值加可觀察價格變動計量。",
    "We define adjusted operating loss as operating loss excluding share-based compensation.",
))
def test_section_intent_alone_cannot_create_an_independent_summary_anchor(text):
    parsed, pipeline = source_fixture([(text,)])
    _, metadata, packages, _, _ = reading._candidates(parsed, pipeline)
    assert not any(not row.get("context_only") for row in metadata.values()), text
    assert not packages, text
    assert parsed.units[0].raw_text == text


@pytest.mark.parametrize("text", (
    "我們憑藉廣泛的基礎設施提供全套雲產品，並基於相同的基礎技術能力打造行業解決方案。",
    "Our platform routes customer workloads through partner infrastructure.",
    "截至报告期末，研发人员达1,237人。",
    "展望下半年，我們將持續投資技術研發並提升AI能力。",
    "本期毛利率下降主要是由于服务器成本增加，以支持AI业务扩张。",
    "我們的大部分業務以人民幣交易，有外幣風險敞口，目前並無外幣對沖政策。",
    "本集團並無任何未來重大投資及資本資產計劃。",
    "本集團使用月度使用記錄確認一段時間的收入，因為此種計量反映服務的同時消費和交付。",
))
def test_complete_qualitative_unknown_resources_causes_risks_and_future_remain_support(text):
    parsed, pipeline = source_fixture([(text,)])
    _, metadata, packages, _, withheld = reading._candidates(parsed, pipeline)
    assert any(not row.get("context_only") for row in metadata.values()), (text, withheld)
    assert packages


def test_new_source_context_projects_required_scope_use_and_reason():
    parsed, _ = source_fixture([("本公司已向客户交付专用设备，但尚未完成量产认证。",)])
    selected = reading.select_reading_evidence(parsed, title="Business review", existing_kind="semi_annual_report")
    assert selected.reading_context["schema_version"] == "du-production-reading/4"
    views = [view for group in selected.reading_context["groups"] for view in group["citation_views"]]
    assert views
    assert all(view["reading_support_use"] == "support" and 0 < len(view["reading_support_reason"]) <= 80
               for view in views)


def test_context_furniture_cannot_spend_the_one_available_business_slot():
    business = "本公司已向客户交付专用设备，但尚未完成量产认证。"
    parsed, pipeline = source_fixture([(f"{index} 示例控股有限公司",) for index in range(1, 18)] + [(business,)])
    # Independent parsed HTML paragraphs, with no manufactured PDF adjacency
    # or a package declaring an unrelated footer as mandatory context.
    parsed = replace(parsed, mime_type="text/html", units=tuple(
        replace(unit, unit_kind="html_paragraph", metadata={}) for unit in parsed.units))
    pipeline["observation"]["units"] = [{"unit_id": unit.unit_id, "ordinal": index,
        "page": 1, "text": unit.raw_text, "kind": "paragraph", "role": unit.source_role,
        "language": "zh", "hints": {"source_id": unit.source_id}}
        for index, unit in enumerate(parsed.units)]
    pipeline["packages"]["packages"] = [{"package_id": str(index), "kind": "paragraph_event",
        "member_unit_ids": [unit.unit_id], "anchor_unit_ids": [unit.unit_id],
        "required_context_unit_ids": []} for index, unit in enumerate(parsed.units)]
    originals = tuple(parsed.units)
    candidates, metadata, _, _, _ = reading._candidates(parsed, pipeline)
    result = selected(parsed, pipeline, candidates, metadata, limit=1)
    assert {uid for uid, value in metadata.items() if not value.get("context_only")} == {parsed.units[-1].unit_id}
    assert [span.raw_text for span in result.evidence_spans] == [business]
    assert parsed.units == originals


@pytest.mark.parametrize("text", (
    "Share-based compensation is recognized under the accounting policy. We hired 24 engineers for our R&D center.",
    "本集团按成本减减值计量股权投资。公司已向客户交付12套设备。",
    "Our employee share incentive scheme lasts ten years. In the second half we will invest in research and development.",
))
def test_independent_business_assertions_survive_inside_financial_or_incentive_notes(text):
    parsed, pipeline = source_fixture([(text,)])
    _, metadata, packages, _, withheld = reading._candidates(parsed, pipeline)
    assert packages and any(not row.get("context_only") for row in metadata.values()), withheld


def test_source_use_is_not_a_fact_score_or_known_purpose_threshold():
    from company_wiki.source_catalog.n6_candidate_operating_facts import OperatingFact
    from company_wiki.source_catalog.narrative_support_use import source_support_use
    description = "Our platform routes customer workloads through partner infrastructure."
    assert source_support_use(description, fact=OperatingFact(), financial_only=False)[0] == "support"
    unresolved = OperatingFact(True, (), ("operating_state_unknown",), 99)
    assert source_support_use("This item.", fact=unresolved, financial_only=False)[0] != "support"


def test_source_assessment_exhaustion_is_explicit_and_never_an_unbounded_fallback():
    from company_wiki.resource_budget import WorkBudget
    from company_wiki.source_catalog.n6_candidate_operating_facts import OperatingFact
    from company_wiki.source_catalog.narrative_support_use import source_support_use
    assert source_support_use("Our plant started production.", fact=OperatingFact(), financial_only=None) == (
        "unresolved", "source_assessment_incomplete")
    parsed, _ = source_fixture([("本公司已向客户交付12套设备。",)])
    result = reading.select_reading_evidence(parsed, title="Business review", work_budget=WorkBudget(1))
    assert not result.evidence_spans and not result.coverage_complete


def test_unknown_state_cannot_borrow_an_object_or_predicate_from_context():
    from company_wiki.source_catalog.n6_candidate_operating_facts import OperatingFact
    from company_wiki.source_catalog.narrative_support_use import source_support_use
    fact = OperatingFact(True, (), ("operating_state_unknown",), 3)
    for field in ("object_refs", "predicate_refs"):
        relation = {"object_refs": [{"unit_id": "support"}], "predicate_refs": [{"unit_id": "support"}]}
        relation[field] = [{"unit_id": "context"}]
        result = source_support_use("Our customers and platform.", fact=fact, financial_only=False,
            source_relations={"relations": [relation]}, support_unit_ids=("support",))
        assert result[0] == "context_only"


def test_multiple_unknown_relations_share_one_source_object_scan(monkeypatch):
    from company_wiki.source_catalog.n6_candidate_operating_facts import OperatingFact
    from company_wiki.source_catalog import narrative_support_use as owner
    calls = []
    from company_wiki.source_catalog import narrative_business_policy as policy
    observed = policy.source_has_operating_object
    def counted(text):
        calls.append(len(text))
        return observed(text)
    monkeypatch.setattr(policy, "source_has_operating_object", counted)
    relations = [{"object_refs": [], "predicate_refs": [{"unit_id": "context"}]} for _ in range(40)]
    result = owner.source_support_use("Our customers and platform.", fact=OperatingFact(), financial_only=False,
        source_relations={"relations": relations}, support_unit_ids=("support",))
    assert result[0] == "context_only" and len(calls) <= 1


@pytest.mark.parametrize("text", (
    "Our equipment is used by hospitals to sterilise surgical tools.",
    "Our filtration systems are used by food producers to remove particles.",
    "Our software supports customer order processing.",
    "Our platform processes customer transactions.",
    "Our service coverage includes remote factory maintenance.",
    "Our services include onsite repairs and remote diagnostics.",
    "本公司的设备用于医院器械消毒。",
    "我们的软件支持客户订单处理。",
    "本公司的服务范围包括远程工厂维护。",
    "The equipment deployment is scheduled for the next reporting period, not completed.",
))
def test_same_clause_use_function_and_membership_are_source_proofs(text):
    from company_wiki.source_catalog.narrative_source_purpose import descriptive_operating_relation
    assert descriptive_operating_relation(text)
    parsed, pipeline = source_fixture([(text,)])
    _, metadata, packages, _, withheld = reading._candidates(parsed, pipeline)
    assert packages and any(not row.get("context_only") for row in metadata.values()), withheld


@pytest.mark.parametrize("text", (
    "产品名称见词汇表。量产。",
    "Product names appear in the glossary. Production.",
    "Software is mentioned in the glossary. Supports.",
    "设备名称列于索引。用于。",
    "The glossary contains product names.",
    "Product portfolio.",
    "The equipment deployment.",
    "Our service costs include product support expenses.",
))
def test_nouns_or_stage_words_in_a_different_clause_are_not_source_proofs(text):
    from company_wiki.source_catalog.narrative_source_purpose import descriptive_operating_relation
    assert not descriptive_operating_relation(text)
    parsed, pipeline = source_fixture([(text,)])
    _, metadata, packages, _, _ = reading._candidates(parsed, pipeline)
    assert not packages and not any(not row.get("context_only") for row in metadata.values())


def test_unknown_refs_need_one_local_assertion_not_just_scope_membership():
    from company_wiki.source_catalog.n6_candidate_operating_facts import OperatingFact
    from company_wiki.source_catalog.narrative_support_use import source_support_use
    relation = {"object_refs": [{"unit_id": "support", "char_start": 0, "char_end": 8}],
                "predicate_refs": [{"unit_id": "support", "char_start": 21, "char_end": 28}],
                "assertion_refs": [{"unit_id": "support", "char_start": 20, "char_end": 29}]}
    result = source_support_use("Products in glossary. Started.",
        fact=OperatingFact(True, (), ("operating_state_unknown",), 3), financial_only=False,
        source_relations={"relations": [relation]}, support_unit_ids=("support",))
    assert result[0] != "support"


def test_real_unknown_state_refs_preserve_local_negation_without_inventing_a_stage():
    from copy import deepcopy
    from company_wiki.source_catalog.n6_candidate_operating_facts import OperatingFact
    from company_wiki.source_catalog.narrative_support_use import source_support_use
    text = "Our device has not started qualification."
    relation = {"stage": "unknown", "polarity": "negative",
        "object_refs": [{"unit_id": "support", "char_start": text.index("device"), "char_end": text.index("device") + 6}],
        "predicate_refs": [{"unit_id": "support", "char_start": text.index("started"), "char_end": text.index("started") + 7}],
        "assertion_refs": [{"unit_id": "support", "char_start": 0, "char_end": len(text)}]}
    original = deepcopy(relation)
    result = source_support_use(text, fact=OperatingFact(True, (), ("operating_state_unknown",), 3),
        financial_only=False, source_relations={"relations": [relation]}, support_unit_ids=("support",))
    assert result == ("support", "source_operating_description") and relation == original


def test_word_only_stage_does_not_remain_a_business_fact_upstream_of_support_use():
    from company_wiki.source_catalog.narrative_operating_relations import SourceOperatingSession
    from company_wiki.resource_budget import WorkBudget
    from company_wiki.source_catalog.narrative_business_policy import reading_material_value, detect_reading_business_fact
    parsed, _ = source_fixture([("产品名称见词汇表。量产。",)])
    session = SourceOperatingSession({unit.unit_id: unit for unit in parsed.units}, work_budget=WorkBudget(100000))
    fact = session.fact(parsed.units[0].unit_id)
    assert not fact.eligible and reading_material_value(fact) == "description"
    assert not detect_reading_business_fact(parsed.units[0].raw_text).eligible


def test_clause_description_work_is_linear_in_repeated_unbound_heads(monkeypatch):
    import re
    from company_wiki.document_understanding.operating_states import assertion_roles as owner
    from unit.document_understanding_selection.test_prepared_predicate_context import RegexMeter
    patterns = {name: value for name, value in vars(owner).items() if isinstance(value, re.Pattern)}
    normalized = []
    for count in (32, 64, 128):
        text = "equipment marker in glossary " * count
        totals = {}
        with monkeypatch.context() as patch:
            for name, pattern in patterns.items():
                patch.setattr(owner, name, RegexMeter(pattern, totals, name))
            assert not owner.descriptive_operating_relation(text)
        normalized.append(sum(totals.values()) / len(text))
    assert max(normalized) / min(normalized) <= 1.15, normalized


def test_provision_subject_is_bound_not_just_an_earlier_nonempty_prefix():
    from company_wiki.source_catalog.narrative_source_purpose import descriptive_operating_relation
    assert not descriptive_operating_relation("Product labels mention providing software.")
    assert descriptive_operating_relation("ExampleCo provides industrial software.")


@pytest.mark.parametrize("text", (
    "We provide option-pricing software to banks.",
    "公司向银行提供期权定价软件。",
    "Our option-pricing software supports client order processing.",
    "Our lease liabilities software supports customer contract processing.",
    "公司向零售客户提供租赁负债管理软件。",
))
def test_financial_terms_can_modify_a_real_supplied_or_functional_product(text):
    from company_wiki.source_catalog.narrative_source_purpose import source_purpose
    assert source_purpose(text) == "operating"
    parsed, pipeline = source_fixture([(text,)])
    _, metadata, packages, _, withheld = reading._candidates(parsed, pipeline)
    assert packages and any(not row.get("context_only") for row in metadata.values()), withheld


@pytest.mark.parametrize("text", (
    "We use option-pricing software to estimate employee share options.",
    "公司采用期权定价软件计量股份支付费用。",
    "The fair value of equity investments is measured using software.",
    "公司按照会计政策计量租赁负债。",
    "Our software costs include option-pricing expenses.",
    "Option-pricing is described in an accounting glossary. Software.",
    "期权定价政策列于附注。软件名称列于词汇表。",
))
def test_actual_financial_rules_or_unrelated_product_words_do_not_borrow_a_product_role(text):
    parsed, pipeline = source_fixture([(text,)])
    _, metadata, packages, _, _ = reading._candidates(parsed, pipeline)
    assert not packages and not any(not row.get("context_only") for row in metadata.values())


@pytest.mark.parametrize("text", (
    "Participants.", "参与者。", "(iv)\n经营租赁", "(ii) operating leases",
    "Our financial statements assume assets are realised and liabilities settled in the ordinary course of business.",
    "本集团财务报表按持续经营基准编制，该基准假设资产及负债在日常业务中变现及清偿。",
    "Forward-looking statements may be identified by words including launch, develop, plan and expect.",
    "前瞻性陈述可通过计划、开展、参与、经营等词语识别。",
    "Interim operating results are not necessarily indicative of the full-year results.",
    "本中期经营业绩未必反映全年预期业绩。",
    "Share awards exceeding the individual limit require approval from shareholders.",
    "向参与者授出的股份奖励超过个人限额时须经股东批准。",
    "The auditor's work does not involve an audit of the financial information.",
    "会计师事务所的鉴证工作并不涉及对相关财务资料的独立审计。",
    "The group adopted ASC 842 and reconciled operating leases to IFRS 16.",
    "本集团采用租赁会计准则并对经营租赁作出会计对账。",
))
def test_reporting_rules_nominal_heads_and_disclaimers_are_not_operating_assertions(text):
    parsed,pipeline=source_fixture([(text,)])
    _,metadata,packages,_,_=reading._candidates(parsed,pipeline)
    assert not packages and not any(not row.get('context_only') for row in metadata.values())


@pytest.mark.parametrize("text", (
    "The company acquired a factory. Right-of-use assets were recognized at carrying value.",
    "公司新增制造基地已经投入运行。",
    "Our company opened a new manufacturing facility for customers.",
    "公司抗体药物产线新增年产能10,000批。",
    "另一种产品由区域渠道向客户提供维护服务。",
    "The company commissioned a new manufacturing plant.",
    "The plant can produce 48 machines per year.",
    "ii. 客户复购率超过85%。",
    "本期，第七代云设备P7和R8正式发布，\n支持客户在线推理工作负载。",
    "Nimbus训练与推理平台亦已正式上线，为用户提供模型任务管理平台，\n集成开源模型Nova3。",
    "公司向银行提供公允价值计量软件。",
))
def test_complete_operating_proofs_do_not_depend_on_recognised_stage_or_numeric_presence(text):
    parsed,pipeline=source_fixture([(text,)])
    _,metadata,packages,_,withheld=reading._candidates(parsed,pipeline)
    assert packages and any(not row.get('context_only') for row in metadata.values()), withheld


@pytest.mark.parametrize("text", (
    "Our product portfolio includes recycling systems.",
    "一体化生产服务覆盖多个下游客户工序。",
    "Our service platform covers order processing and customer support workflows.",
    "我们的软件平台涵盖客户的订单处理与生产工作流程。",
    "Our equipment lineup comprises control systems.",
))
def test_closed_operating_membership_and_coverage_are_qualitative_support(text):
    parsed, pipeline = source_fixture([(text,)])
    _, metadata, packages, _, withheld = reading._candidates(parsed, pipeline)
    assert packages and any(not row.get("context_only") for row in metadata.values()), (text, withheld)


@pytest.mark.parametrize("text", (
    "Accounting policy includes rules for product revenue and service costs.",
    "The fair value policy covers equity investments and financial assets.",
    "Employee share incentive scheme covers vesting conditions and administrative procedures.",
    "The art exhibit includes paintings and sculpture.",
    "Our service costs include product support expenses.",
    "本期产品成本涵盖客户服务费用。",
))
def test_nonoperating_membership_or_coverage_does_not_become_a_business_assertion(text):
    parsed, pipeline = source_fixture([(text,)])
    _, metadata, packages, _, _ = reading._candidates(parsed, pipeline)
    assert not packages and not any(not row.get("context_only") for row in metadata.values()), text


# Fixed test oracle: source IDs and expected meaning of saved original scopes,
# never their old support labels or topic/score metadata. No production branch
# depends on these IDs, task numbers, document pages or product names.
_NATIVE_V3_SCOPES = (
    (1, ('urn:company-wiki:evidence-span:sha256:0a44e8b518b43f0498bb64e5b1b741f9466ae5690977fb785efcf39d75f13977',), False),
    (2, ('urn:company-wiki:evidence-span:sha256:2cbd65fffcc7661d9b694f0c55b75bf6472614a9946a0b9e6f457f574160c0de',), False),
    (3, ('urn:company-wiki:evidence-span:sha256:6d1d566a22a33ecf7459fb8fadcefec512e63855c047af810c593c6aa5d401aa',), False),
    (4, ('urn:company-wiki:evidence-span:sha256:72ba56bf52503d6b53082bdb5713157f040a8b8048efe9494bbcc91a32da3738',), False),
    (5, ('urn:company-wiki:evidence-span:sha256:fa2886647d11e2224f1b27aeada8b09c306f97d0a49c8ed98752914846e4524a',), False),
    (6, ('urn:company-wiki:evidence-span:sha256:bf684db5bae1f757ac5045b7682e6056f1fc43190f268670098d113e22a20713',), False),
    (7, ('urn:company-wiki:evidence-span:sha256:772f38b3263dd6d42bf03d11df7aa926230d9ab17f219061f5c398d5a686ddc6',), False),
    (8, ('urn:company-wiki:evidence-span:sha256:32d5668cc470d4ca328098a8deb6e2b86c2907786b8aca869974f061c1b4bbf0',), False),
    (9, ('urn:company-wiki:evidence-span:sha256:18b082e5dafeea15da624de42a54425e193ac1189ae90c7be539785e143c1878',), True),
    (10, ('urn:company-wiki:evidence-span:sha256:ecb6452b41c0dd42cd47aa1cae1dab360d9d681752f528fa4415829fefaf1eab',), False),
    (11, ('urn:company-wiki:evidence-span:sha256:4f4dc87550ede6b49625242286cc6e217104167a4cf5162d98cd15fdd1ebefef',), True),
    (12, ('urn:company-wiki:evidence-span:sha256:b2bf738c04f0d3ac657b433f08a86862175de58bfde28936b72ca32b5eb8860b',), True),
    (13, ('urn:company-wiki:evidence-span:sha256:9a97da3951e863cfdc817d966e1cc40a8c21a3946a7c55351594ff47a8dfc30b',), True),
    (14, ('urn:company-wiki:evidence-span:sha256:936316afeb330e7e435731b866dfffd576596eba6186a0cdb2a0f9a491889ee2',), True),
    (15, ('urn:company-wiki:evidence-span:sha256:4be85a5a2ad4b0a8e79a4d340a7c50a3675aa07b651401ae003d1e14e040dead',), True),
    (16, ('urn:company-wiki:evidence-span:sha256:8818fc521557cd67fae4600425f2ee7100234303cd6172b22b37c636a9fa7316',), True),
    (17, ('urn:company-wiki:evidence-span:sha256:fd73ab37bcdc495e201285ff99002bf617f41a94b9ee6ce873dc9f7ed5edc2c8',), True),
    (18, ('urn:company-wiki:evidence-span:sha256:dec60b36d15cda0943d3cea97d3987ec96d1f6592b4b789bb21172e95e5491d4',), True),
    (19, ('urn:company-wiki:evidence-span:sha256:8facfc0d576e1a57a19bc09a369461f97dd092759766cd021359a17adedfbddc',), True),
    (20, ('urn:company-wiki:evidence-span:sha256:1de7e93f7bb352987434d1213901eae8f134591cb410248cda4b345e0bf67f36',), True),
    (21, ('urn:company-wiki:evidence-span:sha256:525a35d6fe0dc8a88e169207582796b04116d50afb7af3962819cc81e1d13b03',), True),
    (22, ('urn:company-wiki:evidence-span:sha256:e24c44460496474bce1198e35f415a69637010d5cbad058b7825792c796a5c0c',), True),
    (23, ('urn:company-wiki:evidence-span:sha256:4b0dcf1d2805672cfb61e7b85361f4e9c59eba7e0b3cb48600cce507332c9e77',), True),
    (24, ('urn:company-wiki:evidence-span:sha256:ae5f4d14634776a788377b2a94cd69fc31a3cf0713f348ecfebfc2052412bf1f',), True),
    (25, ('urn:company-wiki:evidence-span:sha256:e395049c60cd340ca2d8e90ef42468163895fbd38a73219c4a529f0ffbdd993d',), True),
    (26, ('urn:company-wiki:evidence-span:sha256:a26ef156c5f0fb478d924f579b5dcff216786caba4f5ed126c68755b22913dd8',), True),
    (27, ('urn:company-wiki:evidence-span:sha256:0f887d75ce8ca0b8f1286183e21da451e63f4e297e4efd79664d9414c7a26430',), True),
    (28, ('urn:company-wiki:evidence-span:sha256:c9cfb3cbbc0274cc102d1f53d54e6ca1fb93770d5e923f464d4d6202424dcab2',), True),
    (29, ('urn:company-wiki:evidence-span:sha256:69ff7031971451decb1ea8bf50d13652db9f467b14c74b011cd9c1d64dd2ea0e',), True),
    (30, ('urn:company-wiki:evidence-span:sha256:46871741dd03ce6c6d8005c1d9104bbfd9cc64cbc01895e108b12d2023138253',), True),
    (31, ('urn:company-wiki:evidence-span:sha256:5b61e1e80cdc9a1e4bf7fa418ca8a0ab6b41ffc92b4d12dd9d4c446cc50fb894',), True),
    (32, ('urn:company-wiki:evidence-span:sha256:bb0c40372be5ad55d56fca22cf4db3ca72255c898f30144573d9a9241de9e912',), False),
    (33, ('urn:company-wiki:evidence-span:sha256:fbcc7fe501d4582332c63866c574c7150f7f38d840b50c1441e46f5ad2e6c847',), True),
    (34, ('urn:company-wiki:evidence-span:sha256:cbd98718fcaac669d6da0e7306544063dc66ddc9dfa45af23adb9cd085c0ce5a',), True),
    (35, ('urn:company-wiki:evidence-span:sha256:fe6cfe2186ced6edfca3960c3bb7a46cf187195f11a03bc4ec8e780df9d420da',), False),
    (36, ('urn:company-wiki:evidence-span:sha256:ff18bd232ca837a9f67e68509d8d0d0e69e42f86e2b5e8548bd78e022106c741',), False),
    (37, ('urn:company-wiki:evidence-span:sha256:5701c0c9fc2fb46837bba1ecc82a959671de4ec0b557ddec4b12f8f289974c46',), False),
    (38, ('urn:company-wiki:evidence-span:sha256:0d37f44cedadb1ed894dd513356666eb2f10a4dd1252490d39b2ad38b19d982e',), True),
    (39, ('urn:company-wiki:evidence-span:sha256:7bb32ebac1e7dc20ff552e68622149e7c6ed1ebfcab7b697be7b49e69479b870',), False),
    (40, ('urn:company-wiki:evidence-span:sha256:82b027b386d8f4eeba248557943b4fca6bcd36d49330efeadb801a5110372077',), True),
    (41, ('urn:company-wiki:evidence-span:sha256:4a9445e05fc2d153823d51e9f987f2a869c4c299a28910cb5c5f80a27f40055c',), False),
    (42, ('urn:company-wiki:evidence-span:sha256:fd3bbf438dff21595e48fc4599558af7d5d00416ed1ca794b281428cd1b0bd11',), True),
    (43, ('urn:company-wiki:evidence-span:sha256:30988efa414e481761680d6c9b9b23b063166475d4fc4b66a9eb1cab5f0217bc',), True),
    (44, ('urn:company-wiki:evidence-span:sha256:2599b7c50356c1325e77d15a9bca58af805dd089dcfd2ee8763db140f98bc80d',), True),
    (45, ('urn:company-wiki:evidence-span:sha256:7d38f0f8a080a66f4bed83b4716c4c25caca6146f0386547e0e74eee0c33261f',), True),
    (46, ('urn:company-wiki:evidence-span:sha256:5015d7057fcf95162916fc28736c4880ffee309b97ab29ccd761a19de0c3f27f',), True),
    (47, ('urn:company-wiki:evidence-span:sha256:7368c6055284dd1db049904d2aa2809e6e1521c0237feb29889566c51345ad21',), True),
    (48, ('urn:company-wiki:evidence-span:sha256:c52ff00d650c41765d408edfe0131dfd8fb52e4437d26dd27e9b9a500297482c',), True),
    (49, ('urn:company-wiki:evidence-span:sha256:dddd0d65fc9702548d62db123ca7b814d3d636f2debd1761ca6c0dd4337028e1',), True),
    (50, ('urn:company-wiki:evidence-span:sha256:3ba0b02f3f982b6e3e06fe47e74efac345952a0961629eac4d09766976295215',), True),
    (51, ('urn:company-wiki:evidence-span:sha256:31c115556cefbe354b16117f4063d802417ed181233e3d7d92c5ec6f6eff9132',), False),
)


@pytest.fixture(scope="module")
def saved_native_source_assessments():
    from pathlib import Path
    from hashlib import sha256
    from types import SimpleNamespace
    import gzip
    import json
    from company_wiki.resource_budget import WorkBudget
    from company_wiki.source_contract import EvidenceCoordinates
    from company_wiki.source_catalog.narrative_operating_relations import SourceOperatingSession
    from company_wiki.source_catalog.narrative_support_use import source_support_use
    path=Path(__file__).resolve().parents[3] / 'docs/plans/du11-source-closure-2026-10-18/review/pdf-c3-20261026/evidence/source-use-20261028/v3__native-support-v3__selection.json.gz'
    assert sha256(path.read_bytes()).hexdigest() == 'e22a10df47b0890a2b62794f7134fc5670e00ceeff9707e3c4b9f9a51a9079f6'
    selected=json.loads(gzip.decompress(path.read_bytes()))
    spans={span["span_id"]:span for span in selected["evidence_spans"]}
    units={sid:SimpleNamespace(raw_text=span["raw_text"],source_id=span["source_id"],
        source_role=span["structured_value"].get("source_role","unknown"),
        unit_kind=span["structured_value"].get("unit_kind","unknown"),
        coordinates=EvidenceCoordinates(**span["coordinates"])) for sid,span in spans.items()}
    groups={f"scope-{number}":ids for number,ids,_expected in _NATIVE_V3_SCOPES}
    session=SourceOperatingSession(units,groups=groups,work_budget=WorkBudget(2_000_000))
    observed={}
    for key,ids in groups.items():
        fact=session.fact(key)
        observed[key]=source_support_use(session.source_text(key),fact=fact,
            financial_only=session.financial_only(key),source_relations=session.relations(key),
            support_unit_ids=ids,source_roles=session.source_assertions(key))
    assert len(units)==101 and len(groups)==51 and session.complete and not session.work_budget.exhausted
    assert len({unit.source_id for unit in units.values()})==1
    return session,observed


@pytest.mark.parametrize("number,ids,expected", _NATIVE_V3_SCOPES, ids=lambda value:str(value) if isinstance(value,int) else None)
def test_saved_native_source_scope_replays_real_business_not_prior_metadata(saved_native_source_assessments,number,ids,expected):
    session,observed=saved_native_source_assessments
    key=f"scope-{number}"
    assert (observed[key][0]=="support") is expected, (number,observed[key],session.source_text(key))
    assert session.groups[key]==ids


def test_source_session_shares_one_role_assessment_without_repeated_scans(monkeypatch):
    from company_wiki.document_understanding.operating_states import assertion_roles
    from company_wiki.source_catalog.narrative_operating_relations import SourceOperatingSession
    from company_wiki.source_catalog.narrative_support_use import source_support_use
    from company_wiki.resource_budget import WorkBudget
    text="Our equipment is used by hospitals to sterilise surgical tools."
    parsed,_=source_fixture([(text,)])
    uid=parsed.units[0].unit_id
    session=SourceOperatingSession({uid:parsed.units[0]},work_budget=WorkBudget(100000))
    actual=assertion_roles.prepare_source_assertions
    calls=[]
    def observed(value):
        calls.append(value)
        return actual(value)
    monkeypatch.setattr(assertion_roles,"prepare_source_assertions",observed)
    for _ in range(4):
        fact=session.fact(uid)
        assert source_support_use(text,fact=fact,financial_only=session.financial_only(uid),
            source_relations=session.relations(uid),support_unit_ids=(uid,),
            source_roles=session.source_assertions(uid))[0]=="support"
    assert calls==[text] and session.complete


@pytest.mark.parametrize('text',('服务提供商。','设备供应商。','本集团的服务提供商使之提供服务。'))
def test_derived_provider_nouns_are_not_function_assertions(text):
    from company_wiki.source_catalog.narrative_source_purpose import descriptive_operating_relation
    assert not descriptive_operating_relation(text)


@pytest.mark.parametrize('text',(
    '我们的平台提供商品订单处理服务。',
    '公司向客户提供股权激励计划管理软件。',
    'Our software supports granting share awards to employees.',
))
def test_financial_and_agent_word_parts_do_not_override_actual_product_functions(text):
    parsed,pipeline=source_fixture([(text,)])
    assert reading._candidates(parsed,pipeline)[2]


@pytest.mark.parametrize('text',(
    'Our new device has completed customer qualification and shipments begin next quarter.',
    'Our new device has not completed customer qualification, and delivery remains conditional.',
))
def test_complete_source_predicate_proof_preserves_qualification_and_its_denial(text):
    parsed,pipeline=source_fixture([(text,)])
    assert reading._candidates(parsed,pipeline)[2]
    assert parsed.units[0].raw_text==text


@pytest.mark.parametrize('number',(24,25,27,44,46,47,48,49,50))
def test_native_critical_and_financial_note_services_keep_original_support(saved_native_source_assessments,number):
    session,observed=saved_native_source_assessments
    key=f'scope-{number}'
    assert observed[key][0]=='support'
    expected=next(ids for n,ids,_expected in _NATIVE_V3_SCOPES if n==number)
    assert session.groups[key]==expected


@pytest.mark.parametrize('text',(
    'Forward-looking statements can be identified by words such as "our software supports customer order processing".',
    '前瞻性陈述可通过词语识别，例如“我们的软件支持客户订单处理”。',
))
def test_metatext_definition_cannot_donate_its_quoted_function_as_an_actual_business_assertion(text):
    parsed,pipeline=source_fixture([(text,)])
    assert not reading._candidates(parsed,pipeline)[2]


def test_actual_software_function_can_have_reporting_text_as_its_object():
    parsed,pipeline=source_fixture([('Our software identifies forward-looking statements in customer reports.',)])
    assert reading._candidates(parsed,pipeline)[2]


def _selection_support_case(texts):
    parsed,pipeline=source_fixture([(text,) for text in texts])
    parsed=replace(parsed,mime_type='text/html',units=tuple(
        replace(unit,unit_kind='html_paragraph',metadata={}) for unit in parsed.units))
    pipeline['observation']['units']=[dict(unit_id=unit.unit_id,ordinal=index,page=1,
        text=unit.raw_text,kind='paragraph',role=unit.source_role,language='en',
        hints=dict(source_id=unit.source_id)) for index,unit in enumerate(parsed.units)]
    pipeline['packages']['packages']=[dict(package_id=str(index),kind='paragraph_event',
        member_unit_ids=[unit.unit_id],anchor_unit_ids=[unit.unit_id],required_context_unit_ids=[])
        for index,unit in enumerate(parsed.units)]
    for unit in parsed.units:
        pipeline['reading_plan']['unit_profiles'][unit.unit_id].update(
            priority=9 if unit.raw_text.endswith('infrastructure.') else 1,section_role='business')
    return parsed,pipeline


def _select_support_case(texts,limit):
    from company_wiki.source_catalog.narrative_finalize import finalize_selection
    from company_wiki.source_catalog.narrative_routing import DocumentRoute
    parsed,pipeline=_selection_support_case(texts)
    candidates,metadata,packages,complete,withheld=reading._candidates(parsed,pipeline)
    assert complete and not withheld
    selected=finalize_selection(parsed,DocumentRoute('annual_report',limit,False),candidates,
        group_ids={},heading_pattern=reading._NEVER_HEADING,dropped_financial_count=0,
        budget_policy=reading.READING_BUDGET_POLICY,reading_metadata=metadata,max_chars=48000)
    return selected,packages,parsed


@pytest.mark.parametrize('row',('Depreciation\n528\n912','Active customers\n735\n626'))
@pytest.mark.parametrize('reverse',(False,True))
def test_summary_support_globally_precedes_unresolved_in_a_single_slot(row,reverse):
    business='Our platform routes customer workloads through partner infrastructure.'
    texts=[row,business]
    if reverse:
        texts.reverse()
    selected,_,_=_select_support_case(texts,1)
    assert [span.raw_text for span in selected.evidence_spans]==[business]


@pytest.mark.parametrize('row',(
    'Depreciation and amortisation\n528\n912','折旧及摊销\n125\n160',
    'Foreign currency exchange gains\n125\n160','外币换算调整\n125\n160',
    'Customer advances\n735\n626','客户预收款\n735\n626',
    'Gain on sale of property and equipment\n125\n160','出售物业及设备的收益\n125\n160',
))
def test_statement_account_rows_are_raw_readable_but_not_independent_narrative_material(row):
    selected,packages,parsed=_select_support_case([row],1)
    assert parsed.units[0].raw_text==row and not selected.evidence_spans and not packages


@pytest.mark.parametrize('row',(
    'Active customers\n735\n626','客户数量\n735\n626',
    'Capacity utilization\n80\n75','产能利用率\n80\n75',
    'Foreign currency risk exposure\n125\n160','外币风险敞口\n125\n160',
))
def test_uncertain_business_measures_remain_readable_and_cannot_generate(row):
    selected,packages,parsed=_select_support_case([row],1)
    assert [span.raw_text for span in selected.evidence_spans]==[row] and parsed.units[0].raw_text==row
    assert packages[0]['_reading_support_use_views'][0]['reading_support_use']=='unresolved'


@pytest.mark.parametrize('policy,expected',(
    ('reading_plan/1','unknown'),('reading_plan/2','unknown'),('reading_plan/3','support'),
))
def test_support_rank_metadata_is_current_policy_only_and_does_not_read_payload(policy,expected):
    from company_wiki.source_catalog.narrative_budget import select_budget_items
    from unit.document_understanding_selection.test_reading_budget_plan import _item
    class Opaque:
        @property
        def text(self):raise AssertionError('budget cannot classify payload text')
    items=(replace(_item('unknown',priority=1),reading_support_use='unresolved',payload=Opaque()),
           replace(_item('support',priority=9),reading_support_use='support',payload=Opaque()))
    assert [item.item_id for item in select_budget_items(items,limit=1,policy=policy)]==[expected]


def test_support_tier_keeps_atomic_closure_and_unique_context_cost():
    from company_wiki.source_catalog.narrative_budget import select_budget_items,READING_BUDGET_POLICY
    from unit.document_understanding_selection.test_reading_budget_plan import _item
    items=(replace(_item('unknown',priority=1),reading_support_use='unresolved'),
           replace(_item('support',priority=9,required=('heading','qualification')),reading_support_use='support'),
           _item('heading',context_only=True),_item('qualification',context_only=True))
    selected=select_budget_items(items,limit=3,policy=READING_BUDGET_POLICY)
    assert {item.item_id for item in selected}=={'support','heading','qualification'}
    selected=select_budget_items(items,limit=2,policy=READING_BUDGET_POLICY)
    assert [item.item_id for item in selected]==['unknown']


def test_legacy_none_support_metadata_preserves_existing_priority_order():
    from company_wiki.source_catalog.narrative_budget import select_budget_items,READING_BUDGET_POLICY
    from unit.document_understanding_selection.test_reading_budget_plan import _item
    items=(_item('first',priority=1),_item('second',priority=9))
    assert [item.item_id for item in select_budget_items(items,limit=1,policy=READING_BUDGET_POLICY)]==['first']


@pytest.mark.parametrize('text',(
    '该设备已进入客户进行生产验证。','另一设备已送至客户进行生产验证。',
    '新经销渠道仍在客户认证中。',
))
def test_typed_predicate_binding_supplies_completeness_without_promoting_unknown_stage(text):
    from company_wiki.source_catalog.narrative_operating_relations import SourceOperatingSession
    from company_wiki.resource_budget import WorkBudget
    parsed,_=source_fixture([(text,)])
    uid=parsed.units[0].unit_id
    session=SourceOperatingSession({uid:parsed.units[0]},work_budget=WorkBudget(100000))
    before=session.relations(uid)
    assert before['relations'] and any(r['stage']=='unknown' for r in before['relations'])
    assert session.fact(uid).eligible and session.source_assertions(uid).operating
    assert session.relations(uid)==before and parsed.units[0].raw_text==text


@pytest.mark.parametrize('text',('Other\n125\n160\n23','其他\n125\n160\n23','Unclassified category\n125\n160\n23'))
def test_structured_uncertainty_without_business_proof_has_no_independent_offer(text):
    from company_wiki.resource_budget import WorkBudget
    from company_wiki.source_catalog.narrative_operating_relations import SourceOperatingSession
    from company_wiki.source_catalog.narrative_support_use import source_support_use
    selected,packages,parsed=_select_support_case([text],1)
    uid=parsed.units[0].unit_id
    session=SourceOperatingSession({uid:parsed.units[0]},work_budget=WorkBudget(100000))
    fact=session.fact(uid)
    use=source_support_use(text,fact=fact,financial_only=session.financial_only(uid),
                           source_roles=session.source_assertions(uid))
    assert use==('unresolved','source_numeric_scope_unresolved')
    assert session.source_assertions(uid).numeric_role=='unknown'
    assert not packages and not selected.evidence_spans and parsed.units[0].raw_text==text


def test_positive_offer_keeps_raw_unknown_required_context_and_its_full_cost():
    from company_wiki.source_catalog.narrative_finalize import finalize_selection
    from company_wiki.source_catalog.narrative_routing import DocumentRoute
    raw='Other\n125\n160\n23'
    business='Our platform routes customer workloads through partner infrastructure.'
    parsed,pipeline=_selection_support_case([raw,business])
    raw_id,business_id=(unit.unit_id for unit in parsed.units)
    pipeline['packages']['packages'][1]['required_context_unit_ids']=[raw_id]
    candidates,metadata,packages,complete,withheld=reading._candidates(parsed,pipeline)
    assert complete and not withheld and len(packages)==1
    assert metadata[raw_id]['context_only'] and not metadata[business_id]['context_only']
    for cap,count in ((1,0),(2,2)):
        selected=finalize_selection(parsed,DocumentRoute('annual_report',cap,False),candidates,
            group_ids={},heading_pattern=reading._NEVER_HEADING,dropped_financial_count=0,
            budget_policy=reading.READING_BUDGET_POLICY,reading_metadata=metadata,max_chars=48000)
        assert len(selected.evidence_spans)==count
        if count:
            assert [span.raw_text for span in selected.evidence_spans]==[raw,business]


def test_complete_structured_raw_only_source_uses_existing_no_narrative_terminal():
    parsed,_=_selection_support_case(['Other\n125\n160\n23','其他\n175\n180\n26'])
    before=tuple((unit.unit_id,unit.raw_text,unit.coordinates) for unit in parsed.units)
    selected=reading.select_reading_evidence(parsed,title='Annual report',existing_kind='annual_report')
    assert selected.status=='skipped_no_narrative' and selected.coverage_complete
    assert not selected.evidence_spans and selected.candidate_count==0
    assert selected.dropped_financial_count==0, 'unknown rows must not be relabelled financial'
    assert tuple((unit.unit_id,unit.raw_text,unit.coordinates) for unit in parsed.units)==before


@pytest.mark.parametrize('mode',('prose','unread','budget'))
def test_unproved_prose_or_incomplete_source_cannot_use_raw_only_skip(mode):
    from company_wiki.resource_budget import WorkBudget
    text='The other matters are still being examined.' if mode=='prose' else 'Other\n125\n160\n23'
    parsed,_=_selection_support_case([text])
    if mode=='unread':
        parsed=replace(parsed,pages_read=0,opaque_pages=(1,))
    kwargs={'work_budget':WorkBudget(1)} if mode=='budget' else {}
    selected=reading.select_reading_evidence(parsed,title='Annual report',existing_kind='annual_report',**kwargs)
    assert selected.status!='skipped_no_narrative'


def test_direct_admission_projects_use_and_relevance_from_one_preparation(monkeypatch):
    from company_wiki.document_understanding.operating_states import assertion_roles
    from company_wiki.source_catalog import narrative_support_use
    from company_wiki.source_catalog.n6_candidate_operating_facts import OperatingFact
    text='Our platform routes customer workloads through partner infrastructure.'
    parsed,_=_selection_support_case([text])
    actual=assertion_roles.prepare_source_assertions
    calls=[]
    def observed(value):
        calls.append(value)
        return actual(value)
    monkeypatch.setattr(assertion_roles,'prepare_source_assertions',observed)
    monkeypatch.setattr(narrative_support_use,'prepare_source_assertions',observed)
    assert reading._admitted(parsed.units[0],{},'background',fact=OperatingFact(),financial_only=False)[0]
    assert calls==[text]


@pytest.mark.parametrize('texts',(
    ['The other matters are still being examined.','Other\n125\n160\n23'],
    ['The other matters are still being examined.\nOther\n125\n160\n23'],
    ['Other\n125\n160\n23\nThe other matters are still being examined.'],
    ['Other\n125\n160\n23\nOther\n125\n160\n23'],
))
def test_raw_only_skip_requires_whole_unit_coverage_not_numeric_run_presence(texts):
    parsed,_=_selection_support_case(texts)
    before=tuple((unit.unit_id,unit.raw_text,unit.coordinates) for unit in parsed.units)
    selected=reading.select_reading_evidence(parsed,title='Annual report',existing_kind='annual_report')
    assert selected.status=='needs_review' and selected.coverage_complete
    assert not selected.evidence_spans and selected.candidate_count==0
    assert selected.dropped_financial_count==0
    assert tuple((unit.unit_id,unit.raw_text,unit.coordinates) for unit in parsed.units)==before


@pytest.mark.parametrize('texts',(
    ['Other\n125\n160\n23'],
    ['Other\n125\n160\n23','Other\n125\n160\n23'],
    ['Other\n125'],
    ['125\n160\n23'],
))
def test_complete_single_row_or_scalar_material_can_use_raw_only_skip(texts):
    parsed,_=_selection_support_case(texts)
    selected=reading.select_reading_evidence(parsed,title='Annual report',existing_kind='annual_report')
    assert selected.status=='skipped_no_narrative' and selected.coverage_complete
    assert not selected.evidence_spans and selected.dropped_financial_count==0


@pytest.mark.parametrize('text,present,complete',(
    ('Other\n125\n160\n23',True,True),
    ('The other matters are still being examined.\nOther\n125\n160\n23',True,False),
    ('Other\n125\n160\n23\nThe other matters are still being examined.',True,False),
    ('Other\n125\n160\n23\nOther\n125\n160\n23',True,False),
    ('The other matters are still being examined.\n125\n160\n23',True,False),
    ('Other|$125|(160)|—',True,True),
    ('Other\n125',False,True),
    ('125\n160\n23',False,True),
    ('Other',False,False),
    ('',False,False),
))
def test_value_cell_presence_and_full_coverage_are_distinct_cached_structural_facts(text,present,complete):
    from company_wiki.document_normalization.table_shapes import observe_value_cells, has_unbound_numeric_cells
    from company_wiki.document_understanding.operating_states.assertion_roles import prepare_source_assertions
    observed=observe_value_cells(text)
    assert observed.unbound_numeric_cells is present
    assert observed.complete_value_row is complete
    assert has_unbound_numeric_cells(text) is present
    prepared=prepare_source_assertions(text)
    assert prepared.numeric_ambiguous is present
    assert prepared.raw_structure_complete is complete


@pytest.mark.parametrize('texts',(
    ['The other matters are still being examined.','所得税费用\n125\n160\n23'],
    ['The other matters are still being examined.\n所得税费用\n125\n160\n23'],
    ['所得税费用\n125\n160\n23\nThe other matters are still being examined.'],
))
def test_financial_drop_count_does_not_certify_unexplained_numeric_material(texts):
    parsed,_=_selection_support_case(texts)
    before=tuple((unit.unit_id,unit.raw_text,unit.coordinates) for unit in parsed.units)
    selected=reading.select_reading_evidence(parsed,title='Annual report',existing_kind='annual_report')
    assert selected.status=='needs_review' and selected.coverage_complete
    assert selected.dropped_financial_count==1
    assert not selected.evidence_spans and selected.candidate_count==0
    assert tuple((unit.unit_id,unit.raw_text,unit.coordinates) for unit in parsed.units)==before


def test_administrative_route_cannot_certify_mixed_numeric_material():
    parsed,_=_selection_support_case(['The other matters are still being examined.\n所得税费用\n125\n160\n23'])
    selected=reading.select_reading_evidence(parsed,title='Annual report',existing_kind='ir_policy')
    assert selected.status=='needs_review' and selected.coverage_complete
    assert selected.dropped_financial_count==1


@pytest.mark.parametrize('policy',('reading_plan/3','reading_plan/2','reading_plan/1','legacy'))
def test_current_finalizer_requires_source_disposition_proof_and_retains_legacy_counter_replay(policy):
    from company_wiki.source_catalog.narrative_finalize import finalize_selection
    from company_wiki.source_catalog.narrative_routing import DocumentRoute
    parsed,_=_selection_support_case(['The other matters are still being examined.\n所得税费用\n125\n160\n23'])
    result=finalize_selection(parsed,DocumentRoute('annual_report',112,False),(),group_ids={},
        heading_pattern=reading._NEVER_HEADING,dropped_financial_count=1,budget_policy=policy)
    assert result.dropped_financial_count==1 and result.coverage_complete
    assert result.status==('needs_review' if policy=='reading_plan/3' else 'skipped_no_narrative')


def _ci_source_assessment(text):
    from company_wiki.resource_budget import WorkBudget
    from company_wiki.source_catalog.narrative_operating_relations import SourceOperatingSession
    from company_wiki.source_catalog.narrative_support_use import source_support_use
    parsed,_=source_fixture([(text,)])
    unit=parsed.units[0]
    session=SourceOperatingSession({unit.unit_id:unit},work_budget=WorkBudget(500000))
    fact=session.fact(unit.unit_id)
    roles=session.source_assertions(unit.unit_id)
    use=source_support_use(text,fact=fact,financial_only=session.financial_only(unit.unit_id),source_roles=roles)
    return fact,roles,use


@pytest.mark.parametrize('text',(
    'a new product for overseas customers.',
    'Equipment available in several configurations.',
    'A product offered in several configurations.',
))
def test_product_np_modifiers_do_not_supply_an_independent_predicate(text):
    fact,roles,use=_ci_source_assessment(text)
    assert not roles.operating and not fact.eligible and use[0]!='support'


@pytest.mark.parametrize('text',(
    'Our equipment is for hospitals to sterilise surgical tools.',
    'Our products are available in several configurations.',
    'Our product is offered in several configurations.',
    'Our product comes in several configurations.',
))
def test_copular_and_finite_product_descriptions_have_real_predicates(text):
    fact,roles,use=_ci_source_assessment(text)
    assert roles.operating and fact.eligible and use[0]=='support'


@pytest.mark.parametrize('text',(
    '公司已收购设备企业，与现有产品形成客户协同。',
    '公司采用期权定价模型计量股份支付。公司已收购设备企业，与现有产品形成客户协同。',
    '公司已收購設備企業，與現有產品形成客戶協同。',
    'The company acquired an equipment company. Equity investments are measured at fair value.',
))
def test_independent_acquisition_binds_local_actor_action_and_operating_object(text):
    fact,roles,use=_ci_source_assessment(text)
    assert roles.operating and fact.eligible and use[0]=='support'


@pytest.mark.parametrize('text',(
    '公司收购交易性金融资产。',
    'The company acquired treasury assets.',
    '收购。设备企业。',
))
def test_acquisition_word_without_local_operating_object_does_not_complete_a_proof(text):
    _fact,roles,use=_ci_source_assessment(text)
    assert not roles.operating and use[0]!='support'


def test_real_guidance_clause_survives_a_separate_disclaimer_without_retyping_that_disclaimer():
    from company_wiki.source_catalog.narrative_source_purpose import source_purpose
    guidance='预计2029年公司整体收入达到125-140亿元。'
    premise='上述2029年全年经营业绩展望以客户订单按期交付为前提，并不代表公司对全年经营业绩的盈利预测，不构成实质承诺。'
    fact,_roles,use=_ci_source_assessment(guidance+premise)
    assert fact.eligible and fact.purpose=='operating_guidance' and use[0]=='support'
    assert source_purpose(premise)=='reporting_definition'


@pytest.mark.parametrize('text',(
    'Active customers\n—\n735\n–\nIncrease from new distribution channels',
    'Capacity utilization\n—\n80\n–',
    '客戶數量\n—\n164\n–\n增加源自海外渠道',
))
def test_single_operating_value_cells_keep_role_and_readable_offer_without_multiple_value_claim(text):
    from company_wiki.document_normalization.table_shapes import has_unbound_numeric_cells
    selected,packages,_parsed=_select_support_case([text],4)
    _fact,roles,use=_ci_source_assessment(text)
    assert not has_unbound_numeric_cells(text) and not roles.numeric_ambiguous
    assert roles.numeric_role=='operating'
    assert use==('unresolved','source_numeric_scope_unresolved')
    assert packages and selected.evidence_spans
