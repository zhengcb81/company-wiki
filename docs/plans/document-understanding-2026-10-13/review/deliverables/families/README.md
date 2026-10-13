# DU2-FAMILIES：文档用途、生命周期与完整阅读策略数据包

`du2-family-spec/1` + `du2-reading-case/1` 交付包。把各类文档“如何识别、先读什么、哪些限定不能丢”
做成可导入唯一策略库的数据规格与真实证据。**本包不是路由器、不是金标判定器、不接生产**：
ROOT 负责把 records/ 导入唯一 profiles registry 并做实际消费测试；数据工程通过 ≠ 生产已支持全部类型。

- 任务卡：[DU2-FAMILIES](../../cards/DU2-FAMILIES.md)；公共接口：[INTERFACES](../../INTERFACES.md) §2/§4/§6
- 覆盖矩阵：[coverage_matrix.md](coverage_matrix.md)；逐形态状态：[index.json](index.json)
- 缺样补采：[acquisition_requests.json](acquisition_requests.json)；交接：`.planning/du2-families/handoff.{json,md}`

## 目录

| 路径 | 内容 |
|---|---|
| `records/*.json` | 24 份 du2-family-spec/1 规格：A/H/US 定期（年/半/季）、A/H/US 招股、定增/可转债/可研/项目变更、IR/call、release/deck、8-K/6-K 容器、摘要/修订横切、行政负例、问询与重大经营事件、研报/新闻/政策 |
| `cases/*.json` | 31 个真实摘录 case（13 份原件、两家 A/H 公司为主、美股佐证）+ 8 个合成正反例 case；每 case 带失败反例 mutation |
| `tests/` | 结构不变量测试（85 项）+ `_support.py` 校验 helper + `c_node_quote_check.py`（C 节点原文对照工具，非 pytest） |
| `index.json` | du2-family-index/1：records 相对路径 + 每形态独立 spec/evidence/integration 状态与 gaps |

## 规格要点（du2-family-spec/1）

- 三条独立轴：`regimes`（cn_exchange/hkex/sec/other/unknown）× `family`（DU/1 十一类）×
  `modifiers{extent, revision}`。上市地不代替用途；摘要/修订是正交修饰
  （`lifecycle_revision_overlay` 单记录处理，不复制各 family 策略）。
- `recognition` 只用 `literal_phrase`（短语，无 regex/DSL）与 `metadata_equals`（field 限七项），
  每条带 location 与非空 reason；反例显式区分“目录≠正文、标题≠正文、问句≠事实、测算≠实际”。
  执行信号不含公司名与固定页码（测试强制）。
- `sections.role` 复用 DU/1 角色枚举；`heading_path` 层内 OR、层间 AND；
  同 role 别名可组合且不丢（R01 防御，测试用 merge helper 校验并集不缩水）。
- `context_requirements` 四种触发（always_for_assertion/quantity_emitted/project_emitted/
  explicit_condition_present）+ 12 个槽位 + missing_behavior（unknown/partial/deferred）；
  每条带非空 reason。`always_for_assertion` 必含 period（scope/生命周期绑定）。
- `fallback` 三键（unread/ambiguous/no_business）描述进入 generic/缺口/合法 skip 的方式，不新增审批。

## 证据要点（du2-reading-case/1）

- 真实 case 均带 `source_sha256`（与母计划 sample_manifest 一致）、`origin`（含出处/纠正说明）、
  `local_binding_key`（本机 `bindings.local.json`，不提交）。
- `locator` 一律 null + `anchor{physical_page|line, exact_quote}`（quote anchor 交 ROOT 解析为正式定位），不伪造 SourceRef。
- 支持集外 OR、内 AND；`must_preserve`/`must_not_assert` 写明限定与误读；每 case 带 `mutations` 失败反例。
- 语义生产执行一律 `execution_status=NOT_RUN_ROOT_INTEGRATION`：本包只证明数据结构与证据可回放，
  不声称引擎已理解正确、不虚报召回。

