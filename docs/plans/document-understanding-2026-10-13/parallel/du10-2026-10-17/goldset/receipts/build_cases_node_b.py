# DU10-CWP-SUMMARY-GOLDSET case builder (node B authoring tool, run once by the
# author; kept under receipts/ for provenance). Generates cases/*.json from the
# frozen node-A sample list and re-verifies every anchor quote against the
# original via read-only extraction before writing anything.
from __future__ import annotations

import hashlib
import json
import os
import re
import warnings

warnings.filterwarnings("ignore")

HERE = os.path.dirname(os.path.abspath(__file__))
CASES_DIR = os.path.join(HERE, "..", "cases")
FREEZE = json.load(open(os.path.join(HERE, "node_a_freeze.json"), encoding="utf-8"))
BY_ID = {c["case_id"]: c for c in FREEZE["cases"]}

MAIN = "C:/Users/郑曾波/Projects/company-wiki"


def norm(s: str) -> str:
    return re.sub(r"\s+", "", s)


def sha256_file(p: str) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def page_text(path: str, page: int | None, carrier: str) -> str:
    if carrier == ".pdf":
        import fitz

        d = fitz.open(path)
        try:
            if page is None:
                return "\n".join(d[i].get_text("text") for i in range(d.page_count))
            return d[page - 1].get_text("text")
        finally:
            d.close()
    from bs4 import BeautifulSoup

    raw = open(path, "rb").read()
    return BeautifulSoup(raw, "lxml").get_text("\n")


VERIFIED: list[tuple[str, int | None, str]] = []


def anchor(case_id: str, page: int | None, quote: str, kind: str = "page") -> dict:
    VERIFIED.append((case_id, page, quote))
    a = {"exact_quote": quote, "location_kind": kind}
    if page is not None:
        a["page"] = page
    return a


def fact(fid, importance, target_kind, modality, quantity_basis, role, sets,
         must_preserve, must_not_assert, reason) -> dict:
    return {
        "id": fid,
        "importance": importance,
        "target_kind": target_kind,
        "quantity_basis": quantity_basis,
        "modality": modality,
        "role": role,
        "any_support_sets": sets,
        "must_preserve": must_preserve,
        "must_not_assert": must_not_assert,
        "reason": reason,
    }


CASES: list[dict] = []

# ---------------------------------------------------------------- 1 CATL industry
cid = "du10gs-cn-annual-catl-industry"
src = BY_ID[cid]
CASES.append({
    "schema_version": "du10-summary-goldset-case/1",
    "case_id": cid,
    "created": "2026-10-17",
    "market": "CN",
    "company": "宁德时代",
    "doc_type": "annual_report",
    "carrier": ".pdf",
    "language": "zh",
    "narrative_focus": "industry_change",
    "bound_failure_mode": "第三方行业数据当公司收入；预测当实际",
    "source_ref": {
        "carrier_root": "company_raw",
        "source_id": "宁德时代/raw/financial_reports/宁德时代：2025年年度报告.pdf",
        "source_sha256": src["sha256"],
        "mime_type": "application/pdf",
        "registered_sidecar": {"market": "CN", "security_id": "300750",
                               "source_title": "宁德时代：2025年年度报告",
                               "published_date": "2026-04-30"},
    },
    "summary_proposition": "2025年全球动力电池使用量1,187GWh（SNE Research，同比+31.7%），宁德时代市占率39.2%（+1.2pct）、连续9年全球第一；全球储能电池出货量550GWh（+79%），公司连续5年储能出货第一。",
    "allowed_summary": [
        "据SNE Research数据，2025年全球动力电池使用量1,187GWh，同比增长31.7%；宁德时代动力电池使用量全球市占率39.2%，较上年提升1.2个百分点，连续9年（2017-2025年）全球第一。",
        "2025年全球储能电池出货量550GWh，同比增长79%（SNE Research统计）；宁德时代储能电池出货量连续5年（2021-2025年）全球第一。",
    ],
    "summary_guidance": {
        "must_preserve": ["SNE Research 来源归属", "使用量（动力）与出货量（储能）两种口径不得互换", "2025 年度期间", "39.2%/1,187GWh/550GWh 数值"],
        "boundary": ["行业总量不得写成公司业务量或收入", "公司自评表述（如“综合竞争力行业领先”）不得升格为第三方结论"],
    },
    "facts": [
        fact("industry-global-power-usage", "critical", "required_business", "third_party",
             "total", "third_party",
             [[anchor(cid, 17, "2025年全球动力电池使用量为1,187GWh，同比增长31.7%")]],
             ["SNE Research", "2025年", "1,187GWh", "31.7%", "使用量口径"],
             ["宁德时代2025年动力电池收入1,187GWh对应金额", "全球动力电池出货量1,187GWh（使用量≠出货量）", "该统计为公司自报产销量"],
             "行业总量数据来自SNE Research，是行业背景而非公司业绩；使用量口径是摘要最容易写错的字段。"),
        fact("catl-power-market-share", "critical", "required_business", "actual",
             "ratio", "company_filing",
             [[anchor(cid, 17, "2025年公司动力电池使用量全球市占率为39.2%，较去年同期提升1.2个百分点，公司已连续9年（2017-2025年）动力电池使用量排名全球第一")]],
             ["39.2%", "+1.2个百分点", "动力电池使用量口径", "SNE Research", "连续9年"],
             ["39.2%为储能市占率", "39.2%为收入占比", "连续9年储能第一（储能是连续5年）"],
             "公司份额叙述依赖第三方统计；口径（使用量）与连续年数必须原样保留。"),
        fact("industry-global-ess-shipment", "normal", "required_business", "third_party",
             "total", "third_party",
             [[anchor(cid, 17, "2025年全球储能电池出货量550GWh，同比增长79%"),
               anchor(cid, 17, "在储能领域，公司已连续5年（2021-2025年）储能电池出货量排名全球第一")]],
             ["550GWh", "79%", "出货量口径（储能）", "连续5年"],
             ["储能收入550GWh对应金额", "550GWh为动力电池数据"],
             "同页两类行业数据（动力使用量/储能出货量）口径不同，混用即错引。"),
    ],
    "misread_traps": [
        {"page": 16, "kind": "same_page_mixed",
         "note": "p16 上半为公司经营模式与业绩驱动因素叙述（含自评“综合竞争力行业领先”），下半为行业情况叙述；自评与第三方数据同页。",
         "exact_quote": "综合竞争力行业领先，实现业务稳健增长"},
        {"page": 17, "kind": "third_party_attribution",
         "note": "p17 所有行业数字均带数据来源（SNE Research/中国汽车工业协会/IEA/国家能源局等）；漏掉来源归属即失真。"},
    ],
    "prior_use": src["prior_use"],
    "notes": "年报物理页码按 PDF 1 基页。p17 行业地位段落为 SNE Research 转引。",
})

