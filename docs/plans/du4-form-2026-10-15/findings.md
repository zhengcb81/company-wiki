# 发现与限制

真实观察的来源及 SHA 见 fixtures/manifest.json。参考设计是未实施方案，不能当作已通过测试。目录内不含原始财报或生产数据库；生产接线由 ROOT 承担。

实施发现（2026-10-15 DU4-FORM）：

- `html_parser` 的 text ownership 是「每个 DOM block owner 恰好一个 unit」，因此「同 owner inline 包裹」= 单 unit 内多 span；跨 unit 的 value_refs 即跨 owner 分词，禁止串接（SPLIT_OWNER_VALUE）。若 ROOT 的 walk 将同 owner 拆成多 unit，需在 carrier 侧合并后再交本组件。
- 「冒号大写形状只是候选」在本组件内的可执行含义：本组件不做形状识别、不做全文扫描；形状候选属 ROOT router 层，只有 native_speaker_turn carrier 能产出 turn_evidence，且需真实正文或 source-owned turn_id。财务标签因此被结构性排除，无需也不可能有禁止词黑名单。
- 声明冲突只做字面值词法比较（declared 提取出的表单字面值 vs observed normalized_value）；`quarterly_report` 等非字面声明不可词法比较，仅在完全无观察载体时报告 DECLARED_FORM_UNOBSERVED。语义级 declared-kind vs form 一致性留给 ROOT 的唯一 router 诊断。
- 预算契约细节：计费 = unit 索引 + carrier + carrier unit_ids + value_refs；耗尽保留已确定结果、返回 partial 与计数（含 observed_counts）；结构畸形（错误 schema/重复 carrier unit_id/非法索引）抛 ValueError，原文不足（ref 越文本/空 span/缺 unit/跨 parent）逐项诊断不拒绝整文档。
