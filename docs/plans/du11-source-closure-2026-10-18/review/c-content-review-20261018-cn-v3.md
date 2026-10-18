# DU11 正式 C 内容复审（第三轮，CN，2026-10-18）

- 复审对象：CN 真实供应商 C run
  - 目录：.planning/shared-reading-production/du11/live-cn-h1-b2v3w-20261018
  - 模型：MiMo mimo-v2.6-flash；prompt reading-source-scoped/4.0.6；receipt PASS，1 POST，15,970 tokens / $0.002968
  - claims：22；evidence spans：96；claim 上限 40，target 36
- 审查方式：只读；打开 receipt/overall/rf-narrative、claims 引用的 evidence/context spans、gold 与 metadata；未改源码/测试/配置，未做 git 写操作，未调用供应商。
- 工程状态：receipt PASS、quality_status=needs_review、selection_status=partial；receipt PASS 不是内容通过。
- 本轮范围：只审 CN；US 不重审。

## 结论

**CN：CONTENT_FAIL**。

- required business facts 命中 **8/10**；critical 命中 **5/7**。
- 上一轮 5 个 P1 全部关闭：f-gan（t32-1）、f-inp（t37-1）、t2-1/t3-1/t4-1（本轮不再输出）。
- 仍缺两个 critical required facts：**f-five-year-target-is-plan**、**f-current-coverage-30**；两者对应 evidence 已选中，属于 summary 漏写，不是不可读。
- 新 claims 的引用/数字基本成立；没有发现错误数字、翻译、投资结论。问题是 required 覆盖仍差两条 + 若干 P2 模态/命名/重复问题。
- 因为没有达到 required 10/10、critical 7/7，不能判 CONTENT_PASS；补上两条 strategic claim 后才有 PASS_WITH_FIXES/PASS 空间。

## 1. 上一轮 P1 关闭表

| 上一轮 P1 | 状态 | 证据 |
|---|---|---|
| CN-P1-1 f-gan-power-stage | **CLOSED** | t32-1 逐字支持：2022 年推出 PRISMO PD5、已交付客户生产验证、取得重复订单；source page18/paragraph14。 |
| CN-P1-2 f-inp-development-started | **CLOSED** | t37-1 逐字支持：报告期内启动 InP 专用 MOCVD、实验室进展、下半年计划；source page18/paragraph29；modality planned。 |
| CN-P1-3 t2-1 该新产品未闭合 | **CLOSED by omission** | 本轮 22 claims 中没有“该新产品”；无裸指代。 |
| CN-P1-4 t3-1 截断/（原文截断） | **CLOSED by omission** | 本轮没有 t3-1 或“（原文截断）”。 |
| CN-P1-5 t4-1 从句中段开始 | **CLOSED by omission** | 本轮没有“到多个…”fragment。 |

## 2. Required facts 覆盖表（CN 10 required；critical 7）

| fact | importance | 状态 | claim | 说明 |
|---|---|---|---|---|
| f-five-year-target-is-plan | critical | **缺失** | 无 | selected page13/paragraph18 有未来五年 60%/70%；本轮无 claim |
| f-current-coverage-30 | critical | **缺失** | 无 | selected 同段有五十多种/超30%；本轮无 claim |
| f-cmp-acquisition-completed | critical | **命中** | t12-1 | 报告期内完成众硅公司控股权收购/CMP；t6-1 另有商誉侧 CMP |
| f-microled-sample-verification | critical | **命中** | t30-1 | Preciomo Udx/2023 年底/验证/重复订单 |
| f-gan-power-stage | critical | **命中** | t32-1 | PRISMO PD5 2022 推出/交付验证/重复订单 |
| f-sic-8inch-stage | critical | **命中** | t34-1 | 8 寸碳化硅外延/验证/重复订单 |
| f-inp-development-started | critical | **命中** | t37-1 | InP MOCVD 启动/实验室进展/下半年计划 |
| f-advanced-packaging-primo-matrix | normal | **命中** | t38-1 | Primo Matrix 即将发往国内头部客户产线验证 |
| f-tsv-300e-serving | normal | **命中** | t38-1 | Primo TSV 300E 持续服务/重复订单 |
| f-third-gen-tsv-rd | normal | **命中** | t38-1 | 第三代 TSV 刻蚀机研发/订单/即将验证 |

CN 8/10；critical 5/7。仅缺 f-five-year 与 f-current30，二者都是 critical 且 evidence 已选中。

## 3. Claim 逐条引用核对（22 claims）

