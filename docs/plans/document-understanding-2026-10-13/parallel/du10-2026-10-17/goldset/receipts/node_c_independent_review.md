# DU10-CWP-SUMMARY-GOLDSET — Node C 独立实读审查报告（independent reviewer）

- Reviewer：独立上下文、非作者。日期：2026-10-17。
- 被审 worktree：`C:/Users/郑曾波/Projects/company-wiki-du10-summary-goldset`，分支 `codex/du10-cwp-summary-goldset`。
- 本报告同时落盘 `receipts/node_c_independent_review.md` 与同名 `.json`；两文件是本次审查唯一写入。

## 1. Reviewed HEAD 与完整性

- Reviewed HEAD（完整 SHA）：`5747dc07b21fae34db7c04048b282d51e9c88591`
  （`git rev-parse HEAD` 输出，与任务卡预期一致；`git log --oneline -3` 首条即本提交）。
- `git status --short`：仅 `?? .../receipts/node_c_anchor_verify_reviewer_run.json`（reviewer 复跑 verify 的输出，属允许写入，保留作为回放证据）；无任何对原件、配置或生产目录的改动。
- diff 基线 `900dbf6489f3b995a0bfb7fcbb8a001a68df241d...HEAD` 共 22 个文件，全部位于
  `docs/plans/document-understanding-2026-10-13/parallel/du10-2026-10-17/goldset/` 下：
  `cases/`（11 case + index.json）、`tests/`（_support.py、test_goldset_structure.py、verify_anchors.py）、
  `receipts/`（node_a_freeze.json、node_b_tests.json、anchor_verify_author_run.json、build_cases_node_b.py）、
  `task_plan.md`、`findings.md`、`progress.md`。无越界文件。

### 复跑命令与退出码

| # | 命令 | 结果 | exit |
|---|---|---|---|
| 1 | `python -B -X utf8 -m pytest "docs/plans/document-understanding-2026-10-13/parallel/du10-2026-10-17/goldset/tests" -q --ignore-glob "*verify_anchors*"` | **58 passed** in 3.22s | **0** |
| 2 | `python -B -X utf8 tests/verify_anchors.py --bindings "C:/Users/郑曾波/.du10-goldset/bindings.local.json" --output receipts/node_c_anchor_verify_reviewer_run.json` | 11/11 case PASS（收据已落盘） | **0** |

### 原件 SHA-256 复算（reviewer 独立计算）

10 份唯一原件全部与 case `source_sha256` 一致：

| 原件 | SHA-256（前16） |
|---|---|
| 宁德时代2025年报.pdf | `c15272977147dee7`（两 case 共用，一致） |
| 中科曙光2025半年报.pdf | `8f17b0af565dddcb` |
| 东方电缆2025三季报.pdf | `980224213ff8aa32` |
| 华锐精密招股说明书.PDF | `e463853bf1efd788` |
| 密尔克卫可转债募集说明书.PDF | `9ada21401dd35e73` |
| 中微交流纪要20220416.pdf | `9e8a36d3f974c0f8` |
| 阿里巴巴招股说明书2019.pdf | `7ae21e7f811d1b74` |
| 名创优品2025半年报（港股）.pdf | `9ca846507bf4fcf7` |
| 名创优品 2024 Q4 Transcript.pdf | `dbe321a9343aa3dd` |
| vrsk20260331_10q.htm | `8273e1412f7892b0` |

### 引文预算与 NOT_AVAILABLE

- 每 case `quote_budget_chars_normalized`（复跑 verify 输出）：190/134/178/124/265/149/301/158/273/226/456，
  全部 ≤ 8192；同一原件（CATL 两 case）按文档合并 324，仍远低于 du-gold/1 的 8KiB/文档预算。✅
- NOT_AVAILABLE 声明核查：只读 `find` 确认主仓 `companies/` 下唯一 transcripts 目录是
  `companies/Microsoft/raw/transcripts/`（含 MSFT_Q4_2026_earnings_call.txt，已由既有 us-txt gold 使用）。
  “无新的 CN/US 电话会 TXT 原件”声明属实。✅

## 2. 逐例 verdict

判定依据：锚点在所指 PDF 物理页（1 基）±1 页实读复验；语义（支持关系、must_preserve、must_not_assert、
misread_traps、planned/actual 双向）逐条人工复核；每份原件另抽查 2-3 个锚点外页面。

