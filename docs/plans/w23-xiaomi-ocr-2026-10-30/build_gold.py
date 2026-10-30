"""W23 build frozen gold.json.

Per page: base transcript = native PDF text layer (candidate only); every page
is visually verified against the frozen 200-DPI render and corrected here.
Corrections are explicit (old -> new) edits; pages whose native layer is
garbled or absent carry a full manual transcription.  Numbers are NOT
hand-listed: the comparator derives the number set from gold full_text.
"""
import json
from pathlib import Path

WT = Path(r"C:/Users/郑曾波/Projects/company-wiki-w23-xiaomi-ocr")
PLAN = WT / "docs" / "plans" / "w23-xiaomi-ocr-2026-10-30"
CAND = WT / ".w23_cache" / "gold_candidates"


def native(page_id):
    return (CAND / f"{page_id}.txt").read_text(encoding="utf-8")


def move_page_number_to_end(text, num):
    """Native extraction often emits the page number right after the header;
    visually it is the page footer, so gold reading order moves it to the end."""
    first_nl = text.find("\n")
    head = text[:first_nl].strip()
    if head == num:
        return text[first_nl + 1:].rstrip() + "\n" + head
    return text.rstrip()


PAGES = {}

# ---------- BYD AR2024 p021 (eval) ----------
t = native("byd_ar_2024_p021")
t = move_page_number_to_end(t, "22")
t = t.replace("适用 □不适用", "☑适用 □不适用", 1)
PAGES["byd_ar_2024_p021"] = {
    "role": "eval",
    "full_text": t.rstrip() + "\n",
    "provenance": "native text layer as base; visually verified against frozen 200-DPI render",
    "corrections": [
        "checkbox glyph restored: 适用 □不适用 -> ☑适用 □不适用 (native layer lost the checked-box glyph)",
        "page footer number 22 moved to reading-order end",
    ],
    "facts": [
        "消费电子业务深度参与客户新产品开发,安卓零部件和整机组装业务年内均实现增长",
        "海外大客户业务份额持续提升,带动出货量和收入同比增长",
        "并表二零二三年年底完成收购的业务,零部件业务规模快速扩大",
        "3D打印机、AI服务器于年内实现量产,液冷和电源产品完成开发",
        "主营:以新能源汽车为主的汽车业务、手机部件及组装业务、二次充电电池及光伏业务,并拓展城市轨道交通业务",
        "动力电池开发磷酸铁锂'刀片电池';储能覆盖电源侧/电网/工商业/家庭",
        "光伏业务拥有硅片、电池片、光伏组件、光伏系统应用等全产业链布局",
        "城市轨道交通领域研发中运量'云轨'和低运量'云巴'产品",
        "乘用车快报产量4,281,084辆(上年同期3,033,662辆,+41.12%),快报销量4,250,370辆(上年同期3,012,906辆,+41.07%)",
    ],
    "conditions": ["报告期内整车制造生产经营情况:☑适用(□不适用未勾选)"],
    "non_text_regions": [],
}

# ---------- AMEC H1 2026 p009 (eval) ----------
t = native("amec_h1_2026_p009")
t = move_page_number_to_end(t, "10 / 210")
fig = "（下图内文字：软件网络电商 传媒 大数据等应用；年产值几十万亿美金；电子系统；年产值几万亿美金；AMEC；中微公司）\n"
anchor = "半导体设备的极端重要性更加凸显出来。\n"
t = t.replace(anchor, anchor + fig, 1)
PAGES["amec_h1_2026_p009"] = {
    "role": "eval",
    "full_text": t.rstrip() + "\n",
    "provenance": "native text layer as base; visually verified; in-figure marketing text added manually",
    "corrections": [
        "page footer '10 / 210' moved to reading-order end",
        "in-figure stylized text transcribed from the frozen render and inserted at the figure's reading-order position",
    ],
    "facts": [
        "预测2026年全球半导体制造设备(OEM)总销售额将创下1659亿美元的历史新高,同比增长23.2%",
        "中微公司主要从事高端半导体设备及泛半导体设备的研发、生产和销售",
        "CCP高能等离子体和ICP低能等离子体刻蚀两大类、包括二十几种细分刻蚀设备,已可覆盖大多数刻蚀应用",
        "等离子体刻蚀设备已广泛应用于国内和国际一线客户,覆盖65纳米到3纳米及更先进工艺",
        "已实现CMP湿法设备多种应用研发和客户验证",
        "最近十年着重开发多种导体和半导体化学薄膜设备,如MOCVD、LPCVD(行至页尾未完)",
    ],
    "conditions": ["没有能加工微米和纳米尺度的光刻机、等离子体刻蚀机和薄膜沉积等设备,就不可能制造出集成电路和微观器件(否定条件)"],
    "non_text_regions": [
        "配图下层金字塔小字(半导体器件/封装测试层级与'年产值约…美金')在200DPI下不可靠,记不可判,不入分母",
    ],
}

