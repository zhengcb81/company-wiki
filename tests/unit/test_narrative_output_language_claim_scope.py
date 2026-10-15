"""Each claim's actual citations own its language; no cross-claim permission.

The saved-HK fixture is observation only. Alias-only duck values certify no
source identity, native locator, summary contract or historical canonical set.
"""
from collections import Counter
import hashlib
from pathlib import Path
from types import SimpleNamespace

import pytest

from company_wiki.automation import narrative_output_language as observer


EN_SOURCE = (
    "The new reactor completed customer validation and received repeat orders during the quarter. "
    "The engineering team reduced installation time while customers continued to qualify additional production lines."
)
EN_OUTPUT = (
    "Customers validated the new reactor and placed repeat orders this quarter. "
    "Installation time declined while qualification continued on additional production lines."
)
ZH_SOURCE = "本季度公司新一代设备完成客户验证并获得重复订单，安装团队缩短了产线调试时间。公司同时继续开发下一代工艺设备，尚未披露新产品的具体收入金额。"
ZH_OUTPUT = "新一代设备本季度通过客户验证并取得重复订单，安装与调试时间缩短。下一代工艺设备仍在开发中，公司没有披露该新产品的收入规模。"
ES_OUTPUT = (
    "Los clientes validaron el nuevo reactor y realizaron pedidos repetidos durante el trimestre. "
    "El equipo redujo el tiempo de instalación y continuó las pruebas en otras líneas de producción."
)

# Exact saved HK c4 + e6 and c13 + e25/e27 from the immutable actual request/final.
HK_C4 = "TOP TOY自2020年在中国内地扩展门店网络，并自2024年起进入海外市场；截至2024年12月31日共276家门店，其中272家位于中国内地。"
HK_E6 = (
    "We have expanded our TOP TOY store network in mainland China \nsince 2020. TOP TOY has also begun to expand to overseas \nmarkets since 2024. This strategic move aligns with the Company’s \nplan to expand globally and strengthen its brand presence. As of \nDecember 31, 2024, we had a total of 276 TOP TOY stores, 272 \nof which located in mainland China. The following table shows the \nnumber of TOP TOY stores in mainland China and overseas as of \nthe dates presented:"
)
HK_C13 = "公司采用直营、名创合伙人及代理等灵活门店运营模式拓展全球网络；海外加盟商有时会在名创合伙人与代理模式之间转换。"
HK_E25 = "我們在拓展全球的門店網絡的同時，根據市場的增\n長潛力、當地法規和其他因素，採用了一系列靈活\n的門店運營模式，包括直營、名創合夥人模式和代\n理模式。考慮到當地不斷變化的監管要求、市場條\n件及彼等的營運需求，我們的海外加盟商有時會從\n名創合夥人轉變為代理商，反之亦然。"
HK_E27 = "We have adopted flexible store operation models, including direct \noperation, MINISO Retail Partner model and distributor model as \nwe expand our global footprints, depending on the growth potential, \nlocal regulation and other factors in the markets. In consideration of \nthe evolving local regulatory requirements, market conditions and \ntheir operational needs, our overseas franchisees may sometimes \nconvert from a MINISO Retail Partner to a distributor, or vice versa."


@pytest.fixture(autouse=True)
def preserve_production_config():
    root = Path(__file__).resolve().parents[2]
    paths = (root / "config.yaml", root / "config/source_catalog.yaml")
    before = {p: (hashlib.sha256(p.read_bytes()).hexdigest(), p.stat().st_size, p.stat().st_mtime_ns) for p in paths}
    yield
    assert {p: (hashlib.sha256(p.read_bytes()).hexdigest(), p.stat().st_size, p.stat().st_mtime_ns) for p in paths} == before


def observe(rows, claims):
    spans = tuple(SimpleNamespace(span_id=alias, raw_text=text) for alias, text in rows.items())
    adapted = tuple(SimpleNamespace(text=text, evidence_ids=tuple(cites)) for text, cites in claims)
    return observer.observe_summary_language(adapted, evidence_spans=spans)


def test_saved_hk_long_english_translation_is_not_excused_by_another_chinese_lane():
    result = observe({"e6": HK_E6, "e25": HK_E25, "e27": HK_E27},
                     [(HK_C4, ["e6"]), (HK_C13, ["e25", "e27"])])
    assert (result.state, result.output_family, result.source_families, result.prose_claims) == (
        "different", "zh", ("en", "zh"), 2)


