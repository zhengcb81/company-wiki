# W22-PDF-DEPLOY 独审报告 R2（代码/规范一致性 + 反例）

- 审查者：独立代码审查 agent（非作者，round-1 报告同源；本文件为 D1–D3 修复后的复审）
- 复审时间：2026-10-30/31
- 复审基线：`e962198c` + `ee8138cf`（D1–D3 修复），中途新增 `cb37d82b`（recover 套件配对 samefile 契约）一并复核
- 复审方式：全部证据由审查者在只读条件下重新推导（重新计算 SHA、重新打开部署树/收据/plan、重新运行全套测试）；
  未修改任何既有文件；仅新增 `tests/unit/test_w22_review_code_r2.py` 与本报告；未推送；`C:/cwp-runtime` 只读

## 结论

**READY_FOR_ROOT**（附 1 项 nonblocking OPEN + 交接前流程要求，见文末）。

Round-1 的 3 项阻塞（D1/D2/D3）与 samefile 契约缺口均已实际关闭，证据见下；测试重绑全部诚实、无断言弱化；
新增反例仅发现 1 项 nonblocking 残余（R3）。

## D1 — CLI 默认 repo-src 偏移：已关闭

- `tools/pdf_runtime_deployment/__main__.py:17` 现为 `parents[2] / "src"`，解析为本仓 `src/`（实测 `is_dir()=True`）。
- `tools/pdf_runtime_deployment/_alignment_diagnostic.py:52` 同步修正；`deployment.py` 死变量 `_REPO_ROOT` 已删除。
- 附带修复（R2 非阻塞观察项）：`cmd_status` 对文件型 target 不再抛 `NotADirectoryError`（`__main__.py` 现按
  `target.is_dir()` 分支）。
- 证据：重绑后的正向断言测试（round-1 `test_cli_default_repo_src_points_at_this_repo`、R2
  `test_cli_default_repo_src_resolves_into_this_repo`、`test_alignment_diagnostic_parent_path_resolves_into_this_repo`）
  全部通过；若回退该索引会立即转红。

## D2 — 部署与最终代码绑定：已关闭（证据重新推导）

- 部署收据 `C:/cwp-runtime/w22-pdf-sdk/deployment.json` 的 `tool.implementation_sha256 =
  302bf87d14450d09c7e904a4ae4a9d242e967f8d44dc40e618f03bca2ddc0819`，与 worktree 及
  `git show HEAD:tools/pdf_runtime_deployment/deployment.py`（CRLF→LF 归一）逐字节一致（审查者重新计算，True）。
- plan 清单已按 C6 保留：`C:/cwp-runtime/w22-pdf-sdk-plan.local.json`；审查者用 `load_plan()` 重算
  `plan_digest` 自洽（`plan_sha256 = 1cba5f2e4dca2a900c39b4ba368b8a1d94a9f29362f20f5ebf64daf9a1e8e931`
  == 收据）；plan 内工具 SHA 同为 `302bf87d…`；36,121 env 行 + 6 模型行、53 script 行、0 blocking。
- 中间版本收据已按约定保全：`delivery/w22-pdf-deploy/review/deployment-intermediate-revision-99a5d250.json`
  （旧工具 SHA `99a5d250…`，COMPLETE，36,127 links，与退役前原收据一致）。
- 源保护复核（审查者抽样重算）：新树 `docling-2.96.0.dist-info/RECORD`、`torch/version.py` 与源 env
  `os.path.samefile=True`；`model.safetensors`（171MB）与 HF snapshot
  `8f39ad3c0b4c58e9c2d2c84a38465abf757272d8` samefile=True，源 SHA 复核未变
  （`00333a43…` == plan `source_profile.model_sha256`）。
- 输出配置仍仅 `python`/`artifacts` 与源 profile 不同（审查者逐 key diff）；封顶 120s/3页/4GiB 不变。

## D3 — deployment.json 输出接口：已关闭

