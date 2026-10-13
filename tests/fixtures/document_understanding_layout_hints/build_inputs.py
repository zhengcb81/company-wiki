"""Frozen du2-layout-input/1 synthetic fixtures for the DU2-LAYOUT lane.

This builder is test-side tooling only: it writes the JSON files under
``inputs/`` exactly once per invocation so the wire examples stay reviewable
and reproducible.  It is not product code and never opens a real original.

Run from the repository root:

    python -B -X utf8 tests/fixtures/document_understanding_layout_hints/build_inputs.py
"""

from __future__ import annotations

import json
from pathlib import Path

OUT = Path(__file__).resolve().parent / "inputs"
PAGE_W = 595.0
PAGE_H = 842.0


def unit(n: int, text: str, bbox, size=10.0, weight="regular", kind="paragraph", hints=None):
    return {
        "unit_id": f"u{n}",
        "ordinal": n - 1,
        "locator": f"synthetic-locator-u{n}",
        "text": text,
        "bbox": list(bbox) if bbox is not None else None,
        "font_size": size,
        "font_weight": weight,
        "kind": kind,
        "upstream_hints": hints or {},
    }


def page(number: int, units, width=PAGE_W, height=PAGE_H):
    return {"page": number, "width": width, "height": height, "units": units}


def case(name: str, pages, note: str):
    doc = {
        "schema_version": "du2-layout-input/1",
        "source_ref": {"source_id": f"synthetic-{name}", "source_sha256": None},
        "coverage": {"opaque_pages": [], "deferred_pages": []},
        "pages": pages,
    }
    OUT.mkdir(parents=True, exist_ok=True)
    path = OUT / f"{name}.json"
    path.write_text(json.dumps(doc, ensure_ascii=False, indent=1) + "\n", encoding="utf8")
    print(f"wrote {path.name}: {sum(len(p['units']) for p in pages)} units ({note})")


