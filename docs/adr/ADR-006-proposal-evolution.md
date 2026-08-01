# ADR-006：Proposal-first 自我演化

> 现行范围见 [ADR 适用范围说明](README.md)：proposal-first 只治理上游 source/collector/parser/schema，不治理投资研究状态。

- 状态：accepted
- 日期：2026-07-10
- 背景：当前系统没有可靠的证据谱系和提交状态，却已有批量写入、评估重写和 schema evolve 能力。此时增加自动化会提高错误复制速度。
- 决策：采用 **proposal-first** 自我演化机制：
  - 生命周期：detected → proposed → evidence_attached → impact_simulated → validated → approved → canary → promoted
  - 提议模型与评价机制分离，避免自提、自批、自评
  - 高风险变化（schema/config/entity 删除）长期保留人工批准
  - 自治成熟度梯级：observe-only → propose → reviewed apply → sampled low-risk auto-apply → SLO-governed autonomy
- 不采用的方案：模型直接改 schema/config/entity/wiki
- 保护的不变量：控制守恒、复现守恒
- 影响范围：所有演化路径（schema、config、entity、question）
- 迁移策略：从 observe-only 开始，逐步升级
- 回滚/修订方式：回滚上一 catalog/config/schema version
- 验证：没有 proposal ID 的自动修改被拒绝