# ---------------------------------------------------------------- 2 CATL capacity
cid = "du10gs-cn-annual-catl-capacity"
src = BY_ID[cid]
CASES.append({
    "schema_version": "du10-summary-goldset-case/1",
    "case_id": cid,
    "created": "2026-10-17",
    "market": "CN",
    "company": "宁德时代",
    "doc_type": "annual_report",
    "carrier": ".pdf",
    "language": "zh",
    "narrative_focus": "project_progress",
    "bound_failure_mode": "planned/actual（在建≠投产）；叙述与财务表同页借数",
    "source_ref": {
        "carrier_root": "company_raw",
        "source_id": "宁德时代/raw/financial_reports/宁德时代：2025年年度报告.pdf",
        "source_sha256": src["sha256"],
        "mime_type": "application/pdf",
        "registered_sidecar": {"market": "CN", "security_id": "300750",
                               "source_title": "宁德时代：2025年年度报告",
                               "published_date": "2026-04-30"},
    },
    "summary_proposition": "报告期内公司稳步推进中州基地、济宁基地、福鼎基地、溧阳基地、宜宾基地、匈牙利工厂及印尼电池产业链等项目的建设；锂电池产能772GWh，期末在建产能321GWh。",
    "allowed_summary": [
        "2025年宁德时代稳步推进中州基地、济宁基地、福鼎基地、溧阳基地、宜宾基地、匈牙利工厂及印尼电池产业链等项目的建设，期末锂电池产能772GWh、在建产能321GWh。",
    ],
    "summary_guidance": {
        "must_preserve": ["“推进……建设”进行时态", "在建321GWh 与产能772GWh 两个数字分开", "项目列举不得扩写为“已投产”"],
        "boundary": ["在建/推进中项目不得写成已投产或已贡献产量", "产能（期末存量）不得写成当期产量或销量"],
    },
    "facts": [
        fact("capacity-projects-under-construction", "critical", "required_business", "plan",
             "capacity_total", "company_filing",
             [[anchor(cid, 24, "公司稳步推进中州基地、济宁基地、福鼎基地、溧阳基地、宜宾基地、匈牙利工厂及印尼电池产业链等项目的建设。报告期内公司锂电池产能772GWh，期末在建产能321GWh")]],
             ["“稳步推进……建设”", "772GWh 为产能", "321GWh 为在建产能", "期末时点"],
             ["匈牙利工厂或印尼项目已投产", "海外基地已贡献产量", "321GWh 为已投产产能", "772GWh 为2025年产量"],
             "产能叙述全部是进行时/存量口径；“推进建设”写成“建成投产”即 planned/actual 错引。"),
        fact("revenue-table-same-page", "normal", "correctness_if_emitted", "actual",
             "period_flow", "company_filing",
             [[anchor(cid, 24, "营业收入合计 423,701,834 100.00% 362,012,554 100.00% 17.04%")]],
             ["单位：千元", "2025年 vs 2024年", "17.04% 为同比"],
             ["营业收入单位为元或万元", "把占比列当同比增速", "把423,701,834当元"],
             "同一物理页下半为收入构成表（单位千元）；摘要若引用收入数字必须落到本表并核对单位。"),
    ],
    "misread_traps": [
        {"page": 24, "kind": "mixed_narrative_and_table",
         "note": "p24 上半为供应链/产能/可持续叙述，下半为营业收入构成表（单位：千元）；叙述与表格混同页，借数风险高。",
         "exact_quote": "单位：千元"},
        {"page": 24, "kind": "tense",
         "note": "“稳步推进……建设”为进行时；同段项目名（匈牙利工厂、印尼电池产业链）容易被误读为已完工资产。"},
    ],
    "prior_use": src["prior_use"],
    "notes": "与 du10gs-cn-annual-catl-industry 共用同一原件（不同命题）；新增证据为项目进度+混表页。",
})

# ---------------------------------------------------------------- 3 Sugon interim
cid = "du10gs-cn-interim-sugon"
src = BY_ID[cid]
CASES.append({
    "schema_version": "du10-summary-goldset-case/1",
    "case_id": cid,
    "created": "2026-10-17",
    "market": "CN",
    "company": "中科曙光",
    "doc_type": "interim_report",
    "carrier": ".pdf",
    "language": "zh",
    "narrative_focus": "main_business",
    "bound_failure_mode": "预测当实际（IDC 全年预测 vs 统计局 H1 实际）；第三方数据归属",
    "source_ref": {
        "carrier_root": "company_raw",
        "source_id": "中科曙光/raw/financial_reports/中科曙光：中科曙光2025年半年度报告.pdf",
        "source_sha256": src["sha256"],
        "mime_type": "application/pdf",
        "registered_sidecar": {"market": "CN", "security_id": "中科曙光",
                               "source_title": "中科曙光：中科曙光2025年半年度报告"},
    },
    "summary_proposition": "ParaStor分布式存储连续6年中标中国移动集采；2024年第三代C8000浸没液冷单机柜功率密度突破750kW以上；2025H1中国服务器产量+126.7%（国家统计局），IDC预测2025年全球服务器市场规模有望达3660亿美元（+44.6%）。",
    "allowed_summary": [
        "报告期内ParaStor分布式存储系列连续6年中标中国移动分布式存储集采。",
        "2024年第三代C8000浸没液冷解决方案单机柜功率密度突破至750kW以上；2025年子公司曙光数创发布C7000-F相变间接液冷技术。",
        "行业侧：国家统计局数据显示2025年上半年中国服务器产量增长126.7%；IDC预测2025年全球服务器市场规模有望达到3660亿美元、同比增速44.6%。",
    ],
    "summary_guidance": {
        "must_preserve": ["国家统计局（实际）与 IDC（预测）来源分开", "“有望达到”预测措辞", "2024年（C8000）与2025年（C7000-F）时间归属"],
        "boundary": ["全年市场规模预测不得写成上半年已实现", "行业产量/规模不得写成公司收入", "自建研发中心数量等资质叙述不升格为行业结论"],
    },
    "facts": [
        fact("parastor-china-mobile-streak", "critical", "required_business", "actual",
             "count", "company_filing",
             [[anchor(cid, 8, "报告期内，公司ParaStor分布式存储系列连续6年中标中国移动分布式存储集采")]],
             ["连续6年", "中国移动", "分布式存储集采", "ParaStor"],
             ["连续6年存储市场份额第一（份额第一是赛迪报告中具身智能/自动驾驶/科教等细分领域口径，属另一句）", "海外运营商订单"],
             "公司主营业务实际进展；与同页“市场份额首位”句是两个不同事实，来源与口径都不同。"),
        fact("liquid-cooling-c8000-750kw", "critical", "required_business", "actual",
             "projected_output", "company_filing",
             [[anchor(cid, 8, "2024年第三代C8000浸没液冷解决方案单机柜功率密度突破至750kW以上")]],
             ["2024年", "第三代C8000", "单机柜功率密度", "750kW以上"],
             ["750kW为2025年发布（2025年是曙光数创C7000-F相变间接液冷技术）", "公司全部服务器功率密度"],
             "产品代际与年份绑定；同页下一句才是2025年C7000-F，时间错位是高发错引。"),
        fact("industry-server-output-h1", "normal", "required_business", "third_party",
             "incremental", "third_party",
             [[anchor(cid, 9, "国家统计局数据显示，中国服务器产量增长126.7%")]],
             ["国家统计局", "中国服务器产量", "2025年上半年"],
             ["全球服务器产量增长126.7%", "公司服务器产量增长126.7%", "IDC数据"],
             "行业实际数据（半年、中国、产量）；与下一条IDC全年预测形成实际/预测对照。"),
        fact("industry-server-market-idc-forecast", "normal", "required_business", "plan",
             "total", "third_party",
             [[anchor(cid, 9, "IDC（国际数据公司）发布预测，2025年全球服务器市场规模有望达到3660亿美元，同比增速44.6%")]],
             ["IDC", "2025年全年", "3660亿美元", "“有望”预测措辞"],
             ["2025年上半年已实现3660亿美元市场规模", "公司收入3660亿美元", "预测当已实现"],
             "第三方全年预测；丢掉“有望”或把期间换成上半年即 planned/actual 错引。"),
    ],
    "misread_traps": [
        {"page": 9, "kind": "forecast_vs_actual_same_section",
         "note": "p9 行业段先给统计局H1实际产量增速，紧接着给IDC全年规模预测；两句连排且都带百分数。",
         "exact_quote": "国家统计局数据显示，中国服务器产量增长126.7%"},
        {"page": 8, "kind": "footnote_sources",
         "note": "p8-9 多个数字带脚注来源（赛迪/SPC/工信部/IDC 等），脚注编号在PDF抽取中黏在数字后（如126.7%⁴）；引文比对须空白归一化。"},
    ],
    "prior_use": src["prior_use"],
    "notes": "半年报 physical pages 8-9（PDF 1基）。189页。",
})

