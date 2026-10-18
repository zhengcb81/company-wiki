# P3-IDENTITY-AUDIT 任务计划

PLAN_ID=parallel-packages-2026-10-18/P3-IDENTITY-AUDIT
worktree=`C:/Users/郑曾波/Projects/company-wiki-p3-identity-audit`
branch=`codex/p3-identity-audit-20261018`，baseline=`4045787f`（派发当日 master；作者不改基线）

## 目标

新增只读 CLI `tools/identity_audit/`：给定 catalog 配置 + request JSON，逐 source 核对
`ref` / `bytes` / `identity` / `period` / `availability` / `span` / `unit` 七类检查，
输出 `identity-audit-receipt/1`。唯一写操作是 `--out`；catalog 只读打开。

## 独占写集（只写这些）

- `tools/identity_audit/**`
- `tests/unit/test_identity_audit/**`
- `docs/plans/parallel-packages-2026-10-18/P3-IDENTITY-AUDIT/**`

## 步骤

1. 侦察既有契约（SourceRef / SourceVersionReader / verified_availability_evidence /
   EvidenceSpan / SourceExportBundleV2 / load_catalog_config / source_export_v2_cli 模式）。
2. 写 RED 用例（≥15，实现在前失败，日志留断言消息）→ `red-1-pre-implementation.log`。
3. 实现 `__init__ / __main__ / cli / core / export / receipt` + `README.md`。
4. GREEN：pytest / ruff / mypy / 手工 CLI（`--pretty` → `receipt.json`）。
5. 只读证明、字段对照、只写 `--out` 复核。
6. 独立审查（非作者）→ 修复 → 对最终 SHA 复审 → `review/independent.md`。
7. 提交实现，再单独提交交接；`handoff.md` + `handoff.json` 一次性交 ROOT。

## 冻结接口约束（不得违反）

- request/receipt schema：`identity-audit-request/1`、`identity-audit-receipt/1`。
- 状态词表：顶层只用 `ok|partial|fail|blocked|unavailable`；`not_applicable`/`not_evaluated`
  只在单项检查里且必须带 `reason`。
- 退出码：0=全部适用检查通过，2=至少一项 fail，3=blocked/unavailable。
- 未知一律 `null`，不得写成 `""`/`0`/`[]`/通过。
- 上限：`source_refs ≤ 500`、`evidence_spans ≤ 5000`、收据 ≤ 16 MiB → `blocked` + `limit_exceeded`。

## 红线

- 不写 `src/**`（整目录）、`tests/integration/**`、`tests/unit` 下其他目录、
  `tools/` 下除 `identity_audit/` 之外任何路径、`pyproject.toml`、`.githooks/**`、ROOT 独占清单。
- 越界即停写并在 `handoff.md` 报 `BLOCKED_BY_SCOPE`，不得先改后报。
- 不读密钥、不联网、不调模型；不写生产 config/DB/`output/`/gold、不改原件。