# ---------- AMEC H1 2026 p011 (eval) ----------
t = native("amec_h1_2026_p011")
t = move_page_number_to_end(t, "12 / 210")
t = t.replace("□适用 √不适用", "□适用 √不适用", 1)
PAGES["amec_h1_2026_p011"] = {
    "role": "eval",
    "full_text": t.rstrip() + "\n",
    "provenance": "native text layer as base; visually verified against frozen render",
    "corrections": ["page footer '12 / 210' moved to reading-order end"],
    "facts": [
        "采购模式:严格的供应商选择和审核制度,合格供应商名录并定期审核,与全球众多供应商建立长期稳定合作关系",
        "生产模式:订单式生产为主,结合少量库存式生产为辅",
        "营销及销售模式:直销为主;欧洲市场客户较为分散,该区域通过代理商模式销售",
        "下设中国大陆、中国台湾、韩国、新加坡、美国等国家或地区的区域销售和支持部门",
        "新增重要非主营业务情况:□适用 √不适用",
        "量检测设备已成为占半导体前道设备总市场约13%的第四大设备门类",
        "中微公司于2024年新发起设立了超微(行至页尾未完)",
    ],
    "conditions": [
        "欧洲市场客户较为分散,公司在该区域通过代理商模式进行销售(条件)",
        "订单式生产:与客户签订订单后,根据订单情况进行定制化设计及生产制造",
    ],
    "non_text_regions": [],
}

