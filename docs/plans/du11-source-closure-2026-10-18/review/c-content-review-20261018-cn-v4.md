# DU11 正式 C 内容复审（第四轮，CN，2026-10-18）

- 复审对象：CN 真实供应商 C run
  - 目录：.planning/shared-reading-production/du11/live-cn-h1-b2v4e-20261018
  - 模型：MiMo mimo-v2.6-flash；prompt reading-source-scoped/4.0.8；receipt PASS，1 POST，15,071 tokens / $0.002665
  - claims：14；evidence spans：96；selection partial；quality needs_review
- 审查方式：只读；打开 receipt/overall/rf-narrative、claims 引用的 evidence/context spans、gold 与 metadata；未改源码/测试/配置，未做 git 写操作，未调用供应商。
- 本轮范围：只审 CN；US 不重审。

## 结论

**CN：CONTENT_FAIL**。

- required business facts 命中 **6/10**；critical 命中 **4/7**（f-gan 为 partial，若把 partial 计入 critical 则为 5/7，但仍缺 f-sic/f-inp）。
- 上一轮两条 P1（f-five-year、f-current30）已关闭：t13-2 命中未来五年 60%/70%，t13-1 命中五十多种/超30% 当前覆盖。
- 但本轮反转出新的 P1：**f-inp-development-started 缺失**、**f-sic-8inch-stage 缺失**、**f-gan-power-stage 仅 partial**，以及 **t45-1 文本损坏（公司在上\nte海临港）**。
- f-primo-matrix 仍是 required normal 缺失（P2）；f-tsv300e、f-third-gen-tsv 均已命中。
- 未发现错误数字/单位/翻译/投资结论；新 claims 的引用除 t45 文本损坏外基本支持。

## 1. 上一轮 P1 关闭表

| 上一轮 P1 | 状态 | 证据 |
|---|---|---|
| CN-P1-1 f-five-year-target-is-plan | **CLOSED** | t13-2 planned：未来五年 60%/70%；source page13/paragraph18。 |
| CN-P1-2 f-current-coverage-30 | **CLOSED** | t13-1 actual：五十多种设备/超30% 当前覆盖；source 同段。 |
| CN-P1-3 f-inp-development-started（上轮已 CLOSED） | **REGRESSED/OPEN** | 本轮 14 claims 没有任何 InP 专用 MOCVD claim；selected page18/paragraph29 仍在。 |
| CN-P1-4 f-sic-8inch-stage（上轮命中） | **REGRESSED/OPEN** | 本轮没有 8 寸碳化硅外延设备 claim；selected page18/paragraph21 仍在。 |
| CN-P1-5 f-gan-power-stage（上轮 t32 命中） | **PARTIAL/OPEN** | t55-1 只引用 page27/paragraph11 的技术段（PRISMO PD5 验证/重复订单），没有 page18/paragraph14 的“2022 年推出/交付客户生产验证”；缺 2022 年推出与 launch 事实。 |

## 2. Required facts 覆盖表（10 required；critical 7）

| fact | importance | 状态 | claim | 说明 |
|---|---|---|---|---|
| f-five-year-target-is-plan | critical | **命中** | t13-2 | 未来五年 60%/70%；planned |
| f-current-coverage-30 | critical | **命中** | t13-1 | 五十多种/超30%；actual |
| f-cmp-acquisition-completed | critical | **命中** | t12-1 | 众硅公司控股权/CMP |
| f-microled-sample-verification | critical | **命中** | t30-1 | Preciomo Udx/2023 年底/重复订单 |
| f-gan-power-stage | critical | **PARTIAL/错误** | t55-1 | PRISMO PD5/验证/重复订单有；缺 2022 年推出；且 t55 “验证通过”与 gold must_not_assert “PRISMO PD5 已完成生产验证”冲突 |
| f-sic-8inch-stage | critical | **缺失** | 无 | selected page18/paragraph21 有 8 寸碳化硅/验证/重复订单；14 claims 无 |
| f-inp-development-started | critical | **缺失** | 无 | selected page18/paragraph29 有 InP 开发/实验室进展/下半年计划；14 claims 无 |
| f-advanced-packaging-primo-matrix | normal | **缺失** | 无 | selected page18/paragraph35 有 Primo Matrix 即将发往；t38-1 只取 TSV 300E，未取 Matrix |
| f-tsv-300e-serving | normal | **命中** | t38-1 | TSV 300E 持续服务/重复订单 |
| f-third-gen-tsv-rd | normal | **命中** | t38-2 | 第三代 TSV 研发/订单/即将验证 |