# ---------------------------------------------------------------- 4 DFC Q3
cid = "du10gs-cn-q3-dfc"
src = BY_ID[cid]
CASES.append({
    "schema_version": "du10-summary-goldset-case/1",
    "case_id": cid,
    "created": "2026-10-17",
    "market": "CN",
    "company": "东方电缆",
    "doc_type": "quarterly_report",
    "carrier": ".pdf",
    "language": "zh",
    "narrative_focus": "main_business",
    "bound_failure_mode": "同量纲不同时期（单季 vs 累计）；类别收入当总收入",
    "source_ref": {
        "carrier_root": "company_raw",
        "source_id": "东方电缆/raw/financial_reports/东方电缆：东方电缆2025年第三季度报告.pdf",
        "source_sha256": src["sha256"],
        "mime_type": "application/pdf",
        "registered_sidecar": {"market": "CN", "security_id": "东方电缆",
                               "source_title": "东方电缆：东方电缆2025年第三季度报告"},
    },
    "summary_proposition": "2025年第三季度（本报告期=单季）：海底电缆与高压电缆实现营业收入35.49亿元、同比+35.8%，为本报告期利润总额+51.19%的主要原因。",
    "allowed_summary": [
        "2025年第三季度（单季），东方电缆海底电缆与高压电缆实现营业收入35.49亿元，同比增长35.8%，带动本报告期利润总额同比增长51.19%。",
    ],
    "summary_guidance": {
        "must_preserve": ["本报告期=单季（Q3三个月）", "海底电缆与高压电缆类别口径", "35.49亿元/35.8%/51.19%"],
        "boundary": ["不得把单季类别收入写成前三季度累计或全年", "类别收入不得写成公司营业总收入"],
    },
    "facts": [
        fact("q3-submarine-hv-cable-revenue", "critical", "required_business", "actual",
             "period_flow", "company_filing",
             [[anchor(cid, 3, "主要系本报告期高附加值海底电缆营业收入增长较多，本报告期海底电缆与高压电缆实现营业收入35.49亿元，同比增长35.8%")]],
             ["本报告期（单季）", "海底电缆与高压电缆", "35.49亿元", "35.8%"],
             ["前三季度累计类别收入35.49亿元", "公司营业总收入35.49亿元", "全年收入35.49亿元", "海外订单收入"],
             "单季+类别口径双限定；报告仅11页，累计算法上极易被放大三倍误引。"),
        fact("q3-profit-change-reason", "normal", "required_business", "actual",
             "ratio", "company_filing",
             [[anchor(cid, 3, "利润总额_本报告期"),
               anchor(cid, 3, "归属于上市公司股东的净利润_本报告期")]],
             ["本报告期口径", "利润总额+51.19%、归母净利+53.12%（见变动表）"],
             ["年初至报告期末累计同比", "扣非口径混淆（扣非净利+71.73%是另一行）"],
             "变动原因叙述绑定变动表的“本报告期”列；三列同比数字并存，行名必须随数保留。"),
        fact("quarter-definition-note", "critical", "disposition_context", "actual",
             "unknown", "company_filing",
             [[anchor(cid, 2, "“本报告期”指本季度初至本季度末3个月期间，下同")]],
             ["单季定义注释"],
             ["把“本报告期”读成前三季度"],
             "p2 注释显式定义单季口径，是本报告所有“本报告期”数字的解释锚。"),
    ],
    "misread_traps": [
        {"page": 3, "kind": "same_page_mixed",
         "note": "p3 上半为变动原因叙述，下半为前10名股东表；业绩叙述与股东信息同页。",
         "exact_quote": "二、股东信息"},
        {"page": 2, "kind": "dual_period_columns",
         "note": "p2-3 非经常性损益表同时给出“本期金额”与“年初至报告期末金额”两列，双期间并存是错引高发点。",
         "exact_quote": "年初至报告期末"},
    ],
    "prior_use": src["prior_use"],
    "notes": "11页短季报；physical pages 2-3（PDF 1基）。",
})

# ---------------------------------------------------------------- 5 HRJC IPO
cid = "du10gs-cn-ipo-hrjc"
src = BY_ID[cid]
CASES.append({
    "schema_version": "du10-summary-goldset-case/1",
    "case_id": cid,
    "created": "2026-10-17",
    "market": "CN",
    "company": "华锐精密",
    "doc_type": "ipo_prospectus",
    "carrier": ".pdf",
    "language": "zh",
    "narrative_focus": "industry_change+project_plan",
    "bound_failure_mode": "planned/actual（拟建募投当已建成）；行业规模当公司收入",
    "source_ref": {
        "carrier_root": "company_raw",
        "source_id": "华锐精密/raw/prospectus/华锐精密：华锐精密首次公开发行股票并在科创板上市招股说明书.PDF",
        "source_sha256": src["sha256"],
        "mime_type": "application/pdf",
        "registered_sidecar": {"market": "CN", "security_id": "华锐精密",
                               "source_title": "华锐精密：华锐精密首次公开发行股票并在科创板上市招股说明书"},
    },
    "summary_proposition": "招股书披露：2019年我国刀具市场总消费规模约393亿元、进口刀具136亿元，进口占比从2016年37.17%降至2019年34.61%（中国机床工具工业协会统计）；公司产能利用率已基本饱和，拟通过募投扩建新生产基地并新增金属陶瓷数控刀片、整体刀具等产能。",
    "allowed_summary": [
        "据中国机床工具工业协会统计（招股书转引），2019年我国刀具市场总消费规模约393亿元，其中进口刀具136亿元；进口占比由2016年37.17%降至2019年34.61%。",
        "招股书披露报告期内公司产能利用率已基本处于饱和状态，拟通过募投项目扩建新生产基地，新增金属陶瓷数控刀片、硬质合金整体刀具和刀杆、刀盘等产能。",
    ],
    "summary_guidance": {
        "must_preserve": ["“约393亿元”的约", "协会统计来源（脚注6）", "募投“拟/将”计划语态", "2016→2019 期间"],
        "boundary": ["行业市场规模不得写成公司收入", "拟建产能不得写成已建成/已投产", "行业趋势不得外推为招股书发布后承诺"],
    },
    "facts": [
        fact("tool-market-2019-scale", "critical", "required_business", "third_party",
             "total", "third_party",
             [[anchor(cid, 105, "2019年我国刀具市场总消费规模约为393亿元，进口刀具规模为136亿元")]],
             ["2019年", "我国（中国）刀具市场", "约393亿元", "136亿元", "中国机床工具工业协会统计"],
             ["公司收入393亿元", "全球刀具市场规模", "精确值（原文为“约”）"],
             "行业规模叙述；“约”与来源归属必须保留。"),
        fact("import-share-decline", "normal", "required_business", "third_party",
             "ratio", "third_party",
             [[anchor(cid, 105, "2016—2019年进口刀具占总消费的比重从37.17%下降至34.61%")]],
             ["2016—2019年", "占比口径", "37.17%→34.61%"],
             ["进口刀具绝对额降至34.61%", "占比变化被写成金额变化", "趋势延续至招股书发布日的承诺"],
             "进口替代趋势的行业证据；期间与占比口径绑定。"),
        fact("capacity-saturation-expansion-plan", "critical", "required_business", "plan",
             "capacity_new", "company_filing",
             [[anchor(cid, 293, "报告期内，公司适时把握市场需求变化趋势，积极引进先进生产设备提升产能规模，但产能利用率已基本处于饱和状态，扩大产能成为公司进一步发展的迫切任务。通过本次募集资金投资项目的实施，公司将扩建新生产基地，引进国内外先进生产设备"),
               anchor(cid, 293, "通过本次募集资金投资项目，公司将新增金属陶瓷数控刀片、硬质合金整体刀具和刀杆、刀盘等数控刀具配套产品产能")]],
             ["产能饱和为报告期内状态", "“拟/将”（计划）", "新增产能品类列举"],
             ["新产能已建成或已投产", "募投项目已实现新增收入", "产能饱和为摘要时点状态"],
             "募投必要性论证是计划语态；写成已完成的扩产即 planned/actual 错引。"),
    ],
    "misread_traps": [
        {"page": 105, "kind": "industry_vs_company",
         "note": "p105 下半为上游碳化钨/钴粉供应商叙述（厦门钨业等公司名连排），行业叙述与具体公司名单同页。",
         "exact_quote": "厦门钨业"},
        {"page": 293, "kind": "persuasive_registration_document",
         "note": "p293 属募集资金运用必要性论证（发行申请文件的说理性内容），“迫切任务/打下坚实基础”等措辞不是已实现事实。",
         "exact_quote": "为未来转型向终端客户提供整体刀具解决方案打下坚实基础"},
    ],
    "prior_use": src["prior_use"],
    "notes": "350页科创板招股书；physical pages 104-105、293（PDF 1基）。",
})

