# P3-IDENTITY-AUDIT 交接说明（致 ROOT）

- **lane**：`P3-IDENTITY-AUDIT`（parallel-packages-2026-10-18 第 3 包）
- **基线**：`4045787f6bf77722d8125911f3475ecff9bca9b0`（派发日远程 master，由 ROOT 写入；本卡未改基线）
- **分支**：`codex/p3-identity-audit-20261018`（独立 worktree `company-wiki-p3-identity-audit`，与其他三包互不共享）
- **提交**：实现 `99a67f06` → 独立审查修复 `20a43fab` → 本交接提交（第三个提交，即本文件与 `handoff.json` 入库之时）
- **状态**：`FROZEN_AWAITING_ROOT_REVIEW`

## 交付物

只读 CLI `python -m tools.identity_audit`：对每个精确 source 版本，比较 export 侧请求声明与只读侧实得事实，七项冻结检查
`ref / bytes / identity / period / availability / spans / unit`，产出 `identity-audit-receipt/1`。
退出码 0（全通过）/ 2（≥1 fail）/ 3（blocked/unavailable）；stdout 恒为单行规范 ASCII JSON；`--out` 走临时文件 +
`os.replace`；目录、`..` 穿越、符号链接目标一律拒绝。生产模块全部位于 `tools/identity_audit/`（7 个文件），
测试 50 个用例位于 `tests/unit/test_identity_audit/`。

## 验收命令与结果（复跑方式见 `handoff.json` tests[]）

| 命令 | 退出码 | 结果 | 证据 |
|---|---|---|---|
| `python -B -m pytest tests/unit/test_identity_audit -q -p no:cacheprovider` | 0 | 50 passed / 0 skipped（审查复审中再跑一次亦稳定） | `green-2.log` |
| `python -m ruff check tools/identity_audit tests/unit/test_identity_audit` | 0 | All checks passed | `static-2.log` |
| `python -m mypy`（6 个 lane 生产模块） | 0 | 0 issues | `static-2.log` |
| `python demo-cli-run.py`（合成 tmp 夹具 + 只读证明） | 0 | exit 0 / status=ok / counts={checked:6, passed:5, not_applicable:1}，合成树逐字节零改动 | `static-2.log` + `receipt.json` |

RED 前置证据：`red-1-pre-implementation.log`（44 failed / 2 passed，全部显式 `AssertionError: … is not implemented yet`，非裸 ImportError）。

## 独立审查（reviewer ≠ author ≠ ROOT）

- 第 1 轮（绑定 `99a67f06`）：**REJECT** — 1 BLOCKER + 2 MAJOR + 4 MINOR + 4 NOTE。
  BLOCKER：span 校验曾以本地副本取代冻结的 `EvidenceSpan.from_dict`，全 null 坐标可令 CLI 崩溃（exit 1、stdout 空）；
  MAJOR：同根因造成一处「未知→通过」，另一处为越界 offset 被切片静默截断后通过。
- 作者修复（`20a43fab`，+81/−0 行测试差异，未删未弱化任何既有断言）：span 全部走 `from_dict`，拒绝即 `blocked`；
  越界 offset → `p3_span_ungrounded` + `detail.bounds_violation`；bytes 通过路径防御性复核请求摘要；
  `LIMITATIONS` 披露计数语义；period `detail` 全路径携带 `date_provenance`；`--out` 拒绝 `..` 与符号链接。
- 第 2 轮（同一独立 agent，绑定最终 SHA `20a43fab`）：**APPROVE** — F1–F7 逐项复验修复，无新增 BLOCKER/MAJOR；
  3 个非阻塞 MINOR/NOTE（junction 父目录、README 未同步 F5/F7 描述、无害双写）已转入 `known_limits` 由 ROOT 裁决。
- 报告：`review/independent.md`（其 SHA 与全部被审文件 SHA 见 `handoff.json` `independent_review.bound_files_sha256`）。

## 范围证明（`handoff.json` `scope_proof`）

production_writes / config_writes / db_writes / original_reads / original_writes / network_calls / model_calls /
key_reads 全为 0，`forbidden_paths_touched` 为空。`git diff 4045787f..HEAD` 共 25 个路径，全部落在本卡写集
（`tools/identity_audit/**`、`tests/unit/test_identity_audit/**`、本计划目录），未触碰 `src/**`、`pyproject.toml`、
`.githooks/**`、ROOT 专属路径及其他三包写集。审查两轮各自独立用字节级快照（sha256+size+mtime_ns）复证只读。

## 已知边界（完整列表见 `handoff.json` `known_limits`）

- PDF/DOCX span 区间不校验（仅精确 UTF-8 `text/plain`）；单位只做记号一致性，不换算。
- 卡 §5.4(5) 的键名（`source_url`/`captured_at`）与现行 `source-availability-evidence/1` 实际键不一致：按实键原样透传并披露。
- 复审 NEW-M1：`--out` 仅检查最终目标，junction 父目录仍写穿——是否补祖先 reparse 扫描由 ROOT 决定。
- 复审 NEW-M2：lane README 未同步 F5/F7 修复描述（receipt 与审查报告已披露）；修 README 会移动最终 SHA、
  破坏审查绑定，故留待 ROOT 裁决。
- **本工具未接入生产 worker 与 CI 门禁；接入须 ROOT 明确决定（卡 §9）。**

## ROOT 接收步骤

1. 按基线 `4045787f` 合入分支 `codex/p3-identity-audit-20261018`（或 cherry-pick `99a67f06`、`20a43fab`）。
2. 逐文件复核 `handoff.json` `file_bindings` 的 sha256/bytes（`changed_paths` 不含 `handoff.md`/`handoff.json`
   自身——自指哈希无法在文件内固定）。
3. 复跑上表四条命令，应与本文结果一致。
4. 按 README §6 清单终审；任何一项不符即 `REJECTED` 并回 lane。

（机器可读全量交接见同目录 `handoff.json`，schema `parallel-packages-handoff/1`。）
