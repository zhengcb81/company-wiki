# W08-CWP-G2-REPLAY 交接

- lane_id: `W08-CWP-G2-REPLAY`
- plan_id: `w08-cwp-g2-replay`
- repo: company-wiki
- workdir: `C:/Users/郑曾波/Projects/_harness_worktrees/w08/cwp-g2-replay`
- branch: `codex/w08-cwp-g2-replay`
- base_head: `122bbe3ba142979a2e478f886eb25de76edf2e00`
- scope_status: **COMPLETE**（本包范围内；真实 W04 既有失败如实记录，未修）

## 一句话结论

用真实 canonical 扫描、真实 finite batch、真实公开 read 与固定 RF 只读快照，
把「摘要 → 公开读取 → RF 消费」跑通并可复现：**连续两次独立 PASS**，
run2 零新模型 POST，9/9 公开读取验真，owned 容器恢复原样，0 付费调用。
同时把基线上真实的 W04 失败作为**已知失败**记录，不改成期望、不冒签。

## 交付入口（参数/README 一次定义并实际启动）

```bash
python -B tools/narrative_g2_replay/run.py \
  --rf-project <ABS_FIXED_RF_PROJECT> \
  --owned-root <ABS_NEW> --out-root <ABS_NEW>
```

产物 schema `narrative-g2-replay/1`。退出码 0=PASS / 3=PARTIAL / 1=FAIL / 2=INVALID。

## A / B / C 三大节点记录（UTC，真实命令与结果）

### A — 设计与 TDD

- 先读施工卡、HANDOFF_CONTRACT、INPUTS、本目录 INTERFACES。
- **实跑**候选 CLI 的 `--help` 确认参数，未按记忆造 CLI：
  `company_wiki.automation.narrative_batch_cli`、
  `company_wiki.source_catalog.narrative_transport_cli`。
- 先写行为 RED（`tests/unit/test_w08_narrative_g2_replay.py`），
  实现 oracle/specs 后转绿。
- 结果：RED 已确认（`ImportError: cannot import name 'oracle'`），随后实现。

### B — 集中回归

命令：`python -B -m pytest -q tests/unit/test_w08_narrative_g2_replay.py`

- 结果：**26 passed**。
- 另跑 `tests/unit -k narrative` 作邻域体检：
  `5 failed, 1097 passed, 2379 deselected`（141s）。
  这 5 项位于 `tests/unit/test_narrative_evidence.py`，属**基线既有**：
  将 `tools/narrative_g2_replay/` 整个移开后重跑仍为 `5 failed, 60 passed`，
  且 `git status --untracked-files=no` 为空（本包未改任何已跟踪文件）。

### C — 一次实际原生/公开 E2E

命令（实际执行，两次）：

```bash
python -B tools/narrative_g2_replay/run.py \
  --rf-project .planning/w08-cwp-g2-replay/input/runtime/rf \
  --owned-root .tmp-e2e/owned --out-root .tmp-e2e/out
```

- attempt-0001：`overall: PASS`，exit 0，elapsed 记录于报告。
- attempt-0002（紧接着同参数重跑）：`overall: PASS`，exit 0；
  attempt-0001 未被覆盖。

关键实测（`evidence/report-attempt-0001.json`）：

| 观测项 | 实际值 |
|---|---|
| run1 | `completed`, exit 0, **8** real loopback POST |
| run2（同 run_id/版本/spec） | `completed`, exit 0, **0** new POST；pins 相同 |
| 公开读取 | 9/9 exit 0，body SHA == pin，locator 已对原件重放 |
| RF 消费 | 9/9 read ok；8 有证据，1（ir-policy）正确地无证据 |
| 语言/period | 保留 |
| cleanup | restored=True，remaining=[] |
| provider_calls / paid_usd | 0 / 0.0 |
| raw / derived bytes | 13,846 / 753,292 |

类型矩阵实测（kind 保持、selection、locator 数、model POST）：

| case | kind | selection | loc | POST |
|---|---|---|---|---|
| annual-report | annual_report | selected | 1 | 1 |
| half-year-report | semi_annual_report | selected | 1 | 1 |
| quarterly-report | quarterly_report | selected | 1 | 1 |
| prospectus | prospectus | selected | 2 | 1 |
| placement | equity_offering_prospectus | selected | 1 | 1 |
| convertible-bond | convertible_bond_prospectus | selected | 1 | 1 |
| ir-policy | investor_relations | skipped_no_narrative | 0 | 0 |
| call-txt-zh | investor_call_transcript | selected | 1 | 1 |
| call-txt-en | investor_call_transcript | selected | 2 | 1 |

