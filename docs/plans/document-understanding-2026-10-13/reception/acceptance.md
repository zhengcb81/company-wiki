# 旧 DU 三包接收结果 — 2026-10-13

## 接收范围

| 交付 | 最终作者提交 | 接收处理 |
|---|---|---|
| DU-PROFILES | e74b9dcbc1c58204c01df583fadaa98dbd7156ff | 旧实现保留；合 R01/R07 修复 7fa6dee2，180 项 profile 回归通过 |
| DU-STRUCTURE | f8f456a3475ef7ff56b15f0984f812535e5ebf75 | 合入已有语义结构与跨页数据；ROOT 一次绑定实际策略及最终上下文 |
| DU-BENCH | b891cf7498acff0e7d8f1b00cef9de91131ad141 | handoff 原 ad77758d 已过时；接真实最新提交及 ead4aab6 修复，17 gold / 192 facts 保留 |
| 旧 ROOT | 4b6a8599358bfc2ef6e425b4de8e1ec0a60d45b4 | 与当前主线整合；原件不复制，生产配置不切换 |

ROOT 修复 e9af9ae9 / 1c5784cb；最终真实切片观察接口 8a5721db。Git 祖先与实际树为准，不依赖过时 handoff 列表。

## 共用根因和修复

- **策略只是标签：** 合并多市场 aliases、分布式探测正文，S-1/F-1 走 prospectus；8-K/6-K 仅已读原件内附件生成子范围。实际章节/单元绑定自己的 profile/priority/focus，来源日期与修订范围进入摘要输入。
- **先闭包后截断造成假完整：** 统一有限依赖图，原选择保留、上下文/否定按不动点补齐；最终实发预算裁剪后再验证真实全集，断链明确 deferred，非必要缺失 partial。禁止以相同文字推断重复角色。
- **评价拿模型文字证明原件：** 只有最终所选原文 locator+text 能证明 recall；OR 支持组内全部 AND，项目/期间/单位约束保留；行政来源与财务常规数据不强求业务召回，未知与未审模型不伪称 PASS。
- **测到了测试包装却没测实际生产者：** 新 pure `observe_pipeline` 从实际最终 request 映射到独立 oracle DTO，三份 source_ref 对齐、每成员 text/locator/page 核对 original observation；不读 gold、不替 producer 挑文、不生 claims，0 模型且 producer-only。

## 测试与独审

一次集中四模块 491 PASS / 18 real_data deselected（13.76s）；显式四原件 11 PASS / 0 FAIL（14.72s）；新增 seam 最终 5 PASS（1.90s），benchmark 一次 147 PASS / 7 real_data deselected（6.11s，含前 4 seam）。测试不是几百次模型调用。
原件/6 配置 SHA+mtime、测试预存哨兵、独立 tmp 恢复全部通过。费用与外部调用均零；原始失败 XML 与最终大节点 XML 压缩留证，可回读完全一致。

独审发现过 2 个 P1 最终预算断链与 1 个 P2 幽灵完整状态，ROOT 先写 RED 再共用修复，7 个独立正反例通过。最终独立 agent 复核闭包、unknown/child route 与 observer 证据映射：没有当前并线阻断。其指出的 observation/source_ref 对齐缺口已补反例并修。

## 不能混为完成的内容

微软真实 baseline：5215 units / 96 selected，关键业务 4/8，漏 4 条 → FAIL。不是新 DU 摘要质量通过，也不能用旧 oracle 分数消除此缺口。
生产 AUTO/实际配置模型仍未切换；DU2 布局、业务 facet、价值预算和真实摘要/公司 G2/G4/G5 开放。Observer 尚不测整份 CID 乱码或模型语义；native observer 与独立审查仍负责相应质量维度。缺来源坐标/期间/scope 标未知，不发明。

## 冲突控制与空间

DU2 三树和独占模块零写。其他仓库、生产配置、原件零写；不扫删历史其他 owner 文件。本轮只保存紧凑测试留证，不存另一份 PDF/完整 MD、第二数据库或模型全文副本。发布后仅回收 ROOT 自建两个 fix 树和 reception 树，作者树仍用于交接。
