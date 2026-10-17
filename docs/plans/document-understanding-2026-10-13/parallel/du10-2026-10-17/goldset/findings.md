## ROOT 最终接收 — 2026-10-17

状态：PASS，作者完整历史 faf5e580 已 merge；ROOT 修正与独立复审以 receipts/root-gold-final-review.json 的 17 项实际文件 SHA 为准。下方旧 schema1、raw bindings 命令、旧 PASS 和原始 handoff SHA 均为历史，不能用于当前 schema2。

### 实际修正

- 语义：Verisk 单一 Insurance segment 的分母（552.1+230.5=782.6 million）不再误罚为非总收入；阿里8.60亿与含蚂蚁9.60亿去重口径分开；东方电缆原文 Q3 总额约30.66亿与类别35.49亿的冲突保持未知，不自创包含其他收入/YTD解释；名创电话会按开场创始人/CEO归因；中微21.81%属于等离子体刻蚀设备，XD RIE与YDRIE时间点分开；宁德772保留报告期内，仅321在建为期末。
- 抽象：source_ref 使用真实公开v2身份，source_binding仅用于测试初次登记；临时 SourceCatalog.register_sources → query_ref → open_version 实读验证SHA。HTML严格绑定 canonical unit_id+source_locator 并批量 replay；PDF只查指定物理页，无全篇回退。生产根/配置不改，不复制原文。
- TDD语义先8FAIL；当前71PASS/2.83秒，含5个真实临时Catalog正反控（错误SHA、大小、页码、quote拒绝）。11/11真实来源回放PASS；独立复算10原件SHA/size/mtime保持，生产config SHA保持，隔离目录和sentinel恢复。
- 最终独立复审8项全部闭环、0未解决。旧独审Verisk数字误读保留为历史，由本ROOT结论覆盖。

### 当前复现命令（从 company-wiki 根运行）

```powershell
python -B -X utf8 -m pytest docs/plans/document-understanding-2026-10-13/parallel/du10-2026-10-17/goldset/tests -q -p no:cacheprovider
python -B -X utf8 docs/plans/document-understanding-2026-10-13/parallel/du10-2026-10-17/goldset/tests/verify_anchors.py --project-root . --output <独立测试收据路径>
```

环境需已安装本项目和catalog/PDF依赖；第二条需要当前source_catalog配置中的原件。只在隔离临时catalog登记少量选定路径，不扫描全湖、不写生产库。回放PASS只证明来源/locator，不证明经济语义或摘要质量；语义另由独立实读审查负责。

**这是已被读取和修正的回归标注集，不是盲holdout，不是正式模型摘要质量验收。** case.prior_use仅描述最初选样时的历史；新holdout必须另选未参与调整的来源。新增股发行等完整文档阅读覆盖仍遵循母计划，不以本11例冒称全覆盖。0收费/下载/翻译，原件无变更。

Next Step：ROOT继续共享引擎PDF生产接线，随后配置供应商真实摘要、缓存恢复与新盲样本验收；此数据包不新增生产门禁。


---

以下为历史记录（状态以顶部 ROOT 更新为准）。

# DU10-CWP-SUMMARY-GOLDSET — 发现记录（findings）

更新：2026-10-17（A 节点完成，B 节点施工中）

## 1. A 节点：缺口盘点结论

对照对象与结论依据：

- 既有 DU-Gold 29 个 sample（`tools/document_understanding_benchmark/gold/`，含 DU5 新集与
  fresh/holdout 系列）：全部 ID 列表见 `receipts/node_a_freeze.json`。
- DU2 families/facets 交付约定（`review/deliverables/{families,facets}/README.md`）：
  复用 quote-anchor（`{page|line, exact_quote}`、空白归一化）、`must_preserve`/`must_not_assert`、
  机内 bindings 不提交、C 节点只读核对三件套（SHA 复算/引文逐字/mtime 不变）。
- 摘要合同与已知失败（`review/summary_grounding_implementation.md`、
  `review/source_scoped_summary_implementation.md`）：真实 cn-h1 独审 8PASS/6WARN/6FAIL 中
  六类错引——缩小/错换 unit、邻接/标题借数、产品指代、同量纲不同时期、planned/actual、
  QA 问句数字当事实。本基准每例至少绑定其中一类失败模式。

