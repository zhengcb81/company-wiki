"""Source purpose must distinguish policies, no-event forms and real operations."""
from hashlib import sha256
from pathlib import Path
import json

import pytest

from company_wiki.source_catalog.narrative_source_purpose import source_purpose, NON_OPERATING_PURPOSES
from company_wiki.source_catalog.narrative_business_policy import detect_reading_business_fact
from company_wiki.source_catalog.narrative_evidence import _make_unit, select_narrative_evidence
from company_wiki.source_catalog.narrative_document import DocumentStructure
from company_wiki.source_catalog.narrative_reading import _admitted
from company_wiki.source_contract import EvidenceCoordinates, source_id_for_sha256


@pytest.fixture(autouse=True)
def source_owner_is_this_checkout():
    from company_wiki.source_catalog import narrative_source_purpose
    assert Path(narrative_source_purpose.__file__).resolve().is_relative_to(Path(__file__).resolve().parents[3] / "src")


POLICIES = [
    "控制是指投资方拥有对被投资方的权力，通过参与被投资方的相关活动而享有可变回报，并且有能力运用对被投资方的权力影响其回报金额。",
    "Control exists when an investor has power over an investee, exposure to variable returns and the ability to affect those returns.",
    "对于以常规方式购买或出售金融资产的，在交易日确认将收到的资产和为此将承担的负债，或者在交易日终止确认已出售的资产。",
    "Regular way purchases and sales of financial assets are recognized on the trade date when the Group commits to purchase or sell the asset.",
    "于资产负债表日，若本集团判断金融工具只具有较低的信用风险，则本集团假定该金融工具的信用风险自初始确认后并未显著增加。",
    "At each reporting date the Group assesses whether the credit risk on financial instruments has increased significantly since initial recognition.",
    "终止经营，是指满足下列条件之一的、能够单独区分的组成部分，且该组成部分已经处置或划分为持有待售类别。",
    "A discontinued operation is a component that has been disposed of or is classified as held for sale and represents a separate major business.",
    "终止经营损益在利润表中与持续经营损益分别列示。",
    "Profit or loss from discontinued operations is presented separately in the income statement.",
]
NO_EVENTS = [
    "B.报告期内向单个客户的销售比例超过总额的50%、前5名客户中存在新增客户的或严重依赖于少数客户的情形\n□适用√不适用",
    "A.报告期内公司新产品商业化取得重大进展情况\n□适用√不适用",
]
NAVIGATION = [
    "具体详见本报告第三节、五、报告期内主要经营情况。",
    "For further details see Section 8 of this report.",
]
STATUTORY_SUBSIDY_EXCEPTION = (
    "计入当期损益的政府补助，但与公司正常经营业务密切相关、符合国家政策规定、"
    "按照确定的标准享有、对公司损益产生持续影响的政府补助除外"
)


def unit(text, index=0):
    digest = sha256(b"neutral-purpose-source").hexdigest()
    return _make_unit(source_id=source_id_for_sha256(digest), parser_version="1.0.0",
        coordinates=EvidenceCoordinates(page_number=1, paragraph_index=index),
        raw_text=text, unit_kind="paragraph", source_role="company_filing", language="zh", metadata={})


@pytest.mark.parametrize("text", POLICIES)
def test_accounting_definitions_are_not_business_facts_even_in_business_profile(text):
    assert source_purpose(text) == "accounting_policy"
    fact = detect_reading_business_fact(text)
    assert not fact.eligible
    assert not _admitted(unit(text), {"section_role": "business"}, "background", fact=fact)[0]


@pytest.mark.parametrize("text", NO_EVENTS)
def test_lettered_form_no_event_is_not_a_disclosed_operating_percentage(text):
    assert source_purpose(text) == "template_no_event"
    assert not _admitted(unit(text), {"section_role": "business"}, "background")[0]


@pytest.mark.parametrize("text", NAVIGATION)
def test_pure_forward_pointer_is_not_a_business_status(text):
    assert source_purpose(text) == "navigation"
    assert not _admitted(unit(text), {"section_role": "business"}, "background")[0]