# ---------- Meituan AR2024 p011 (eval; native garbled -> manual) ----------
PAGES["meituan_ar_2024_p011"] = {
    "role": "eval",
    "full_text": """11 美團 2024 年度報告
主席報告
2024年，即時配送業務實現了穩健增長。如今，外賣已成為餐飲行業增長的重要驅動力，而即時零售已成為零售行業不可或缺的組成部分。我們順應不斷演變的消費趨勢，強化了「省」的用戶心智，構建更高效且普惠的消費生態。我們深入推進供應鏈創新，優化運營，以滿足消費者的多樣化需求。我們的新供給模式為商家帶來新的增長機遇，幫助他們抵禦外部挑戰。通過「拼好飯」，大量餐飲商家成功提升了銷售額，吸引了新客。與此同時，消費者也獲得了更多價格實惠的外賣選擇。我們進一步拓展了「拼好飯」供給，加強食品安全管控，提升用戶體驗，這激發了更多場景下的消費需求，並提高了消費者的購買頻次。「品牌衛星店」成為品牌餐飲商家低成本擴張的有效途徑。這些「品牌衛星店」，借助商家品牌資產和採用更優的成本結構，為消費者提供了相較於堂食價格更為實惠的高品質餐品。我們還優化了「神搶手」的選品，更好地滿足消費者對品質餐飲的需求。此外，在2024年，「美團閃電倉」實現了顯著增長，尤其在低線市場，它已經成為各類零售商重要的新增長渠道。許多大型傳統零售商積極採用「美團閃電倉」模式，其與傳統線下零售供應形成互補，提升即時零售的便利性，進一步激發消費需求。即時零售現已穩固成為一種高確定性的生活方式。我們還不斷改善了不同品類即時配送的服務。例如，消費者在我們的平台購買藥品時，可以享受涵蓋居家檢測、線上診斷、醫保支付以及即時配送的一站式服務。
隨著即時配送業務的發展，我們始終致力於構建一個可持續發展的生態系統。在商家方面，我們簡化了促銷體系，規範了營銷活動，加強了食品安全管理，並完善了對惡意差評的治理。我們亦於第四季度推出人民幣10億元的商家扶持計劃。通過現金支持及平台補貼，我們幫助商家提高服務質量、優化效率及探索創新。在騎手方面，保障騎手權益、改善他們的工作體驗是我們的首要任務。自2022年7月以來，在政府部門的指導下，我們已為7個試點省市的所有騎手提供了累計人民幣14億元的職業傷害保障資金。此外，我們還推出了一系列關愛騎手的措施，其中包括在系統中引入防疲勞功能，以及為有聽力障礙的騎手提供特殊關懷和便利措施。另外，我們為大量面臨重大疾病或需要教育幫扶的騎手家庭提供支持。展望未來，我們將繼續保持對生態系統的投入，致力於行業可持續發展。特別是通過深入調研並在相關部門的指導下，我們制定出了一項針對騎手的社保試點方案。我們預計在2025年第二季度開始在部分城市試點實施。
""",
    "provenance": "full manual transcription from the frozen 200-DPI render; the native text layer of this page has broken reading order (fragments reversed/interleaved) and was NOT used",
    "corrections": ["native layer unusable (scrambled order, e.g. 年2024); every character from visual transcription"],
    "facts": [
        "2024年即時配送業務實現穩健增長;外賣成為餐飲行業增長的重要驅動力,即時零售成為零售行業不可或缺的組成部分",
        "通過「拼好飯」大量餐飲商家提升銷售額並吸引新客;「品牌衛星店」成為品牌餐飲商家低成本擴張的有效途徑",
        "優化了「神搶手」的選品;2024年「美團閃電倉」實現顯著增長,尤其低線市場",
        "藥品即時配送可享受居家檢測、線上診斷、醫保支付一站式服務",
        "第四季度推出人民幣10億元的商家扶持計劃",
        "自2022年7月以來為7個試點省市的所有騎手提供累計人民幣14億元職業傷害保障資金",
        "推出防疲勞功能,為聽力障礙騎手提供特殊關懷",
        "制定針對騎手的社保試點方案,預計2025年第二季度開始在部分城市試點實施",
    ],
    "conditions": ["社保試點方案預計2025年第二季度開始在部分城市試點實施(時間條件)"],
    "non_text_regions": ["页面下部大幅装饰留白与浅色吉祥物插画,无文字(编造负对照)"],
}

# ---------- KSY Q1 2026 p002 (eval) ----------
t = native("ksy_q1_2026_p002")
t = move_page_number_to_end(t, "3")
t = t.replace("總收入達人民幣2,703.7百萬元（392.01百萬美元）", "總收入達人民幣2,703.7百萬元（392.0百萬美元）", 1)
PAGES["ksy_q1_2026_p002"] = {
    "role": "eval",
    "full_text": t.rstrip() + "\n",
    "provenance": "native text layer as base; visually verified against frozen render",
    "corrections": [
        "native '392.01百萬美元' merged the superscript footnote marker into the number; visual reading is 392.0 with a superscript footnote 1",
        "page footer number 3 moved to reading-order end",
    ],
    "facts": [
        "金山云控股(納斯達克:KC及港交所:3896)公佈截至二零二六年三月三十一日止第一季度未經審計財務業績",
        "智算雲業務賬單收入同比增長90%,佔公有雲收入比重首次突破半數",
        "總收入人民幣2,703.7百萬元(392.0百萬美元),同比+37.2%,環比-2.1%",
        "經調整毛利人民幣351.4百萬元,同比+7.2%;經調整EBITDA利潤率27.6%,同比增長11.4個百分點",
        "第一季度資本開支及取得的租賃資產合計達人民幣30億元",
        "公有雲服務收入人民幣1,996.3百萬元(289.4百萬美元),同比+47.5%,環比+4.9%",
        "行業雲服務收入人民幣707.4百萬元(102.6百萬美元),同比+14.7%,環比-17.6%",
        "匯率:人民幣6.8980元兌1.00美元(二零二六年三月三十一日有效的午間買入匯率,經紐約聯邦儲備銀行核實)",
    ],
    "conditions": [
        "總收入環比減少主要由於行業雲受到季節性影響",
        "行業雲環比減少主要由於春節帶來的影響及各個項目的交付時間表有所不同",
    ],
    "non_text_regions": [],
}