| case | verdict | 要点 |
|---|---|---|
| du10gs-cn-annual-catl-industry | **PASS** | 三个 fact 引文逐字在 p17（“使用量为1,187GWh，同比增长31.7%”“市占率为39.2%…连续9年（2017-2025年）”“出货量550GWh，同比增长79%”“连续5年（2021-2025年）”）；使用量/出货量两口径正确分列；trap “综合竞争力行业领先，实现业务稳健增长” 确在 p16 公司自评段，与下半行业段同页结构属实；p17 所有行业数字确带 SNE/中汽协/IEA/国家能源局等来源。 |
| du10gs-cn-annual-catl-capacity | **PASS** | 项目“稳步推进……建设”与“产能772GWh，期末在建产能321GWh”逐字在 p24；收入表引文（423,701,834/362,012,554/17.04%）与“单位：千元”均在 p24 同页，混表 trap 属实；modality=plan + must_not_assert（匈牙利/印尼已投产、321 当已投产、772 当产量）方向正确。 |
| du10gs-cn-interim-sugon | **PASS** | ParaStor 连续6年中标中国移动、C8000 2024年 750kW 以上、统计局 126.7%、IDC“有望达到3660亿美元”四条引文分别在 p8/p8/p9/p9 实读命中；“连续6年中标”与“赛迪细分市场份额首位”确为同页同句不同事实，must_not_assert 拆分正确；IDC 标 plan、统计局标实际，脚注黏连已由空白归一化覆盖。 |
| du10gs-cn-q3-dfc | **PASS**（含观察 O1） | 35.49亿/35.8% 引文在 p3 变动原因表；“利润总额_本报告期 51.19”等行名在 p3；“‘本报告期’指本季度初至本季度末3个月期间”在 p2；“二、股东信息”与“年初至报告期末”双 trap 属实。must_preserve 单季口径锚定 p2 注释，正确。 |
| du10gs-cn-ipo-hrjc | **PASS** | “约393亿元/136亿元”与“2016—2019年…37.17%下降至34.61%”逐字在 p105，页内图表（2016=37.17%、2019=34.61%）与文字一致，脚注6 在文中标注；p293 两条募投引文逐字命中，均为“将/拟”计划语态；“厦门钨业”行业供应商名单 trap、“打下坚实基础”说理性措辞 trap 均在所指页。must_preserve“产能饱和为报告期内状态”与“约”保留正确。 |
| du10gs-cn-convbond-mlkw | **PASS** | p344 五条引文（70,000.00万、5.0万吨/年、首个拟建成、完全达产后预计…19,528.30/4,783.21/39.38%/6.17%、徐圩新区 A 地块）全部逐字命中；实施主体张家港密尔克卫环保科技有限公司同页；测算标 conditional、拟建标 plan，反例覆盖“去条件化/业绩承诺/现有业务”三个主要误读。 |
| du10gs-cn-ir-amec-minutes | **PASS**（含建议 I2） | 订单 41.29亿 vs 收入 31.08亿（p1）、设备市场 44.7% 与“2022年会超过800亿美元”+“（2022年是预测数据）”括注（p2）、Nanova 超100%/2021 超200%（p3）、XD RIE/YDRIE 在研两条（p3）全部实读命中；纪要形态 trap（无日期抬头、页内无签字）属实。见 I2。 |
| du10gs-hk-ipo-baba | **FAIL（I1）** | 锚点与命题本身全部属实（p19 规模框双 TTM、p21 集团利润表、p22 占比表旁证），但 fact `global-annual-active-consumers` 的 must_preserve 第 3 条口径错误，见下节。 |
| du10gs-hk-interim-miniso | **PASS** | p14 三模式存量（579/425/2,303）、期初503/净增76/期末579、双语并排、stock vs flow 三行表全部属实；p23 “total number of directly operated stores on the group level was 637, compared to 393 as of June 30, 2024” 与 “RMB2,181.0 million…increased by 43.3% year” 逐字命中；637（集团直营）与 579（品牌海外直营）口径陷阱成立；“净增≠新开”限定正确。 |
| du10gs-call-miniso-q4-2024 | **PASS**（含建议 I3） | p3 头句 7,780/净增1,219、三分口径+“均超额完成2024年初开店目标”、“超过3,100家/接近40%/约170亿人民币”三个量词、p4“今年我们已经筹划了超过90档IP上新”（标 plan）、p2“除非另有说明，货币单位均为人民币”全部逐字命中；“叶董讲稿”页眉 trap 属实；目标数值不给、反推被 must_not_assert 正确禁止。 |
| du10gs-us-10q-vrsk | **PASS**（含建议 I4） | 84%/83% 订阅句与 16%/17% 交易/咨询句均定位在打印页 27（后者原文存在跨标签断词 “t ransactional”，在既定的“删除全部空白”归一化约定下匹配，内容属实）；EBITDA non-GAAP 定义句在打印页 26；“Total revenues $782.6 $753.0” 在分部/地区 disaggregation（打印页 26 前后）与 MD&A 合并利润表（打印页 28，+3.9%）三处一致，确认 782.6 为合并总收入；打印页码 26/27/28 与内容对应。见 I4。 |

### 抽查覆盖（锚点外页面）