@pytest.mark.parametrize("text", [
    "公司新增软件产品已经交付客户，客户完成生产验证。",
    "The company launched a new software platform and delivered it to customers.",
    "公司于本年完成收购新工厂，并开始向海外客户交付产品。",
    "The company acquired a new factory and delivered products to overseas customers.",
    "集团本年终止经营业务实现收入8亿元，交易完成后仍为客户交付原有订单。",
    "Customer credit risk increased after the company delivered products on extended payment terms.",
    "控制系统产品已向海外客户交付，累计客户增长至60家。",
    "B.报告期内公司新产品商业化取得重大进展情况\n√适用□不适用\n公司已交付新产品至海外客户。",
    "公司新增订单同比增长20%，具体详见本报告第三节。",
])
def test_actual_operations_are_not_blocked_by_policy_words_or_form_labels(text):
    assert source_purpose(text) not in NON_OPERATING_PURPOSES


@pytest.mark.parametrize("policy", [POLICIES[0], POLICIES[2], POLICIES[4],
    "1.报告期内公司新产品交付取得重大进展情况\n□适用√不适用",
    "12.报告期内公司新产品交付取得重大进展情况\n□适用√不适用"])
def test_public_selector_retains_real_business_and_drops_separate_policy(policy):
    business="公司新增软件产品已经交付客户，客户完成生产验证。"
    units=(unit(policy), unit(business, 1))
    digest=sha256(b"neutral-purpose-source").hexdigest()
    parsed=DocumentStructure(source_id_for_sha256(digest), digest, "zh", units,
        page_count=1, pages_read=1, mime_type="text/plain")
    result=select_narrative_evidence(parsed,title="Annual report",existing_kind="annual_report",selector_version="0.9.0")
    sent=[span.raw_text for span in result.evidence_spans]
    assert business in sent
    assert policy not in sent


@pytest.mark.parametrize("text", (
    "本集团在履行了合同中的履约义务，即在客户取得相关商品或服务控制权时，按照分摊至该项履约义务的交易价格确认收入。",
    "本集团在合同开始日对合同进行评估，识别各单项履约义务是在某一时段内履行，还是在某一时点履行。",
    "本集团向客户预收销售商品或服务款项的，首先确认为负债，待履行了相关履约义务时再转为收入。",
    "Revenue is recognized when the customer obtains control of the promised goods or services under a performance obligation.",
    "Performance obligations are satisfied either over time or at a point in time based on the transfer of control to the customer.",
))
def test_revenue_recognition_and_customer_delivery_terms_are_business_mechanisms(text):
    fact = detect_reading_business_fact(text)
    assert source_purpose(text) not in NON_OPERATING_PURPOSES
    assert fact.eligible
    assert "business_revenue_recognition" in fact.reasons
    assert _admitted(unit(text), {"section_role": "unknown"}, "background", fact=fact)[0]


@pytest.mark.parametrize("text", (
    "本集团对履约义务与合同负债采用上述会计政策。",
    "收入确认政策涉及履约义务和合同负债。",
    "Performance obligations and contract liabilities are described in the accounting policy.",
    "本集团的收入确认会计政策涵盖履约义务及客户控制权。",
    "Accounting policy for revenue recognition, performance obligations and customer control.",
))
def test_revenue_recognition_nouns_without_a_customer_delivery_rule_remain_policy(text):
    fact = detect_reading_business_fact(text)
    assert source_purpose(text) == "accounting_policy"
    assert not fact.eligible
    assert "business_revenue_recognition" not in fact.reasons