# ---------- IR Wanrun p000 (eval) ----------
t = native("ir_wanrun_20241104_p000")
t = move_page_number_to_end(t, "1")
t = t.replace("□√特定对象调研", "☑特定对象调研", 1)
t = t.replace(
    "天风证券：郭建奇\n国泰君安：周志鹏\n恒安标准人寿：王祉蘅",
    "天风证券：郭建奇\n恒安标准人寿：王祉蘅\n国泰君安：周志鹏",
    1,
)
PAGES["ir_wanrun_20241104_p000"] = {
    "role": "eval",
    "full_text": t.rstrip() + "\n",
    "provenance": "native text layer as base; visually verified against frozen render",
    "corrections": [
        "checkbox glyph restored: □√特定对象调研 -> ☑特定对象调研",
        "participant rows re-ordered to visual row-major order (天风/恒安标准 first row, 国泰君安 second row)",
        "page footer number 1 moved to reading-order end",
    ],
    "facts": [
        "投资者关系活动类别:特定对象调研(☑),分析师会议/媒体采访/业绩说明会/新闻发布会/路演活动/现场参观/其他均未勾选",
        "时间:2024年11月04日14:00~15:30;地点:中节能万润股份有限公司本部三楼会议室;形式:现场会议",
        "参与人员:天风证券郭建奇、恒安标准人寿王祉蘅、国泰君安周志鹏",
        "接待人员:董事会秘书于书敏、证券事务代表肖新玲、证券部其他工作人员",
        "问1:2024年三季度半导体制造材料整体收入继续保持同比增长;产品主要包括光刻胶单体、光刻胶树脂、光致产酸剂以及半导体制程中清洗剂添加材料,国内领先技术水平",
        "问2:已销售的聚酰亚胺材料包括多种电子与显示领域的PI单体(行至页尾未完)",
    ],
    "conditions": [],
    "non_text_regions": [],
}

# ---------- KSY degraded page: identical content to ksy_q1_2026_p002 ----------
PAGES["ksy_q1_2026_p002_synthetic_degraded"] = dict(PAGES["ksy_q1_2026_p002"])
PAGES["ksy_q1_2026_p002_synthetic_degraded"]["role"] = "eval_degraded"
PAGES["ksy_q1_2026_p002_synthetic_degraded"]["provenance"] = (
    "same page content as ksy_q1_2026_p002; synthetic_degradation variant "
    "(0.55x downscale + 1.3deg tilt).  NOT real scan coverage."
)

