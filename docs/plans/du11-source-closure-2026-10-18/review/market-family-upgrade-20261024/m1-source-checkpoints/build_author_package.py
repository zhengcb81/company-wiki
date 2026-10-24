"""Source-authored development gold revision; no product imports or selection.

Author QA is compatibility/anchor evidence, not independent acceptance.
"""
from __future__ import annotations

import copy
import gzip
import hashlib
import json
import re
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

from tools.document_understanding_benchmark.contamination import support_set_digest
from tools.document_understanding_benchmark.evaluate import evaluate
from tools.document_understanding_benchmark.gold import load_gold, load_gold_dir
from tools.document_understanding_benchmark.tests.anchor_verify import extract_text_pages, verify_gold_anchors
from tools.document_understanding_benchmark.textutil import text_contains

HERE = Path(__file__).resolve().parent
ROOT = next(p for p in HERE.parents if (p / "pyproject.toml").exists())
OLD = ROOT / "tools/document_understanding_benchmark/gold"
IDS = ("du5-cn-proya-q1", "du5-hk-kingsoft-interim", "du5-cn-gbits-call", "du5-us-msft-ex991")
P, H, G, M = IDS


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def dump(path, value):
    Path(path).write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def compact(s):
    return re.sub(r"\s+", "", s).casefold()


class Sources:
    def __init__(self):
        self.bindings = json.loads((HERE / "source-bindings.json").read_text(encoding="utf-8"))
        self.pages = {}
        for sid in IDS:
            entry = self.bindings[sid]
            assert sha(entry["original_path"]) == entry["source_sha256"]
            assert sha(ROOT / entry["old_gold_path"]) == entry["old_gold_sha256"]
            self.pages[sid] = extract_text_pages(Path(entry["original_path"]))

    def q(self, sid, needle, page=None):
        """Return the real source substring, retaining original line breaks."""
        text = self.pages[sid][page]
        chars, positions = [], []
        for index, ch in enumerate(text):
            if not ch.isspace():
                chars.append(ch.casefold())
                positions.append(index)
        start = "".join(chars).find(compact(needle))
        if start < 0:
            raise AssertionError((sid, page, needle))
        end = start + len(compact(needle))
        quote = text[positions[start]:positions[end - 1] + 1]
        assert text_contains(text, quote)
        return {"exact_quote": quote, **({"page": page, "location_kind": "page"}
                                      if page else {"location_kind": "document"})}

    def speaker(self, needle):
        text = self.pages[G][None]
        loc = text.find(needle)
        assert loc >= 0
        matches = list(re.finditer(r"说话人[12]\s+\d{2}:\d{2}", text[:loc + 1]))
        assert matches, needle
        return self.q(G, matches[-1].group())


