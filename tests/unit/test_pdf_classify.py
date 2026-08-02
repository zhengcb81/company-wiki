#!/usr/bin/env python3
"""
test_pdf_classify.py — PDF 分类器测试

测试 classify_pdf_v2 的准确率和边界情况。
"""

import sys
import os
from pathlib import Path

# 添加项目根目录和 scripts 目录到路径
project_root = str(Path(__file__).parent.parent.parent)
scripts_dir = os.path.join(project_root, "scripts")
sys.path.insert(0, project_root)
sys.path.insert(0, scripts_dir)

try:
    from scripts.pdf_extract_v3 import classify_pdf_v2
except ImportError:
    from pdf_extract_v3 import classify_pdf_v2


# ── 测试用例定义 ──────────────────────────

# 格式：(文件名, 期望的 doc_type, 期望的 period, 是否需要人工审核)
TEST_CASES = [
    # ==================== 年报 ====================
    ("三环集团：2021年年度报告.pdf", "annual_report", "2021-12-31", False),
    ("三环集团：2022年年度报告.pdf", "annual_report", "2022-12-31", False),
    ("东方电缆：2016年年度报告.pdf", "annual_report", "2016-12-31", False),
    ("东方电缆：东方电缆2024年年度报告.pdf", "annual_report", "2024-12-31", False),
    ("中大力德：2023年年度报告.pdf", "annual_report", "2023-12-31", False),
    # ==================== 半年报（关键测试！）====================
    # 这些必须正确识别为 semi_annual，不能误判为 annual
    ("三环集团：2021年半年度报告.pdf", "semi_annual_report", "2021-06-30", False),
    ("三环集团：2022年半年度报告.pdf", "semi_annual_report", "2022-06-30", False),
    ("三环集团：2023年半年度报告.pdf", "semi_annual_report", "2023-06-30", False),
    ("三环集团：2024年半年度报告.pdf", "semi_annual_report", "2024-06-30", False),
    ("三环集团：2025年半年度报告.pdf", "semi_annual_report", "2025-06-30", False),
    ("东方电缆：2017年半年度报告.pdf", "semi_annual_report", "2017-06-30", False),
    ("东方电缆：2018年半年度报告.pdf", "semi_annual_report", "2018-06-30", False),
    (
        "东方电缆：东方电缆2021年半年度报告.pdf",
        "semi_annual_report",
        "2021-06-30",
        False,
    ),
    ("中大力德：2024年半年度报告.pdf", "semi_annual_report", "2024-06-30", False),
    (
        "上峰水泥：铜城集团2002年半年度报告.pdf",
        "semi_annual_report",
        "2002-06-30",
        False,
    ),
    # ==================== 季报 ====================
    # Q1
    ("三环集团：2022年一季度报告.pdf", "quarterly_report", "2022-03-31", False),
    ("三环集团：2023年一季度报告.pdf", "quarterly_report", "2023-03-31", False),
    ("三环集团：2024年一季度报告.pdf", "quarterly_report", "2024-03-31", False),
    ("三环集团：2025年一季度报告.pdf", "quarterly_report", "2025-03-31", False),
    ("三环集团：2026年一季度报告.pdf", "quarterly_report", "2026-03-31", False),
    ("东方电缆：2017年第一季度报告.pdf", "quarterly_report", "2017-03-31", False),
    ("东方电缆：2018年第一季度报告.pdf", "quarterly_report", "2018-03-31", False),
    (
        "上峰水泥：铜城集团2003年第一季度报告.pdf",
        "quarterly_report",
        "2003-03-31",
        False,
    ),
    # Q3
    ("三环集团：2021年第三季度报告.pdf", "quarterly_report", "2021-09-30", False),
    ("三环集团：2022年三季度报告.pdf", "quarterly_report", "2022-09-30", False),
    ("三环集团：2023年三季度报告.pdf", "quarterly_report", "2023-09-30", False),
    ("三环集团：2024年三季度报告.pdf", "quarterly_report", "2024-09-30", False),
    ("三环集团：2025年三季度报告.pdf", "quarterly_report", "2025-09-30", False),
    ("东方电缆：2016年第三季度报告.pdf", "quarterly_report", "2016-09-30", False),
    ("东方电缆：2017年第三季度报告.pdf", "quarterly_report", "2017-09-30", False),
    ("东方电缆：2019年第三季度报告.pdf", "quarterly_report", "2019-09-30", False),
    # ==================== 招股说明书 ====================
    (
        "三环集团：首次公开发行股票并在创业板上市招股说明书.pdf",
        "prospectus",
        None,
        False,
    ),
    ("东方电缆：首次公开发行股票招股说明书.pdf", "prospectus", None, False),
    ("东方雨虹：首次公开发行股票招股说明书.pdf", "prospectus", None, False),
    ("中大力德：首次公开发行股票招股说明书.pdf", "prospectus", None, False),
    (
        "中密控股：首次公开发行股票并在创业板上市招股说明书.pdf",
        "prospectus",
        None,
        False,
    ),
    (
        "中微公司：首次公开发行股票并在科创板上市招股说明书.pdf",
        "prospectus",
        None,
        False,
    ),
    ("中微公司：中微半导体招股说明书.pdf", "prospectus", None, False),
    ("中科曙光：首次公开发行股票招股说明书.pdf", "prospectus", None, False),
    # ==================== 投资者关系 ====================
    (
        "三环集团：2021年5月13日投资者关系活动记录表.pdf",
        "investor_relations",
        None,
        False,
    ),
    (
        "三环集团：2022年5月17日投资者关系活动记录表.pdf",
        "investor_relations",
        None,
        False,
    ),
    (
        "三环集团：2023年5月12日投资者关系活动记录表.pdf",
        "investor_relations",
        None,
        False,
    ),
    (
        "三环集团：2024年5月16日投资者关系活动记录表.pdf",
        "investor_relations",
        None,
        False,
    ),
    (
        "三环集团：2024年9月2日-9月20日投资者关系活动记录表.pdf",
        "investor_relations",
        None,
        False,
    ),
    (
        "三环集团：2025年5月19日投资者关系活动记录表.pdf",
        "investor_relations",
        None,
        False,
    ),
    (
        "三环集团：2026年4月16日投资者关系活动记录表.pdf",
        "investor_relations",
        None,
        False,
    ),
    (
        "上峰水泥：000672上峰水泥投资者关系管理信息20240427.pdf",
        "investor_relations",
        None,
        False,
    ),
    # ==================== 研报 ====================
    (
        "20211214-中泰证券-互联网行业品牌出海系列深度·SheIn篇：疾如风，徐如林.pdf",
        "research_report",
        None,
        False,
    ),
    (
        "20221009-招商证券-可选消费行业SHEIN深度报告：供应链&流量为核，快时尚跨境巨头厚积薄发.pdf",
        "research_report",
        None,
        False,
    ),
    (
        "20191025-长城证券-七一二-603712-公司深度报告：产品全兵种覆盖，航空无线通信龙头.pdf",
        "research_report",
        None,
        False,
    ),
    (
        "20210826-华创证券-七一二-603712-深度研究报告：老牌军企内生突破，军用超短波通信龙头享黄金大列装时代红利.pdf",
        "research_report",
        None,
        False,
    ),
    (
        "20190910-方正证券-万华化学-600309-深度报告之三：万华BC公司能否兑现业绩承诺？.pdf",
        "research_report",
        None,
        False,
    ),
    # ==================== 公告 ====================
    (
        "东方电缆：关于首次公开发行A股网下发行配售结果及网上中签率公告之更正公告.pdf",
        "announcement",
        None,
        False,
    ),
    ("东方电缆：首次公开发行A股投资风险特别公告.pdf", "announcement", None, False),
    ("东方雨虹：第三届监事会第五次会议决议公告.pdf", "announcement", None, False),
    ("东方雨虹：首次公开发行股票上市公告书.pdf", "announcement", None, False),
    # ==================== 摘要（必须跳过）====================
    ("年度报告摘要.pdf", "abstract", None, True),
    ("招股说明书摘要.pdf", "abstract", None, True),
    (
        "三环集团：发行人控股股东对招股说明书的确认意见.pdf",
        "prospectus",
        None,
        False,
    ),  # 注意：这不是摘要
]


