"""Freeze the DU5-CORPUS gold set: validate, verify anchors, digest, write.

Run from the worktree root BEFORE any candidate output for these samples is
read (the freeze discipline of the card). It

1. loads each ``reader_reports/<sample>.facts.json`` (independent reader
   output, verbatim quotes from the original),
2. normalizes the reader's support-group shapes into ``du-gold/1``,
3. validates the record with the package validator,
4. verifies every anchor against the bound original via the independent
   extraction helper (a miss aborts the freeze),
5. writes ``gold/du5-*.json`` with a frozen ``support_set_digest`` and a
   ``du5_manifest.json`` carrying reading scope, business targets, prior use
   and gold-file SHA-256.

It never runs the selector and never touches production files.
"""

from __future__ import annotations

import hashlib
import json
import sys
from datetime import datetime
from pathlib import Path

REPO = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(REPO))

from tools.document_understanding_benchmark.contamination import support_set_digest  # noqa: E402
from tools.document_understanding_benchmark.gold import load_bindings, sha256_file  # noqa: E402
from tools.document_understanding_benchmark.records import validate_gold  # noqa: E402
from tools.document_understanding_benchmark.tests.anchor_verify import verify_gold_anchors  # noqa: E402

PWF = REPO / "docs" / "plans" / "du5-corpus-2026-10-15"
FACTS_DIR = PWF / "reader_reports"
GOLD_DIR = REPO / "tools" / "document_understanding_benchmark" / "gold"
MANIFEST_PATH = REPO / "tools" / "document_understanding_benchmark" / "du5_manifest.json"

FREEZE_DATE = "2026-10-15"