# ---------------------------------------------------------------- 6 MLKW conv bond
cid = "du10gs-cn-convbond-mlkw"
src = BY_ID[cid]
CASES.append({
    "schema_version": "du10-summary-goldset-case/1",
    "case_id": cid,
    "created": "2026-10-17",
    "market": "CN",
    "company": "密尔克卫",
    "doc_type": "convertible_bond_prospectus",
    "carrier": ".pdf",
    "language": "zh",
    "narrative_focus": "new_business+project_plan",
    "bound_failure_mode": "测算当已实现（完全达产后预计）；拟建首个别当已有业务",
    "source_ref": {
        "carrier_root": "company_raw",
        "source_id": "密尔克卫/raw/research/密尔克卫：密尔克卫化工供应链服务股份有限公司公开发行可转换公司债券募集说明书.PDF",
        "source_sha256": src["sha256"],
        "mime_type": "application/pdf",
        "registered_sidecar": {"market": "CN", "security_id": "密尔克卫",
                               "source_title": "密尔克卫：密尔克卫化工供应链服务股份有限公司公开发行可转换公司债券募集说明书"},
    },
    "summary_proposition": "可转债募投“超临界水氧化及配套环保项目”投资总额70,000.00万元、废液处理能力5.0万吨/年，将成为公司首个拟建成的危废处理中心；完全达产后预计年销售收入19,528.30万元、净利润4,783.21万元、毛利率39.38%、税后内部收益率6.17%。",
    "allowed_summary": [
        "可转债募投项目超临界水氧化及配套环保项目投资总额70,000.00万元，建成后废液处理能力5.0万吨/年，将成为公司首个拟建成的危废处理中心。",
        "该项目完全达产后预计每年实现销售收入19,528.30万元、净利润4,783.21万元，毛利率39.38%、税后内部收益率6.17%（测算值，非业绩承诺）。",
    ],
    "summary_guidance": {
        "must_preserve": ["“完全达产后预计”条件语态", "“首个拟建成”", "实施主体为全资子公司张家港密尔克卫环保科技有限公司", "四个测算数字各自口径"],
        "boundary": ["测算不得写成已实现收入/利润或业绩承诺", "危废处理不得写成公司现有业务", "70,000万元为拟投资总额不是已投入"],
    },
    "facts": [
        fact("supercritical-project-investment", "critical", "required_business", "plan",
             "investment", "company_filing",
             [[anchor(cid, 344, "项目投资总额70,000.00万元"),
               anchor(cid, 344, "处理废液能力达到5.0万吨/年")]],
             ["70,000.00万元为投资总额（拟）", "5.0万吨/年为建成后处理能力", "实施主体张家港密尔克卫环保科技有限公司"],
             ["项目已建成投产", "70,000万元已投入", "5.0万吨/年为现有产能"],
             "募投项目基本要素；拟建语态与建成后能力绑定。"),
        fact("first-hazardous-waste-center", "critical", "required_business", "plan",
             "unknown", "company_filing",
             [[anchor(cid, 344, "本募投项目将成为公司首个拟建成的危废处理中心")]],
             ["“首个”", "“拟建成”（尚未建成）", "危废处理为新进入领域"],
             ["公司已有危废处理中心", "危废处理已是公司现有收入来源", "首个删去"],
             "新业务（第二曲线）定位叙述；“拟建成”是本句关键限定。"),
        fact("benefit-projection-full-capacity", "critical", "required_business", "conditional",
             "period_flow", "company_filing",
             [[anchor(cid, 344, "本项目完全达产后预计每年实现销售收入19,528.30万元，净利润4,783.21万元，毛利率39.38%，税后内部收益率为6.17%")]],
             ["完全达产后（条件）", "预计", "19,528.30万元/4,783.21万元/39.38%/6.17%"],
             ["当前已实现该收入或利润", "测算为业绩承诺", "达产前即产生该等收入"],
             "效益测算四件套数字全部是条件测算；去条件化即 planned/actual 错引。"),
    ],
    "misread_traps": [
        {"page": 344, "kind": "projection_adjacent_to_facts",
         "note": "p344 建设内容叙述（事实性）与经济效益测算（条件性）上下连排，数字密集。",
         "exact_quote": "5、项目经济效益"},
        {"page": 344, "kind": "same_page_scope",
         "note": "p344 下半已开始下一募投项目（徐圩新区A地块）的叙述；两项目数字不得互串。",
         "exact_quote": "徐圩新区化工品供应链一体化服务基地A地块"},
    ],
    "prior_use": src["prior_use"],
    "notes": "401页可转债募集说明书；physical page 344（PDF 1基）。",
})