# ── 测试函数 ──────────────────────────────


def test_classify_accuracy():
    """测试分类准确率"""
    total = len(TEST_CASES)
    passed = 0
    failed_cases = []

    for filename, expected_type, expected_period, expected_needs_review in TEST_CASES:
        result = classify_pdf_v2(filename)

        # 检查类型
        type_ok = result["doc_type"] == expected_type

        # 检查周期（如果有期望值）
        period_ok = True
        if expected_period is not None:
            period_ok = result.get("period") == expected_period

        # 检查跳过标记
        skip_ok = result.get("skip", False) == expected_needs_review

        if type_ok and period_ok and skip_ok:
            passed += 1
        else:
            failed_cases.append(
                {
                    "filename": filename,
                    "expected": {
                        "type": expected_type,
                        "period": expected_period,
                        "skip": expected_needs_review,
                    },
                    "actual": {
                        "type": result["doc_type"],
                        "period": result.get("period"),
                        "skip": result.get("skip", False),
                    },
                    "result": result,
                }
            )

    accuracy = passed / total * 100

    print(f"\n{'=' * 60}")
    print("分类准确率测试结果")
    print(f"{'=' * 60}")
    print(f"总测试数: {total}")
    print(f"通过: {passed}")
    print(f"失败: {len(failed_cases)}")
    print(f"准确率: {accuracy:.1f}%")
    print("目标: >95%")
    print(f"{'=' * 60}")

    if failed_cases:
        print("\n失败案例:")
        for case in failed_cases:
            print(f"\n  文件: {case['filename']}")
            print(f"  期望: {case['expected']}")
            print(f"  实际: {case['actual']}")

    assert accuracy >= 95, f"分类准确率 {accuracy:.1f}% 低于 95%；失败案例: {failed_cases}"