# sample_id -> frozen metadata. Everything here comes from reading the
# originals (independent reader reports), never from selector output.
SAMPLES: dict[str, dict] = {
    "du5-cn-iflytek-h1": {
        "shape": "a_share_interim",
        "market": "CN",
        "company": "科大讯飞",
        "language": "zh",
        "carrier": ".pdf",
        "source_sha256": "8381e3ef16329666c170255a74c39e8614eb96073cf26556b1cb5439e32b9d31",
        "expected_route_families": ["interim", "a_share_interim", "semi_annual_report"],
        "prior_use": {
            "status": "fresh",
            "known_prior_sightings": (
                "none found in .planning, docs/plans, docs/implementation "
                "(searched 2026-10-15): company absent from every benchmark gold, "
                "finding and tuning note before this card"
            ),
        },
        "reading_scope": {
            "fully_read_pages": "1-49, 64-65, 70, 200",
            "skimmed_pages": "233, 250-251",
            "unread_pages": "50-63, 66-69, 71-232, 234-249",
        },
        "business_targets": {
            "subject": "科大讯飞 2025 H1：AI 大模型（讯飞星火）驱动的多行业智能化业务",
            "stage": "大模型持续迭代期（X1 2025-01 发布、07 全面跃升属期后），TO C 硬件放量，海外扩张加速",
            "plan_negation_conditional": "计划：山东肥城医共体预计四季度全面应用；否定：半年度未经审计、无重大诉讼仲裁、无违规担保",
            "overseas_new_business": "国外地区主营收入 178,527,940.25 元 +212.08%；硬件中日韩美 +346%；企业AI解决方案 +349.92%",
            "investment_vs_capacity_vs_revenue": "报告期投资额 55,931,792.80 元（investment）与营业收入 109.11 亿元严格区分，无重大股权投资",
            "amounts_units_periods": "报表单位 元、叙述用亿元、关联交易表用万元；期间 2025-01-01~2025-06-30，资产负债表日 2025-06-30，CNY",
        },
        "designated_trap": "亏损收窄方向（增长40.37%=亏损收窄）、投资额vs收入、计划vs实际",
    },
    "du5-cn-fangbang-q1": {
        "shape": "a_share_quarterly_business",
        "market": "CN",
        "company": "方邦股份",
        "language": "zh",
        "carrier": ".pdf",
        "source_sha256": "da2b66bfc7a8f781aa55ebe7d7faec60d65f6531ca8fc181bafccd1a3aa3e300",
        "expected_route_families": ["quarterly", "a_share_quarterly", "quarterly_report"],
        "prior_use": {
            "status": "fresh",
            "known_prior_sightings": (
                "公司名曾出现在 cross-market-rf-e2e-2026-10-08 路演文本的参会名单"
                "（另一卡采集物）与 n5 raw-duplicate-audit 对另一份研报的路径/哈希元数据中；"
                "本季报原件与内容在本次任务前从未被读取，也未进入任何 benchmark gold/findings/调参讨论"
            ),
        },
        "reading_scope": {
            "fully_read_pages": "1-17",
            "skimmed_pages": "",
            "unread_pages": "none",
        },
        "business_targets": {
            "subject": "方邦股份 2025Q1：电磁屏蔽膜企业，专项委托开发项目结项验收驱动利润转正",
            "stage": "Q1 扭亏（归母 +143.56万）但扣非仍负（-309.57万），经营现金流为负",
            "plan_negation_conditional": "无前瞻计划陈述；否定：财务报表未经审计（□是√否）；因果均为已实现事项（结项验收、降本增效）",
            "overseas_new_business": "无出海；『海外单一供应商』仅为下游客户摆脱依赖的动机，不是公司出口",
            "investment_vs_capacity_vs_revenue": "2,075.47万为项目确认收入（period_flow），929.25万为其利润；购建固定资产 12,182,728.89 元为投资现金流",
            "amounts_units_periods": "表格单位 元、叙述用 万元（8,873.07万=88,730,690.51元）；Q1 报告 本报告期=1—3月=年初至报告期末，无独立 YTD 列；股本表 本报告期末 vs 上年度末",
        },
        "designated_trap": "双单位（元表/万叙述）、负基数不适用、现金流与利润方向背离",
    },
    "du5-cn-proya-q1": {
        "shape": "a_share_quarterly_sparse",
        "market": "CN",
        "company": "珀莱雅",
        "language": "zh",
        "carrier": ".pdf",
        "source_sha256": "873df9697b20c8c8882f9f16f60bdf755bc6b1b27022f2cd491ebc94c012a49e",
        "expected_route_families": ["quarterly", "a_share_quarterly", "quarterly_report"],
        "prior_use": {
            "status": "fresh",
            "known_prior_sightings": (
                "none found in .planning, docs/plans, docs/implementation "
                "(searched 2026-10-15)"
            ),
        },
        "reading_scope": {
            "fully_read_pages": "1-12",
            "skimmed_pages": "",
            "unread_pages": "none",
        },
        "business_targets": {
            "subject": "珀莱雅 2026Q1：纯财务稀疏季报（其他重要信息 不适用），化妆品龙头",
            "stage": "成熟盈利期（Q1 归母 3.67亿）；全文唯一业务句为现金流变动原因",
            "plan_negation_conditional": "否定：未经审计（□是√否）、审计意见类型 不适用、新准则首次执行 不适用",
            "overseas_new_business": "无",
            "investment_vs_capacity_vs_revenue": "投资支付现金 32.13亿、购建固定资产 2,443.9万均为投资项，不得读作产能或收入",
            "amounts_units_periods": "单位：元 币种：人民币；流量块 本报告期(2026Q1)/上年同期/增减幅度(%)，存量块 本报告期末(2026-03-31)/上年度末(2025-12-31)；EPS 元/股，ROE 变动为『减少1.19 个百分点』",
        },
        "designated_trap": "期间/单位表（本报告期 vs 本报告期末 vs 上年度末；元 vs 元/股 vs 个百分点）",
    },
    "du5-cn-zhongmi-offering": {
        "shape": "equity_offering",
        "market": "CN",
        "company": "中密控股",
        "language": "zh",
        "carrier": ".pdf",
        "source_sha256": "d3105354bff42054ffcd9a07fb82bfef7f73058fac43b47c9f94315dd03100ad",
        "expected_route_families": ["offering", "equity_offering_prospectus"],
        "prior_use": {
            "status": "fresh",
            "known_prior_sightings": (
                "2026-07-09 会议转写 e2e 曾处理该公司会议音频（仅元数据+翻译产出，内容未用于调参）；"
                "n5 raw-duplicate-audit 列过其年报路径元数据。本募集说明书原件与内容在本次任务前"
                "从未被读取，也未进入任何 benchmark gold/findings/调参讨论"
            ),
        },
        "reading_scope": {
            "fully_read_pages": "1-16, 24-30, 35-59, 64-67, 79-85",
            "skimmed_pages": "17-23, 31-34, 60-63, 68-78, 86-99",
            "unread_pages": "none",
        },
        "business_targets": {
            "subject": "中密控股 2020 向特定对象发行募集说明书（修订稿）：密封件企业收购新地佩尔阀门+募投",
            "stage": "成熟密封企业外延并购（阀门）；募投项目均为计划（部分软件/设备采购已启动）",
            "plan_negation_conditional": "计划：46,000万募集上限、21,000万现金对价、24/36个月实施周期；条件：以证监会注册+资金到位为前提；否定：研发项目不产生直接经济效益",
            "overseas_new_business": "海外3个服务中心；阀门为并购标的的新品类，非现有主业",
            "investment_vs_capacity_vs_revenue": "46,000/21,000/4,086.65/8,360万均为投资（investment/plan）；『新增密封配套市场容量30至40亿元』为预测市场容量；业绩承诺6,000万为对手方承诺",
            "amounts_units_periods": "元/万元/亿元 人民币；报告期 2017-2019 年度及 2020年1-6月；建设周期 24/36 个月",
        },
        "designated_trap": "投资vs收入、计划/条件vs已实现、承诺vs实际",
    },
    "du5-hk-kingsoft-interim": {
        "shape": "hk_interim",
        "market": "HK",
        "company": "金山雲",
        "language": "zh-hant",
        "carrier": ".pdf",
        "source_sha256": "4f589193fae39fb53cb7d2121d93925b382bb052cfecbdc24e8e8271ea41bd36",
        "expected_route_families": ["interim", "hk_interim"],
        "prior_use": {
            "status": "contaminated",
            "known_prior_sightings": (
                "du-bench 选样时探测过金山雲原件的文字层（.planning/du-bench/progress.md:269 "
                "'壁仞科技 and 金山雲 extract cleanly, so 壁仞 was used'），"
                "portfolio-reuse-fix 的 filing-fetch 复用机制也处理过其年报文件；"
                "本中期报告内容未用于任何规则或金标调参"
            ),
        },
        "reading_scope": {
            "fully_read_pages": "5-16, 33-35, 44-46, 50-54, 58, 64-70",
            "skimmed_pages": "1-4, 17-32, 36-43, 47-49, 55-57, 59-63, 71-75",
            "unread_pages": "none",
        },
        "business_targets": {
            "subject": "金山云控股 2025 中期报告（港交所3896/纳斯达克KC，开曼注册）：亏损扩大期云与智算业务",
            "stage": "收入 +17.8%（AI 相关客户），净亏损扩大 7.8%；单一经营分部；持续高投入（AI 服务器折旧 +107%）",
            "plan_negation_conditional": "计划：下半年维持高质量/可持续战略、持续投资研发与AI；否定：无重大投资（≥5%总资产）、并无未来重大投资及资本资产计划、无中期股息",
            "overseas_new_business": "无国际扩张业务；新业务=智算云（星流平台）、9代服务器 C9a/X9a、KPFS 2.0；主动收缩 CDN",
            "investment_vs_capacity_vs_revenue": "资本开支付现 1,483,742 千元（investment，对比收入 4,319,204 千元）；IDC 最低采购承诺 630,000 千元；产能：2 个数据中心、约 110,000 台服务器",
            "amounts_units_periods": "报表 千元（除股数/每股），MD&A 叙述 百萬元，USD 便利折算 7.1636；期间 2025-01-01~06-30 vs 1H2024 / 2024-12-31；US GAAP 非 IFRS（附注16 IFRS 调节）",
        },
        "designated_trap": "千元表vs百萬元叙述、US GAAP 非 IFRS、收入类别非报告分部、投资vs收入",
    },
    "du5-hk-kingsoft-q1": {
        "shape": "hk_quarterly",
        "market": "HK",
        "company": "金山雲",
        "language": "zh-hant",
        "carrier": ".pdf",
        "source_sha256": "37f0eb13fc9748d6f2f56e76e9a586bcee7cc9482dd77cdceb7a37fc0890ba2f",
        "expected_route_families": ["quarterly", "hk_quarterly", "results_release"],
        "prior_use": {
            "status": "contaminated",
            "known_prior_sightings": (
                "同 du5-hk-kingsoft-interim：金山雲原件文字层曾被 du-bench 选样探测"
                "（.planning/du-bench/progress.md:269）；本公告内容未用于任何规则或金标调参"
            ),
        },
        "reading_scope": {
            "fully_read_pages": "1-13",
            "skimmed_pages": "",
            "unread_pages": "none",
        },
        "business_targets": {
            "subject": "金山云控股 内幕消息公告：2026Q1（三个月）未经审计业绩（港交所上市规则13.09/SFO XIVA）",
            "stage": "高增长重投入亏损期：收入 +37.2% YoY，毛利率降至 12.8%，净亏损扩大；智算云账单 +90% 且占公有云收入过半",
            "plan_negation_conditional": "计划：预计全年继续投资（资本开支+租赁资产 Q1 已达 30 亿元）；否定：非GAAP指标不得孤立考虑、并无责任更新前瞻性陈述",
            "overseas_new_business": "无海外扩张陈述；新业务=智算云（AI），增长驱动含小米/金山生态、AI 客户、行业云渗透",
            "investment_vs_capacity_vs_revenue": "Q1 资本开支及租赁资产 30 亿元（investment/period）vs 收入 2,703.7 百萬元；无产能数字",
            "amounts_units_periods": "叙述 百萬元（USD 6.8980 便利折算），报表 千元；全部流量=三个月口径（2026Q1 vs 2025Q1 vs 2025Q4），无年度/半年数字；US GAAP 非 IFRS",
        },
        "designated_trap": "季度vs年度口径、同比vs环比方向、內幕消息≠负面、千元/百萬元单位",
    },
    "du5-us-msft-8k": {
        "shape": "sec_8k_container",
        "market": "US",
        "company": "MICROSOFT CORP",
        "language": "en",
        "carrier": ".htm",
        "source_sha256": "a3d0bbf6411bb2b2db0bc9deee1541ea44639399e26e1f08adf8df3037ab0878",
        "expected_route_families": ["sec_8k", "container"],
        "prior_use": {
            "status": "contaminated",
            "known_prior_sightings": (
                "company already in benchmark gold/findings via us-10k / us-txt / us-release; "
                "this 8-K file itself was never read before this card, but company-blind "
                "generalisation cannot be claimed"
            ),
        },
        "reading_scope": {
            "fully_read_pages": "whole HTML (cover, Item 7.01, Item 9.01, signature, hidden iXBRL header)",
            "skimmed_pages": "",
            "unread_pages": "none",
        },
        "business_targets": {
            "subject": "Microsoft Form 8-K（事件日 2026-09-02）：Reg FD furnish FY27 分部与投资者指标演示材料",
            "stage": "报告结构变更公告（容器文档），业务内容全部在 Exhibit 99.1",
            "plan_negation_conditional": "计划：自 FY27 起按两个报告分部管理（Agents and Infra / Devices and Consumer）；否定：General Instruction B.2 下『shall not be deemed to be filed』（含 Exhibit 99.1）",
            "overseas_new_business": "无",
            "investment_vs_capacity_vs_revenue": "正文无任何金额；封面证券表仅为注册信息（3.125% 2028票据、2.625% 2033票据）",
            "amounts_units_periods": "无财务数字；事件日 2026-09-02；前瞻期间 FY2027；隐藏 iXBRL 成员令牌（msft:Notes...Member）不是可见文本",
        },
        "designated_trap": "容器≠附件（不把 8-K 主表当完整 exhibit）、iXBRL 令牌噪声、furnished≠filed 否定",
    },
    "du5-us-msft-ex991": {
        "shape": "sec_exhibit",
        "market": "US",
        "company": "MICROSOFT CORP",
        "language": "en",
        "carrier": ".htm",
        "source_sha256": "47a0a4a1d6a335fffab571789aba597eca0637d2650f0f62371afa10e205b987",
        "expected_route_families": ["sec_exhibit", "presentation_deck"],
        "prior_use": {
            "status": "contaminated",
            "known_prior_sightings": (
                "company already in benchmark gold/findings via us-10k / us-txt / us-release; "
                "this exhibit file itself was never read before this card"
            ),
        },
        "reading_scope": {
            "fully_read_pages": "whole HTML (cover, FLS caveat, CEO note, segment structure, metric changes, definitions, restated financials, product revenue, metric growth, FY27 Q1 outlook)",
            "skimmed_pages": "",
            "unread_pages": "none",
        },
        "business_targets": {
            "subject": "Microsoft Exhibit 99.1：FY27 Segments and Investor Metrics（2026-09）投资者演示",
            "stage": "AI 驱动的报告体系重构：FY27 起两个报告分部（Agents and Infra / Devices and Consumer），指标重定义（seats 含 GitHub、bookings/RPO 定义），FY26 历史重述",
            "plan_negation_conditional": "计划：will transition、FY27 Q1 outlook（机械调整自 2026-07-29 展望，Azure 44-45% cc）；FLS 免责（不承诺更新）；『No change to outlook』",
            "overseas_new_business": "无地域数字；新报告单元 Industry solutions / Frontier and support services",
            "investment_vs_capacity_vs_revenue": "FY27 Q1 capex 展望 >$50 billion（investment/plan）vs 收入展望 $89.85–90.95 billion（period_flow/plan）；FY26 重述分部收入 $268,127m / $63,712m",
            "amounts_units_periods": "USD，表格 ($ in millions)；fiscal 年口径（2026=FY2026 非日历年）；y/y 对应上一财年同季；数字可能因四舍五入不合计",
        },
        "designated_trap": "计划vs实际（outlook）、指标定义（bookings/RPO/席位）、财年vs日历年、重述vs原口径",
    },
    "du5-cn-gbits-call": {
        "shape": "earnings_call_transcript",
        "market": "CN",
        "company": "吉比特",
        "language": "zh",
        "carrier": ".docx",
        "source_sha256": "63777874f5956f37ed32f4839c170340af4f61ee7594b99423acc698968a158a",
        "expected_route_families": ["earnings_call", "investor_call_transcript"],
        "prior_use": {
            "status": "fresh",
            "known_prior_sightings": (
                "n5 raw-duplicate-audit 列过吉比特年报路径元数据；本电话会转写原件与内容"
                "在本次任务前从未被读取，也未进入任何 benchmark gold/findings/调参讨论"
            ),
        },
        "reading_scope": {
            "fully_read_pages": "whole document (116 paragraphs, 00:00-33:20)",
            "skimmed_pages": "",
            "unread_pages": "none",
        },
        "business_targets": {
            "subject": "吉比特财报交流会电话会转写（中泰证券，2024-04-09，mp3 STT）：一念逍遥/重装前哨/航海王/亿万光年",
            "stage": "一念逍遥成熟期（买量转存量运营）；重装前哨 3 月底上线爬坡+口碑修复；M72/M88 研发中待版号",
            "plan_negation_conditional": "计划：尽量减少买量依赖、存量运营、跟随节点推更新（计划还没有）；否定：买量不会再回到原水平、品类无大变化、销量不方便分享；条件：能否稳住目前不好判断、即使拿到版号也要明年上半年",
            "overseas_new_business": "海外增长慢因缺适配产品、代理为短板；亿万光年签雷霆全球代理；按回收表现排优先级",
            "investment_vs_capacity_vs_revenue": "买量/营销支出（cost）vs 流水（billings）vs 收入确认（买断当即确认+退货准备『利息负债』ASR，道具消耗递延）严格区分",
            "amounts_units_periods": "RMB 元/亿（7.2亿、1.17亿、1.8亿）、%（好评率65%）、人（雷霆约500人）；ASR 噪声保留（Oa≈ROI、一念/一面、买了≈减了）",
        },
        "designated_trap": "否定/计划/问答角色（分析师前提≠公司事实、计划≠已实现、否定不得丢失、ASR 噪声保留）",
    },
}