# ---------- HRJP CB prospectus p006 (eval) ----------
t = native("hrjp_cb_prospectus_p006")
t = move_page_number_to_end(t, "6")
PAGES["hrjp_cb_prospectus_p006"] = {
    "role": "eval",
    "full_text": t.rstrip() + "\n",
    "provenance": "native text layer as base; visually verified against frozen render",
    "corrections": ["page footer number 6 moved to reading-order end"],
    "facts": [
        "厦门金鹭母公司厦门钨业是国内领先的具有国资背景的大型上市公司,拥有'钨冶炼-硬质合金-刀具制造'全产业链",
        "厦门钨业子公司九江金鹭和厦门金鹭均是原材料碳化钨的生产企业",
        "公司现有主要产品硬质合金数控刀片2021年的产能约为6,300万片",
        "募投项目达产后预计新增精密数控刀体产品50万件和各类高效钻削刀具140万支",
        "建立了以华东、华南、华北刀具集散市场为核心,覆盖全国市场的经销商体系",
    ],
    "conditions": [
        "如果株洲钻石的母公司中钨高新为增强株洲钻石的竞争地位,限制向公司供应原材料,将对公司采购、生产和销售等经营计划的正常组织产生不利影响(条件句)",
        "如果产业政策、销售渠道开拓、市场供需情况、行业竞争态势等出现不利变化,公司将面临新增产能无法及时消化风险(条件句)",
    ],
    "non_text_regions": [],
}

# ---------- Bilibili 4Q22 call p001 (eval) ----------
t = native("bili_call_4q22_en_p001")
t = move_page_number_to_end(t, "2")
PAGES["bili_call_4q22_en_p001"] = {
    "role": "eval",
    "full_text": t.rstrip() + "\n",
    "provenance": "native text layer as base; visually verified against frozen render",
    "corrections": ["page footer number 2 moved to reading-order end"],
    "facts": [
        "Sam Fan delivered opening remarks on behalf of Mr. Chen",
        "2022 strategy refocused on DAU growth and profitability",
        "DAUs increased to 93 million, up 29% year-on-year",
        "DAU-to-MAU ratio reached 28% vs 26% in the same period last year",
        "Average daily time spent per user reached 96 minutes, up 51% year-on-year",
        "2022 total net revenues RMB 21.9 billion; Q4 net revenues RMB 6.1 billion, up 6% year-on-year",
        "Gross margin improved to 20% in Q4 from 18% in the previous quarter",
        "Q4 S&M expenses cut by 28% year-on-year; S&M as % of total net revenues reduced from 30% to 21%",
        "Non-GAAP net loss in Q4 narrowed by 21% year-on-year and 26% quarter-on-quarter",
        "2023 operational goal: grow DAUs, improve gross margin, tighten expenses",
    ],
    "conditions": ["believe we are on the right track to achieve our break-even target by 2024"],
    "non_text_regions": [],
}

# ---------- BYD AR2024 p022 (holdout) ----------
t = native("byd_ar_2024_p022")
t = move_page_number_to_end(t, "23")
t = t.replace("同比变化 30%以上的原因说明\n适用 □不适用",
              "同比变化 30%以上的原因说明\n☑适用 □不适用", 1)
t = t.replace("报告期内汽车零部件生产经营情况\n□适用 不适用",
              "报告期内汽车零部件生产经营情况\n□适用 ☑不适用", 1)
t = t.replace("公司开展汽车金融业务\n□适用 不适用",
              "公司开展汽车金融业务\n□适用 ☑不适用", 1)
t = t.replace("公司开展新能源汽车相关业务\n适用 □不适用",
              "公司开展新能源汽车相关业务\n☑适用 □不适用", 1)
PAGES["byd_ar_2024_p022"] = {
    "role": "holdout",
    "full_text": t.rstrip() + "\n",
    "provenance": "native text layer as base; visually verified against frozen 200-DPI render",
    "corrections": [
        "four checkbox rows restored: ☑适用/□不适用, □适用/☑不适用, □适用/☑不适用, ☑适用/□不适用",
        "page footer number 23 moved to reading-order end",
    ],
    "facts": [
        "轿车产量2,370,709(+47.19%),销量2,358,032(+47.44%)",
        "SUV产量1,805,441(+38.84%),销量1,788,787(+38.41%)",
        "MPV产量104,934(-14.39%),销量103,551(-14.53%)",
        "商用车产量22,989(+98.71%),销量21,775(+89.17%)",
        "客车产量与销量均为5,580(+18.60%)",
        "其他产量17,409(+153.63%),销量16,195(+137.95%)",
        "合计产量4,304,073(+41.34%),销量4,272,145(+41.26%)",
        "分车型类别产销量数据变化主要是公司业务增长以及产品结构变化所致",
        "新能源乘用车产能4,281,084、快报产量4,281,084、快报销量4,250,370、销售收入525,989,680,000.00元",
        "新能源商用车产能22,989、快报产量22,989、快报销量21,775、销售收入7,340,435,000.00元",
        "产能状况指报告期产量,单位为辆",
        "公司秉持'技术为王、创新为本'理念,业务横跨汽车、电子、新能源和轨道交通四大产业",
        "纯电动及插电式混合动力'两条腿、齐步走';率先推动智驾技术全面普及",
    ],
    "conditions": [
        "同比变化30%以上的原因说明:☑适用 □不适用",
        "报告期内汽车零部件生产经营情况:□适用 ☑不适用",
        "公司开展汽车金融业务:□适用 ☑不适用",
        "公司开展新能源汽车相关业务:☑适用 □不适用",
    ],
    "non_text_regions": [],
}