# ---------------------------------------------------------------- 7 AMEC minutes
cid = "du10gs-cn-ir-amec-minutes"
src = BY_ID[cid]
CASES.append({
    "schema_version": "du10-summary-goldset-case/1",
    "case_id": cid,
    "created": "2026-10-17",
    "market": "CN",
    "company": "中微公司",
    "doc_type": "ir_minutes",
    "carrier": ".pdf",
    "language": "zh",
    "narrative_focus": "industry_change+new_business",
    "bound_failure_mode": "订单当收入；预测标注丢失；在研当上市",
    "source_ref": {
        "carrier_root": "company_raw",
        "source_id": "中微公司/raw/investor_relations/【芯片】中微公司交流纪要20220416.pdf",
        "source_sha256": src["sha256"],
        "mime_type": "application/pdf",
        "registered_sidecar": {"market": "CN", "security_id": "688012",
                               "source_title": "【芯片】中微公司交流纪要20220416"},
    },
    "summary_proposition": "纪要转述：2021年收入31.08亿元（+36.72%）、新订单41.29亿元（+90.46%）；2021年全球半导体设备市场增长44.7%，2022年预计超800亿美元（预测）；ICP Nanova每年销售增长超100%、2021年超200%；XD RIE与YDRIE在研、预计一年左右进入市场。",
    "allowed_summary": [
        "交流纪要转述：公司2021年营业收入31.08亿元、同比增长36.72%；新订单41.29亿元、同比增长90.46%。",
        "纪要转述：2021年全球半导体设备市场增长44.7%，预计2022年超过800亿美元（纪要括注2022年为预测数据）。",
        "纪要转述：ICP Nanova进入市场近三年，每年销售增长均超过100%，2021年超过200%；XD RIE、YDRIE处于在研阶段，预计一年左右进入市场。",
    ],
    "summary_guidance": {
        "must_preserve": ["收入与新订单两个口径分开", "“（2022年是预测数据）”括注", "在研/预计进入市场语态", "纪要为第三方整理转述（非公司公告）"],
        "boundary": ["新订单不得写成收入", "行业增速不得写成公司增速", "在研产品不得写成已上市/已量产", "预测不得当实际"],
    },
    "facts": [
        fact("revenue-vs-new-orders-2021", "critical", "required_business", "actual",
             "period_flow", "company_statement",
             [[anchor(cid, 1, "公司2021年营业收入达31.08亿元，同比增长36.72%；公司接受的新订单达41.29亿，同比增长90.46%")]],
             ["31.08亿元=营业收入", "41.29亿=新订单", "两个口径不得互换或合并"],
             ["收入41.29亿元", "新订单31.08亿元", "订单额当期确认收入"],
             "订单/收入双口径并列；错引高发点是两数互换。"),
        fact("industry-equipment-growth-2021", "normal", "required_business", "third_party",
             "incremental", "company_statement",
             [[anchor(cid, 2, "2021年全世界半导体设备市场增长44.7%")]],
             ["2021年", "全球半导体设备市场（行业）", "44.7%"],
             ["公司收入增长44.7%", "2022年增长44.7%"],
             "行业增速由纪要转述；主体（全世界市场）必须保留。"),
        fact("market-size-2022-forecast", "normal", "required_business", "plan",
             "total", "company_statement",
             [[anchor(cid, 2, "2022年会超过800亿美元"),
               anchor(cid, 2, "2019-2022年平均年增长率达21.81%（2022年是预测数据）")]],
             ["2022年为预测", "800亿美元", "21.81%为2019-2022平均年增长率（含预测年）"],
             ["2022年已超过800亿美元", "21.81%为已实现复合增速"],
             "原文自带预测括注；丢括注即把预测写成实际。"),
        fact("icp-nanova-growth", "normal", "required_business", "actual",
             "incremental", "company_statement",
             [[anchor(cid, 3, "公司的Nanova新机台进入市场已将近三年，每年销售增长均超过100%，2021年超过了200%")]],
             ["Nanova/ICP", "销售增长口径", "超过100%/超过200%"],
             ["收入增长200%", "市占率200%", "把“销售增长”写成装机量"],
             "产品线增长叙述；量词“超过”与口径“销售增长”绑定。"),
        fact("xdrie-ydrie-in-development", "critical", "required_business", "plan",
             "unknown", "company_statement",
             [[anchor(cid, 3, "但公司已经开发了XD的RIE，将来会宣布产品名称，很快就完成开发进入市场，初步的demo结果非常好"),
               anchor(cid, 3, "公司正在紧锣密鼓地开发，现在叫YDRIE，正式名称将来宣布，目前正在开发，而且也有非常好的表现，一年左右即将进入市场")]],
             ["XD RIE 与 YDRIE 均为在研", "“一年左右即将进入市场”为预期", "demo/开发中状态"],
             ["两产品已上市或已量产", "已贡献收入", "“一年左右”为承诺日期"],
             "在研管线叙述；写成已上市产品即 planned/actual 错引。"),
    ],
    "misread_traps": [
        {"page": 1, "kind": "document_nature",
         "note": "本件为第三方整理的交流纪要（文件名带“【芯片】”渠道前缀），正文为公司管理层汇报的转述，无签字/审计；会议日期（2022-04-16）来自文件名与侧车，页内无日期抬头。",
         "exact_quote": "一、基本情况"},
        {"page": 2, "kind": "forecast_annotation",
         "note": "p2 “（2022年是预测数据）”括注紧跟21.81%；PDF抽取中括注可能与数字分离。",
         "exact_quote": "（2022年是预测数据）"},
    ],
    "prior_use": src["prior_use"],
    "notes": "10页纪要；physical pages 1-3（PDF 1基）。role=company_statement：纪要转述的管理层陈述。",
})

