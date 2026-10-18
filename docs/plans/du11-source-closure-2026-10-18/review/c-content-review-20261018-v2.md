# DU11 正式 C 内容复审（第二轮，CN / US，2026-10-18）

- 复审对象：第二轮真实供应商 C run
  - CN：live-cn-h1-b2v3p-20261018（MiMo mimo-v2.6-flash，prompt 4.0.3，13 claims）
  - US：live-us-10k-b2v3b-20261018（MiniMax MiniMax-M3，prompt 4.0.3，9 claims）
- 实际收据：.planning/shared-reading-production/du11/live-cn-h1-b2v3p-20261018 与 live-us-10k-b2v3b-20261018；head 说明为 a0e97809 + 未提交 view 收敛改动。
- 审查方式：只读；打开 receipt/overall/rf-narrative、claims 引用的 evidence/context spans、gold 与 metadata；未改源码/测试/配置，未做 git 写操作，未调用供应商。
- 工程 receipt：两次 PASS、1 POST、activation recovery PASS、cross-run zero POST；但 quality_status=needs_review、selection_status=partial，receipt PASS 不是内容通过。

## 结论

- **CN：CONTENT_FAIL**。required business facts 只命中 **2/10**（f-sic-8inch-stage、f-inp-development-started），critical **2/7**；上一轮 5 个 P1 中 4 个关闭，f-gan-power-stage 仍开放；更严重的是本轮 20-task 位置抽样把上一轮已命中的 f-five-year-target-is-plan、f-current-coverage-30、f-cmp-acquisition-completed、f-microled-sample-verification、f-advanced-packaging-primo-matrix、f-tsv-300e-serving、f-third-gen-tsv-rd 全部挤出 claims。新 claims 引用基本成立，但覆盖策略造成大面积回退。
- **US：CONTENT_FAIL**。required facts 命中 **4/8**，critical **4/8**；上一轮 f-azure-inside-intelligent-cloud、f-three-segments、f-segment-change-in-august-2024 已关闭，f-azure-is-consumption-based、f-rpo-scope-and-amount、f-rpo-recognition-is-forward 仍开放；另外本轮丢失了上一轮已命中的 f-m365-consumer-vs-commercial-metric（新回归）。
- 两次均无评级/目标价/估值/买卖建议；语言保持中文/英文；未发现数字、币种、单位错误。

## 1. 上一轮 P1 关闭表

### CN

| 上一轮 P1 | 状态 | 证据 |
|---|---|---|
| CN-P1-1 f-gan-power-stage | **OPEN** | 本轮 13 claims 中没有 PRISMO PD5/GaN 功率器件；t54-1 的 PRISMO UniMax 是 Mini-LED MOCVD，不是 PD5/GaN 功率器件。selected page18/paragraph14 与 page27/paragraph11 仍有 PRISMO PD5。 |
| CN-P1-2 f-inp-development-started | **CLOSED** | t37-1 逐字支持：报告期内启动 InP 专用 MOCVD、实验室进展、下半年计划；source page18/paragraph29。 |
| CN-P1-3 t2-1 该新产品未闭合 | **CLOSED by omission** | 本轮没有“该新产品”claim；无新的裸指代。相关 Micro-LED 推广事实未进入 summary（不是 required fact）。 |
| CN-P1-4 t3-1 截断/（原文截断） | **CLOSED by omission** | 本轮没有 t3-1/“（原文截断）”claim。 |
| CN-P1-5 t4-1 从句中段开始 | **CLOSED by omission** | 本轮没有“到多个…”fragment claim。 |

### US