| claim | 引用 locator | 判断 |
|---|---|---|
| t6-1 商誉/CMP | page177/paragraph9 | 支持；与 t12-1 同属 CMP 收购，t6 是商誉侧，t12 是交易侧；命名“中微众硅” vs t12“众硅公司”P2 |
| t8-1 SEMI 1659 亿美元/23.2% | page10/paragraph14/chars341-436 | 支持 |
| t12-1 收购众硅/CMP | page13/paragraph4/chars88-219 | 支持 |
| t14-1 研发投入 20.41 亿/36.86%/30.51% | page15/paragraph7/chars137-294 | 支持 |
| t17-1 CCP 产品/UD-RIE | page15/paragraph23/chars553-755 | 支持；source 为“单反台”，claim 写“单反应台”，P2 用词；源文本“高深刻比”照抄 P3 |
| t20-1 ICP 50 多客户 | page16/paragraph2/chars38-175 | 支持 |
| t21-1 LUX-Cryo/Angnova | page16/paragraph5/chars176-347 | 支持 |
| t27-1 ALD 氮化钛 | page17/paragraph5/chars108-242 | 支持 |
| t30-1 Micro-LED Preciomo Udx | page18/paragraph6/chars152-250 | 支持 |
| t32-1 GaN PRISMO PD5 | page18/paragraph14/chars409-530 | 支持；关闭 f-gan |
| t34-1 8 寸碳化硅 | page18/paragraph21/chars574-687 | 支持 |
| t37-1 InP MOCVD | page18/paragraph29/chars819-932 | 支持；planned 合理 |
| t38-1 TSV/Matrix/第三代 | page18/paragraph35/chars945-1115 | 支持；三个 required facts 一次覆盖 |
| t44-1 南昌基地 | page19/paragraph38/chars991-1032 | 支持 |
| t45-1 上海临港/二期/总部 | page19/paragraph39/chars1032-1160 | 支持；但 actual claim 含“拟于2026年下半年开工”，P2 模态 |
| t46-1 广州华南总部 | page19/paragraph44/chars1160-1231 | 支持；但 actual claim 含“计划2027年投产”，P2 模态 |
| t47-1 成都基地 | page20/paragraph2/chars38-107 | 支持；但 actual claim 含“预计2027年建成投产”，P2 模态 |
| t51-1 中段/超高深宽比/60:1 | page25/paragraph21/chars453-625 | 支持 |
| t53-1 PRISMO HiT3 1400度/18片/4英寸 | page26/paragraph39/chars1062-1181 | 支持；数字与原文一致 |
| t55-1 PRISMO PD5 4 腔/6-8 英寸 | page27/paragraph11/chars317-455 | 支持；数字与原文一致 |
| t62-1 投资/并购计划 | page32/paragraph37/chars892-1026 | 支持；planned 合理；不是投资建议 |
| t64-1 研发投入不足风险 | page33/paragraph16/chars433-523 | 支持；uncertain 合理 |

本轮没有“引用存在但不支持”的句子；P1 是 required 漏写，P2 集中在模态/命名/用词。

## 4. 未关闭 P1 / 新问题

### P1

- **CN-P1-1 缺 f-five-year-target-is-plan**：selected page13/paragraph18 有“未来五年…60%以上…70%以上”，22 claims 无未来五年/60/70 claim；不能把历史 30% 当未来目标。
- **CN-P1-2 缺 f-current-coverage-30**：同段有“五十多种设备产品…超30%前道集成电路设备产品”，22 claims 无当前覆盖 30% 的 claim；不能只写未来 60/70 而不写当前基线。

（其余上一轮 P1 已关闭；这两条是本轮 required 覆盖的剩余缺口。）

### P2

- **CN-P2-1 t6-1/t12-1 CMP 双 claim + 命名**：t6 是商誉侧“中微众硅”，t12 是交易侧“众硅公司”；两处均逐字支持，但同一标的两种名称、两条 CMP claim 容易让读者以为是两家公司/两笔交易。建议统一名称或加一句等价说明，必要时合并。
- **CN-P2-2 t45-1 modality**：claim 为 actual，但含“二期…拟于2026年下半年开工建设”未来计划；应拆 actual/planned。
- **CN-P2-3 t46-1 modality**：claim 为 actual，但含“计划2027年投产”，应标 planned/未来。
- **CN-P2-4 t47-1 modality**：claim 为 actual，但含“预计2027年建成投产”，应标 planned/未来。
- **CN-P2-5 t17-1 用词**：source “单反台Primo HD-RIE”，claim “单反应台Primo HD-RIE”；不是数量/主体错误，但属于改写，建议保留原文或说明。
- **CN-P2-6 t6-1 与 t12-1 重复主题**：两条都围绕 CMP 收购/商誉；不是同文重复，但内容重叠，可合并为“收购+商誉+能力”一条以减少重复。

### P3

- **CN-P3-1 t17-1 源文本 typo**：source “高深刻比”，claim 照抄；不是模型单位/数字错误，但建议在内容审查标记源文本 typo。
- **CN-P3-2 t53/t55 技术数字**：1400 度/18 片/4 英寸、4 腔/6-8 英寸均与原文一致，无需修改；保留为 P3 仅说明已核对。