新收据逐项覆盖卡要求（审查者实测字段）：`schema_version`；`source` 块含 config_path/python/prefix/
base_prefix/site_packages/artifacts 全部输入源路径；`environment_sha256` + `environment_algorithm`（依赖闭包身份）；
`model_sha256` + `model_config_sha256`；`output_config_path` + `output_config_sha256`（配置字节 SHA 重算一致）；
`logical_shared_bytes` + `new_scaffold_file_bytes`；`actual_allocation` 显式声明 NTFS 实际分配未知；
`source_protection` 证明字段（逐源重哈希 + 逐链接 samefile + 零字节复制 + 源未改）；
`light_verification` 由 `cmd_verify` 写回收据（`zero_write_verified=true`、L0 PASS、L1 PASS，
`recorded_in_receipt` 语义诚实：快照先于收据写入，复核本身对环境零写入）。

## Samefile 契约（round-1 反例）：恢复路径已关闭，零写复用路径留有 R3（nonblocking）

- `_reconcile`（恢复路径）现要求 hash + `os.path.samefile`，普通拷贝按外来内容 fail-closed（TargetConflict），
  保留被拷贝字节；round-1 反例已重绑为断言修复后契约（更强，非弱化）。
- **R3（nonblocking，新反例 `tests/unit/test_w22_review_code_r2.py`）**：`_reconcile_fully_consistent`
  （OWNED_COMPLETE 零写复用，`deployment.py:508` 起）只校验内容 hash，不校验 samefile；且共享的
  `receipt_stub` 在 REUSED 收据上仍断言 `source_protection.samefile_verified_per_link: true`。
  实测：完整部署后把某个 owned 硬链接替换为字节相同的普通拷贝 → 再次 deploy 判 REUSED（不冲突、不修复），
  收据仍声称逐链接 samefile 保护；同一篡改在恢复路径则 TargetConflict（契约不对称）。
  内容完整性不受影响，损害仅限零拷贝性质与该条证明字段。
  **最小修复**：`_reconcile_fully_consistent` 对每行加 `os.path.samefile(Path(row["source"]), destination)`
  （行内已有绝对源路径），或在 REUSED 收据上弱化 samefile 声明。一行级修复，不阻塞 ROOT 接收，建议列 OPEN。

## 测试重绑审查（任务 2）：无弱化

- 作者 recover 套件：helper 从 copy 语义改为真实 `os.link`（配套同 samefile 契约所必需；审查者实证：
  以 HEAD 提交版 copy 语义 helper 跑恢复场景会 TargetConflict 转红，故该改动是必要而非放宽）。
- 审查者 R2 文件（8 项）：corrupt/foreign receipt、配置冲突恢复、PermissionError 恢复、plan digest 键序稳定、
  constructor 截止 exit 1/0/1/3 全部原样保留；constructor 测试新增 `production_launch` 传播断言（默认 False、
  可显式 True）——加强；两处 REPO_SRC xfail 转正向断言——回退即红。
- round-1 文件（7 项）：plain-copy 反例重绑为 TargetConflict + 字节保留 + 移除外来拷贝后 relink + samefile
  断言——加强；unknown RECORD hash algorithm 诚实性缺口仍如实标注为 gap（nonblocking）；其余原样。
- 任何文件均未发现断言删除或放宽。

## L2 形态重绑评估

constructor 从 bare 解释器重绑到 `--production-launch`（真实 `child_launch_command` 形态，含 repo-local
pycache_prefix），最终部署 CONSTRUCTOR_OK 22.95s/30s，`launch=production_child_launch` 由集成测试断言。
评估：合规——未抬 30s 封顶、两次冷超时后停止未反复重试、生产 worker 从不裸启动（形态选择有据）、
bare 形态保留为冷诊断并在 findings 如实记录。

## 运行结果（任务 3）

- 全套 unit：**79 passed**（作者 21 + 审查者 R2 文件 8 + round-1 7 + 既有 environment/paragraph/alignment 43），
  `--basetemp=.w22t-review2`。
- `mypy tools/pdf_runtime_deployment/ + 审查者测试文件`：clean（9 files）；`ruff`：clean。
- 新反例 `tests/unit/test_w22_review_code_r2.py`：2 passed（R3 gap 文档化断言 + production_launch 显式
  repo_src 拒绝猜测）。