def normalize_support(raw_support: list) -> list[list[dict]]:
    groups: list[list[dict]] = []
    for group in raw_support:
        if isinstance(group, dict):
            anchors = group.get("anchors") or group.get("group") or []
        else:
            anchors = group
        normalized = []
        for anchor in anchors:
            item: dict = {"exact_quote": anchor["exact_quote"]}
            if anchor.get("page") is not None:
                item["page"] = anchor["page"]
            if anchor.get("line") is not None:
                item["line"] = anchor["line"]
            item["location_kind"] = anchor.get("location_kind") or (
                "page" if anchor.get("page") is not None else "document"
            )
            normalized.append(item)
        groups.append(normalized)
    return groups


def main() -> int:
    bindings = load_bindings(Path.home() / ".du-bench" / "bindings.local.json")
    frozen_at = datetime.now().astimezone().isoformat(timespec="seconds")
    manifest_samples = []
    failures: list[str] = []

    for sample_id, meta in SAMPLES.items():
        facts_path = FACTS_DIR / f"{sample_id}.facts.json"
        raw_facts = json.loads(facts_path.read_text(encoding="utf8"))
        facts = []
        for fact in raw_facts:
            item = {
                "id": fact["id"],
                "importance": fact["importance"],
                "target_kind": fact["target_kind"],
                "quantity_basis": fact["quantity_basis"],
                "modality": fact["modality"],
                "role": fact["role"],
                "fact_scope": fact["fact_scope"],
                "any_support_sets": normalize_support(fact["support"]),
                "must_preserve": fact["must_preserve"],
                "must_not_assert": fact["must_not_assert"],
                "reason": fact["reason"],
            }
            facts.append(item)

        notes = (
            f"DU5-CORPUS（冻结于 {FREEZE_DATE}，frozen_at={frozen_at}）。"
            f"{meta['company']} {meta['shape']}。prior_use={meta['prior_use']['status']}："
            f"{meta['prior_use']['known_prior_sightings']}。"
            f"support set 在读取本样本任何候选输出前冻结（support_set_frozen_before_output）；"
            f"事实由独立子代理逐字读取原件回报并经锚点逐条验证，重要性由原文阅读判断，"
            f"未使用 selector 输出或生成 claim 填充。指定陷阱：{meta['designated_trap']}。"
        )
        record = {
            "schema_version": "du-gold/1",
            "sample_id": sample_id,
            "market": meta["market"],
            "company": meta["company"],
            "source_sha256": meta["source_sha256"],
            "scope": "holdout",
            "language": meta["language"],
            "support_set_frozen_before_output": True,
            "expected_route_families": meta["expected_route_families"],
            "notes": notes,
            "facts": facts,
        }
        validated = validate_gold(record)
        if validated["gold_quote_chars"] > 8 * 1024:
            failures.append(f"{sample_id}: quote budget {validated['gold_quote_chars']}")
        record["support_set_digest"] = support_set_digest(record)

        # anchor verification against the bound original — abort freeze on any miss
        bound = bindings.get(sample_id)
        if not bound or not Path(bound).is_file():
            failures.append(f"{sample_id}: no local binding at freeze time")
            continue
        actual_sha = sha256_file(Path(bound))
        if actual_sha != meta["source_sha256"]:
            failures.append(f"{sample_id}: bound original SHA mismatch")
            continue
        misses = [row for row in verify_gold_anchors(record, Path(bound)) if not row["ok"]]
        for row in misses:
            failures.append(
                f"{sample_id}/{row['fact_id']} {row['where']}: {row['quote'][:48]!r}"
            )

        gold_path = GOLD_DIR / f"{sample_id}.json"
        gold_bytes = (json.dumps(record, ensure_ascii=False, indent=2) + "\n").encode("utf8")
        gold_path.write_bytes(gold_bytes)
        manifest_samples.append(
            {
                "sample_id": sample_id,
                "shape": meta["shape"],
                "market": meta["market"],
                "company": meta["company"],
                "carrier": meta["carrier"],
                "language": meta["language"],
                "source_sha256": meta["source_sha256"],
                "gold_file": f"gold/{sample_id}.json",
                "gold_sha256": hashlib.sha256(gold_bytes).hexdigest(),
                "support_set_digest": record["support_set_digest"],
                "frozen_at": frozen_at,
                "frozen_before_candidate_output": True,
                "prior_use": meta["prior_use"],
                "reading_scope": meta["reading_scope"],
                "business_targets": meta["business_targets"],
                "designated_trap": meta["designated_trap"],
                "anchor_verification": {
                    "method": "PyMuPDF/zipfile independent extraction + textutil.text_contains",
                    "anchors_total": sum(
                        len(anchor)
                        for fact in facts
                        for anchor in fact["any_support_sets"]
                    ),
                    "anchors_verified": "all",
                },
            }
        )

    if failures:
        print("FREEZE ABORTED — fix authoring first:")
        for failure in failures:
            print("  FAIL:", failure)
        return 1

    manifest = {
        "schema_version": "du5-manifest/1",
        "card": "DU5-CORPUS",
        "created": FREEZE_DATE,
        "frozen_at": frozen_at,
        "base_commit": "8c027011037dc8c8659235fb65f529028dcd15ca",
        "freeze_note": (
            "All gold support sets were frozen before any candidate output for these "
            "samples was read. Gold files are never edited after this point; corrections "
            "go through gold_corrections.json with the old value kept replayable. "
            "Bindings are machine-local and never committed."
        ),
        "samples": manifest_samples,
    }
    MANIFEST_PATH.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf8"
    )
    print(f"froze {len(manifest_samples)} samples at {frozen_at}")
    for row in manifest_samples:
        print(f"  {row['sample_id']:<28} {row['shape']:<26} gold={row['gold_sha256'][:12]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