## 复跑

```powershell
# 数据结构不变量（唯一日常命令；只测本包）
python -B -X utf8 -m pytest docs/plans/document-understanding-2026-10-13/review/deliverables/families/tests -q

# C 节点原文对照（需本机原件可读；只读、不写派生）
python -B -X utf8 docs/plans/document-understanding-2026-10-13/review/deliverables/families/tests/c_node_quote_check.py
```

当前状态：pytest **85 passed**；C 节点对照 **97 项检查 0 失败**（引文/空文本/SHA）。
引文比对规则：PDF 按 `physical_page` 页文本、HTML 按去标签正文，**剔除全部空白后**相等即算可回放
（PDF 抽取在换行处插入空格，逐字节引文不可行）；原文引文均为原语言，不翻译。

## C 节点核实结论（应读/不读含义对照原文）

- 年/半/季：A股年报 MD&A 的业务/模式/计划小节、半年报产品阶段（送样验证 vs 重复订单）、
  季报富业务（单季口径）与稀疏季报（其他提醒事项“不适用”→合法 skip）均逐条对到原文页。
- 招股：A股发行概况/募集资金用途表（总投资 vs 拟投入两列）、港股目录（業務/行業概覽/未來計劃及所得款項用途）
  与门店表（截至呈報日期双截止日）对到原文页。
- 募资：定增项目分期/主体/地点、可转债两项目独立口径、效益测算免责声明，对到原文页。
- IR/call：问答绑定（问句前提 vs 回答数字）、标题误导正例（文件名像制度、正文是活动记录）、
  电话会四角色（参与人表/编辑 takeaways/管理层与IR声明/分析师问题）对到原文行。
- 经营表/图：门店存量vs净增、同店 GMV 脚注口径、演示材料 GMV≠收入，对到原文页。
- 行政：扫描确认函原生文本为空（合法空值，needs_source/OCR，不跳过不编造）。

## 官方资料核对（只读研究，非金标来源）

- SEC [8-K 目录实例](https://www.sec.gov/Archives/edgar/data/1717307/000171730726000010/0001717307-26-000010-index.htm)：
  主表 + EX-99.1 + EX-99.2 展示 + 图片附件，支持容器/附件建模（container_attachment 结构依据）。
- [Form F-1 表格](https://www.sec.gov/files/formf-1.pdf) 与真实 [S-1 正文](https://www.sec.gov/Archives/edgar/data/1500412/000119312526017240/d62272ds1.htm)：
  发行材料的 Business/Risk/Use of Proceeds 结构（prospectus_us 结构依据）。本轮未对这些公司事实建金标。
- HKEX 指南页此前打开超时，未据搜索摘要立结论；港股策略主要依据本地原件。

## 资源与卫生

- 0 付费模型调用、0 网络调用（构建期）；官方网页核对发生在母计划复审阶段，本轮只读本地原件。
- 原件只读：构建后复核 20 份样本 SHA 与 sample_manifest 全部一致（无改动）。
- 无持久 scratch；测试不写文件（合法空值用数据内显式标记表达）。整包持久数据以短引文为主，
  远低于 512KiB 上限；未删任何证据凑体积。
- `bindings.local.json` 为本机未提交绑定（sample_id→绝对路径，无密钥）；hk-release/hk-deck/us-release
  原件位于临时目录（易失），已在 handoff 标注。

## 交给 ROOT 的边界

1. records/ 导入唯一 profiles registry 后，deliverables 仅留版本化设计/证据；运行时不读两套规则。
2. child_routes、依赖闭包、预算、actual 选择与摘要都归 ROOT；本包只给策略数据与证据。
3. 语义反例（mutations）由 ROOT 映射到 du-gold/1 做行为测试；本包不写第二个 recall 检查器。
4. 数据包工程通过不代表生产已支持全部类型；未覆盖形态见 coverage_matrix 与 acquisition_requests。