## 交接前流程要求（非代码缺陷）

1. `handoff.json` 仍为显式草稿（多字段 null、`_note: POPULATED AFTER FINAL BINDING RUN`）：定稿必须补齐
   implementation_commits（e962198c/ee8138cf/cb37d82b）、tested_commit/reviewed_commit（≥ 本报告落盘时的 HEAD，
   且包含 recover os.link 修复 cb37d82b——在此之前 committed 状态为红）、code_files raw/LF SHA、逐项
   requirements 映射（含 D1–D3 关闭证据与 R3 OPEN）、命令/退出码、deployment/config/SDK-E2E/对齐状态、
   independent_review 绑定（本文件 + round-1 环境审查 + `environment-review-r2-20261030.md`）、cleanup、
   原源未变、`open=[R3]`。
2. 未提交的文档收尾（handoff.md/findings.md/progress.md）需随定稿提交；`review/` 下新增文件一并入库。
3. findings.md D2 段落中 `68b82d08…` 为 e962198c 时点的中间 SHA，与最终 `302bf87d…` 并存易误读，建议定稿时
   统一表述（事实无误，表述问题）。

## 未验证/范围外

- 未重跑真实 SDK L2/L3（依据最终收据 + 审查者独立的硬链接/配置/SHA 复核）；未重新生成 1.2GB plan（以
  `load_plan` 重算 digest + 行数/抽样 samefile 代替）；环境独审 R2（另一并行 agent）另有报告。
- 既有 nonblocking 观察维持：unknown RECORD hash algorithm 静默忽略（诚实性小缺口）；目标树内空
  `receipts/` 目录无害存在。

## R3 fix verification（2026-10-31 追加，HEAD `2562d3b4`）

- **修复核验（任务1）**：`git show 2562d3b4 -- tools/pdf_runtime_deployment/deployment.py` 为 11 行 diff：
  `_reconcile_fully_consistent` 的条件由 hash-only 扩为
  `not destination.is_file() or _sha256_file(...) != row["sha256"] or not os.path.samefile(row["source"], destination)`
  ——与本报告 R3 最小修复建议一致；非 samefile 返回 False → 落入 `_reconcile` → TargetConflict，
  与恢复路径对称 fail-closed。commit 内 deployment.py 无其他行为变更（另含文档与审查者文件入库）。
- **重绑核验（任务2）**：`test_zero_write_reuse_enforces_samefile_and_conflicts_on_plain_copy` 断言修复后契约
  ——TargetConflict + 被拷贝字节保留 + 移除后 relink COMPLETE + 再次 deploy 零写 REUSED 且
  samefile 实证 + 恢复路径对称冲突——更强非弱化。（唯一 cosmetic：该文件 module 级 docstring 仍描述修复前
  gap，建议顺手更新，不影响断言。）
- **测试/静态核验（任务3）**：W22 专属 36 passed（author 19 + R2 reviewer 8 + round-1 7）；既有
  environment/paragraph/alignment 43 passed；`mypy tools/pdf_runtime_deployment/` clean（7 files）；`ruff` clean。
- **绑定核验（任务4）**：部署收据 `tool.implementation_sha256 == git show HEAD:...deployment.py ==
  worktree == be7dcf3407afd0bc76d8f173954e96ab8722fdfcb909750a67c9875e7c19eab5`（审查者重算，三方一致）；
  `plan_sha256 == 498b75554fdab844991c0945d8b781f1ffe31418a89dfba9b4c1a37b7734c482`；COMPLETE，
  36,127 links / 0 reused；`light_verification` PASS + `zero_write_verified=true`；`source_protection`
  证明字段齐备。R3 由代码 + 测试 + 收据三方闭环。
- **最终结论：READY_FOR_ROOT**。R3 已关闭；其余交接前流程要求（handoff.json 定稿补齐并列
  `tested_commit/reviewed_commit >= 2562d3b4`、未提交文档收尾入库）维持前文所述，无新增阻塞。