## 5. 数字、单位、期间、语言、投资结论

- **数字/单位**：t8 1659 亿美元/23.2%；t14 20.41/5.50 亿元/36.86%/30.51%；t45 18 万/20 万/10 万平方米/2024-08/2026 下半年/2026-08-01；t46 130 亩/50 亩/2026-07/2027；t47 50 亩/2026-08/2027；t53 1400 度/18 片 2 英寸/4 英寸；t55 4 腔/6-8 英寸；t34 8 寸；均与原文一致，未发现换算/单位改写。
- **期间/模态**：t8 forecast、t12 actual、t30 actual、t32 actual、t34 actual、t37 planned、t38 actual、t62 planned、t64 uncertain 合理；t45/t46/t47 actual 含未来计划（P2）。
- **语言**：draft language=zh；产品名英文；summary.translate=false；未发现翻译或中英混排。
- **投资结论**：无评级/目标价/估值/买卖建议。t62 是中微公司自身的投资/并购计划与风险，不是对证券的投资建议；t64 是风险因素。

## 6. 实际打开的 span / 依据

- page13/paragraph18 — “目前公司的五十多种设备产品已经覆盖了超30%…未来五年…60%以上…70%以上…”（f-current30/f-five-year 缺失；evidence 已选中）。
- page18/paragraph14 — “于2022 年推出…PRISMO PD5…已交付客户进行生产验证，并取得重复订单…”（t32-1；f-gan）。
- page18/paragraph29 — “于报告期内启动磷化铟（InP）材料体系专用MOCVD 设备的开发…下半年将…”（t37-1；f-inp）。
- page13/paragraph4 — “报告期内完成对众硅公司控股权的收购…CMP…”（t12-1；f-cmp）。
- page18/paragraph6 — “2023 年底付运…Preciomo Udx…重复订单”（t30-1；f-microled）。
- page18/paragraph21 — “新型8 寸碳化硅外延设备…重复订单”（t34-1；f-sic）。
- page18/paragraph35 — “Primo TSV 300E…Primo Matrix…第三代TSV…”（t38-1；三个 normal required）。
- page15/paragraph23 — “单反台Primo HD-RIE…高深刻比…”（t17-1；P2/P3 用词）。
- page19/paragraph39 — 上海临港/二期/总部（t45-1；P2 模态）。
- page19/paragraph44 — 广州 130 亩/50 亩/2026-07/2027（t46-1；P2 模态）。
- page20/paragraph2 — 成都 50 亩/2026-08/2027（t47-1；P2 模态）。
- page26/paragraph39 — PRISMO HiT3 1400 度/18 片/4 英寸（t53-1）。
- page27/paragraph11 — PRISMO PD5 4 腔/6-8 英寸（t55-1）。
- gold：tools/document_understanding_benchmark/gold/cn-h1.json；required/critical ids 取 metadata-registered-source-facts-20261017.json。

## 7. 无法验证 / 边界

1. 未重新解析原始 PDF 全文；基于 selected evidence spans 与 gold；页面图像/表格结构未复核。
2. 未重新调用 MiMo；无法判断模型能否在相同 prompt 下补出 f-five-year/current30，或是否会再产出其他 claim。
3. 未审计 prompt 4.0.6/target 36 的实现；本轮 22 claims，低于 target 36。
4. 未审计“回退位置抽样、恢复全量任务”的具体 task 列表；required facts 的 evidence 已选中，但未进入 claims，属于 summary 选择问题。
5. 未独立重算原件/gold SHA；使用 receipt/metadata 值对齐。
6. 未审查工程恢复/缓存/FF-RF 消费；本轮只做内容。
7. US 本轮未跑，未重审。

## 8. 结论摘要

- **CN：CONTENT_FAIL**；required 8/10，critical 5/7。
- 上一轮 P1 全部关闭；本轮只剩两条 P1：缺 f-five-year-target-is-plan、f-current-coverage-30。
- 新 claims 引用/数字基本正确；P2 是 t6/t12 CMP 命名/重复、t45/t46/t47 模态、t17 用词；无投资结论/翻译/单位错误。
- 补上两条 strategic claim 并处理 P2 后，可再审 PASS_WITH_FIXES/PASS；当前未达到 CONTENT_PASS。

## 附录：审查输入

- CN：.planning/shared-reading-production/du11/live-cn-h1-b2v3w-20261018/{receipt.json,overall.json,rf-narrative.stdout.json}
- claims 22；evidence spans 96；prompt reading-source-scoped/4.0.6；model mimo-v2.6-flash。
- 本报告只读生成；未修改源码/测试/配置/gold，未执行 git 写操作，未调用供应商。