| 上一轮 P1 | 状态 | 证据 |
|---|---|---|
| US-P1-1 f-azure-is-consumption-based | **OPEN** | 9 claims 无 consumption-based Azure；selected paragraph233 仍在。 |
| US-P1-2 f-azure-inside-intelligent-cloud | **CLOSED** | t28-1/t59-1 逐字支持 “Our Intelligent Cloud segment consists of our public, private, and hybrid server products and cloud services…”; t7-1 另有 Server/Azure。t28/t59 重复（P2）。 |
| US-P1-3 f-three-segments | **CLOSED** | t35-1 列出 Productivity and Business Processes、Intelligent Cloud、More Personal Computing；source paragraph731。 |
| US-P1-4 f-segment-change-in-august-2024 | **CLOSED** | t16-1 逐字支持 August 2024 segment changes / M365 commercial 并入 Productivity and Business Processes；source paragraph193。modality 标 planned 不准确（P2）。 |
| US-P1-5 f-rpo-scope-and-amount | **OPEN** | 9 claims 无 RPO 375B/368B/June 30 2025；selected paragraph3845 仍在。 |
| US-P1-6 f-rpo-recognition-is-forward | **OPEN** | 9 claims 无 approximately 40%/next 12 months；selected paragraph3845 仍在。 |
| US-P1-7（新回归）f-m365-consumer-vs-commercial-metric | **OPEN** | 上一轮 summary 有 M365 Commercial 14%/15%、Consumer 11%/11%；本轮 9 claims 完全删除；selected paragraph699/701 仍在。 |

## 2. Required facts 覆盖表

### CN（10 required；critical 7）

| fact | importance | 状态 | claim | 说明 |
|---|---|---|---|---|
| f-five-year-target-is-plan | critical | **缺失** | 无 | 上轮 t13-1 已命中；本轮无 60%/70%/未来五年 |
| f-current-coverage-30 | critical | **缺失** | 无 | 上轮 t13-1 已命中；本轮无 50 多/30% |
| f-cmp-acquisition-completed | critical | **缺失** | 无 | 上轮 t12-1 已命中；本轮无众硅/CMP acquisition |
| f-microled-sample-verification | critical | **缺失** | 无 | 上轮 t30-1 已命中；本轮无 Preciomo Udx/2023/重复订单 |
| f-gan-power-stage | critical | **缺失** | 无 | 上轮已缺；本轮仍无 PRISMO PD5/GaN 功率器件 |
| f-sic-8inch-stage | critical | **命中** | t34-1 | 8 寸碳化硅外延/验证/重复订单 |
| f-inp-development-started | critical | **命中** | t37-1 | InP MOCVD 启动/实验室进展/下半年计划 |
| f-advanced-packaging-primo-matrix | normal | **缺失** | 无 | 上轮 t38-1 已命中；本轮无 Primo Matrix |
| f-tsv-300e-serving | normal | **缺失** | 无 | 上轮 t38-1 已命中；本轮无 TSV 300E |
| f-third-gen-tsv-rd | normal | **缺失** | 无 | 上轮 t38-1 已命中；本轮无第三代 TSV |

CN 2/10；critical 2/7。上一轮 8/10 降为 2/10，是 20-task 位置抽样的覆盖回退，不是引用/数字错误。

### US（8 required；全部 critical）

| fact | 状态 | claim | 说明 |
|---|---|---|---|
| f-azure-is-consumption-based | **缺失** | 无 | selected paragraph233；无 claim |
| f-azure-inside-intelligent-cloud | 命中 | t28-1/t59-1 | 逐字支持 Intelligent Cloud segment；t28/t59 重复 |
| f-three-segments | 命中 | t35-1 | 三个 segment 全部列出 |
| f-segment-change-in-august-2024 | 命中 | t16-1 | August 2024/M365 commercial 并入 |
| f-m365-consumer-vs-commercial-metric | **缺失（回归）** | 无 | selected paragraph699/701；本轮无 M365 Consumer/Commercial |
| f-azure-growth-inside-combined-line | 命中 | t7-1 | Server 23%/Azure and other 34%，未误写 |
| f-rpo-scope-and-amount | **缺失** | 无 | selected paragraph3845；无 375B/368B/June 30 2025 |
| f-rpo-recognition-is-forward | **缺失** | 无 | selected paragraph3845；无 40%/next 12 months |

US 4/8；critical 4/8。

## 3. Claim 逐条引用核对

### CN（13 claims）