轻量/失效验证：

- 连续两次运行均 PASS（可复现），attempt 目录不覆盖。
- 第二 run 零新 POST，同时仍做 fresh 公开 read + locator 验真。
- oracle 对真实记录做 12 项对抗篡改（删 core、删必需组、空 case、
  去 raw receipt、坏 SHA、locator 未重放、第二 run 新 POST、
  scratch 未恢复、skip 出摘要、TXT 转 PDF、自报语义质量、
  自报付费调用）——全部被正确拒绝（FAIL/PARTIAL）。

## 变更文件（含计划/测试/工具）

见 `handoff.json` 的 `changed_files`（path + sha256 + byte_size）。
全部为**新增**；`git status --untracked-files=no` 为空，证明未修改任何已跟踪文件。

## 测试恢复

- 首次记录：`.tmp-e2e/` 由本包新建（此前不存在）。
- 临时证据已压缩保存为
  `.planning/w08-cwp-g2-replay/evidence/report-attempt-0001.json` 与
  `-0002.json`（合计 98,247 bytes，远低于 8 MiB）。
- 运行器自建的 owned 子目录与 scratch 已由运行器自身恢复；
  `--owned-root` 预存文件保留。
- 收尾时 `.tmp-e2e/` 的中间产物不再需要，最终清理由 ROOT 决定的
  工作区清理覆盖；本包不删除他人数据、不做 global kill。

## 已知基线失败（如实记录，未修、未改成期望）

本包交付物的必知事实——基线 `122bbe3b` 上真实存在的失败：

1. `tests/integration/test_narrative_batch_cli_e2e.py::
   test_cli_infers_sparse_languages_from_verified_pdf_and_transcript_bytes`
2. `tests/integration/test_narrative_runtime_e2e.py::
   test_runtime_e2e_read_identity_fails_automatically_and_transcript_needs_no_receipt`
3. `tests/unit/test_narrative_evidence.py` 5 项（见 findings F2b）

集成基线合计：`2 failed, 37 passed, 2 skipped`（331s）。

**重要更正**：施工卡提到「W04 核心 selector 的 18 既有边界 FAIL」。
本包实测该数字不成立：初次看到的 26 failed/13 errors 是**会话沙箱伪影**
（当时 workspace root 是 `company-wiki`，本工区是其兄弟目录，整体只读，
失败点是 `tempfile` 的 `PermissionError: [WinError 5]`），
文件策略放宽后重跑得真实为 2 项。详见 findings F1。

## 新缺陷最小复现

- F5：`ir_policy` 默认单次 PDF 解析下 `deferred_table_pages` 非空
  → `coverage_complete=False` → 永远 `needs_review`（0 span），
  走不到 `skipped_no_narrative`。真实批次路径本就做二次
  `full_table_scan=True`；本包照此执行后实测 `skipped_no_narrative`。
  归属：**前置条件**，非产品缺陷。
- 无其他新缺陷。

## remaining / 未知

- 本节点不验证供应商模型语义质量（stub 只回确定性原语言 draft）；
  `llm_semantic_quality=not_evaluated`。
- 真实 MiMo/DeepSeek/MiniMax 配置调用、累计预算、真实公司 G2/G4/G5
  由 ROOT 执行；本包 0 收费调用。
- 未测资源峰值（内存/磁盘瞬时峰值）→ `null`。
- 本包未修改 production config、未同步安装、未 rebase ROOT。

## 给 ROOT 的接口建议（不越界）

1. 收到已修 W04 后，用**同一** CaseSpec 矩阵重跑本包，比较
   `known_baseline_failures` 是否清零。
2. 需要剖面/配置时，请提供 `--rf-project` 指向当前已验固定 RF 快照；
   本包只消费其公开 reader。
3. 若希望把本包纳入 CI，建议作为**手动大节点**，不加入每次提交门禁
   （重型 E2E，约 1–2 分钟，含多个子进程）。
4. 真实的 `placement`/`convertible_bond` 若命名与
   `equity_offering_prospectus`/`convertible_bond_prospectus` 不同，
   需在 scanner/routing 词表层统一，而非在本工具里映射。