def test_semi_annual_not_annual():
    """
    关键测试：半年报不能被误判为年报
    这是最容易出错的边界情况
    """
    semi_annual_cases = [
        ("三环集团：2021年半年度报告.pdf", "semi_annual_report"),
        ("三环集团：2022年半年度报告.pdf", "semi_annual_report"),
        ("三环集团：2023年半年度报告.pdf", "semi_annual_report"),
        ("三环集团：2024年半年度报告.pdf", "semi_annual_report"),
        ("东方电缆：2017年半年度报告.pdf", "semi_annual_report"),
        ("东方电缆：2018年半年度报告.pdf", "semi_annual_report"),
        ("东方电缆：东方电缆2021年半年度报告.pdf", "semi_annual_report"),
        ("中大力德：2024年半年度报告.pdf", "semi_annual_report"),
    ]

    passed = 0
    for filename, expected_type in semi_annual_cases:
        result = classify_pdf_v2(filename)
        if result["doc_type"] == expected_type:
            passed += 1
        else:
            print(
                f"  FAIL: {filename} → {result['doc_type']} (expected {expected_type})"
            )

    print(f"\n半年报/年报区分测试: {passed}/{len(semi_annual_cases)} 通过")
    assert passed == len(semi_annual_cases)


def test_abstract_skip():
    """测试摘要是否正确跳过"""
    abstract_cases = [
        ("年度报告摘要.pdf", True),
        ("招股说明书摘要.pdf", True),
        ("某公司2024年年度报告.pdf", False),  # 不是摘要
        ("某公司2024年半年度报告.pdf", False),  # 不是摘要
    ]

    passed = 0
    for filename, should_skip in abstract_cases:
        result = classify_pdf_v2(filename)
        if result.get("skip", False) == should_skip:
            passed += 1
        else:
            print(
                f"  FAIL: {filename} → skip={result.get('skip', False)} (expected {should_skip})"
            )

    print(f"\n摘要跳过测试: {passed}/{len(abstract_cases)} 通过")
    assert passed == len(abstract_cases)


def test_confidence_levels():
    """测试置信度是否合理"""
    # 高置信度案例
    high_confidence_cases = [
        "三环集团：2024年年度报告.pdf",
        "东方电缆：2017年半年度报告.pdf",
        "三环集团：2022年一季度报告.pdf",
    ]

    for filename in high_confidence_cases:
        result = classify_pdf_v2(filename)
        confidence = result.get("confidence", 0)
        assert confidence >= 0.9, (
            f"Expected high confidence (>=0.9) for {filename}, got {confidence}"
        )

    print("\n置信度测试: 通过")


# ── 主函数 ──────────────────────────────

if __name__ == "__main__":
    import pytest

    raise SystemExit(pytest.main([__file__, "-v"]))