# ---------------------------------------------------------------- 8 BABA HK IPO
cid = "du10gs-hk-ipo-baba"
src = BY_ID[cid]
CASES.append({
    "schema_version": "du10-summary-goldset-case/1",
    "case_id": cid,
    "created": "2026-10-17",
    "market": "HK",
    "company": "阿里巴巴",
    "doc_type": "ipo_prospectus",
    "carrier": ".pdf",
    "language": "zh-Hant",
    "narrative_focus": "overseas+main_business",
    "bound_failure_mode": "同页不同 TTM 期间混用；去重口径丢失",
    "source_ref": {
        "carrier_root": "company_raw",
        "source_id": "阿里巴巴/raw/prospectus/阿里巴巴招股说明书2019.pdf",
        "source_sha256": src["sha256"],
        "mime_type": "application/pdf",
        "registered_sidecar": {"market": "CN", "security_id": "阿里巴巴",
                               "source_title": "阿里巴巴招股说明书2019"},
    },
    "summary_proposition": "招股书概要：截至2019年6月30日止12个月全球年度活跃消费者8.60亿，其中国际1.30亿（Lazada与速卖通去重后总和）；中国零售市场GMV人民币5.727万亿元为截至2019年3月31日止12个月；FY2019雲計算分部收入24,702百万元（FY2018：13,390百万元）。",
    "allowed_summary": [
        "招股书披露：截至2019年6月30日止12个月，阿里巴巴数字经济体全球年度活跃消费者8.60亿，其中国际年度活跃消费者1.30亿（Lazada与速卖通去重后总和）。",
        "中国零售市场GMV为人民币5.727万亿元，截至2019年3月31日止12个月（与用户数期间口径不同）。",
        "FY2019（截至2019年3月31日止年度）雲計算分部收入24,702百万元，FY2018为13,390百万元（人民币百万元）。",
    ],
    "summary_guidance": {
        "must_preserve": ["两组TTM期间（6/30 vs 3/31）不得互换", "国际1.30亿的去重定义", "GMV的中国零售市场范围", "分部收入的人民币百万元单位与财年口径"],
        "boundary": ["国际消费者不得写成全部国际业务用户", "8.60亿不得写成公司收入用户（含蚂蚁金服中国用户，去重合并口径）", "GMV不得写为全集团/全球或与用户同期"],
    },
    "facts": [
        fact("global-annual-active-consumers", "critical", "required_business", "actual",
             "count", "company_filing",
             [[anchor(cid, 19, "全球年度活躍"),
               anchor(cid, 19, "8.60億"),
               anchor(cid, 19, "截至2019年6月30日止12個月期間")]],
             ["8.60亿", "截至2019年6月30日止12个月", "中国消费业务+蚂蚁金服去重合并口径"],
             ["8.60亿为公司单一口径注册用户", "期间为2019年3月31日"],
             "规模框内数字全部带注释限定；期间与口径注释是事实的一部分。"),
        fact("international-active-consumers", "critical", "required_business", "actual",
             "count", "company_filing",
             [[anchor(cid, 19, "國際年度活躍"),
               anchor(cid, 19, "1.30億"),
               anchor(cid, 19, "去重後Lazada和速賣通年度活躍消費者之總和")]],
             ["1.30亿", "Lazada+速卖通去重", "截至2019年6月30日止12个月"],
             ["1.30亿为全部国际业务用户（如国际站/菜鸟）", "去重定义删去"],
             "出海叙述核心数字；去重范围（仅Lazada与速卖通）是定义的一部分。"),
        fact("china-retail-gmv-march-ttm", "critical", "required_business", "actual",
             "total", "company_filing",
             [[anchor(cid, 19, "GMV"),
               anchor(cid, 19, "人民幣5.727萬億元"),
               anchor(cid, 19, "截至2019年3月31日止12個月期間我們的中國零售市場")]],
             ["5.727万亿元", "截至2019年3月31日止12个月", "中国零售市场范围"],
             ["GMV与年度活跃消费者同一期间（6/30）", "GMV为全集团或全球口径"],
             "同页两组TTM并存（用户6/30、GMV 3/31），混用即期间错引。"),
        fact("cloud-segment-revenue-fy2019", "normal", "required_business", "actual",
             "period_flow", "company_filing",
             [[anchor(cid, 21, "雲計算"),
               anchor(cid, 21, "24,702"),
               anchor(cid, 21, "13,390")]],
             ["FY2019=截至2019年3月31日止年度", "24,702百万元", "FY2018为13,390百万元", "人民币百万元"],
             ["日历年口径", "收入占比7%当作绝对额", "与6月止季度数字（7,787）混算"],
             "分部表按财年列示；第二曲线（云）进展的规模与增速证据。"),
    ],
    "misread_traps": [
        {"page": 19, "kind": "dual_ttm_same_page",
         "note": "p19 规模框：用户数截至6/30 TTM，GMV截至3/31 TTM；注释(1)-(6)逐项限定。",
         "exact_quote": "截至2019年3月31日止12個月期間我們的中國零售市場"},
        {"page": 21, "kind": "non_gaap_rows",
         "note": "p21 表内同时有GAAP收入与经调整EBITDA等非公认会计准则指标；引用非GAAP行必须保留“經調整/非公認會計準則”标识。",
         "exact_quote": "經調整EBITDA"},
    ],
    "prior_use": src["prior_use"],
    "notes": "666页港股全球发售招股书（封面股份代号9988）；physical pages 19、21（PDF 1基）。侧车market=CN与实际（HK发行）不符，已如实记录，case以文档内容为准。",
})

# ---------------------------------------------------------------- 9 MINISO interim
cid = "du10gs-hk-interim-miniso"
src = BY_ID[cid]
CASES.append({
    "schema_version": "du10-summary-goldset-case/1",
    "case_id": cid,
    "created": "2026-10-17",
    "market": "HK",
    "company": "名创优品",
    "doc_type": "interim_report",
    "carrier": ".pdf",
    "language": "bilingual-en-zh-Hant",
    "narrative_focus": "overseas",
    "bound_failure_mode": "存量 vs 净增；品牌口径 vs 集团口径",
    "source_ref": {
        "carrier_root": "dropbox_stock",
        "source_id": "消费品/名创优品/2025半年报（港股）.pdf",
        "source_sha256": src["sha256"],
        "mime_type": "application/pdf",
        "registered_sidecar": None,
    },
    "summary_proposition": "截至2025年6月30日，名创优品品牌海外市场拥有579家直营店、425家名创合伙人门店与2,303家代理门店（海外直营期初503家、期内净增76家）；集团层面直营店总数637家（2024年6月30日为393家）。",
    "allowed_summary": [
        "截至2025年6月30日，名创优品品牌在海外市场拥有579家直营店、425家名创合伙人门店与2,303家代理门店；海外直营店期内净增76家（期初503家）。",
        "集团层面直营门店总数由2024年6月30日的393家增至2025年6月30日的637家。",
    ],
    "summary_guidance": {
        "must_preserve": ["期末存量与期内净增分开", "名创优品品牌+海外市场 vs 集团层面两种口径", "截至日期", "三种门店模式分列"],
        "boundary": ["不得把海外三模式相加写成全球门店总数", "637不得写成海外直营（海外直营579）", "净增不得写成新开门店数（无闭店拆分不得推断）"],
    },
    "facts": [
        fact("overseas-store-mix", "critical", "required_business", "actual",
             "count", "company_filing",
             [[anchor(cid, 14, "截至2025年6月30日，名創優品品牌在海外市場"),
               anchor(cid, 14, "579家直營店，425家名創合夥人門店與"),
               anchor(cid, 14, "2,303家代理門店")]],
             ["截至2025年6月30日（期末存量）", "579/425/2,303 三模式分列", "名创优品品牌+海外市场范围"],
             ["全球门店总数", "含中国门店", "含TOP TOY门店", "三数相加当全球总数"],
             "海外门店三模式存量；范围（品牌+海外）与时点绑定。"),
        fact("overseas-direct-store-flow", "normal", "required_business", "actual",
             "count", "company_filing",
             [[anchor(cid, 14, "期初門店數量"),
               anchor(cid, 14, "期內門店數量的淨增加"),
               anchor(cid, 14, "503"),
               anchor(cid, 14, "76"),
               anchor(cid, 14, "579")]],
             ["期初503/净增76/期末579", "净增≠新开"],
             ["新开76家（无闭店拆分不得推断）", "净增76写成期末数"],
             "门店流量结构表（期初/净增/期末三行）；存量与流量错位是已知失败现场。"),
        fact("group-direct-stores-637", "critical", "required_business", "actual",
             "count", "company_filing",
             [[anchor(cid, 23, "As of June 30, 2025,"),
               anchor(cid, 23, "total number of directly operated stores on the group level was"),
               anchor(cid, 23, "637, compared to 393 as of June 30, 2024")]],
             ["group level（集团）", "直营", "637（2025-06-30）vs 393（2024-06-30）"],
             ["637为海外直营（海外直营579）", "637为全部门店模式合计"],
             "集团直营口径与p14海外品牌直营口径并存；主体范围错换是绑定失败模式。"),
        fact("selling-expense-us-investment", "normal", "required_business", "actual",
             "period_flow", "company_filing",
             [[anchor(cid, 23, "RMB2,181.0 million"),
               anchor(cid, 23, "increased by 43.3% year")]],
             ["人民币百万元", "截至2025年6月30日止六个月", "43.3%为费用同比"],
             ["43.3%为收入增长", "单季口径", "美元单位"],
             "费用叙述带期间与币种；美国市场为费用增长归因（strategic overseas markets such as the U.S.）。"),
    ],
    "misread_traps": [
        {"page": 14, "kind": "stock_vs_flow_table",
         "note": "p14 表格三模式各设 期初/期内净增加/期末 三行；行错位即存量/净增混淆。",
         "exact_quote": "期內門店數量的淨增加"},
        {"page": 14, "kind": "bilingual_duplication",
         "note": "p14 同页中英双语并排（同一事实两份文本）；重复引用或双语数错位均属引文范围过宽。",
         "exact_quote": "Store operations in overseas markets"},
        {"page": 23, "kind": "scope_shift",
         "note": "p23 的637为集团直营，与p14的579（名创品牌海外直营）口径不同、数字接近，易错换。",
         "exact_quote": "on the group level"},
    ],
    "prior_use": src["prior_use"],
    "notes": "110页中期报告（双语）；physical pages 14、23（PDF 1基）。无侧车（source_registered=false），解析走 dropbox_stock 根+SHA。与 hk-annual gold（2024年报）同公司不同原件；新增证据为 H1 2025 存量/净增与集团口径。",
})