| claim | 引用 locator | 判断 |
|---|---|---|
| t1-1 ICP/PVD 项目投资 | page30/table0/row1-2 + header/unit | 1.35/0.59/1.16、1.71/0.01/1.00 与 row1/2 一致；但 6 个 span 均 table_structure_ambiguous，表格结构未证明；P2 |
| t8-1 SEMI 1659 亿美元/23.2% | page10/paragraph14/chars341-436 | 支持 |
| t14-1 研发投入 20.41 亿/36.86%/30.51% | page15/paragraph7/chars137-294 | 支持 |
| t18-1 Primo XD-RIE Alpha/Beta | page15/paragraph35/chars919-970 | 支持 |
| t21-1 LUX-Cryo/Angnova | page16/paragraph5/chars176-347 | 支持 |
| t24-1 Primo Domingo | page16/paragraph15/chars487-551 | 支持 |
| t34-1 8 寸碳化硅 | page18/paragraph21/chars574-687 | 支持 |
| t37-1 InP MOCVD | page18/paragraph29/chars819-932 | 支持；但 modality=actual 同时含“下半年将…”计划，P2 |
| t44-1 南昌基地 | page19/paragraph38/chars991-1032 | 支持 |
| t47-1 成都基地 50 亩/2026-08 封顶/2027 投产 | page20/paragraph2/chars38-107 | 支持；但 modality=actual 同时含“预计 2027 年”计划，P2 |
| t51-1 中段/超高深宽比量产/60:1 | page25/paragraph21/chars453-625 | 支持 |
| t54-1 PRISMO UniMax 4 腔/785mm/164/72 | page27/paragraph2/chars38-202 | 支持；数字与原文一致 |
| t64-1 研发投入不足风险 | page33/paragraph16/chars433-523 | 支持；uncertain 合理 |

本轮 CN 没有“引用存在但不支持”的句子；问题是 required facts 未进入 claims，以及 t1 表格/t37/t47 模态。

### US（9 claims）

| claim | 引用 locator | 判断 |
|---|---|---|
| t7-1 Server 23%/Azure 34% | paragraph707 | 逐字支持 |
| t13-1 search/news $1.6B/13%/20% | paragraph945 | 逐字支持 |
| t16-1 August 2024 segment change | paragraph193 | 逐字支持；modality=planned 不准确（announced 是 actual），P2 |
| t22-1 intelligent cloud/edge platform | paragraph165 | source 是 “Build the intelligent cloud…”，claim 加 “We build”；策略 bullet 被写成 company_statement，P2 |
| t25-1 Productivity and Business Processes segment | paragraph197 | 支持 |
| t28-1 Intelligent Cloud segment | paragraph224 | 逐字支持 |
| t35-1 three segments | paragraph731 | 支持（句式改写但语义一致） |
| t38-1 effective tax rate/Ireland | paragraph1063 | 逐字支持；非 required |
| t59-1 Intelligent Cloud segment | paragraph4433 | 与 t28-1 完全重复；P2 |

US 没有错误数字/单位；问题在 required 覆盖、重复 claim 与两处 modality/主语。

## 4. 新问题清单

### P1

**CN**

- **CN-P1-1 缺 f-five-year-target-is-plan**：上一轮 t13-1 命中未来五年 60%/70%；本轮 13 claims 没有任何未来五年/60%/70% 计划。
- **CN-P1-2 缺 f-current-coverage-30**：上一轮 t13-1 命中五十多种设备/超 30% 当前覆盖；本轮无。
- **CN-P1-3 缺 f-cmp-acquisition-completed**：上一轮 t12-1 命中报告期内完成众硅公司控股权收购/CMP；本轮无。
- **CN-P1-4 缺 f-microled-sample-verification**：上一轮 t30-1 命中 Preciomo Udx/2023 年底/重复订单；本轮无；t54 的 PRISMO UniMax 是 Mini-LED MOCVD，不是该 facts 的样机验证。
- **CN-P1-5 缺 f-gan-power-stage**：上一轮已缺；本轮仍没有 PRISMO PD5 2022 推出/交付验证/重复订单。
- **CN-P1-6 20-task 位置抽样造成覆盖回退**：本轮 13 claims 中只有 t34/t37 对应 required；其余 11 条都是非 required 的表格、SEMI、研发投入、产品技术、基地、风险；required 从 8/10 降至 2/10。这是本轮 view 收敛的直接内容后果，不能算“内容通过”。

