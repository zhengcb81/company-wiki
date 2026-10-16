# DU7-PDF-TABLE：ROOT 独立验收与隔离修复

日期：2026-10-16。作者交付 HEAD `caca0eb61e657bead05609ec963e00c48502761f`。
本记录优先解释该交付的验收状态；原作者 handoff 不覆盖 ROOT 后续发现。

## 当前结论

作者31项与旧相关回归在独审时547PASS/24SKIP，仍被新增6项独立反例全部击中。ROOT随后在专用集成树修复共同根因：数值碎片不能冒充完整值；最左格不能无依据变成行标签；准备工作必须先付共享预算；细格page/parent/table矛盾不能归到owner；丢弃格必须partial；header关系必须按真正目标作用域生效。

修复后 **43项组件/独立控例全部PASS（5.91秒）**，Ruff通过，Git whitespace检查通过。**旧相关大回归修后复跑由ROOT统一排队，不能把修前547PASS写成修后结果。** 生产选择、正式摘要、缓存和RF端到端仍由主PWF验收。

## A：保留真实旧行为与首次RED

- 原作者源码/新增测试仍在不可变作者HEAD；ROOT留存原31测试字节zip、最初6FAIL XML/日志和独立探针JSON。
- 作者测试修改前，在新实现下 ROOT10项全部PASS，原31有11处失败。失败原因：原测试把最左文本强制当标签，假定邻格单位/海外范围必然属于另格数值，并假定full_work-1一定落在第二表而不是最后诊断扫描。这些是未被input观察到的事实。
- 经ROOT授权，仅纠正本次作者新增测试6文件的错误假设；原binder/layout金标和旧测试一字未改。并增加全部预算切点的闭合前缀检查、纯数字首列、文本首列、partial与无partial标记多carrier、scope矛盾、无关共享分组控例。

## B：实现责任与真实新语义

- 仍唯一 `build_pdf_table_observations(observation, layout_hints, *, work_budget)`，输出原DU4观察，复用原binder，没有解析新PDF、货币换算或新数字引擎。
- 同一个WorkBudget实例，收费包括scope/unit/relation/member索引、排序预付、一次row索引、引用复制和最终诊断扫描。没有O(rows×all-cells)循环，也不提升2M上限。
- partial_cell或多原carrier同一槽无法证明完整值时，保留真实text_refs并使用已有`presence=unavailable`，原binder返回unavailable；不拼1234，也不将12/34各自标bound。
- 当前DU2没有真实row-label角色关系；**不猜任何最左文本/数字为标签**。缺角色时保留原格/原值，报告ROW_LABEL_UNAVAILABLE/partial，不能从邻格借单位/地理范围。这是保守能力边界，不是新增许可。
- 只用实际相容 `(parent, table_id, page)` 的header_for。当前PDF table_header kind由旧row0强制产生，不独立证明实际表头；缺关系时HEADER_ROLE_UNCONFIRMED/partial。无关普通layout分组直接忽略，不伪报跨表。
- 显式fine.page/source_id/table/row与owner矛盾拒绝，缺格保留truncated/partial。未知span继续None。

## C：真实原件与清理

真实名创2024双语年报p12（源SHA `07f4937e0558fc31189a56236313ad93c1cef4182adb10ebaf4f355acb9bf1cf`），正常主机隔离Temp、网络全封：原parser单次→现adapter/layout→新组件→原binder。最终2表28格、16measurements（12bound/4ambiguous），全部回切原文一致。

共享预算2,000,000，最终总用 **1,162,753**，组件 **10,098**。真实数据保持原有绑定/歧义数量，不把结构complete等同业务解释全部正确。原件SHA、作者树/集成树源码与配置SHA+mtime不变；临时目录删除，预存sentinel未变。0供应商调用、0生产写入。

另保留真实E2E中发现并修正的ROOT草案误诊：最初把文档中的非native-table共享header关系也当跨表，导致283条噪音；增加精确控例后只诊断真正相互矛盾的已观察table作用域，最终该真实样本0此类误诊。

## 复现

从本集成树设置PYTHONPATH为本树src，然后：

```powershell
python -B -X utf8 -m pytest -q -p no:cacheprovider tests/unit/pdf_table_observations_root tests/unit/pdf_table_observations
python -B -X utf8 -m ruff check --no-cache src/company_wiki/document_normalization/pdf_table_observations tests/unit/pdf_table_observations tests/unit/pdf_table_observations_root
```

真实E2E沿用卡的显式原件/manifest入口，`--sample hk-annual --pages 12 --work-budget 2000000`，所有派生放独立Temp；运行前后核原件与配置SHA，临时材料结束清理。ROOT独审收据在主仓 `.planning/shared-reading-production/du67-reception/pdf-review/`，母PWF归档时保留原RED与最终GREEN，不覆盖旧失败。

## OPEN

- 金禾可转债p223/224：仍受上游64页fine捕获硬上限限制，深页绑定质量 **NOT_RUN/OPEN**，p25/26不得冒充已验深页。
- 缺真实row-label/原生header角色、空位和merged span，不在适配层猜；上游增强和生产组合由ROOT负责。
- 本包只验组件，不把它当正式摘要的业务准确性验收。未Git提交、未自行并线。
