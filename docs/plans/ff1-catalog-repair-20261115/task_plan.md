# FF-1 CWP 半边：目录层缺口修复四件套

- 分支: codex/ff1-catalog-repair-20261115
- worktree: C:/Users/郑曾波/Projects/company-wiki-ff1-catalog-20261115
- base commit: ac8841c55（任务书写的 66c97834d 之后 master 又进了 4 个 docs-only 提交，src 无差异，以当前 master HEAD 为基）
- 日期: 2026-11-15

## 目标

修复 catalog 目录层缺口四件套（每件独立 commit）：

1. **B1 resolver 具名分类**（先做）
   - `matching_sources_have_unknown_published_date` 拆分：unknown_date 命中恰为 1 个语义匹配 → 新具名 reason `unique_match_published_date_unknown`；多个 → 保留原 reason。
   - ResolutionResult 暴露 unknown-date 计数与被排除候选明细（供 B2/B4），不改各状态核心语义。
   - observability REASONS/STAGES_BY_REASON 注册新 code（FC-1301 门禁）。

2. **B2 ensure 内嵌一次性自愈**
   - ensure 的 resolution 命中两类 unknown-date reason 时：只读预检被排除候选 group 的盘上 sidecar（dayu_portfolio=组目录 meta.json；company_raw/directory=.source.json）是否声明 filing_date。
   - 有声明才修复：`register_groups(root_id, relative_paths)` 库函数（重构 cli register 分支与 service.register_sources，行为不变），只登记本次排除集内 group。
   - 修复后恰好重跑一次 resolution；仍失败 → 按 B1 具名 reason 落失败。无声明 → 直接落失败不空转。
   - 锁序：不在持 ensure/journal 锁时嵌套抢 scan/catalog 锁。修复写 append-only journal 事件（catalog_repair_applied，含登记 group 与数据来源）。
   - resolve/query 保持纯读零自愈。

3. **B3 写侧根因**
   - company_raw/directory 根 ensure 导入落库（canonical_writer._record_validated_capture）时，从 acquisition candidate 的 filing_date 声明式写入 published_date（走既有 source-facts 断言/投影机制，不引入猜测值）。
   - 根因（实测）：2026-11-08 批量写入的 verified 断言 patch 记录 published_date=None 显式未知；后续导入的 facts 在 `_record_validated_capture` 里被 `key not in previous` 过滤掉（显式未知被视为强于 provider 声明），导致 documents.published_date 永远 NULL。修复：显式未知（None）视为"stored 空列"，本次捕获带非空声明时允许 FILL（对齐 scanner _merge_columns 的 FILL 规则）；prior 非 None 值仍然获胜、scope 冲突检查不变。

4. **B4 operation 候选投影（生产方）**
   - --source-ref-v2 operation payload 在 status∈{ambiguous,not_found} 时新增可选字段 `candidates`（≤5，白名单逐字段，exclusion_reason 闭集）与 `reason`（闭集词表）。
   - completed/gap 不得携带；pathless guard 对 candidates 生效；operation_schema_version 保持 "1.0"。
   - 契约文本以任务书 ---CONTRACT-START--- 为准，不偏离。

## 红线

- resolve/query 零写语义不变；扫描合并/冲突/provenance 语义不变（复用既有机制）。
- 不动 src/company_wiki/source_catalog/security_identity.py；不动 docs/plans/module-pwf-reconciliation-2026-11-14/。
- 测试零真实网络/零真实下载。不 push、不并 master。每次提交前 git branch --show-current。conventional commits。

## 节点

- [N0] 基线测试跑通并记录数字
- [N1] B1 实现 + 单测 + commit
- [N2] B2 实现 + 隔离实例测试 + commit
- [N3] B3 实现 + 落库断言测试 + commit
- [N4] B4 实现 + 契约校验测试 + commit
- [N5] 回归不低于基线 + 交报告