**US**

- **US-P1-1 缺 f-azure-is-consumption-based**：selected paragraph233 有 consumption-based Azure；9 claims 无。
- **US-P1-2 缺 f-m365-consumer-vs-commercial-metric（新回归）**：上一轮有 Commercial 14%/15%、Consumer 11%/11%；本轮 9 claims 无；selected paragraph699/701 仍在。
- **US-P1-3 缺 f-rpo-scope-and-amount**：selected paragraph3845 有 375B/368B/June 30 2025；9 claims 无。
- **US-P1-4 缺 f-rpo-recognition-is-forward**：同段有 approximately 40%/next 12 months；9 claims 无。

### P2

- **CN-P2-1 t1-1 表格结构**：6 个 span 全带 table_structure_ambiguous；数值与 row1/2 对齐，但列映射依赖 header，仍应 needs_review。
- **CN-P2-2 t37-1 modality**：claim 为 actual，但含“下半年将…尽早付运”计划；应拆 actual + plan 或标 planned。
- **CN-P2-3 t47-1 modality**：claim 为 actual，但含“预计 2027 年建成投产”；应标 planned/未来。
- **CN-P2-4 缺 normal required facts**：f-advanced-packaging-primo-matrix、f-tsv-300e-serving、f-third-gen-tsv-rd 是 required normal；本轮未覆盖，内容覆盖不完整（P2，不影响 critical 判定，但 required 只剩 2/10）。
- **US-P2-1 t28-1/t59-1 重复**：两条 claim 文本相同（Intelligent Cloud segment），来自不同 section；重复消耗 claims 配额，且 t59 是 Note 8/Item 8 重复。
- **US-P2-2 t16-1 modality**：announced/August 2024 是 actual；claim 标 planned。
- **US-P2-3 t22-1 主语/模态**：source 是 “Build the intelligent cloud…”，claim 改写成 “We build…”；策略 bullet 被当作 company_statement，且 modality=planned 与句式不一致。

### P3

- 无新的投资结论/评级/目标价/估值。
- 无翻译混排；CN 中文、US 英文。
- 数字/单位未发现错误。
- **CN t1-1** row3-6 作为 evidence 附带但 claim 只用 row1/2；不影响事实，但 evidence 冗余。
- **US t38-1** tax rate/Ireland 不是 required fact，属于非关键补充；内容本身逐字支持。

## 5. 数字、单位、期间、语言与投资结论

- **CN 数字**：t1 1.35/0.59/1.16、1.71/0.01/1.00 亿元；t8 1659 亿美元/23.2%；t14 20.41/5.50 亿元/36.86%/30.51%；t47 50 亩/2026 年 8 月/2027；t54 4 腔/785mm/164 片 4 英寸/72 片 6 英寸；t34 8 寸；均与原文一致。
- **US 数字**：23%/34%、$1.6B/13%/20%；均与原文一致；未把 Azure 34% 写成 23%。
- **期间/模态**：CN t8 forecast、t64 uncertain 合理；t37/t47 actual 含未来计划（P2）。US t16 planned 错误、t22 planned/句子来源需注意（P2）。
- **语言**：CN draft language=zh；US=en；summary.translate=false；未发现翻译或中英混排（产品名除外）。
- **投资结论**：CN/US 均无评级/目标价/估值/买卖建议。

## 6. 实际打开的 span / 依据