严格 full 命中 6/10；critical full 4/7；f-gan partial（若把 partial 算入 critical 则 5/7）。f-primo matrix 是 required normal 缺失（P2）；f-sic/f-inp 是 critical 缺失（P1）。

## 3. Claim 逐条引用核对（14 claims）

| claim | 引用 locator | 判断 |
|---|---|---|
| t8-1 SEMI 1659 亿美元/23.2% | page10/paragraph14/chars341-436 | 支持；forecast |
| t12-1 收购众硅/CMP | page13/paragraph4/chars88-219 | 支持 |
| t13-1 当前 50 多/超30% | page13/paragraph18/chars495-605 | 支持；actual |
| t13-2 未来五年 60%/70% | 同段 | 支持；planned |
| t14-1 研发投入 20.41 亿/36.86%/30.51% | page15/paragraph7/chars137-294 | 支持 |
| t30-1 Micro-LED Preciomo Udx | page18/paragraph6/chars152-250 | 支持 |
| t38-1 TSV 300E | page18/paragraph35/chars945-1115 | 支持；只取 TSV 300E，未取 Primo Matrix |
| t38-2 第三代 TSV | 同段 | 支持；planned 合理 |
| t45-1 上海临港/二期/总部 | page19/paragraph39/chars1032-1160 | **文本损坏**：claim 为“公司在上\nte海临港”，source 为“公司在上\n海临港”；多出“te”；P1；actual 还含“拟于2026下半年开工”，P2 |
| t46-1 广州华南总部 | page19/paragraph44/chars1160-1231 | 支持；modality planned，但 claim 同时含“已于2026年7月封顶” actual；P2 |
| t51-1 中段/超高深宽比量产 | page25/paragraph21/chars453-625 | 支持 |
| t51-2 CCP 60:1/下一代 | 同段 | 支持 |
| t55-1 PRISMO PD5 技术段 | page27/paragraph11/chars317-455 | 支持技术描述；缺 2022 推出/交付验证；且“验证通过”与 gold must_not_assert “已完成生产验证”冲突；partial/错误 |
| t64-1 研发投入不足风险 | page33/paragraph16/chars433-523 | 支持；uncertain |

除 t45 文本损坏外，没有“引用存在但不支持”的句子；t45 是生成文本损坏，不是源文本错误。

## 4. 未关闭 P1 / 新问题

### P1

- **CN-P1-1 缺 f-inp-development-started**：selected page18/paragraph29 有“报告期内启动磷化铟（InP）材料体系专用 MOCVD 设备的开发…下半年将…尽早付运样机”，14 claims 无 InP claim；上一轮 t37 已命中，本轮回归。
- **CN-P1-2 缺 f-sic-8inch-stage**：selected page18/paragraph21 有“新型8 寸碳化硅外延设备…生产验证…重复订单”，14 claims 无；上一轮 t34 已命中，本轮回归。
- **CN-P1-3 f-gan-power-stage 仅 partial/含 must_not 冲突**：t55-1 只覆盖 page27 技术段的 PRISMO PD5 验证/重复订单，缺 page18/paragraph14 的“2022 年推出/交付客户生产验证”；且 t55 的“已在客户生产线上验证通过”等于“已完成生产验证”，与 gold 的 must_not_assert “PRISMO PD5 已完成生产验证”明确冲突；严格 required fact 仍未完整。
- **CN-P1-4 t45-1 文本损坏**：claim 为“公司在上\nte海临港”，source 为“公司在上\n海临港”；多出“te”，是用户可见的损坏文本；P1。

### P2

- **CN-P2-1 缺 f-advanced-packaging-primo-matrix**：t38-1 只取 TSV 300E；primo Matrix 在 selected page18/paragraph35 中但未进入 claims；required normal 缺失。
- **CN-P2-2 t45-1 modality**：claim 为 actual，但含“临港二期…拟于2026年下半年开工建设”；应拆 actual/planned（与文本损坏分开）。
- **CN-P2-3 t46-1 modality**：claim 为 planned，但含“主体结构已于2026年7月封顶” actual；模态混合。
- **CN-P2-4 t38-1/t38-2 覆盖**：t38-1 只取 TSV 300E，t38-2 只取第三代 TSV；Primo Matrix 缺失（同上）；三条 advanced packaging required 未在同一 summary 完整覆盖。
- **CN-P2-5 t55-1 作为 f-gan 证据**：技术段可支持产品/验证/重复订单，但不能替代 2022 年推出/交付验证；若保留，应补 t32-equivalent claim，而不是把它当完整 f-gan。

### P3

