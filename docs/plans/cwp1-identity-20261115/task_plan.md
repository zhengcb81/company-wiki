# CWP1: 身份匹配双缺陷修复（OWNERPKG-CWP-CANDIDATES-01 / CWP-1）

- 包 ID: OWNERPKG-CWP-CANDIDATES-01（缺陷 2：CWP-1 阿里身份候选唯一化）
- 分支: codex/cwp1-identity-suffix-20261115（独立 worktree
  C:/Users/郑曾波/Projects/company-wiki-cwp1-identity-20261115）
- 基线 commit: ac8841c55cb416c63f6d426dfb7c8edcd68729a2（master HEAD @ 2026-11-15 开工时；
  任务书写的 66c97834d 已被 4 个 docs(pwf) 提交推进，均为文档，见 findings.md 偏离登记）
- 主工作区: 有他人在途 PWF 改动（docs/plans/module-pwf-reconciliation-2026-11-14/），
  本包全程不碰主工作区。

## 目标

1. A1（主修）: 身份 exact 匹配路径（official_name/alias）引入公司后缀等价归一化
   （Ltd≈Limited 等），使 "Alibaba Group Holding Limited" 对 "Alibaba Group Holding Ltd"
   official_name_exact 单命中。归一化只用于比对，不改数据；多 exact 候选仍走既有
   ambiguous fail-closed，绝不静默选边。
2. A2（辅修）: exact 候选集跨 market 且共享同一 issuer_link_id 时，reason 细化为
   cross_market_dual_listing_requires_market_selection（候选照常携带
   market/exchange/ticker）。同市场多候选语义不变。schema 结构不动（值域扩展）。

## 红线

- 不动已登记实体与 security_master 数据文件；不删/不改既有候选数据。
- 只加匹配与标注语义；不改 security_identity.py 之外的 src 文件（测试文件除外）。
  唯一预期偏离: A2 新 reason 必须按 FC-1301 门禁在 observability.py 的
  REASONS/STAGES_BY_REASON 做纯增量注册，否则仓内契约测试红（详见 findings.md）。
- 不动 docs/plans/module-pwf-reconciliation-2026-11-14/；不 push；不并入 master。
- 测试与探针零网络零下载零模型。

## 验收

- 探针: "Alibaba Group Holding Limited"→resolved(US BABA)；"BABA"→ambiguous +
  具名双上市 reason + 两候选；"09988"→resolved。
- 回归探针: "AMD"/"腾讯"/"騰訊控股"/"贵州茅台"/"Apple Inc" 与基线一致。
- 既有身份相关测试全绿，总数不低于基线。

## 节点

| # | 节点 | 状态 |
|---|------|------|
| 1 | PWF 登记与基线探针/测试数字 | done |
| 2 | A1 后缀归一化实现+单测+commit | done |
| 3 | A2 具名 reason+注册+单测+commit | done |
| 4 | 改后全量验证（测试+探针）+commit | done |
| 5 | PWF 收尾 | done |
| 6 | §5.1 三查询解析探针 + 具名消歧语义（带命令输出） | done |
| 7 | §5.2 FF reuse_only 联动（阿里 20-F）+ master 基线对照 | done |
| 8 | §5.3 RF 六路线联动 + 六路线 master 归因对照 | done |
| 9 | §5.4 证据索引/失败样本保留 + 提交 | done |
| 10 | §8-1 独立 agent 重审（0 OPEN P1/P2 才交接） | 见 findings |
| 11 | §8-3 并线或明示交接 + handoff | 见 findings |

## 本轮追加节点（2026-11-15 续作，施工包全文执行）

- 承接范围: 节点 1-5 为既有实现（A1/A2），本轮**不重做实现、不删/不改候选数据**，
  只补齐施工包 §5 的验收 2/3/4 与 §8 收口。
- 写域: 仅本 worktree 的 `docs/plans/cwp1-identity-20261115/` 与 `evidence/`；
  不碰主工作区在途 WIP、不碰 ff1-catalog lane、不碰 Dashboard 侧适配器、
  不碰生产配置、不碰既有已登记实体。
- 联动探针夹具: tmp 目录 `C:/Users/郑曾波/AppData/Local/Temp/cwp1-probe/`，
  CWP CLI 指向修复后 lane src，catalog 数据只读指向主仓，零下载、零模型。
- 验收判据: §5.1 三查询具名结果 / §5.2 FF 20-F 不再 ambiguous /
  §5.3 六路线至少一条 found+capture_ready 或具名新原因 / §5.4 全证据带命令输出。
- §8-3 并线判断: 主工作区存在在途 WIP（module-pwf-reconciliation-2026-11-14 等），
  且 ff1-catalog lane 未收口；按 §8-3 情形 2 走**明示交接**，不强行并线。
