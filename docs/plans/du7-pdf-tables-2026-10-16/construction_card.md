# DU7-PDF-TABLE：PDF已观察细格到统一TABLE观察的适配

## 0. 位置、现状与目标

工作目录：`C:/Users/郑曾波/Projects/company-wiki-du7-pdf-tables`。
自有计划：`docs/plans/du7-pdf-tables-2026-10-16/task_plan.md`。
分支：`codex/du7-pdf-tables-20261016`；真实base/seed见launch.json。

用户已同意“一个共享引擎＋多份文档阅读策略”。现有PDF parser及DU3几何捕获已经产出精确cells/words/char refs，DU4 TABLE已经有 `bind_operating_table` 和 `du4-table-observation/1`。ROOT刚完成HTML原生槽位适配；PDF仍没有同责任的生产观察适配，不能复制测试投影或重新解析整份PDF解决。

只读调查事实：`PdfLayoutCollector.capture_table`保留有值且有bbox的cell；空格及合并跨度信息已在上游丢失。FineViews保留原生列但span可能None。`tests/unit/du4_table_measurements/real_packet.py`的固定前四行header与派生parent只是测试样本适配，不是生产依据。**本卡只正确使用已观察信息，不承诺从已丢资料恢复完整原表。**

最终产物是一个纯适配组件＋扎实测试/可复现小样本，可由ROOT直接接原binder。当前即可独立实施，不等待DU6或ROOT的后续v4接线。

## 1. 排他写入范围

- 新 `src/company_wiki/document_normalization/pdf_table_observations/`。
- 新 `tests/unit/pdf_table_observations/`，自己的fixture只在该目录。
- 自有PWF及其 `e2e/`、`receipts/`。

现有parser、layout_snapshots、layout_hints、structure、observation_adapter、native_table_bridge、table_measurements、pipeline、source_catalog、现有tests/gold/配置/CI全部只读。不要改HTML桥、不要另造binder或PDF提取引擎。需要源新增字段则给出反例和ROOT接线建议，组件对缺失信息保守降级。

## 2. 冻结接口与语义

```python
def build_pdf_table_observations(
    observation: Mapping, layout_hints: Mapping | None, *, work_budget: WorkBudget
) -> dict:
    # {"status": "complete|partial|unavailable", "tables": [...],
    #  "diagnostics": [...], "work_used": <本调用增量>}
```

输入为现有`du-input/1`及已有`du2-layout-hints/1`，非路径/文件bytes。复用已有unit ID、parent source_id、page/table/row/column、fine cells/words及精确scalar offsets。先按真实对象定位阅读对应源文件和schema，不猜字段名；A节点写字段对照表。

`tables`每项**严格**是现有`du4-table-observation/1`：scope(parent_id/table_id/page)、units、cells、header_rows、provenance、truncated等按现contract，不发明第二schema。cells的text_refs和header_refs必须回切原text完全相等；不可依局部value字符串全局查找碰巧相等位置。

- row/column来自真实native slot，不能按页上文字顺序/右对齐/年份大小推列。
- row_span/column_span缺失保持None/unknown；不默认1、不拆多值merged格猜列。
- 只有实际观察为空的格能标empty；上游没保留的空位是unavailable/未观察，不能造原文或虚构空单元。不要为补完整矩形而创造TextRef。
- header依已观察原生关系或已有共享header_for/caption/row label关系；不硬编码HEADER_ROWS，不把第0行/最新年一概当标题。
- table_id可复用页面原生身份，但必须带真实parent/page作用域，跨source同页/同编号绝不合并。单位/币种/期间只搬原文refs，具体解释交原binder；不做FX或billion/亿换算。
- words/cells坐标只有frame已知、char_alignment exact才可作为值定位依据；粗bbox不够时unknown，不借OCR/猜测。
- 同一实例work_budget贯穿准备；零/已用尽在遍历前停止，部分耗尽保留已闭合table，不返回半个完整table、不续预算；不额外创建余额。明确逻辑预算，不夸称regex墙钟硬界。

## 3. A：调查与独立期望/RED

读共享主PWF `review/du4_production_integration.md` §4、DU4 TABLE `INTERFACES.md`、现bindings/contract、DU3 layout_snapshots/fine提取和ROOT observation_adapter。旧卡已完成，不重做其引擎。先保存当前原unit/EvidenceSpan/locator/provenance与binder输入输出样本。

列出从真实已有fine载体到contract的字段映射，并写手工期望：双期同数值、行标签/单位/范围分别引用哪一原片段；缺失时应unknown。新增组件不存在不算全部RED，至少用现行公开适配/retained样本展示目前PDF生产观察缺口或错误header假设，和非fixture常量方案比较。

## 4. B：组件实现与测试包

先写行为测试，再实现。至少覆盖：

1. 单次index/原材料只准备一次，多表/多页及同编号不同parent。
2. 同数不同年/列、数值为负/破折号/字符串、万元/亿元/币种/复合单位，不变更原词。
3. 稀疏列、空位丢失、缺bbox、span None、未知frame、不可用header、边界错offset及外parent refs。
4. 多原unit承接同cell时仅搬真实refs，不伪造连续原文；歧义由原binder保持ambiguous。
5. 0预算/已有used/中途耗尽、异常清理/原输入不变；下游原binder真实调用同budget。
6. 使用不同合法table_id、表头顺序和业务名，不加公司/页码/样本金标特判。

原TABLE、原layout snapshots/adapter相关旧测试在B集中跑一次；只运行实际存在的路径，不改旧gold迎合组件。独立手算/回切核验报告放receipts，结构合法不等于真实经营/期间解释一定正确。

## 5. C：真实细格与端到端

提供自有 `e2e/run_e2e.py`，可显式接收只读原件bindings与工作目录，按相同原parser单次parse→现adapter/layout→本组件→原binder执行，不fake生产结果。原parser的工作无需本组件重复做。组件部署后ROOT再接正式selection/summary，作者不能把组件C算正式摘要验收。

开发回归可用名创双语年报p12与恒锋增发p61/62；换公司/格式的金禾可转债p223/224作真实holdout，路径从主PWF sample_manifest和可用本机bindings只读取得，不提交绝对机器路径或原件。若不能在工区定位已存在原件，先查当前目录清单/manifest；仍不可得写NOT_RUN并交ROOT，不伪造真实C通过。HK retained gzip只作开发，不作未见holdout。

真实每个值逐一回切原文（source ID/page/table/offset/hash），定位不足的例子必须演示unknown；不要求为了高bound率补猜。保存parse次数、实际work、耗时、可绑定/歧义/不可用及原因，不将未读部分从分母隐藏。截图/大fine arrays只临时，结束恢复测试目录，不复制整PDF或完整中间MD。

按共同handoff接口交付，列出ROOT需要的一处生产组合调用/依赖闭包接线、真实未覆盖项。正常commit、冻结源码后STOP。