# ---------- Meituan AR2024 p000 (holdout; no native -> manual) ----------
PAGES["meituan_ar_2024_p000"] = {
    "role": "holdout",
    "full_text": """美团\nMeituan\n（於開曼群島註冊成立以不同投票權控制的有限公司）\n港幣櫃臺股份代號：3690\n人民幣櫃臺股份代號：83690\n2024\n年度報告\n""",
    "provenance": "full manual transcription from the frozen 200-DPI render; page is an image cover with no text layer",
    "corrections": [],
    "facts": [
        "於開曼群島註冊成立以不同投票權控制的有限公司",
        "港幣櫃臺股份代號:3690",
        "人民幣櫃臺股份代號:83690",
        "2024年度報告",
    ],
    "conditions": [],
    "non_text_regions": [
        "插画城市/无人机/自动配送车/吉祥物骑手为装饰图形;楼体横幅'#Eat Better Live Bette…'为艺术字且被裁切,无人机箱体'美团无人机'为微小印刷字,均记不可判,不入分母",
        "大面积纯装饰区域无文字(编造负对照)",
    ],
}

# ---------- IR Wanrun p002 (holdout) ----------
t = native("ir_wanrun_20241104_p002")
t = move_page_number_to_end(t, "3")
PAGES["ir_wanrun_20241104_p002"] = {
    "role": "holdout",
    "full_text": t.rstrip() + "\n",
    "provenance": "native text layer as base; visually verified against frozen render",
    "corrections": ["page footer number 3 moved to reading-order end"],
    "facts": [
        "问7:钙钛矿材料方面,2024年三季度公司继续推进产品开发和市场推广,产品种类与客户数量均有增加",
        "业内下游企业及新进入企业持续推进钙钛矿光伏组件性能优化开发,相应尺寸效率不断创新高",
        "控股子公司九目化学的无氟氢燃料电池质子膜材料中试产品有向下游销售",
        "问8:液晶材料业务2024年三季度收入较去年同期相对平稳",
        "关于本次活动是否涉及应披露重大信息的说明:否",
        "活动过程中所使用的演示文稿、提供的文档等附件:无",
        "公司是以研发创新驱动的平台型企业,向着成为世界先进化学材料制造者的目标砥砺前行",
    ],
    "conditions": [
        "如果未来能够成功产业化,有望为公司带来新的业绩增长点(条件句)",
        "未来希望下游终端消费及液晶面板行业能够向好,从而带动上游液晶材料需求(条件)",
    ],
    "non_text_regions": [],
}