- 无新的投资结论/评级/目标价/估值。
- 无翻译混排；CN 中文、产品名英文。
- 数字/单位未发现错误：1659 亿美元/23.2%；20.41/5.50 亿元/36.86%/30.51%；18/20/10 万平方米；130/50 亩；1400 度/18 片/4 英寸；4 腔/6-8 英寸等均与原文一致（t45 仅文本损坏，数字未错）。
- t45 的“te”是生成文本损坏，不是数字/单位问题；已列 P1。

## 5. 数字、单位、期间、语言、投资结论

- **数字/单位**：t8 1659 亿美元/23.2%；t13 50 多/30%/60%/70%；t14 20.41/5.50 亿元/36.86%/30.51%；t45 18/20/10 万平方米、2024-08/2026H2/2026-08-01；t46 130/50 亩、2026-07/2027；t55 4 腔/6-8 英寸；均与原文一致（t45 文本损坏除外）。
- **期间/模态**：t8 forecast、t12 actual、t13-1 actual、t13-2 planned、t30 actual、t38-1 actual、t38-2 planned、t64 uncertain 合理；t45 actual 含未来开工计划（P2）、t46 planned 含已封顶 actual（P2）。
- **语言**：zh；产品名英文；translate=false；除 t45 损坏外无翻译/混排。
- **投资结论**：无评级/目标价/估值/买卖建议；无投资建议。

## 6. 实际打开的 span / 依据

- page13/paragraph18 — “目前公司的五十多种设备产品已经覆盖了超30%…未来五年…60%以上…70%以上…”（t13-1/t13-2）。
- page13/paragraph4 — 众硅公司控股权/CMP（t12-1）。
- page18/paragraph6 — Preciomo Udx/2023/重复订单（t30-1）。
- page18/paragraph14 — “于2022 年推出…PRISMO PD5…已交付客户进行生产验证，并取得重复订单…”（f-gan 的完整原文；t55 未覆盖 2022/交付验证）。
- page18/paragraph21 — 8 寸碳化硅/生产验证/重复订单（f-sic 缺失）。
- page18/paragraph29 — InP 专用 MOCVD 开发/实验室进展/下半年计划（f-inp 缺失）。
- page18/paragraph35 — TSV 300E/Primo Matrix/第三代 TSV（t38-1 只取 TSV 300E；t38-2 取第三代；Matrix 缺失）。
- page19/paragraph39 — 上海临港/二期/总部（t45-1；文本损坏“te海临港”）。
- page19/paragraph44 — 广州华南总部 130/50 亩/2026-07/2027（t46-1）。
- page25/paragraph21 — 中段/超高深宽比/60:1（t51-1/t51-2）。
- page27/paragraph11 — PRISMO PD5 4 腔/6-8 英寸（t55-1）。
- page10/paragraph14 — SEMI（t8-1）；page15/paragraph7 — 研发投入（t14-1）；page33/paragraph16 — 风险（t64-1）。

## 7. 无法验证 / 边界

1. 未重新解析原始 PDF 全文；基于 selected evidence spans 与 gold；页面图像/表格结构未复核。
2. 未重新调用 MiMo；无法判断模型能否在相同 prompt 下补出 InP/SIC/完整 GAN/Primo Matrix，或 t45 是否偶发损坏。
3. 未审计 prompt 4.0.8 的实现；本轮 14 claims，少于上一轮 22。
4. 未审计“必须包含覆盖率/市场份额与多年目标”的 prompt 逻辑是否挤掉了产品/客户/产能事实；从 claims 看，五年/30% 被加入，但 InP/SIC/GAN 2022/Primo Matrix 被挤掉。
5. 未独立重算原件/gold SHA；使用 receipt/metadata 值对齐。
6. 未审查工程恢复/缓存/FF-RF 消费；本轮只做内容。
7. US 本轮未跑，未重审。

## 8. 结论摘要

- **CN：CONTENT_FAIL**；required full 6/10，critical full 4/7（f-gan partial 可算 5/7）。
- 上一轮 f-five-year/f-current30 已关闭；f-inp/f-sic 回归缺失，f-gan partial 且 t55 与 gold must_not 冲突，t45 文本损坏。
- 新 claims 引用/数字基本正确；P2 是 Primo Matrix 缺失、t45/t46 模态、t38 覆盖。
- 补 InP/SIC/完整 GAN/Primo Matrix，并修复 t45 文本，才有 PASS_WITH_FIXES/PASS 空间；当前未达到 CONTENT_PASS。

## 附录：审查输入

- CN：.planning/shared-reading-production/du11/live-cn-h1-b2v4e-20261018/{receipt.json,overall.json,rf-narrative.stdout.json}
- claims 14；evidence spans 96；prompt reading-source-scoped/4.0.8；model mimo-v2.6-flash。
- 本报告只读生成；未修改源码/测试/配置/gold，未执行 git 写操作，未调用供应商。