def test_revenue_recognition_mechanism_reaches_public_selector_without_admitting_general_policy():
    mechanism = "本集团在履行合同中的履约义务、客户取得商品或服务控制权时确认收入。"
    timing = "符合条件的履约义务在某一时段内按履约进度确认收入，否则在某一时点确认收入。"
    prepayment = "本集团向客户预收服务款确认为负债，待履行相关履约义务后转为收入。"
    policy = POLICIES[0]
    units = tuple(unit(text, index) for index, text in enumerate((mechanism, timing, prepayment, policy)))
    digest = sha256(b"revenue-recognition-mechanism").hexdigest()
    parsed = DocumentStructure(source_id_for_sha256(digest), digest, "zh", units,
        page_count=1, pages_read=1, mime_type="text/plain")
    result = select_narrative_evidence(parsed, title="Annual report", existing_kind="annual_report",
        selector_version="0.9.0")
    sent = [span.raw_text for span in result.evidence_spans]
    assert mechanism in sent
    assert timing in sent
    assert prepayment in sent
    assert policy not in sent


_INDEPENDENT_CASES = json.loads((Path(__file__).resolve().parents[2] /
    "fixtures/narrative_source_purpose_cases.json").read_text(encoding="utf-8"))["cases"]


@pytest.mark.parametrize("case", _INDEPENDENT_CASES, ids=lambda case: case["id"])
def test_independently_found_purpose_boundaries(case):
    purpose = source_purpose(case["text"])
    assert (purpose in NON_OPERATING_PURPOSES) is case["expected_nonoperating"]
    if case["expected_nonoperating"]:
        assert not _admitted(unit(case["text"]), {"section_role": "business"}, "background")[0]



def test_public_selector_retains_factory_event_inside_accounting_note():
    text="The company acquired a factory. Right-of-use assets were recognized at carrying value."
    digest=sha256(b"neutral-purpose-source").hexdigest()
    parsed=DocumentStructure(source_id_for_sha256(digest), digest, "en", (unit(text),),
        page_count=1, pages_read=1, mime_type="text/plain")
    result=select_narrative_evidence(parsed,title="Annual report",existing_kind="annual_report",selector_version="0.9.0")
    assert text in [span.raw_text for span in result.evidence_spans]


def test_standard_government_subsidy_exception_is_not_a_current_operating_state():
    assert source_purpose(STATUTORY_SUBSIDY_EXCEPTION) == "accounting_policy"
    fact = detect_reading_business_fact(STATUTORY_SUBSIDY_EXCEPTION)
    assert not fact.eligible


def test_standard_government_subsidy_exception_does_not_become_a_source_card():
    digest = sha256(b"quarterly-template-source").hexdigest()
    parsed = DocumentStructure(source_id_for_sha256(digest), digest, "zh",
        (unit(STATUTORY_SUBSIDY_EXCEPTION),), page_count=1, pages_read=1,
        mime_type="text/plain")
    result = select_narrative_evidence(parsed, title="季度报告",
        existing_kind="quarterly_report", selector_version="0.9.0")
    assert not result.evidence_spans


def test_real_operating_and_subsidy_events_are_not_treated_as_statutory_template():
    actual = "公司新增软件产品已经交付客户，客户完成生产验证。"
    assert source_purpose(actual) not in NON_OPERATING_PURPOSES
    assert detect_reading_business_fact(actual).eligible


@pytest.mark.parametrize("prefix", ["1.", "12.", "a.", "(B)."])
@pytest.mark.parametrize("label", ["新产品交付情况 □适用√不适用", "新產品交付情況 □適用√不適用"])
def test_only_explicit_heading_can_override_observed_form_response(prefix, label):
    from company_wiki.document_understanding.observation_adapter import _heading_level
    from company_wiki.document_understanding.structure.contract import ObservationUnit
    from company_wiki.document_understanding.structure.layout import is_heading
    text=prefix + label
    assert _heading_level(text,{}) is None
    assert _heading_level(text,{"heading_level":2}) == 2
    wire={"unit_id":"field","ordinal":0,"locator":"source:field","text":text,
          "kind":"paragraph","page":1,"layout":{},"hints":{}}
    assert not is_heading(ObservationUnit(wire,0))
    wire["hints"]={"heading_level":2,"heading_level_source":"native"}
    assert is_heading(ObservationUnit(wire,0))