# ---------- HRJP CB prospectus p037 (holdout) ----------
t = native("hrjp_cb_prospectus_p037")
t = move_page_number_to_end(t, "37")
PAGES["hrjp_cb_prospectus_p037"] = {
    "role": "holdout",
    "full_text": t.rstrip() + "\n",
    "provenance": "native text layer as base; visually verified against frozen render",
    "corrections": ["page footer number 37 moved to reading-order end"],
    "facts": [
        "数控刀具产品主要应用于模具、通用机械和汽车行业等领域",
        "最近两年我国汽车产销量连续下滑",
        "株洲钻石是国内第一大刀具供应商,是公司主要竞争对手之一,同时是中钨高新的二级子公司",
        "中钨高新是由中国五矿集团有限公司控制的一家钨产业集团",
        "自贡硬质合金有限责任公司及株洲硬质合金集团有限公司均是公司重要原材料碳化钨粉及钴粉供应商",
        "向自贡硬质合金采购碳化钨粉金额占材料采购总额的比例分别为34.52%、32.59%和29.03%",
        "向株洲硬质合金集团采购碳化钨粉、钴粉及其他金属粉末金额占比分别为1.72%、2.95%和1.73%",
        "厦门金鹭母公司厦门钨业拥有'钨冶炼-硬质合金-刀具制造'全产业链",
    ],
    "conditions": [
        "如果公司不能保持并强化自身的竞争优势和核心竞争力,公司产品的市场份额及价格可能会因市场竞争加剧而下降(条件句)",
        "若未来宏观经济不景气、产业政策发生重大调整或居民消费习惯发生重大变化,将有可能导致模具、通用机械及汽车行业的需求增速放缓或萎缩(条件句)",
    ],
    "non_text_regions": [],
}

# ---------- Bilibili 4Q22 call p003 (holdout) ----------
t = native("bili_call_4q22_en_p003")
t = move_page_number_to_end(t, "4")
PAGES["bili_call_4q22_en_p003"] = {
    "role": "holdout",
    "full_text": t.rstrip() + "\n",
    "provenance": "native text layer as base; visually verified against frozen render",
    "corrections": ["page footer number 4 moved to reading-order end"],
    "facts": [
        "Full year revenues grew by 13% to RMB 21.9 billion",
        "VAS revenues RMB2.3 billion in Q4 and RMB8.7 billion for the year, up 24% and 26% year-on-year",
        "2022 live broadcasting revenues increased by over 30%",
        "Monthly active live broadcasting hosts increased by over 70%; MPUs for live broadcasting grew by over 40%",
        "Added nearly one million premium members in Q4, reaching 21.4 million premium memberships",
        "Launched Chinese anime titles including The Three-Body Problem and Yao-Chinese Folktale (中国奇谭)",
        "Yao-Chinese Folktale generated over 200 million views",
        "Advertising revenues up by 12%, reaching RMB 5.1 billion in 2022 and RMB 1.5 billion in 4Q",
        "Top Q4 advertising verticals: mobile games, e-commerce, digital products & home appliances, automotive, skincare & cosmetics",
        "Q4 performance-based ad revenue grew by over 50% year-on-year",
    ],
    "conditions": [],
    "non_text_regions": [],
}

gold = {
    "schema_version": "cwp-ocr-gold/1",
    "plan_id": "w23-xiaomi-ocr-2026-10-30",
    "frozen_before_engine_outputs": True,
    "method": (
        "gold = visual transcription verified against the frozen 200-DPI page "
        "renders.  For born-digital pages the PDF text layer served only as a "
        "candidate base and every page was visually checked and corrected "
        "(checkbox glyphs, footnote-marker merges, page-number reading order, "
        "row-major participant order, garbled-layer replacements).  Native "
        "text alone was never accepted as gold.  Number tokens for the number "
        "accuracy metric are derived from gold full_text by the comparator."
    ),
    "table_linearization": "table content kept row-major in visual reading order; cells whitespace separated",
    "superscript_note": "ksy_q1_2026_p002: '392.0' carries a superscript footnote marker '1' on the page; the marker is not part of the number and is excluded from full_text; engines emitting '392.01' count as a wrong number",
    "pages": PAGES,
}
out = PLAN / "gold.json"
out.write_text(json.dumps(gold, ensure_ascii=False, indent=1), encoding="utf-8")
total_chars = sum(len(p["full_text"]) for p in PAGES.values())
print(f"WROTE {out} pages={len(PAGES)} total_chars={total_chars}")