### 缺口矩阵（既有 gold 覆盖 × 本卡新增）

| 类型 | 既有 gold 覆盖（sample_id） | 本卡新增 case | 缺口说明 |
|---|---|---|---|
| A/年报 | 中微2025年报（survey）、SMIC fy2025（fresh） | `du10gs-cn-annual-catl-industry`、`du10gs-cn-annual-catl-capacity` | 宁德时代 2025 年报：第三方行业数据归属；产能/项目"推进建设中"叙述与收入表同页 |
| A/半年报 | 中微 H1、讯飞 H1 | `du10gs-cn-interim-sugon` | 中科曙光 H1：液冷/存储产品进展、行业预测（IDC）vs 统计局实际 |
| A/季报 | 方邦/珀莱雅/广联达/雅克 Q1、中微 Q1、世华稀疏 Q1 | `du10gs-cn-q3-dfc` | 三季报（Q3）未覆盖；单季口径注释与"类别收入"叙述在同一 11 页短文档 |
| A/招股书 | 仅 IPO 确认意见（cn-ipo-confirmation，1 页扫描） | `du10gs-cn-ipo-hrjc` | 招股书正文（行业+募投计划）从未有 gold；350 页科创板招股书 |
| A/增发 | 中密控股（du5）、恒锋工具（cn-equity） | 不新增（避免重复） | 既有覆盖充分；本卡不重复 |
| A/可转债 | 无 | `du10gs-cn-convbond-mlkw` | 密尔克卫可转债：达产后效益测算（预计/完全达产后条件）+首个危废中心新业务 |
| A/IR | 万润活动记录表（cn-ir） | `du10gs-cn-ir-amec-minutes` | 交流纪要形态未覆盖：管理层转述、预测标注、在研产品、订单vs收入 |
| H/年报 | 名创2024、阿里FY23、安踏、Biren、金山雲 | 不新增（避免重复） | 覆盖充分 |
| H/中报 | 金山雲 interim（du5） | `du10gs-hk-interim-miniso` | 名创 2025 中报：海外门店三模式存量/净增、品牌口径vs集团口径、RMB 单位 |
| H/招股书 | 无 | `du10gs-hk-ipo-baba` | 2019 全球发售招股书：同页两组 TTM 期间口径、国际消费者去重定义 |
| 电话会 TXT | MSFT Q4 2026 TXT（us-txt）、吉比特 docx（du5） | `du10gs-call-miniso-q4-2024`（PDF 讲稿形态） | 新的 CN TXT 原件在本仓 configured roots 内不存在（见 NOT_AVAILABLE）；名创官方讲稿为 PDF 形态，补"话轮/讲稿+actual超额+2025计划"证据 |
| US/10-K/20-F/8-K | MSFT 10-K/8-K、Apple/MDB/NVDA 10-K、TAL 20-F | 不新增（避免重复） | 覆盖充分 |
| US/10-Q | （du2-families 用过 vrsk20250331，非 summary gold） | `du10gs-us-10q-vrsk` | 10-Q MD&A 订阅占比叙述 + non-GAAP EBITDA 定义；本卡用更新的 2026Q1 文件 |

### NOT_AVAILABLE（如实缺样，不以合成冒充）

1. **新的 CN 电话会 TXT 原件**：本仓 configured roots（company_raw/dropbox_stock/dayu_portfolio）
   内唯一的电话会 TXT 是 `companies/Microsoft/raw/transcripts/MSFT_Q4_2026_earnings_call.txt`，
   已被 us-txt gold 使用。earnings-transcripts 仓内另有 MDB/MSFT/SNOW/NVO/TAL/FIG 原语言 TXT，
   但不在本卡仓库边界（CWP configured roots）内，本卡不引用、不复制、不声称覆盖。
2. **H/季报公告（新原件）**：金山雲 2025Q4/2026Q1 内幕消息已被 du5 覆盖；未再新增。
3. **US 电话会 TXT 新原件**：同第 1 条；以名创 PDF 官方讲稿补话轮/讲稿证据并明确标注形态差异。