CN 关键：
- page18/paragraph14 — “于2022 年推出…MOCVD 设备PRISMO PD5…已交付客户进行生产验证，并取得重复订单。”（仍缺 f-gan）
- page18/paragraph29 — “于报告期内启动磷化铟（InP）材料体系专用MOCVD 设备的开发…下半年将…”（t37-1 关闭 f-inp）
- page13/paragraph18 — “目前公司的五十多种设备产品已经覆盖了超30%…未来五年…覆盖60%以上…70%以上…”（f-current30/f-five-year 缺失；evidence 已选中）
- page13/paragraph4 — “完成对众硅公司控股权的收购…CMP…”（f-cmp 缺失；evidence 已选中）
- page18/paragraph6 — “2023 年底付运…Preciomo Udx…重复订单”（f-microled 缺失）
- page18/paragraph35 — “Primo TSV 300E…Primo Matrix…第三代TSV…”（f-primo/tsv/thirdgen 缺失）
- page30/table0/row1-2 — 项目投资数值（t1-1）
- page16/paragraph15 — Primo Domingo（t24-1）
- page20/paragraph2 — 成都基地 50 亩/2026-08/2027（t47-1）
- page27/paragraph2 — PRISMO UniMax 4 腔/785mm/164/72（t54-1）

US 关键：
- paragraph233 — Azure consumption-based（f-azure-consumption 缺）
- paragraph699/701 — M365 Commercial 14/15、Consumer 11/11（f-m365 缺，本轮回归）
- paragraph3845 — RPO 375B/368B/June 30 2025、~40%/next 12 months（两项缺）
- paragraph193 — August 2024 segment change（t16-1）
- paragraph224/4433 — Intelligent Cloud segment（t28-1/t59-1，重复）
- paragraph731 — three segments（t35-1）
- paragraph707 — Server 23%/Azure 34%（t7-1）
- paragraph945/1063 — search/news 与 tax（t13-1/t38-1）

Gold：tools/document_understanding_benchmark/gold/cn-h1.json、us-10k.json；required/critical ids 取 metadata-registered-source-facts-20261017.json。

## 7. 无法验证 / 边界

1. 未重新解析原始 PDF/HTML 全文；基于 selected evidence spans 与 gold；CN 表格结构、页面边界未用版面图像复核。
2. 未重新调用 MiMo/MiniMax；无法判断更多 claims 是否可用；只审已成稿 summary。
3. 未审计 20-task 位置抽样的实现细节；从 claims 与 evidence 可确认 required fact 的 evidence 已被选中，但未进入 claims；抽样策略是内容回退的直接原因。
4. 未审计 prompt 4.0.3/18 claims 目标；US 9/CN 13 均低于目标，原因未验证。
5. 未独立重算原件/gold SHA；使用 receipt/metadata 值对齐。
6. 未审查工程恢复/缓存/FF-RF 消费；本轮只做内容。
7. 请求的 docs/plans/live-* 路径不存在；使用 .planning 实际收据；若另有同名副本未覆盖。

## 8. 结论摘要

- **CN：CONTENT_FAIL**。required 2/10，critical 2/7；只有 f-sic/f-inp 命中；上轮 P1 中 f-gan 仍开，InP/t2/t3/t4 关闭；但 20-task 位置抽样让 f-five-year/current30/cmp/microled/primo/tsv/thirdgen 全部消失，形成新的 P1 覆盖回退。新 claims 引用/数字基本正确，t1 表格与 t37/t47 模态是 P2。
- **US：CONTENT_FAIL**。required 4/8，critical 4/8；azure inside/three segments/segment change 已关闭；azure consumption、RPO scope、RPO recognition 仍开；另丢失上一轮已命中的 M365 Consumer/Commercial，形成新 P1 回归；t28/t59 重复、t16/t22 模态是 P2。
- 两次都没有投资结论；语言/数字未发现错误。均未达到 CONTENT_PASS。

## 附录：审查输入

- CN：.planning/shared-reading-production/du11/live-cn-h1-b2v3p-20261018/{receipt.json,overall.json,rf-narrative.stdout.json}
- US：.planning/shared-reading-production/du11/live-us-10k-b2v3b-20261018/{receipt.json,overall.json,rf-narrative.stdout.json}
- CN 13 claims / US 9 claims；evidence spans 96/96；prompt reading-source-scoped/4.0.3。
- 本报告只读生成；未修改源码/测试/配置/gold，未执行 git 写操作，未调用供应商。