- CATL：p15/16/18/23/25 —— 章节归属与页码无错位。
- 曙光：p7/10 —— 非经常性损益表与经营讨论衔接正确。
- 东缆：p1/4 —— 主要财务数据与股东表正确。
- 华锐：p104/106/292/294、p200 —— 印刷页码 1-1-103/1-1-105/1-1-291/1-1-293/1-1-199，物理页=印刷页+1，全册一致。
- 密尔克卫：p343/345、p200（印刷 199）—— 同上，一致。
- 中微：p4 —— CCP/ICP 运出量等数字与 p3 产品线口径不冲突。
- 阿里：p18（–9–）/p20（–11–）/p22（–13–）—— p22 确有“雲計算 7%”占比行，佐证 case 中“占比当绝对额”反例的现实性。
- 名创中报：p13/15/22/24 —— 合伙人表、区域分布表、收入/毛利、经营利润链条连贯。
- 名创讲稿：p1/5 —— Operator 开场（创始人兼首席执行官叶国富先生）与海外业务段。
- VRSK：打印页 26/27/28 定位与内容逐一对上。

## 3. Issues（逐项）

### I1（阻断，必须修复）du10gs-hk-ipo-baba — must_preserve 口径错配

- 位置：`cases/du10gs-hk-ipo-baba.json` → `facts[id=global-annual-active-consumers].must_preserve[2]`：
  **“中国消费业务+蚂蚁金服去重合并口径”**。
- 原件证据（p19 规模框及注释）：
  - “阿里巴巴數字經濟體中國用戶(1)（中國消費業務(2) + 螞蟻金服）9.60億”，注(1)=去重后中国消费业务 AAC
    与蚂蚁金服中国年度活跃用户之总和；
  - “全球年度活躍消費者(3) 8.60億”，注(3)仅为期间（截至2019-06-30止12个月）；
  - “國際年度活躍消費者(3)(4) 1.30億”，注(4)=去重后 Lazada 和速卖通 AAC 之总和。
  即 **8.60亿 = 中国消费业务 7.30亿 + 国际 1.30亿，不含蚂蚁金服用户**；蚂蚁金服去重并入的是 9.60亿中国用户口径。
- 问题性质：must_preserve 要求摘要为 8.60亿保留“含蚂蚁金服去重合并”范围，与原件不符；且与本 case 自身的
  boundary（“8.60亿不得写成……含蚂蚁金服中国用户，去重合并口径”）直接矛盾——同一条目内自相矛盾。
  下游若照 must_preserve 执行会把错误范围注入摘要。
- 建议修复（一行）：将 must_preserve[2] 替换为类似
  “全球8.60亿＝中国消费业务7.30亿＋国际1.30亿（Lazada与速卖通去重），不含蚂蚁金服用户（蚂蚁金服仅并入9.60亿中国用户口径）”。
- 其余部分（锚点、命题、allowed_summary、boundary、must_not_assert、其余三 fact）复核无误。

### I2（非阻断建议）du10gs-cn-ir-amec-minutes — allowed_summary[2] 时间限定轻微混并

- allowed_summary[2]：“XD RIE、YDRIE处于在研阶段，预计一年左右进入市场。”
- 原件 p3：“一年左右即将进入市场”仅绑定 YDRIE；XD RIE 是“很快就完成开发进入市场”。
- 建议改为分列，例如：“XD RIE 已开发出样机、很快完成开发进入市场；YDRIE 在研，预计一年左右进入市场。”
  （fact 的 exact_quote 与 must_preserve 本身正确，故不阻断。）

### I3（非阻断建议）du10gs-call-miniso-q4-2024 — 说话人头衔

- proposition/must_preserve 称“叶国富（董事长）”；讲稿自身表述为 p1 “创始人兼首席执行官叶国富先生”+p3 页眉
  “叶董讲稿”。“董事长”是外部常识头衔，非本件原文。建议 must_preserve 改为“说话人=叶国富（本件自称创始人兼
  首席执行官，页眉‘叶董讲稿’）”或径用“叶国富”。说话人归属与讲稿形态本身正确，不阻断。

### I4（非阻断建议）du10gs-us-10q-vrsk — boundary 括注理据过时

- boundary “84%不得写成总收入占比（公司另有能源与专业市场等收入）”：本 10-Q 的收入 disaggregation 仅含
  Insurance（Underwriting+Claims）且其合计=总收入（782.6），全文无 “specialized/能源” 行。理据与文本不符，
  但边界方向（84% 的句子范围是 insurance revenues，不得改写为 total）仍正确。建议括注改为
  “（原句 scope 为 insurance revenues；本件 disaggregation 中 Underwriting+Claims 即合计总收入，二者数值相同但口径表述不得互换）”。

### 观察项（不构成 case 缺陷）