### 先用（prior-use）与原件身份要点

- 中科曙光、东方电缆：`.planning/` 与 `docs/plans/` 零提及，fresh。
- 华锐精密：n5 raw-duplicate-audit 与 narrative-pilot 结果仅路径/哈希元数据；其可转债募集
  说明书曾被 n5-document-quality S06 读取——本卡改选其 IPO 招股书（未被读取），如实记录。
- 密尔克卫：仅路径/哈希元数据扫描，内容未读。
- 宁德时代：万润 cn-ir 引文上下文提及公司名；du8-ff41 一次 filing-fetch 临时目录元数据；
  本 2025 年报原件与内容未被读取。
- 名创优品/阿里巴巴/中微公司/Verisk：同公司其他文档已有 gold/读取记录，本卡全部选用
  同公司**不同原件**并在每例 `prior_use` 中说明新增证据。
- 侧车元数据观察（如实记录，不影响 case 判定）：
  - `阿里巴巴招股说明书2019.pdf.source.json` 的 `market=CN`（实为港股全球发售招股书，封面股份代号 9988）；
  - `vrsk20260331_10q.htm.source.json` 的 `market=HK`（实为 US/NASDAQ:VRSK）；
  - 名创优品 `2025半年报（港股）.pdf` 无侧车（`source_registered=false`）。
  case 内 `market` 以文档内容证据为准，侧车原值保留在 `registered_sidecar` 字段，不改写。

## 2. 每例绑定失败模式（映射已知六类错引）

| case | 主绑定失败模式 |
|---|---|
| catl-industry | 第三方行业数据当公司收入；预测当实际 |
| catl-capacity | planned/actual（在建≠投产）；叙述与财务表同页借数 |
| sugon-interim | 预测（IDC 全年）当实际（H1）；第三方数据归属 |
| dfc-q3 | 同量纲不同时期（单季 vs 累计）；类别收入当总收入 |
| hrjc-ipo | planned/actual（拟建募投当已建成）；行业规模当公司收入 |
| mlkw-convbond | 测算当已实现（完全达产后预计）；拟建首个别当已有业务 |
| amec-minutes | 订单当收入；预测标注丢失；在研当上市 |
| baba-hk-ipo | 同页不同 TTM 期间混用；去重口径丢失 |
| miniso-hk-interim | 存量 vs 净增；品牌口径 vs 集团口径 |
| miniso-call | 讲稿量词（约/接近/超过）丢失；2025 计划当已实现；说话人归属 |
| vrsk-10q | "insurance revenues"范围当总收入；non-GAAP 当 GAAP；approximately 丢失 |

## 3. B 节点设计决定

- case schema 定为 `du10-summary-goldset-case/1`：fact 结构沿用 du-gold/1
  （`any_support_sets` 组内 AND、组间 OR；`{page|line, exact_quote}` 锚点；
  `must_preserve`/`must_not_assert`），新增摘要专用顶层字段
  `allowed_summary`（允许的摘要表达）、`summary_guidance`（结论边界与必要限定）、
  `misread_traps`（同页/邻近易误读反例锚点）。
- 引文预算沿用 ≤8KiB/文档（du-gold/1 约定）；不存整页/整份。
- 校验器（`tests/verify_anchors.py`）只查数据完整性 + 只读原件锚点回放；
  不判定经济事实与摘要质量；不接 catalog.db（该库为空，接口见第 4 节）。
- `catalog.db` 为空库（零表）的观察：`ReadOnlyCatalogReader` 路径存在但本机无登记数据；
  因此"SourceRef 只读解析"实现为 configured-root + repo 相对路径 + SHA 复算
  （与 benchmark native bindings 规则一致），不伪造 SourceExport 记录。

## 4. C 节点安排

- 独立 reviewer（非作者）用 `tests/verify_anchors.py` + 自行抽样重开原件核对；
  检查项：SHA 一致、锚点逐字在页、支持关系成立、无"展望当已实现"、边界完整。
- 终审对最终 HEAD 与每例 hash 复核后出报告 `receipts/node_c_independent_review.md`。