# ---------------------------------------------------------------- 10 MINISO call
cid = "du10gs-call-miniso-q4-2024"
src = BY_ID[cid]
CASES.append({
    "schema_version": "du10-summary-goldset-case/1",
    "case_id": cid,
    "created": "2026-10-17",
    "market": "HK",
    "company": "名创优品",
    "doc_type": "call_transcript",
    "carrier": ".pdf",
    "language": "zh",
    "narrative_focus": "overseas+management_plan",
    "bound_failure_mode": "讲稿量词丢失；2025计划当已实现；说话人归属",
    "source_ref": {
        "carrier_root": "dropbox_stock",
        "source_id": "消费品/名创优品/December Quarter and Full Year of 2024  Transcript.pdf",
        "source_sha256": src["sha256"],
        "mime_type": "application/pdf",
        "registered_sidecar": {"market": "HK", "security_id": "Unresolved (dropbox_stock)",
                               "source_title": "December Quarter and Full Year of 2024  Transcript"},
    },
    "summary_proposition": "叶国富（董事长）讲稿：截至2024年12月31日集团全球门店7,780家、全年净增1,219家（MINISO中国+460、海外+631、TOP TOY+128），均超额完成2024年初开店目标；海外超3,100家门店、贡献接近40%收入；集团收入增长23%、约170亿人民币；2025年已筹划超过90档IP上新。",
    "allowed_summary": [
        "管理层讲稿：截至2024年12月31日，集团全球门店7,780家，全年净增1,219家，其中MINISO中国增长460家、海外增长631家、TOP TOY增长128家，均超额完成2024年初开店目标。",
        "管理层讲稿：名创海外市场超3,100家门店，为集团贡献接近40%的收入；集团全年收入增长23%、约170亿人民币。",
        "管理层讲稿：2025年已筹划超过90档IP上新（计划）。",
    ],
    "summary_guidence_placeholder_removed": None,
    "summary_guidance": {
        "must_preserve": ["说话人（叶国富/董事长）与讲稿形态", "超过3,100/接近40%/约170亿三个量词", "净增口径", "“筹划”（2025计划）"],
        "boundary": ["量词不得删（恰值化）", "开店目标数值原文未给，不得反推", "计划（90档IP上新）不得写成已完成", "讲稿数字与审计年报数字不得互串"],
    },
    "facts": [
        fact("global-stores-and-net-adds", "critical", "required_business", "actual",
             "count", "management_prepared",
             [[anchor(cid, 3, "截止2024年12月31日，集团全球门店达到7,780家，全年净增"),
               anchor(cid, 3, "7,780")]],
             ["截止2024年12月31日", "净增1,219家", "集团全球口径"],
             ["7,780为期初数", "直营门店数"],
             "讲稿头句；存量与净增同句。"),
        fact("brand-split-net-adds-beat-target", "critical", "required_business", "actual",
             "count", "management_prepared",
             [[anchor(cid, 3, "MINISO海外增长631家，TOPTOY增长128家，均超额完成2024年初开店目标")]],
             ["三分口径（中国/海外/TOP TOY）", "“超额完成2024年初开店目标”"],
             ["目标数值（原文未给，不得反推）", "门店增长写成收入增长"],
             "actual对照计划的成功表述；但目标数值不在文中，摘要不得补数。"),
        fact("overseas-share-hedged", "critical", "required_business", "actual",
             "ratio", "management_prepared",
             [[anchor(cid, 3, "名创在海外市场拥有超过3,100家门店，为集团贡献了接近40%的收入"),
               anchor(cid, 3, "助力集团整体收入增长23%，达到约170亿人民币")]],
             ["超过3,100家", "接近40%", "约170亿人民币", "增长23%"],
             ["恰为3,100家/40%/170亿", "量词删除", "美元"],
             "出海贡献叙述带三个量词；量词是准确性的组成部分。"),
        fact("ip-pipeline-2025-plan", "critical", "required_business", "plan",
             "count", "management_prepared",
             [[anchor(cid, 4, "今年我们已经筹划了超过90档IP上新，覆盖了从常青、潜力到强属性等不同类别")]],
             ["“筹划”（计划）", "超过90档", "2025年"],
             ["已完成90档上新", "90档为2024年实绩"],
             "管理层2025计划；写成已实现即 planned/actual 错引。"),
        fact("currency-statement", "normal", "disposition_context", "actual",
             "unknown", "management_prepared",
             [[anchor(cid, 2, "除非另有说明，货币单位均为人民币")]],
             ["币种声明"],
             ["默认美元"],
             "讲稿币种约定锚。"),
    ],
    "misread_traps": [
        {"page": 3, "kind": "prepared_remarks",
         "note": "本件为公司官方业绩电话会讲稿（management prepared remarks），页眉“叶董讲稿”；是公司口径但非审计文件。",
         "exact_quote": "2024 年全年财报电话会议 叶董讲稿"},
        {"page": 4, "kind": "plan_language",
         "note": "p4 渠道/产品/IP三段均为2025年策略与计划叙述（“正在”“筹划”“将成为”）。",
         "exact_quote": "我们正在对渠道和加盟商结构进行优化"},
    ],
    "prior_use": src["prior_use"],
    "notes": "16页讲稿；physical pages 2-4（PDF 1基）。与hk-annual gold同公司不同原件；新增证据为话轮/讲稿形态+actual超额对照+2025计划。",
})