- O1（dfc）：原件内部数字张力——单季总收入 30.66亿（p1，本报告期 3,065,970,750.30 元）小于同一“本报告期”
  口径下的类别收入 35.49亿（p3）。标注逐字忠实于原件且以 p2 单季注释为锚，属原件层面现象，超出 goldset
  可修复范围；建议在下游使用说明中提示。
- O2（vrsk）：原文 “providing t ransactional…” 存在跨标签断词；`_support.py norm()` 为“删除全部空白”
  （沿 du-gold/1 与 DU2 families 约定，有 docstring 声明），在该约定下匹配成立；若未来换用“折叠空白”
  规则会失配，建议保持约定一致并在 README/卡片中已声明（现已声明）。

## 4. “展望/计划写成已实现事实”逐例结论

| case | 结论 |
|---|---|
| catl-industry | 无展望；行业统计均按已实现转述且带第三方来源 ✅ |
| catl-capacity | “推进……建设”保持进行时，modality=plan，无“已投产”升格 ✅ |
| sugon | IDC 全年预测保留“有望”并标 plan；统计局 H1 标实际；C8000（2024 实际）与 C7000-F（2025 发布）时间归属正确 ✅ |
| dfc | 全部已实现数据，单季口径保留 ✅ |
| hrjc | 募投标 plan（“拟/将”）；产能饱和限定为“报告期内状态”，未写成摘要时点事实 ✅ |
| mlkw | 效益测算标 conditional 且保留“完全达产后预计”；“首个拟建成”未写成已有业务 ✅ |
| amec | 2022 市场规模标 plan 且保留预测括注；XD RIE/YDRIE 标 plan（在研）✅（见 I2 时间归属建议） |
| baba | 全部历史实际数据 ✅（问题在 I1 口径，非展望方向） |
| miniso-hk | 全部已实现存量/流量 ✅ |
| miniso-call | 90 档 IP 上新标 plan（“筹划”）；三个量词（超过/接近/约）保留；反向检查无已实现被错标为计划 ✅ |
| vrsk | 全部已实现 + EBITDA non-GAAP 属性保留 ✅ |

未发现任何一例把管理层展望/计划/测算写成已实现事实，也未发现反向错误（已实现被错标为计划）。

## 5. Overall 结论

**FAIL（1 项未解决问题）**。

- 阻断：I1（baba must_preserve 将 9.60亿口径误配给 8.60亿，且与同 case boundary 矛盾）。
- 非阻断建议：I2/I3/I4（措辞与理据，可随 I1 一并小改）。
- 其余 10 例全部 PASS；两条收据命令 exit=0；SHA/锚点/页码/预算/边界/NOT_AVAILABLE 全部核验通过；
  reviewer 复跑收据保留于 `receipts/node_c_anchor_verify_reviewer_run.json`。

修复 I1（单行 JSON 编辑）并复跑 `tests/verify_anchors.py` 后，预期整体可达 PASS；届时按任务卡由 reviewer
对最终 HEAD 与每例 hash 复核换版。

## 附：cases/*.json SHA-256（reviewed HEAD 5747dc07）

```
du10gs-call-miniso-q4-2024.json      b46e1a7aaa5b59303d77d3a7f03f74f1bb3c8b7e76f6b3f549987db9aa60e61d
du10gs-cn-annual-catl-capacity.json  5e4b9bf294b9506e372ac2d4b6e88f37c7e561933cf7b295cc7df2a764ce9179
du10gs-cn-annual-catl-industry.json  ef0f3704fff5e4a8ad1c8836b2d52bcb02f1595780333cd8d2606efddb1bbc58
du10gs-cn-convbond-mlkw.json         27988c3ba23cd19ea9906ae9302faf017352b0473c9be66ebc990eb24aa496a8
du10gs-cn-interim-sugon.json         7c58a68161697c08c3f1f49892aa2b32348a4cafa950a5f683cc5a712e34a810
du10gs-cn-ipo-hrjc.json              5502d0f67658f748db01675e5850cb94494f700314cc05ad8d86d65a931009ba
du10gs-cn-ir-amec-minutes.json       e0b3da655acf8dde06416a00a127748d1338c5b7bc53b3e7bc5b19c8991d75bb
du10gs-cn-q3-dfc.json                21e186fb55ad47288a157ad8e562ca1ac26e63e7343819a3ec295f7ba2b02e7e
du10gs-hk-interim-miniso.json        c1b140f7ad913801a89210c9e3ac7e6e0edc29dcf66699cb16edff42070c1e5f
du10gs-hk-ipo-baba.json              4504c5ef898c8dcf7aef8221987e213ad2b2614a9934a72bf36b2efe8e36b470
du10gs-us-10q-vrsk.json              cf46b219b0c4cff8f0d98d3a3453a6a887dd14580526df5f2941f63096d220f8
index.json                           8982b90f3eaafc86ef30117d3866f00ae83347ede21c7bd04a87ca54f6a56102
```