def build_all() -> None:
    # 1. unnumbered heading vs ordinary short sentences -----------------
    case(
        "heading_unnumbered_vs_sentence",
        [
            page(
                1,
                [
                    unit(1, "业务发展概况", (70, 100, 210, 120), size=14.0, weight="bold", kind="heading"),
                    unit(2, "公司持续优化产品结构，加强供应链管理。", (70, 140, 360, 154)),
                    unit(3, "研发投入保持稳定增长，客户结构进一步改善。", (70, 162, 380, 176)),
                    unit(4, "主要产品与服务", (70, 210, 190, 226), size=12.0, kind="heading"),
                    unit(5, "公司主要产品包括智能装备与精密工具两类。", (70, 240, 370, 254)),
                ],
            )
        ],
        "无编号标题 vs 普通短句",
    )

    # 2. a year line is not a heading ----------------------------------
    case(
        "year_not_heading",
        [
            page(
                1,
                [
                    unit(1, "经营情况讨论", (70, 100, 190, 120), size=14.0, weight="bold", kind="heading"),
                    unit(2, "2023年", (70, 150, 120, 168), size=13.0, weight="bold"),
                    unit(3, "2024", (70, 190, 110, 208), size=13.0, weight="bold"),
                    unit(4, "报告期内公司经营规模稳步提升，市场份额保持稳定。", (70, 230, 420, 244)),
                    unit(5, "2023年12月31日", (70, 270, 180, 284)),
                ],
            )
        ],
        "年份不是标题",
    )

    # 3. full-width running header must not split columns ---------------
    case(
        "cross_column_header",
        [
            page(
                1,
                [
                    unit(1, "示例股份有限公司 2024 年年度报告", (70, 30, 525, 44), size=8.0, kind="header"),
                    unit(3, "Left column paragraph one discusses operations.", (70, 120, 290, 134), size=9.0),
                    unit(4, "右栏第一段叙述经营情况与订单变化。", (310, 120, 525, 134), size=9.0),
                    unit(5, "Left column paragraph two covers capacity.", (70, 142, 290, 156), size=9.0),
                    unit(6, "右栏第二段覆盖产能建设进度。", (310, 142, 525, 156), size=9.0),
                    unit(7, "Left column paragraph three adds risks.", (70, 164, 280, 178), size=9.0),
                    unit(8, "右栏第三段补充风险提示。", (310, 164, 510, 178), size=9.0),
                    unit(9, "第 1 页 共 10 页", (70, 800, 525, 812), size=8.0, kind="footer"),
                ],
            ),
            page(
                2,
                [
                    unit(10, "示例股份有限公司 2024 年年度报告", (70, 30, 525, 44), size=8.0, kind="header"),
                    unit(11, "Left column paragraph four discusses outlook.", (70, 120, 290, 134), size=9.0),
                    unit(12, "右栏第四段讨论后续展望。", (310, 120, 525, 134), size=9.0),
                    unit(13, "第 2 页 共 10 页", (70, 800, 525, 812), size=8.0, kind="footer"),
                ],
            ),
        ],
        "跨栏页眉不拆栏",
    )

    # 4. bilingual two-column body plus one full-width table -------------
    case(
        "bilingual_two_column",
        [
            page(
                1,
                [
                    unit(1, "We are a global value retailer of lifestyle products.", (70, 100, 300, 114), size=9.0),
                    unit(2, "我們是一家提供潮流生活家居产品的全球价值零售商。", (320, 100, 550, 114), size=9.0),
                    unit(3, "We operate stores across mainland China and overseas.", (70, 122, 300, 136), size=9.0),
                    unit(4, "我们在中国内地和海外市场经营门店网络。", (320, 122, 550, 136), size=9.0),
                    unit(5, "Store network expanded during the reporting period.", (70, 144, 290, 158), size=9.0),
                    unit(6, "报告期内门店网络持续扩张。", (320, 144, 540, 158), size=9.0),
                    unit(7, "表1 门店数量", (70, 190, 150, 204), size=10.0, weight="bold", kind="caption"),
                    unit(8, "地区", (70, 215, 110, 228), size=9.0, weight="bold"),
                    unit(9, "2023", (380, 215, 420, 228), size=9.0, weight="bold"),
                    unit(10, "2024", (480, 215, 520, 228), size=9.0, weight="bold"),
                    unit(11, "中国内地", (70, 238, 130, 251), size=9.0),
                    unit(12, "3,926", (380, 238, 420, 251), size=9.0),
                    unit(13, "4,386", (480, 238, 520, 251), size=9.0),
                    unit(14, "海外", (70, 260, 110, 273), size=9.0),
                    unit(15, "2,487", (380, 260, 420, 273), size=9.0),
                    unit(16, "3,118", (480, 260, 520, 273), size=9.0),
                ],
            )
        ],
        "左右中英栏 + 跨栏表",
    )

    # 5. table with an isolated numeric-only row ------------------------
    case(
        "table_isolated_numeric_row",
        [
            page(
                1,
                [
                    unit(1, "表2 主要经营指标", (70, 120, 180, 134), size=10.0, weight="bold", kind="caption"),
                    unit(2, "指标", (70, 150, 110, 163), size=9.0, weight="bold"),
                    unit(3, "2023", (380, 150, 420, 163), size=9.0, weight="bold"),
                    unit(4, "2024", (480, 150, 520, 163), size=9.0, weight="bold"),
                    unit(5, "门店数量", (70, 172, 130, 185), size=9.0),
                    unit(6, "6,413", (380, 172, 420, 185), size=9.0),
                    unit(7, "7,504", (480, 172, 520, 185), size=9.0),
                    unit(8, "3,118", (380, 194, 420, 207), size=9.0),
                    unit(9, "4,386", (480, 194, 520, 207), size=9.0),
                    unit(10, "营业收入", (70, 216, 130, 229), size=9.0),
                    unit(11, "114.7", (380, 216, 420, 229), size=9.0),
                    unit(12, "139.1", (480, 216, 520, 229), size=9.0),
                ],
            )
        ],
        "表格数字孤立行",
    )

    # 6. header / period / unit line / footnote around one table ---------
    case(
        "table_header_period_unit_footnote",
        [
            page(
                1,
                [
                    unit(1, "表1 门店数量分布", (70, 110, 180, 124), size=11.0, weight="bold", kind="caption"),
                    unit(2, "截至2024年12月31日", (380, 130, 520, 142), size=9.0),
                    unit(3, "单位：家", (455, 150, 520, 162), size=9.0),
                    unit(4, "地区", (70, 175, 110, 188), size=9.0, weight="bold"),
                    unit(5, "2023年", (370, 175, 430, 188), size=9.0, weight="bold"),
                    unit(6, "2024年", (470, 175, 530, 188), size=9.0, weight="bold"),
                    unit(7, "中国内地", (70, 198, 130, 211), size=9.0),
                    unit(8, "3,926", (380, 198, 425, 211), size=9.0),
                    unit(9, "4,386", (485, 198, 530, 211), size=9.0),
                    unit(10, "海外", (70, 220, 110, 233), size=9.0),
                    unit(11, "2,487", (380, 220, 425, 233), size=9.0),
                    unit(12, "3,118", (485, 220, 530, 233), size=9.0),
                    unit(13, "合计", (70, 242, 110, 255), size=9.0, weight="bold"),
                    unit(14, "6,413", (380, 242, 425, 255), size=9.0, weight="bold"),
                    unit(15, "7,504", (485, 242, 530, 255), size=9.0, weight="bold"),
                    unit(16, "注：数据来源于公司内部统计。", (70, 268, 270, 280), size=8.0, kind="footnote"),
                ],
            )
        ],
        "表头/期间/单位/脚注",
    )

    # 7. cross-page continued table with repeated header -----------------
    p1_units = [
        unit(1, "表2 项目投资明细", (70, 600, 180, 614), size=11.0, weight="bold", kind="caption"),
        unit(2, "单位：万元", (455, 620, 520, 632), size=9.0),
        unit(3, "序号", (80, 645, 120, 658), size=9.0, weight="bold"),
        unit(4, "项目名称", (180, 645, 240, 658), size=9.0, weight="bold"),
        unit(5, "金额", (350, 645, 390, 658), size=9.0, weight="bold"),
        unit(6, "占比", (470, 645, 510, 658), size=9.0, weight="bold"),
        unit(7, "1", (85, 670, 105, 683), size=9.0),
        unit(8, "智能制造项目", (175, 670, 265, 683), size=9.0),
        unit(9, "29,779.00", (330, 670, 395, 683), size=9.0),
        unit(10, "84.36%", (455, 670, 510, 683), size=9.0),
        unit(11, "2", (85, 695, 105, 708), size=9.0),
        unit(12, "技术中心项目", (175, 695, 265, 708), size=9.0),
        unit(13, "3,185.00", (335, 695, 395, 708), size=9.0),
        unit(14, "9.02%", (462, 695, 510, 708), size=9.0),
    ]
    p2_units = [
        unit(15, "序号", (80, 80, 120, 93), size=9.0, weight="bold"),
        unit(16, "项目名称", (180, 80, 240, 93), size=9.0, weight="bold"),
        unit(17, "金额", (350, 80, 390, 93), size=9.0, weight="bold"),
        unit(18, "占比", (470, 80, 510, 93), size=9.0, weight="bold"),
        unit(19, "3", (85, 105, 105, 118), size=9.0),
        unit(20, "补充流动资金", (175, 105, 265, 118), size=9.0),
        unit(21, "7,300.00", (335, 105, 395, 118), size=9.0),
        unit(22, "20.62%", (455, 105, 510, 118), size=9.0),
        unit(23, "4", (85, 130, 105, 143), size=9.0),
        unit(24, "预备费", (185, 130, 235, 143), size=9.0),
        unit(25, "189.00", (345, 130, 395, 143), size=9.0),
        unit(26, "0.53%", (462, 130, 510, 143), size=9.0),
        unit(27, "本节其余内容为项目可行性分析，与上表数据无关。", (70, 300, 500, 314), size=10.0),
    ]
    case(
        "cross_page_table_continuation",
        [page(1, p1_units), page(2, p2_units)],
        "跨页续表（重复表头）",
    )

    # 8. table on the next page is a NEW table, not a continuation -------
    p1_units = [
        unit(1, "表2 项目投资明细", (70, 600, 180, 614), size=11.0, weight="bold", kind="caption"),
        unit(2, "序号", (80, 645, 120, 658), size=9.0, weight="bold"),
        unit(3, "项目名称", (180, 645, 240, 658), size=9.0, weight="bold"),
        unit(4, "金额", (350, 645, 390, 658), size=9.0, weight="bold"),
        unit(5, "1", (85, 670, 105, 683), size=9.0),
        unit(6, "智能制造项目", (175, 670, 265, 683), size=9.0),
        unit(7, "29,779.00", (330, 670, 395, 683), size=9.0),
    ]
    p2_units = [
        unit(8, "表3 员工结构", (70, 60, 150, 74), size=11.0, weight="bold", kind="caption"),
        unit(9, "类别", (70, 95, 110, 108), size=9.0, weight="bold"),
        unit(10, "人数", (260, 95, 300, 108), size=9.0, weight="bold"),
        unit(11, "占比", (470, 95, 510, 108), size=9.0, weight="bold"),
        unit(12, "生产人员", (70, 120, 130, 133), size=9.0),
        unit(13, "1,200", (255, 120, 305, 133), size=9.0),
        unit(14, "60.0%", (455, 120, 510, 133), size=9.0),
        unit(15, "销售人员", (70, 145, 130, 158), size=9.0),
        unit(16, "800", (265, 145, 305, 158), size=9.0),
        unit(17, "40.0%", (455, 145, 510, 158), size=9.0),
    ]
    case(
        "cross_page_table_unrelated",
        [page(1, p1_units), page(2, p2_units)],
        "跨页但非续表",
    )

    # 9. bad geometry / missing font / empty page ------------------------
    case(
        "bad_geometry_missing_font_empty_page",
        [
            page(
                1,
                [
                    unit(1, "正常段落，几何与字体均完整。", (70, 100, 300, 114), size=10.0),
                    unit(2, "几何损坏的单元。", (500, 100, 100, 120), size=10.0),
                    unit(3, "缺几何单元", None, size=None),
                    unit(4, "第三阶段验证工作进展顺利。", (70, 160, 200, 174), size=None),
                ],
            ),
            page(2, []),
            page(
                3,
                [
                    unit(5, "产能建设进展", (70, 100, 180, 118), size=None, weight="bold", kind="heading"),
                ],
            ),
        ],
        "坏几何/缺字体/空页面",
    )

    # 10. two adjacent tables keep their own header/footnote -------------
    case(
        "adjacent_tables_isolated",
        [
            page(
                1,
                [
                    unit(1, "表1 收入构成", (70, 90, 150, 104), size=10.0, weight="bold", kind="caption"),
                    unit(2, "项目", (70, 115, 110, 128), size=9.0, weight="bold"),
                    unit(3, "金额", (350, 115, 390, 128), size=9.0, weight="bold"),
                    unit(4, "产品销售", (70, 138, 130, 151), size=9.0),
                    unit(5, "1,000.00", (330, 138, 395, 151), size=9.0),
                    unit(6, "服务收入", (70, 160, 130, 173), size=9.0),
                    unit(7, "500.00", (340, 160, 395, 173), size=9.0),
                    unit(8, "注：口径为合并报表。", (70, 185, 200, 197), size=8.0, kind="footnote"),
                    unit(9, "表2 成本构成", (70, 240, 150, 254), size=10.0, weight="bold", kind="caption"),
                    unit(10, "项目", (70, 265, 110, 278), size=9.0, weight="bold"),
                    unit(11, "成本", (350, 265, 390, 278), size=9.0, weight="bold"),
                    unit(12, "原材料", (70, 288, 130, 301), size=9.0),
                    unit(13, "1,000.00", (330, 288, 395, 301), size=9.0),
                    unit(14, "人工", (70, 310, 110, 323), size=9.0),
                    unit(15, "200.00", (340, 310, 395, 323), size=9.0),
                    unit(16, "注：数据为管理口径。", (70, 335, 200, 347), size=8.0, kind="footnote"),
                ],
            )
        ],
        "相邻无关表隔离",
    )

    # 11. identical amounts must not merge different items ---------------
    case(
        "same_amounts_different_items",
        [
            page(
                1,
                [
                    unit(1, "项目", (70, 90, 110, 103), size=9.0, weight="bold"),
                    unit(2, "2023", (350, 90, 390, 103), size=9.0, weight="bold"),
                    unit(3, "甲项目", (70, 112, 130, 125), size=9.0),
                    unit(4, "1,000.00", (330, 112, 395, 125), size=9.0),
                    unit(5, "乙项目", (70, 137, 130, 150), size=9.0),
                    unit(6, "1,000.00", (330, 137, 395, 150), size=9.0),
                    unit(7, "项目", (70, 190, 110, 203), size=9.0, weight="bold"),
                    unit(8, "2023", (350, 190, 390, 203), size=9.0, weight="bold"),
                    unit(9, "丙项目", (70, 212, 130, 225), size=9.0),
                    unit(10, "1,000.00", (330, 212, 395, 225), size=9.0),
                ],
            )
        ],
        "金额相同项目不同",
    )

    # 12. two languages, not sentence-aligned ----------------------------
    case(
        "bilingual_not_sentence_aligned",
        [
            page(
                1,
                [
                    unit(1, "English line one describes the store network.", (70, 100, 300, 114), size=9.0),
                    unit(2, "English line two covers overseas markets.", (70, 122, 300, 136), size=9.0),
                    unit(3, "English line three adds product mix.", (70, 144, 290, 158), size=9.0),
                    unit(4, "中文第一行描述门店网络与经营情况。", (320, 100, 550, 114), size=9.0),
                    unit(5, "中文第二行覆盖海外市场进展。", (320, 122, 550, 136), size=9.0),
                    unit(6, "中文第三行补充产品结构变化。", (320, 144, 550, 158), size=9.0),
                    unit(7, "中文第四行为管理层展望。", (320, 166, 540, 180), size=9.0),
                    unit(8, "中文第五行讨论渠道建设。", (320, 188, 540, 202), size=9.0),
                ],
            )
        ],
        "双语非逐句对应",
    )

    # 13. table without any header row -----------------------------------
    case(
        "table_without_header",
        [
            page(
                1,
                [
                    unit(1, "甲项目", (70, 100, 130, 113), size=9.0),
                    unit(2, "1,000.00", (330, 100, 395, 113), size=9.0),
                    unit(3, "乙项目", (70, 125, 130, 138), size=9.0),
                    unit(4, "2,000.00", (330, 125, 395, 138), size=9.0),
                    unit(5, "丙项目", (70, 150, 130, 163), size=9.0),
                    unit(6, "3,000.00", (330, 150, 395, 163), size=9.0),
                ],
            )
        ],
        "表格无表头",
    )

    # 14. footnote under a figure must not attach to the table below ------
    case(
        "footnote_belongs_to_previous_figure",
        [
            page(
                1,
                [
                    unit(1, "图1 门店形象示意图", (70, 90, 190, 104), size=10.0, weight="bold", kind="caption"),
                    unit(2, "注：图片仅供参考。", (70, 115, 190, 127), size=8.0, kind="footnote"),
                    unit(3, "表2 门店数量", (70, 180, 150, 194), size=10.0, weight="bold", kind="caption"),
                    unit(4, "地区", (70, 205, 110, 218), size=9.0, weight="bold"),
                    unit(5, "数量", (350, 205, 390, 218), size=9.0, weight="bold"),
                    unit(6, "中国内地", (70, 228, 130, 241), size=9.0),
                    unit(7, "4,386", (335, 228, 395, 241), size=9.0),
                ],
            )
        ],
        "脚注属于上一图",
    )

    # 15. coordinates outside the page -----------------------------------
    case(
        "coordinates_out_of_bounds",
        [
            page(
                1,
                [
                    unit(1, "正常单元一。", (70, 100, 300, 114), size=10.0),
                    unit(2, "横向越界单元。", (600, 100, 700, 120), size=10.0),
                    unit(3, "纵向越界单元。", (70, -20, 300, 10), size=10.0),
                    unit(4, "正常单元二。", (70, 200, 300, 214), size=10.0),
                ],
            )
        ],
        "坐标越界",
    )

    # 16. whole-row single units: no cell coordinates to prove columns ----
    case(
        "whole_row_units_no_cells",
        [
            page(
                1,
                [
                    unit(1, "表1 门店数量", (70, 90, 150, 104), size=10.0, weight="bold", kind="caption"),
                    unit(2, "地区 2023年 2024年", (70, 115, 520, 129), size=9.0),
                    unit(3, "中国内地 3,926 4,386", (70, 137, 520, 151), size=9.0),
                    unit(4, "海外 2,487 3,118", (70, 159, 520, 173), size=9.0),
                    unit(5, "合计 6,413 7,504", (70, 181, 520, 195), size=9.0),
                ],
            )
        ],
        "整行单格无格子坐标",
    )

    # 17. multiple periods/regions must stay distinct columns -------------
    case(
        "multi_period_columns",
        [
            page(
                1,
                [
                    unit(1, "中国大陆", (150, 90, 250, 103), size=9.0, weight="bold"),
                    unit(2, "海外", (350, 90, 420, 103), size=9.0, weight="bold"),
                    unit(3, "2023年", (130, 112, 190, 125), size=9.0, weight="bold"),
                    unit(4, "2024年", (230, 112, 290, 125), size=9.0, weight="bold"),
                    unit(5, "2023年", (330, 112, 390, 125), size=9.0, weight="bold"),
                    unit(6, "2024年", (430, 112, 490, 125), size=9.0, weight="bold"),
                    unit(7, "门店数量", (70, 140, 130, 153), size=9.0),
                    unit(8, "3,926", (145, 140, 195, 153), size=9.0),
                    unit(9, "4,386", (245, 140, 295, 153), size=9.0),
                    unit(10, "2,487", (345, 140, 395, 153), size=9.0),
                    unit(11, "3,118", (445, 140, 495, 153), size=9.0),
                    unit(12, "直营店", (70, 162, 130, 175), size=9.0),
                    unit(13, "26", (170, 162, 195, 175), size=9.0),
                    unit(14, "25", (270, 162, 295, 175), size=9.0),
                    unit(15, "238", (365, 162, 395, 175), size=9.0),
                    unit(16, "503", (465, 162, 495, 175), size=9.0),
                ],
            )
        ],
        "多时期/地区列不混并",
    )


if __name__ == "__main__":
    build_all()
