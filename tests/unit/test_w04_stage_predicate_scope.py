"""Stage polarity belongs to the predicate, not every word in its clause."""

from __future__ import annotations

import pytest

from company_wiki.source_catalog.narrative_business_groups import (
    _commercialization_milestone,
    _operating_fact,
)
from company_wiki.source_catalog.narrative_evidence import _candidate_rules


@pytest.mark.parametrize("text", [
    "新型医疗设备未通过客户现场验证。",
    "新型系统没有获得客户重复订单。",
    "新型医疗设备并未完成客户现场验证。",
    "新型系统未取得客户追加订单。",
    "新型医疗设备没有顺利完成现场验证。",
    "新型医疗设备未能通过客户现场验证。",
    "新型医疗设备尚未完成客户现场验证。",
    "新型系统没有再次获得客户复购订单。",
    "新型设备已投入测试，但未通过客户认证。",
    "Our medical equipment has not passed customer validation.",
    "The platform has never received repeat orders.",
    "The equipment was not shipped to customers.",
])
def test_negated_stage_is_not_a_realized_milestone(text: str) -> None:
    assert not _commercialization_milestone(text)
    assert "new_product_commercialization_milestone" not in _operating_fact(
        text, _candidate_rules(selector_version="0.8.0")
    ).reasons


@pytest.mark.parametrize("text", [
    "没有缺陷的新型医疗设备已完成客户现场验证。",
    "新型系统未发现缺陷且已获得客户重复订单。",
    "新型医疗设备未发生故障且已经通过现场验证。",
    "新型平台尚未完成验证，但已交付首批客户。",
    "新型平台尚未完成验证但已交付首批客户。",
    "新型设备已付运至客户且没有通过现场验证。",
    "The platform has never failed validation and has received repeat orders.",
    "The platform has not passed validation but it has received repeat orders.",
    "Our new equipment without defects has successfully passed customer qualification.",
])
def test_unrelated_negation_does_not_erase_a_realized_stage(text: str) -> None:
    assert _commercialization_milestone(text)


@pytest.mark.parametrize("text", [
    "若设备已通过客户验证，按合同结算货款。",
    "新型医疗设备计划通过客户现场验证。",
    "The product will be shipped after validation.",
])
def test_conditional_or_future_stage_remains_unrealized(text: str) -> None:
    assert not _commercialization_milestone(text)


@pytest.mark.parametrize("text", [
    "公司于2022年推出了新型设备，目前已交付客户进行生产验证，并取得了重复订单。",
    "公司此前推出了新型设备，目前已交付首批客户。",
    "公司开发了一种系统，目前已完成客户现场验证。",
    "公司已完成新型系统开发，并取得了客户重复订单。",
    "公司于2022年推出了一种设备，并已获得客户重复订单。",
    "公司推出新型产品，并已经取得客户追加订单。",
    "旧系统此前尚未上市，目前已完成现场认证。",
    "平台发布已两年，目前已顺利通过客户验证。",
    "Products were launched in 2022, and have now been delivered to customers.",
])
def test_current_elided_subject_stage_survives_historical_launch(text):
    assert _commercialization_milestone(text)
    assert "new_product_commercialization_milestone" in _operating_fact(
        text, _candidate_rules(selector_version="0.8.0")
    ).reasons


@pytest.mark.parametrize("text", [
    "公司于2022年推出了一种设备，目前未交付客户。",
    "公司推出了系统，目前计划交付客户。",
    "公司推出了系统，并取得了合同付款。",
    "公司推出了系统，目前已交付保证金给客户。",
    "公司推出了系统，已将保证金交付给客户。",
    "公司推出了系统。并取得了客户重复订单。",
    "公司推出了系统；目前已完成客户验证。",
    "公司推出了系统，如果已完成客户验证则可结算。",
    "公司推出了系统，并没有取得客户重复订单。",
    "Products were launched in 2022, and will be delivered to customers.",
])
def test_elided_reference_does_not_cross_polarity_money_or_sentence_boundary(text):
    assert not _commercialization_milestone(text)