def main():
    source = Sources()
    revisions = {sid: copy.deepcopy(json.loads((OLD / f"{sid}.json").read_text(encoding="utf-8"))) for sid in IDS}
    reasons = {}

    def setfact(sid, fid, specs, must, why, **updates):
        fact = next(f for f in revisions[sid]["facts"] if f["id"] == fid)
        # The list is ONE sufficient joint source set; it is never one OR per fragment.
        fact["any_support_sets"] = [[source.q(sid, text, page) for page, text in specs]]
        fact["must_preserve"] = must
        fact["reason"] = why
        fact.update(updates)
        reasons[(sid, fid)] = why
        return fact

    # CN quarter: exact finance remains conditional; retain every old importance/counterexample.
    flow = (1, "本报告期\n上年同期\n本报告期比上年\n同期增减变动幅\n度(%)")
    unit = (1, "单位：元\n币种：人民币")
    quarter = (1, "珀莱雅化妆品股份有限公司\n2026 年第一季度报告")
    setfact(P, "report-period-unaudited-identity", [quarter, (8, "合并利润表\n2026 年1—3 月"),
            (12, "特此公告\n珀莱雅化妆品股份有限公司董事会\n2026 年4 月20 日")],
            ["2026 年第一季度报告", "2026 年1—3 月", "珀莱雅化妆品股份有限公司", "2026 年4 月20 日"],
            "公司、流量期间和发布日期互为补充，必须联合；落款不能单独替代财报期间。归元数据通道。")
    setfact(P, "statements-unaudited-no-new-standards", [
        (1, "第一季度财务报表是否经审计\n□是√否"),
        (6, "2026 年3 月31 日\n编制单位：珀莱雅化妆品股份有限公司\n单位：元\n币种:人民币\n审计类型：未经审计"),
        (12, "(三)2026 年起首次执行新会计准则或准则解释等涉及调整首次执行当年年初的财务报表\n□适用√不适用")],
        ["□是√否", "未经审计", "2026 年3 月31 日", "□适用√不适用"],
        "联合未审计勾选/报表属性和首次执行导致期初调整不适用；不把不适用扩大成没有任何新准则。")
    for fid, page, row, must in [
        ("q1-revenue-yoy-decline", 1, "营业收入\n2,305,344,625.43\n2,359,334,894.91\n-2.29",
         ["2,305,344,625.43", "2,359,334,894.91", "-2.29", "本报告期", "元"]),
        ("attributable-net-profit-q1", 1, "归属于上市公司股东的净\n利润\n366,686,734.14\n390,281,697.93\n-6.05",
         ["366,686,734.14", "390,281,697.93", "-6.05", "归属于"]),
        ("operating-cash-flow-collapse", 2, "经营活动产生的现金流量\n净额\n106,971,167.62\n675,490,380.59\n-84.16",
         ["106,971,167.62", "675,490,380.59", "-84.16", "本报告期"]),
    ]:
        setfact(P, fid, [quarter, unit, flow, (page, row)], must,
                "精确财务数若输出须同时有一季度、元、本期/上年同期及带符号完整数值；不同精度/缺同比行不是充分替代。保留重要性与错误数字反例。")
    setfact(P, "deducted-net-profit-and-nonrecurring-total", [quarter, unit, flow,
        (2, "归属于上市公司股东的扣\n除非经常性损益的净利润\n341,157,237.18\n378,934,039.06\n-9.97"),
        (2, "非经常性损益项目\n本期金额\n说明"), (3, "合计\n25,529,496.96")],
        ["341,157,237.18", "378,934,039.06", "-9.97", "扣除非经常性损益", "本期金额", "25,529,496.96"],
        "扣非行、非经常性本期金额列头及合计互补AND；只表名不能证明精确扣非/非经常总额。")
    setfact(P, "cash-flow-drop-driver", [(3, "2026 年第一季度报告"),
        (3, "项目名称\n变动比例（%）\n主要原因\n经营活动产生的现金流\n量净额\n-84.16\n主要系收回货款减少以及支付的\n推广费增加。")],
        ["收回货款减少", "推广费增加", "-84.16"],
        "经营解释本体包含下降对象/幅度与双原因，非原因标题OR。保留required_business和normal重要性，不要求三张主表全选。")
    setfact(P, "eps-basic-diluted-unit", [quarter, flow,
        (2, "基本每股收益（元/股）\n0.93\n0.99\n-6.06"),
        (2, "稀释每股收益（元/股）\n0.93\n0.99\n-6.06")],
        ["0.93", "0.99", "元/股", "-6.06", "基本", "稀释"],
        "基本与稀释相等这一合取事实须两行共同支持；只一行不能证明另一行。季度和每股单位仍绑定。")
    setfact(P, "total-assets-point-in-time", [unit,
        (2, "本报告期末\n上年度末\n本报告期末比上\n年度末增减变动\n幅度(%)"),
        (2, "总资产\n8,912,125,388.70\n8,487,416,240.25\n5.00"),
        (6, "项目\n2026 年3 月31 日\n2025 年12 月31 日")],
        ["8,912,125,388.70", "8,487,416,240.25", "5.00", "本报告期末", "上年度末"],
        "存量金额行、期末/上年末标签及两日期联合；不能把缺数表头当作完整资产支持。")
    setfact(P, "share-capital-and-buyback-holdings", [(8, "实收资本（或股本）\n395,976,008.00\n395,975,998.00"),
        (6, "合并资产负债表\n2026 年3 月31 日\n编制单位：珀莱雅化妆品股份有限公司\n单位：元"),
        (6, "项目\n2026 年3 月31 日\n2025 年12 月31 日"),
        (5, "截至本报告期末，公司回购专用证券账户中持有公司股份3,757,848 股，占公司总股本的0.95%")],
        ["395,976,008.00", "395,975,998.00", "3,757,848 股", "0.95%", "2026 年3 月31 日"],
        "股本货币额与回购持股数是两个量纲，联合而非OR。原件未给面值/发行因果，不能把股本10元差额推成10股或激励发行。", quantity_basis="unknown")

    # HK interim: precise finance is conditional; filing metadata stays context;
    # real business causal descriptions/structure/plans remain required.
    hperiod = (5, "截至二零二五年六月三十日止六個月的財務摘要")
    hhead = (5, "截至六月三十日止六個月\n同比變動\n二零二四年\n二零二五年\n人民幣千元\n人民幣千元\n%")
    htable = (12, "（除股數和每股數據外，所有金額以千計）\n截至六月三十日止六個月\n二零二四年\n二零二五年\n二零二五年\n人民幣\n人民幣\n美元")
    setfact(H, "total-revenue-h1-2025", [hperiod, hhead, (5, "收入\n3,667,464\n4,319,204\n17.8%")],
        ["4,319,204", "人民幣千元", "17.8%", "3,667,464"],
        "精确财报总额属correctness_if_emitted，与CN季报普通财务数同责；保留critical与全部单位/负方向反例。圆整百万元文字不是精确千元表的充分OR。", target_kind="correctness_if_emitted")
    setfact(H, "segment-revenue-split", [hperiod, htable,
        (12, "公有雲服務\n2,421,912\n2,978,788\n415,823"),
        (12, "行業雲服務\n1,245,400\n1,340,416\n187,115")],
        ["2,978,788", "1,340,416", "公有雲服務", "行業雲服務", "千計"],
        "本项仅精确分业务金额，条件输出与CN财务金额同责；两行+三币种/年度列头联合。业务分类/驱动另有required检查，不因降精度假称整业务缺失。", target_kind="correctness_if_emitted")
    setfact(H, "net-loss-us-gaap-widened", [hperiod, hhead, (5, "淨虧損\n(717,334)\n(772,973)\n7.8%"),
        (5, "未經審計中期簡明合併財務資料乃根據美國公認會計準則（「美國公認會計準則」）編製。")],
        ["(772,973)", "717,334", "淨虧損", "7.8%", "千元"],
        "亏损精确数为条件输出，critical/数字反例不降级；金额符号、同比、会计基础、期间与币种同包，经营亏损不能替代净亏损。", target_kind="correctness_if_emitted")
    setfact(H, "us-gaap-basis-not-ifrs", [hperiod,
        (67, "未經審計中期簡明財務報表乃根據美國公認會計準則編製，在若干方面有別於《國際財務報告準則》")],
        ["美國公認會計準則", "《國際財務報告準則》", "未經審計"],
        "会计框架/审计状态为document_meta disposition_context，保留critical；IFRS对账句自身同时支持USGAAP与差异，不以仅USGAAP一句代替完整差异命题。", target_kind="disposition_context")
    setfact(H, "unit-and-fx-convention", [hperiod, htable,
        (45, "（金額以人民幣千元（「人民幣」）及千美元（「美元」）列示，股份數目及每股數據除外）"),
        (45, "美元金額乃為方便讀者而呈列，並於二零二五年六月三十日在紐約市就經紐約聯邦儲備銀行海關核證的\n人民幣電匯轉賬以人民幣7.1636元兌1.00美元的中午買入匯率換算。概不表示人民幣金額可以或可能\n按該匯率兌換為美元。")],
        ["千計", "7.1636", "人民幣千元", "美元", "概不表示"],
        "千元列头、股数例外与便捷美元换算/不可当实际兑换须联合，属于数值消费的元数据责任，critical不变。", target_kind="disposition_context")
    setfact(H, "gross-margin-decline", [hperiod,
        (13, "毛利為人民幣657.2百萬元（91.7百萬美元），較二零二四年同期的人民幣611.6百萬元增加7.4%。"),
        (13, "毛利率為15.2%，而二零二四年同期則為16.7%。該減\n少主要是由於隨著AI業務擴張，服務器成本增加，以及若干客戶的進一步營收活動所產生的前期成本。")],
        ["毛利", "15.2%", "16.7%", "服務器成本增加", "前期成本"],
        "保留required_business：毛利额改善而利润率下降及AI服务器/客户前期成本经营解释；完整方向与原因联合，利润率与纯金额不互为OR。精确千元额另属财务责任。")
    setfact(H, "adjusted-ebitda-nongaap", [hperiod,
        (14, "非公認會計準則EBITDA為人民幣724.6百萬元（101.1百萬美元），較二零二四年同期的人民幣93.8百萬元增\n加672.6%。")],
        ["非公認會計準則", "724.6", "101.1", "百萬元"],
        "普通非GAAP财务金额为correctness_if_emitted，若输出仍需非GAAP/币种/规模/期间，不强制叙述引入财务盈利指标。", target_kind="correctness_if_emitted")
    setfact(H, "capex-vs-revenue", [
        (41, "截至二零二四年及二零二五年六月三十日止六個月\n未經審計中期簡明合併現金流量表\n（金額以人民幣千元（「人民幣」）及千美元（「美元」）列示，股份數目及每股數據除外）"),
        (41, "截至六月三十日止六個月\n二零二四年\n二零二五年\n二零二五年\n人民幣\n人民幣\n美元"),
        (41, "投資活動產生的現金流量\n購買物業及設備及預付款項\n(1,866,298)\n(1,483,742)\n(207,123)")],
        ["1,483,742", "1,866,298", "千元", "購買物業及設備"],
        "现金购置支出只有投资现金流原行及完整列头支持；删除折旧摊销替代，不把cash capex与费用/收入互证。critical与全部错误数字反例保留，条件输出与其他财务数同责。", target_kind="correctness_if_emitted")
    setfact(H, "no-material-investments-or-capex-plans", [
        (15, "截至二零二五年六月三十日，本集團並無持有任何重大投資（包括對被投資公司的任何投資價值佔本集團截\n至二零二五年六月三十日總資產的5%或以上）。截至二零二五年六月三十日，本集團並無任何未來重大投資\n及資本資產計劃。")],
        ["並無", "重大投資", "5%", "資本資產計劃"],
        "现有重大投资阈值与未来重大计划两否定须同包，不以不完整前半句替代；不将普通AI购置活动与公告重大投资计划混同。")
    setfact(H, "h2-2025-business-outlook", [hperiod,
        (11, "展望下半年，我們將維持高質量發展和可持續發展戰略，不斷投資技術研發，並全面提升AI能力。同時，我\n們將積極擁抱AI時代小米和金山生態系統的雲需求。")],
        ["展望下半年", "將", "戰略", "AI"],
        "下半年AI/小米金山生态需求方向是业务计划，不是元数据，改required_business且normal不变；不能当已实现业绩。", target_kind="required_business")
    setfact(H, "single-operating-segment", [
        (50, "本集團整體表現的決策時審閱合併經營業績，因此本集團僅有一個經營分部。"),
        (50, "本集團的大部分收入來自中國內地，且本集團的大部分長期資產位於中國內地，因此並無呈列地區分\n部。")],
        ["一個經營分部", "並無呈列地區分"],
        "一经营分部与不列地区分部是互补结构定义，联合支持；不能把公有云/行业云收入分类误当可报告分部。保留旧重要性。", target_kind="required_business")
    setfact(H, "related-party-revenue", [
        (64, "（金額以人民幣千元（「人民幣」）及千美元（「美元」）列示，股份數目及每股數據除外）"),
        (64, "截至六月三十日止六個月\n二零二四年\n二零二五年\n二零二五年\n人民幣\n人民幣\n美元"),
        (64, "收益：\n向小米集團提供公有雲服務\n490,133\n772,761\n107,873\n向金山軟件集團提供公有雲服務\n136,596\n173,094\n24,163\n向其他關聯方提供公有雲服務\n232\n336\n47\n向小米集團提供行業雲服務\n67,117\n171,315\n23,915\n向金山軟件集團提供行業雲服務\n7,996\n7,855\n1,097\n向其他關聯方提供行業雲服務\n16\n–\n–\n向其他關聯方提供其他服務\n291\n97\n14\n702,381\n1,125,458\n157,109")],
        ["小米集團", "772,761", "1,125,458", "千元"],
        "条件财务金额：小米公有云772761与全部关联方收入1125458分母不同；完整科目/列头联合，不把总关联收入说成小米收入。", target_kind="correctness_if_emitted")
    setfact(H, "interim-period-meta", [hperiod,
        (5, "未經審計中期簡明合併財務資料乃根據美國公認會計準則（「美國公認會計準則」）編製。")],
        ["截至二零二五年六月三十日止六個月", "未經審計"],
        "期间元数据只约束六个月/未审计，剔除无关采购承诺630000的错误OR与must。该采购业务事实及单位反例迁移至独立合同阶段，未遗失来源责任。", target_kind="disposition_context")
    migrated_commitment_counterexample = "採購承諾金額為人民幣630,000元整（非千元列示基準）"
    next(f for f in revisions[H]["facts"] if f["id"] == "interim-period-meta")["must_not_assert"].remove(migrated_commitment_counterexample)
    new_h = [
        dict(id="cloud-revenue-operating-drivers", importance="critical", target_kind="required_business",
             quantity_basis="unknown", modality="actual", role="company_filing", fact_scope="narrative",
             any_support_sets=[[source.q(H, t, pg) for pg, t in [hperiod,
                 (9, "該增加主要是由於AI相關客戶收入增長強勁及我們擴展行業雲項目，但部分被我們主動縮減提供予\n內容分發網絡(CDN)客戶的服務規模所抵銷。")]]],
             must_preserve=["AI", "行業雲項目", "主動縮減", "CDN", "抵銷"],
             must_not_assert=["金山雲所有業務增長均來自AI且沒有抵銷因素", "CDN服務擴張是收入增長的主要原因"],
             reason="源侧新增关键经营因果：AI客户与行业云扩张、主动缩减CDN的抵销必须同时保留；补正金融数责任拆分，不以降分母取绿。"),
        dict(id="cloud-service-growth-causal-split", importance="critical", target_kind="required_business",
             quantity_basis="unknown", modality="actual", role="company_filing", fact_scope="narrative",
             any_support_sets=[[source.q(H, t, pg) for pg, t in [hperiod,
                 (13, "來自公有雲服務的收入由二零二四年同期的人民幣2,421.9百萬元增加23.0%至人民幣2,978.8百萬元\n（415.8百萬美元）。該同比增加主要是由於AI相關服務增長。"),
                 (13, "來自行業雲服務的收入為人民幣1,340.4百萬元（187.1百萬美元），較二零二四年同期的人民幣1,245.4\n百萬元增加7.6%。該同比增加主要是由於不斷增長的IT需求及我們向垂直行業客戶複製行業解決方案\n的能力。")]]],
             must_preserve=["公有雲服務", "AI相關服務增長", "行業雲服務", "IT需求", "垂直行業客戶"],
             must_not_assert=["行業雲收入增長23.0%", "公有雲增長全部因垂直行業方案複製且與AI無關"],
             reason="按真实业务主体分开增长驱动，避免兄弟业务归因串线；数字在源包中保留但不要求把全表精度塞进叙述。"),
        dict(id="idc-purchase-commitment-stage", importance="normal", target_kind="required_business",
             quantity_basis="unknown", modality="actual", role="company_filing", fact_scope="narrative",
             any_support_sets=[[source.q(H, "（金額以人民幣千元（「人民幣」）及千美元（「美元」）列示，股份數目及每股數據除外）", 66),
                                source.q(H, "於二零二五年六月一日，本集團簽訂一份不可取消一年期互聯網數據中心服務協議，據此，本集團作出\n合同最低採購承諾，總金額為人民幣630,000元（87,945美元）。截至二零二五年六月三十日，剩餘採\n購承諾金額為人民幣576,101元（80,421美元）。", 66)]],
             must_preserve=["二零二五年六月一日", "不可取消一年期", "服務協議", "630,000", "576,101", "人民幣千元"],
             must_not_assert=["一年期IDC採購承諾已成為公司收入", "金山雲已完成全部IDC服務採購履約", migrated_commitment_counterexample],
             reason="保留原period-meta错误OR曾引用的采购责任为独立业务合同阶段，完整金额原话与全节千元说明联合，迁移原错误单位反例；不凭正文元字抹去全节单位，也不自造已履约/收入。"),
    ]
    revisions[H]["facts"].extend(new_h)
    for f in new_h:
        reasons[(H, f["id"])] = f["reason"]

    # Anonymous DOCX: speaker labels are source evidence, not verified identities.
    def gfact(fid, fragments, must, why, **updates):
        speaker = source.speaker(fragments[0])
        fact = setfact(G, fid, [(None, t) for t in fragments], must, why,
                       role="unknown", require_same_scope=True, **updates)
        fact["any_support_sets"][0].insert(0, speaker)
        if speaker["exact_quote"].split()[0] not in fact["must_preserve"]:
            fact["must_preserve"].insert(0, speaker["exact_quote"].split()[0])
        return fact

    gfact("yy-flow-decline-premise", ["然后我们一念今年在如果相对趋缓一些竞争的一个环境下，流水是否还有一定的回升的空间？"],
        ["流水是否还有一定的回升的空间", "如果相对趋缓"],
        "匿名说话人1提出条件性问题，不确认其分析师身份；speaker/问题/条件须同scope，斜线角色注释与省略号不是原文must。保留旧公司确认反例。")
    gfact("steam-activity-premise", [
        "然后我看现在每天的活跃人次，根据就steam时代上面的监测的话，我们一直是有这样过万的一个活跃，从绝对值可能不太准确，但是趋势是相对稳定的。",
        "不没有，因为就初期的大量的负面评价，然后我们用户的活跃出现明显滑坡"],
        ["steam时代", "从绝对值可能不太准确", "过万"],
        "匿名说话人1外部监测/追问的两片互补，不将steam时代强修成SteamDB；ASR不没有保留，不认公司披露用户指标。")
    gfact("lei-ting-profit-analyst-inference", [
        "我看了一下我们雷霆这边就是q三的利润是1.17亿，然后q4的话是1.8亿",
        "因为他是不没有单季度的，只有半年度的，但是我们从少数股东这边推出来"],
        ["1.17亿", "1.8亿", "从少数股东这边推出来"],
        "匿名说话人1的推算与数值必须联合，不能拿只数字片段当公司季报披露。角色字段unknown避免未经来源核身份。")
    gfact("yy-roi-decline-actual", [
        "但是去年上半年观察到 Oa明显的有比较大的下降",
        "相当于是从二三年下半年我们是主动买了买量的一个支出",
        "新增的这一块的话会采用一些创新的营销方式，但是买量这块比较大幅度的减少了。"],
        ["去年上半年", "Oa", "二三年下半年", "买量这块比较大幅度的减少了"],
        "下降/时间与清楚的买量减少句联合；保留Oa/买了原ASR，不声称已验证为ROI或将买了强修成减了。仅匿名说话人2陈述。", quantity_basis="unknown")
    gfact("buydown-cut-and-stock-operation-plan", [
        "往后的话其实整个产品的思路还是会延续，这个思路还是更多的去存量运营的一个思路去做。"],
        ["往后的话", "更多的去存量运营"],
        "本ID只跟随同一匿名说话人2回合的未来存量运营意向；另一26:44回合减少依赖改独立事实，不能把不同话题远距离拼成同task。无定量资本投资值，quantity_basis unknown。", modality="plan", quantity_basis="unknown")
    gfact("buydown-no-return-negation", ["那版本有一些新版本推出来的时候，会配合一些短期的买量，但整体来看的话，买量会不会再走到原来的水平了。"],
        ["短期的买量", "买量会不会再走到原来的水平了"],
        "保留原ID作修订追踪，但ASR会不会是歧义，不标确定否定或确定回升；无音频不能强修。unknown不是取消检查，仍禁止两向编造承诺。无定量资本投资值。", modality="unknown", quantity_basis="unknown")
    next(f for f in revisions[G]["facts"] if f["id"] == "buydown-no-return-negation")["must_not_assert"].extend([
        "公司明确承诺买量不会再回到原有水平", "公司明确承诺买量一定回到原有水平"])
    gfact("yy-stabilize-target-uncertain", [
        "所以后期的话我们希望能够在一个新的水平去稳住这款产品，但具体能在什么样的一个情况下稳住，目前也不太好判断，我们再观察一段时间看一下。"],
        ["希望", "目前也不太好判断", "再观察一段时间"],
        "意愿与明确不确定性同段AND，不把只含希望的短片作充分替代；匿名说话人2，不给企稳时间承诺。")
    gfact("outpost-update-plan-uncommitted", [
        "我们也会跟着这些节点再去集中推出一些更新迭代的版本，希望在那个时候能够去再推一波，但具体的计划还没有，最终落地可能还会有所变化。"],
        ["希望", "具体的计划还没有", "可能还会有所变化"],
        "更新意向+未落地+可能变化必须同片，拒绝只意向的OR；保留匿名说话人2回合，不把路线图说已锁定。")
    # Accounting comparison crosses two speaker2 turns interrupted by speaker1;
    # quote both specific marked turns rather than manufacturing one speech turn.
    f = setfact(G, "outpost-buyout-revenue-recognition", [
        (None, "说话人2 09:24这款的话会卖出卖出，然后会根据就看退货率的一个情况，会去做一个他是当即确认收入，但是会做一个利息负债什么类似的处理，"),
        (None, "说话人1 09:41它不像"),
        (None, "说话人2 09:42其他的消耗型道具一样，还要做一个递延。")],
        ["说话人2", "当即确认收入", "利息负债什么类似的处理", "它不像", "消耗型道具", "递延"],
        "09:24/09:41/09:42三个匿名短回合AND：说话人1的它不像是消耗型道具递延比较的否定连接，不能删去导致关系反转。role unknown且不伪造同回合；利息负债ASR不扩充成预计负债或退款负债，不能推出精确金额或无准备。", role="unknown", require_same_scope=False)
    f["must_not_assert"].extend(["公司明确披露了名为退款负债的金额", "原文已经确认利息负债就是预计负债"])
    gfact("outpost-stage-problems-resolved", [
        "现在大部分的情况是可以解决了，还有一些少数的我们也会持续的去跟进跟调整。"],
        ["大部分的情况是可以解决了", "少数", "持续的去跟进跟调整"],
        "分级现状与残余跟进同片，去除省略号编辑token；不扩成全部修复，匿名speaker2身份未验证。")
    gfact("strategy-category-unchanged-negation", ["品类上来看的话，目前没有一个很大的变化"],
        ["品类上", "没有一个很大的变化"],
        "局限品类没有很大变化，不能扩成所有战略毫无变化；匿名speaker2不作姓名/职务推断。")
    gfact("yy-user-base-scale", ["最开始我们现在整个大盘子有2000多用户，然后有一些流失再回来的"],
        ["整个大盘子", "2000多用户", "流失再回来"],
        "2000多用户存在ASR单位/指标含义歧义；quantity_basis/modality unknown，不填万、不解释成MAU/注册或精确人数。数值原话与匿名speaker2同scope。", quantity_basis="unknown", modality="unknown")
    extra = dict(id="buydown-dependence-reduction-intent", importance="critical", target_kind="required_business",
        quantity_basis="unknown", modality="plan", role="unknown", fact_scope="narrative", require_same_scope=True,
        any_support_sets=[[source.q(G, "说话人2 26:44"), source.q(G, "因为大趋势上它肯定不是我们希望我们会尽量的去减少对买量的一个依赖。")]],
        must_preserve=["说话人2", "希望", "尽量的去减少对买量的一个依赖"],
        must_not_assert=["公司已消除买量依赖", "说话人2称已经停止广告投放"],
        reason="从旧复合买量计划单独保留另一回合的减少依赖意向，仍critical，不因纠正OR漏掉责任；不将愿望写成完成。")
    revisions[G]["facts"].append(extra)
    reasons[(G, extra["id"])] = extra["reason"]

    # US exhibit: slide text, historical/adjusted and product definitions are joint.
    transition = "Beginning with FY27, we will transition from our current three reporting segments, Productivity and Business Processes, Intelligent Cloud, and More Personal Computing, to two segments: Agents and Infra and Devices and Consumer."
    setfact(M, "fy27-two-reporting-segments", [(None, transition)],
        ["two segments", "Agents and Infra", "Devices and Consumer", "FY27"],
        "完整will transition/FY27/旧三段/新两段同句，不用只旧三段短语当充分OR；保留前瞻而非已完成。")
    setfact(M, "prior-three-segments-retired", [(None, transition)],
        ["Productivity and Business Processes", "Intelligent Cloud", "More Personal Computing", "three"],
        "来源为FY27将转换，旧三段名字必须与transition语境同在，不能表述为已经完成全部更改。", modality="plan")
    setfact(M, "commercial-bookings-definition", [(None, "FY27 Investor Metric Definitions"), (None,
        "Commercial bookings growth: for commercial products and cloud services, sum of revenue growth, plus change in balance of unearned revenue plus the change in contracted not billed balance")],
        ["sum of revenue growth", "unearned revenue", "contracted not billed", "commercial", "FY27"],
        "FY27定义版本标题与商业范围/三项复合计算完整同句联合；删缺contracted-not-billed的OR，不将bookings当新签合同绝对额，也不无时点套用另一版本指标。")
    setfact(M, "commercial-rpo-definition", [(None, "FY27 Investor Metric Definitions"), (None,
        "Commercial remaining performance obligation: commercial portion of revenue allocated to remaining performance obligations, which includes unearned revenue and amounts that will be invoiced and recognized as revenue in future periods")],
        ["commercial portion", "remaining performance obligations", "unearned revenue", "future periods", "FY27"],
        "FY27版本标题与商业范围、未实现/未来开票及未来确认联合，不能只选名字/末半句或从不明时点指标反套本定义。")
    setfact(M, "seat-growth-includes-github", [(None, "FY27 Metric Updates"), (None,
        "Microsoft 365 commercial seat growth metric definition has been updated to include paid GitHub seats"),
        (None, "Microsoft 365 commercial seat growth: the number of Microsoft 365 Commercial seats and GitHub Cloud seats at end of period where seats are paid users covered by a Microsoft 365 Commercial subscription or GitHub subscription")],
        ["paid GitHub seats", "paid users", "end of period", "Microsoft 365 Commercial seats", "FY27"],
        "FY27版本标题、定义变化与付费/期末用户范围联合；业务机制定义改required_business，normal保留，不把座席定义当真实座席增量，也不将新范围用于旧已报增长率。", target_kind="required_business")
    mechanical = "we have provided mechanical adjustments only to our outlook as provided on July 29, 2026, for the changes discussed in this presentation."
    setfact(M, "fy27q1-outlook-mechanical-only", [(None, "FY27 Q1 Outlook"), (None, mechanical)],
        ["FY27 Q1", "mechanical adjustments only", "outlook", "July 29, 2026"],
        "指引期次+旧指引机械改列联合；不能作为9月新上调/下调指引。")
    azuredef = ("Azure has been updated to reflect the move of GitHub cloud and other developer cloud services "
                "as well as Security Copilot to Microsoft 365 cloud. Healthcare and Life Sciences cloud will move "
                "to the new Industry solutions cloud metric.")
    setfact(M, "azure-fy27q1-growth-outlook", [(None, "FY27 Q1 Outlook"), (None, mechanical),
        (None, azuredef), (None, "Adjusted Outlook Agents and Infra"),
        (None, "Azure revenue Growth of 44% to 45% in constant currency, with FX expected to decrease revenue by less than 1 point")],
        ["Azure", "44% to 45%", "constant currency", "Growth", "FY27 Q1", "Adjusted Outlook",
         "Healthcare and Life Sciences cloud", "Industry solutions cloud"],
        "新Azure定义包含GitHub/developer/Security Copilot移到M365及Healthcare/LifeSciences移到Industry solutions，完整范围与FY27Q1、机械调整旧指引、Adjusted/恒汇率/FX作用联合；不能仅保留一类剔除项再混用旧口径。")
    setfact(M, "total-company-fy27q1-revenue-outlook", [(None, "FY27 Q1 Outlook"), (None, mechanical),
        (None, "Total Company Revenue of $89.85 to $90.95 billion"),
        (None, "Adjusted Outlook Foreign currency impact Decrease to total revenue growth by less than 1 point, with roughly 1 point in Agents and Infra, and no meaningful impact in Devices and Consumer No meaningful impact to COGS or operating expense growth Total Company No change to outlook")],
        ["$89.85 to $90.95 billion", "Total Company", "Revenue", "FY27 Q1", "mechanical adjustments only", "No change to outlook"],
        "旧July29总公司区间必须与Adjusted Outlook中Total Company No change联合，不能仅用通用机械调整语句推出总额不变。收入展望仍required_business/normal，季度与新旧范围明确。", target_kind="required_business")
    setfact(M, "restated-segment-fy26-revenue", [(None, "Restated Historical Financials"),
        (None, "($ in millions) 2026 2025 Agents and Infra Q1 Q2 Q3 Q4 Fiscal Year Q1 Q2 Q3 Q4 Fiscal Year Revenue $61,672 $64,441 $67,438 $74,576 $268,127"),
        (None, "Devices and Consumer Q1 Q2 Q3 Q4 Fiscal Year Q1 Q2 Q3 Q4 Fiscal Year Revenue $16,001 $16,832 $15,448 $15,431 $63,712")],
        ["$268,127", "$63,712", "in millions", "Fiscal Year", "2026", "Restated"],
        "精确历史财务表为correctness_if_emitted，critical与错误年份/单位反例不变；两分部金额+FY26/FY25列头+inmillions+重述背景联合，不能一分部OR替代两者。", target_kind="correctness_if_emitted")
    setfact(M, "forward-looking-caveat", [(None,
        "forward-looking statements, which are any predictions, projections, or other statements about future events."),
        (None, "Actual results could materially differ because of factors discussed in the Risk Factors section"),
        (None, "We do not undertake any duty to update forward-looking statements.")],
        ["forward-looking statements", "predictions, projections", "not undertake any duty to update", "materially differ"],
        "风险不确定/预测属性/不负更新义务三者AND，只有风险一句不能替代不更新条款；仍critical document_meta。")
    setfact(M, "exhibit-identity-fy27-segments-metrics", [(None,
        "FY27 Segments and Investor Metrics September 2026 Exhibit 99.1")],
        ["Exhibit 99.1", "FY27 Segments and Investor Metrics", "September 2026"],
        "标题+月年+exhibit同封面，不能只标题或只月年OR，也不能从文件名回填封面具体9月2日。")
    setfact(M, "growth-comparison-fiscal-basis", [(None,
        "All growth comparisons in this presentation relate to the corresponding period of last fiscal year unless otherwise noted. Numbers may not foot due to rounding.")],
        ["corresponding period of last fiscal year", "unless otherwise noted", "rounding"],
        "同比财年/除非另说明及舍入限制联合；不得推成季度环比、日历年或强制每表精确加总。")

    revision_rows, qa = [], []
    for sid in IDS:
        old = json.loads((OLD / f"{sid}.json").read_text(encoding="utf-8"))
        new = revisions[sid]
        assert {f["id"] for f in old["facts"]} <= {f["id"] for f in new["facts"]}
        assert all(next(x for x in new["facts"] if x["id"] == f["id"])["importance"] == f["importance"] for f in old["facts"])
        assert {t for f in old["facts"] for t in f["must_not_assert"]} <= {t for f in new["facts"] for t in f["must_not_assert"]}
        new["scope"] = "development"
        new["support_set_frozen_before_output"] = False
        new.pop("support_set_digest_at_freeze", None)
        new["notes"] = ("M1 source-checkpoints revision 2026-10-24. All samples already diagnosed; development only, "
                        "not fresh or frozen before prior output. Every original fact id/importance and error counterexample retained; "
                        "full source-side joint evidence, anonymous/ASR ambiguity and explicit responsibility separation. "
                        "Author QA is not independent acceptance. See ../revision_manifest.json.")
        new["support_set_digest"] = support_set_digest(new)
        target = HERE / "gold" / f"{sid}.json"
        dump(target, new)
        loaded = load_gold(target)
        assert loaded["scope"] == "development" and not loaded["support_set_frozen_before_output"]
        assert loaded["gold_quote_chars"] <= 8192
        checks = verify_gold_anchors(new, Path(source.bindings[sid]["original_path"]))
        assert checks and all(row["ok"] for row in checks), [c for c in checks if not c["ok"]]
        # No editorial token is required that the complete source pack cannot carry.
        for f in new["facts"]:
            for group in f["any_support_sets"]:
                full = "\n".join(a["exact_quote"] for a in group)
                assert all(text_contains(full, t) for t in f["must_preserve"]), (sid, f["id"], f["must_preserve"])
        old_by_id = {f["id"]: f for f in old["facts"]}
        fact_changes = []
        for f in new["facts"]:
            prev = old_by_id.get(f["id"])
            if prev is None:
                changes = [{"field": "fact", "old": None, "new": f, "reason": reasons[(sid, f["id"])]}]
            else:
                changes = [{"field": k, "old": prev.get(k), "new": f.get(k), "reason": reasons[(sid, f["id"])]}
                           for k in sorted(prev.keys() | f.keys()) if prev.get(k) != f.get(k)]
            fact_changes.append({"fact_id": f["id"], "source_semantics_reviewed": True, "changes": changes})
        revision_rows.append({"sample_id": sid, "old_gold_sha256": sha(OLD / f"{sid}.json"),
                              "new_gold_path": f"gold/{sid}.json", "new_gold_sha256": sha(target),
                              "source_sha256": new["source_sha256"], "support_set_digest": new["support_set_digest"],
                              "original_fact_count": len(old["facts"]), "revised_fact_count": len(new["facts"]),
                              "original_importances_preserved": True, "fact_revisions": fact_changes,
                              "record_revisions": [{"field": k, "old": old.get(k), "new": new.get(k),
                                                     "reason": "Development contamination truth and source-authored revision lineage."}
                                                    for k in sorted(old.keys() | new.keys()) if k != "facts" and old.get(k) != new.get(k)]})
        obs = json.loads(gzip.decompress((HERE.parent / "baseline-selection" / f"{sid}.json.gz").read_bytes()))["observed"]
        evaluated = evaluate(obs, loaded)
        qa.append({"sample_id": sid, "gold_loads": True, "anchor_count": len(checks), "anchors_pass": sum(c["ok"] for c in checks),
                   "quote_chars": loaded["gold_quote_chars"], "old_required_counts": dict(Counter(f["importance"] for f in old["facts"] if f["target_kind"] == "required_business")),
                   "new_required_counts": dict(Counter(f["importance"] for f in new["facts"] if f["target_kind"] == "required_business")),
                   "existing_baseline_evaluation_status": evaluated["status"], "existing_baseline_metrics": evaluated["metrics"],
                   "existing_baseline_checks": evaluated["checks"]})
    assert len(load_gold_dir(HERE / "gold")) == 4
    for sid, entry in source.bindings.items():
        assert sha(entry["original_path"]) == entry["source_sha256"]
        assert sha(ROOT / entry["old_gold_path"]) == entry["old_gold_sha256"]
    dump(HERE / "revision_manifest.json", {"schema_version": "m1-source-checkpoint-revisions/1",
        "created_at": datetime.now(timezone.utc).isoformat(), "scope": "development", "author_only": True,
        "independent_review_status": "PENDING_OTHER_REVIEWER", "samples": revision_rows})
    dump(HERE / "author-report.json", {"schema_version": "m1-source-checkpoint-author-qa/1", "created_at": datetime.now(timezone.utc).isoformat(),
        "author": "/root/w08_reporting_selection_content", "verdict": "AUTHOR_PACKAGE_READY_FOR_INDEPENDENT_REVIEW",
        "source_and_old_gold_unchanged": True, "all_old_fact_ids_and_importances_retained": True,
        "samples": qa, "limitations": ["No product selection rerun or model output acceptance.",
            "Anonymous voices/ASR uncertainty not repaired using unavailable audio.",
            "Fixture compatibility and exact anchors do not replace independent semantic review."],
        "external_calls": 0, "downloads": 0, "original_copies": 0})
    print(json.dumps([{k: row[k] for k in ("sample_id", "anchor_count", "quote_chars", "existing_baseline_evaluation_status")} for row in qa], ensure_ascii=False))


if __name__ == "__main__":
    main()