# ---------------------------------------------------------------- 11 VRSK 10-Q
cid = "du10gs-us-10q-vrsk"
src = BY_ID[cid]
CASES.append({
    "schema_version": "du10-summary-goldset-case/1",
    "case_id": cid,
    "created": "2026-10-17",
    "market": "US",
    "company": "Verisk Analytics",
    "doc_type": "form_10q",
    "carrier": ".htm",
    "language": "en",
    "narrative_focus": "main_business",
    "bound_failure_mode": "insurance 收入范围当总收入；non-GAAP 当 GAAP；approximately 丢失",
    "source_ref": {
        "carrier_root": "dayu_portfolio",
        "source_id": "VRSK/filings/fil_0001437749-26-013729/vrsk20260331_10q.htm",
        "source_sha256": src["sha256"],
        "mime_type": "text/html",
        "registered_sidecar": {"market": "HK", "security_id": "VRSK",
                               "source_title": "vrsk20260331_10q"},
    },
    "summary_proposition": "2026Q1 10-Q MD&A：截至2026年3月31日止三个月，约84%的保险（insurance）收入来自托管订阅（协议一般一至五年），2025年同期约83%；约16%/17%来自交易型与咨询/顾问服务；EBITDA为非GAAP指标（净利加回利息、所得税、折旧摊销）。",
    "allowed_summary": [
        "Verisk 2026Q1（截至2026年3月31日止三个月）约84%的保险收入来自托管订阅（协议一般一至五年），上年同期约83%。",
        "EBITDA是公司使用的非GAAP指标（净利加回利息费用、所得税准备及折旧摊销），公司提示其作为分析工具的局限。",
    ],
    "summary_guidance": {
        "must_preserve": ["insurance revenues 范围（非总收入）", "approximately（约）", "三个月期间与两年对比", "EBITDA non-GAAP 属性"],
        "boundary": ["84%不得写成总收入占比（公司另有能源与专业市场等收入）", "EBITDA不得写成GAAP经营利润或净利", "订阅占比不得写成订阅收入金额"],
    },
    "facts": [
        fact("insurance-subscription-share", "critical", "required_business", "actual",
             "ratio", "company_filing",
             [[anchor(cid, None, "approximately 84% and 83% of our insurance revenues were derived from hosted subscriptions through agreements (generally one to five years) for our solutions, respectively.", kind="document")]],
             ["insurance revenues 范围", "approximately", "三个月（Q1）期间", "2026 vs 2025（84%/83%）"],
             ["84%为总收入占比", "84%为订阅收入金额", "期间为全年"],
             "商业模式叙述；“insurance revenues”是公司分部口径下的子集，范围错换即主体错引。"),
        fact("transactional-advisory-share", "normal", "required_business", "actual",
             "ratio", "company_filing",
             [[anchor(cid, None, "approximately 16% and 17% of our insurance revenues were derived from providing transactional and advisory/consulting solutions, respectively.", kind="document")]],
             ["16%/17% 交易型+咨询", "保险收入口径", "两年对比"],
             ["16%为全部收入的交易占比", "与84%相加后写成一个口径"],
             "与订阅占比互补（84%+16%≈100%，83%+17%=100%）；两行必须同口径引用。"),
        fact("ebitda-non-gaap-definition", "normal", "disposition_context", "actual",
             "unknown", "company_filing",
             [[anchor(cid, None, "EBITDA is defined as net income before interest expense, provision for income taxes, and depreciation and amortization of fixed and intangible assets", kind="document")]],
             ["非GAAP属性", "定义（净利+利息+所得税+折旧摊销）"],
             ["EBITDA为GAAP指标", "EBITDA等于经营利润或净利"],
             "指标定义叙述；摘要引用EBITDA必须带non-GAAP标识。"),
        fact("total-revenue-q1-2026", "normal", "correctness_if_emitted", "actual",
             "period_flow", "company_filing",
             [[anchor(cid, None, "Total revenues $ 782.6 $ 753.0", kind="document")]],
             ["百万美元", "三个月", "782.6 vs 753.0（+3.9%）"],
             ["单位为人民币", "全年口径"],
             "若摘要引用总收入数字，以本表为准（单位百万美元、Q1三个月）。"),
    ],
    "misread_traps": [
        {"page": None, "kind": "scope_insurance_vs_total",
         "note": "MD&A 同时讨论 insurance revenues 占比与 total revenues；两者范围不同。",
         "exact_quote": "Total revenues"},
        {"page": None, "kind": "printed_page_markers",
         "note": "HTML 无物理页；正文嵌有打印页码提示（26/27/28）与 Table of Contents 链接文本。锚点按 location_kind=document 全文空白归一化匹配。",
         "exact_quote": "Table of Contents"},
    ],
    "prior_use": src["prior_use"],
    "notes": "10-Q Q1 2026（period 2026-03-31）。锚点 location_kind=document。侧车market=HK为登记误值（实为US/NASDAQ:VRSK），已如实记录，case以文档内容为准。",
})

# ---------------------------------------------------------------- write + verify
os.makedirs(CASES_DIR, exist_ok=True)
# resolve absolute paths per case from bindings recorded in freeze
errors = []
budget = {}
for case in CASES:
    cid = case["case_id"]
    meta = BY_ID[cid]
    path = meta["path"]
    if sha256_file(path) != meta["sha256"]:
        errors.append(f"{cid}: SHA mismatch vs freeze")
    carrier = case["carrier"]
    doc_norm = None
    for f in case["facts"]:
        for group in f["any_support_sets"]:
            for a in group:
                text = page_text(path, a.get("page"), carrier)
                if norm(a["exact_quote"]) not in norm(text):
                    errors.append(f"{cid}/{f['id']}: anchor not found: {a['exact_quote'][:40]}")
                doc_norm = (doc_norm or 0) + len(norm(a["exact_quote"]))
    trap_chars = 0
    for t in case.get("misread_traps", []):
        q = t.get("exact_quote")
        if q:
            text = page_text(path, t.get("page"), carrier)
            if norm(q) not in norm(text):
                errors.append(f"{cid}/trap: anchor not found: {q[:40]}")
            trap_chars += len(norm(q))
    budget[cid] = doc_norm + trap_chars
    case["quote_budget_chars_normalized"] = doc_norm + trap_chars
    case["bound_failure_mode_check"] = case["bound_failure_mode"]

if errors:
    print("ANCHOR ERRORS:")
    for e in errors:
        print(" -", e)
    raise SystemExit(1)

# placeholder cleanup (typo guard)
for case in CASES:
    case.pop("summary_guidence_placeholder_removed", None)

index_cases = []
for case in CASES:
    cid = case["case_id"]
    out = os.path.join(CASES_DIR, cid + ".json")
    with open(out, "w", encoding="utf-8", newline="\n") as f:
        json.dump(case, f, ensure_ascii=False, indent=1, sort_keys=False)
        f.write("\n")
    index_cases.append({
        "case_id": cid,
        "file": f"cases/{cid}.json",
        "market": case["market"],
        "doc_type": case["doc_type"],
        "narrative_focus": case["narrative_focus"],
        "source_sha256": case["source_ref"]["source_sha256"],
        "quote_budget_chars_normalized": case["quote_budget_chars_normalized"],
    })

index = {
    "schema_version": "du10-summary-goldset-index/1",
    "card": "DU10-CWP-SUMMARY-GOLDSET",
    "created": "2026-10-17",
    "case_count": len(index_cases),
    "unique_originals": len({c["source_sha256"] for c in index_cases}),
    "cases": index_cases,
    "coverage_matrix": {
        "CN": ["annual_report", "interim_report", "quarterly_report", "ipo_prospectus",
               "convertible_bond_prospectus", "ir_minutes"],
        "HK": ["ipo_prospectus", "interim_report", "call_transcript"],
        "US": ["form_10q"],
        "not_available_new": [
            "CN call TXT new original (only CWP-local TXT already covered by us-txt; ET repo outside repo boundary)",
            "HK quarterly announcement new original (du5 kingsoft coverage exists)",
        ],
    },
}
with open(os.path.join(CASES_DIR, "index.json"), "w", encoding="utf-8", newline="\n") as f:
    json.dump(index, f, ensure_ascii=False, indent=1)
    f.write("\n")

print(f"wrote {len(index_cases)} cases; anchors all verified; unique originals={index['unique_originals']}")
for c in index_cases:
    print(f"  {c['case_id']:38s} {c['market']:2s} {c['doc_type']:28s} q={c['quote_budget_chars_normalized']}B")