@pytest.mark.parametrize("reverse", [False, True])
def test_strong_local_difference_beats_other_claim_compatibility_for_any_language(reverse):
    claims = [(ES_OUTPUT, ["english"]), (ES_OUTPUT, ["spanish"])]
    if reverse:
        claims.reverse()
    result = observe({"english": EN_SOURCE, "spanish": ES_OUTPUT}, claims)
    assert (result.state, result.output_family, result.source_families) == ("different", "es", ("en", "es"))


def test_independent_native_english_and_chinese_claims_keep_each_own_language():
    result = observe({"english": EN_SOURCE, "chinese": ZH_SOURCE},
                     [(EN_OUTPUT, ["english"]), (ZH_OUTPUT, ["chinese"])])
    assert (result.state, result.output_family, result.source_families) == ("compatible", None, ("en", "zh"))


def test_strong_difference_is_not_hidden_by_a_different_native_output_language():
    result = observe({"english": EN_SOURCE}, [(EN_OUTPUT, ["english"]), (ES_OUTPUT, ["english"])])
    assert (result.state, result.output_family, result.source_families) == ("different", None, ("en",))


def test_short_translated_prose_remains_diagnostic_beside_native_chinese():
    short = "截至2024年12月31日，名创优品门店总数超过7,500家，其中中国内地近4,400家、海外超3,100家。"
    result = observe({"english": EN_SOURCE, "chinese": ZH_SOURCE},
                     [(short, ["english"]), (ZH_OUTPUT, ["chinese"])])
    assert (result.state, result.output_family, result.source_families) == ("uncertain", "zh", ("en", "zh"))


def test_unobservable_short_source_cannot_borrow_another_claims_source_language():
    result = observe({"short": "Item 1", "english": EN_SOURCE},
                     [(ES_OUTPUT, ["short"]), (EN_OUTPUT, ["english"])])
    assert result.state == "uncertain"


def test_strong_difference_remains_visible_beside_unobservable_claim():
    result = observe({"short": "Item 1", "english": EN_SOURCE},
                     [(ES_OUTPUT, ["short"]), (ES_OUTPUT, ["english"])])
    assert (result.state, result.source_families) == ("different", ("en",))


def test_actual_bilingual_citation_can_support_its_own_chinese_prose():
    result = observe({"bilingual": EN_SOURCE + "\n" + ZH_SOURCE}, [(ZH_OUTPUT, ["bilingual"])])
    assert (result.state, result.output_family, result.source_families) == ("compatible", "zh", ("en", "zh"))


def test_short_brand_and_numbers_are_not_converted_to_language_violations():
    result = observe({"english": EN_SOURCE}, [("TOP TOY 276", ["english"])])
    assert (result.state, result.output_family, result.prose_claims) == ("uncertain", None, 0)


def test_retained_foreign_quotation_in_its_actual_source_is_not_a_translation():
    quotation = "La nueva línea comenzará a operar el próximo año."
    source = EN_SOURCE + " Management stated: ‘" + quotation + "’"
    output = "Management retained the original quotation: ‘" + quotation + "’ " + EN_OUTPUT
    result = observe({"english": source}, [(output, ["english"])])
    assert (result.state, result.output_family) == ("compatible", "en")


def test_foreign_quote_in_another_claims_source_is_not_silently_erased():
    quotation = "La nueva línea comenzará a operar el próximo año."
    output = "‘" + ES_OUTPUT + "’ " + EN_OUTPUT
    result = observe({"english": EN_SOURCE, "spanish": quotation},
                     [(output, ["english"])])
    assert (result.state, result.output_family, result.source_families) == ("uncertain", None, ("en",))


def test_repeated_twenty_claims_reuse_one_finite_classification_pass(monkeypatch):
    real = observer._get_identifier()
    calls = Counter()

    def classify(text):
        calls[text] += 1
        return real.classify(text)

    monkeypatch.setattr(observer, "_get_identifier", lambda: SimpleNamespace(classify=classify))
    result = observe({"english": EN_SOURCE}, [(EN_OUTPUT, ["english"])] * 20)
    assert (result.state, result.prose_claims) == ("compatible", 20)
    assert calls and max(calls.values()) == 1
    assert len(calls) <= 8
