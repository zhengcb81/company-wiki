# P4-CONSUMER-CONTRACT — 独立审查报告 / independent review

- **Reviewer**: `independent-reviewer (non-author, non-ROOT)`
- **Date**: 2026-10-18
- **Worktree**: `C:\Users\郑曾波\Projects\company-wiki-p4-consumer-contract`
- **Branch**: `codex/p4-consumer-contract-20261018`（baseline `4045787f`）
- **Commits reviewed**:
  - 作者实现提交：`cdf5be5a`（审查起点，逐项核对 card.md 1–10 与 INTERFACES.md 1/2/3/5.4/8/9/10）
  - 审查者修复提交：`025c0b71`（仅 write set 内 3 个文件，未 amend 作者提交）
  - 本报告 + 最终 `receipt.json` 由紧随其后的独立提交承载（自引用不可能，见 INTERFACES §8 末段；SHA 由审查者在回报消息中交给 orchestrator）。
- **Overall verdict**: **PASS**（3 项缺陷已修复并复验；2 项文档/流程观察项转 `known_limit`，不阻断）

所有命令均在 worktree 根目录执行；`$env:PYTHONPATH = (Join-Path (Get-Location) 'src')` 每次显式设置。
`python -B -c "import company_wiki; print(list(company_wiki.__path__))` →
`['C:\...\company-wiki-p4-consumer-contract\src\company_wiki']`（确认跑在本 worktree，INTERFACES §10 第 2 行）。

---

## 1. 强制检查逐项裁定（card §10）

### Check 1 — skip 从不被算作 pass：**PASS**

命令（无 env）：
```powershell
$env:PYTHONPATH = (Join-Path (Get-Location) 'src')
python -m pytest tests/integration/test_p4_contract -q -p no:cacheprovider
```
实测输出：
```
============================= 34 skipped in 1.14s =============================
exit: 0
receipt: partial {'checked': 0, 'failed': 0, 'not_evaluated': 0, 'passed': 0, 'skipped': 34}
case statuses: 34 个全部 skip；skip reason 全部为 "Skipped: P4 requires CWP_P4_CATALOG_CONFIG"
```
- 0 个 pass：`pass cases carrying a not_evaluated check: []`；`skip/not_evaluated cases without reason: []`（脚本对最终收据逐 case 断言）。
- `CWP_P4_REQUIRE=1`（无 catalog）复跑：`============================= 34 errors in 4.18s ==============================`，exit 1，首条错误
  `Failed: P4 requires CWP_P4_CATALOG_CONFIG (CWP_P4_REQUIRE=1 turns skips into failures)`，
  收据 `status=fail, counts={'checked': 34, 'failed': 34, 'passed': 0, 'skipped': 0, 'not_evaluated': 0}`。
- 无任何 `pytest.mark.skip`/`xfail`：grep 全 lane，skip 只经 `conftest.skip_or_fail()`（有 reason 强制），
  且 `support/sessionreport.py` 对**无 reason 的 skip** 记为失败并把 exitstatus 置 1（`test_p4_unreasoned_skip_is_rejected` 覆盖）。
- `not_evaluated` 永不写成 `pass`：最终收据中 4 个 not_evaluated case
  （`test_p4_missing_manifest_is_not_evaluated`、`test_p4_read_before_after_are_identical`、
  `test_p4_missing_manifest_maps_to_not_evaluated`、`p4_probe_never_ran`）全部保留 `status=not_evaluated` + reason，
  顶层 `status=partial`（不是 ok）；`counts.not_evaluated == len(not_evaluated cases)` → True。

### Check 2 — 收据 counts 与真实运行一致：**PASS**

命令（最终验收运行，"last run wins"）：
```powershell
$env:CWP_P4_CATALOG_CONFIG = (Resolve-Path 'docs\plans\parallel-packages-2026-10-18\P4-CONSUMER-CONTRACT\fixtures\catalog\catalog.yaml').Path
python -m pytest tests/integration/test_p4_contract -q -p no:cacheprovider
```
实测汇总行与收据（同一运行）：
```
============================= 34 passed in 8.26s ==============================   (exit 0)
receipt.json  schema=p4-contract-receipt/1  status=partial  generated_at=2026-10-18T17:38:56Z
counts = {'checked': 34, 'failed': 0, 'not_evaluated': 4, 'passed': 34, 'skipped': 0}
cases  = 35 (34 pytest case + 1 ledger 探针 case p4_probe_never_ran)
```
- `passed=34` == 汇总的 `34 passed`；`failed=0`、`skipped=0`、`checked=34=passed+failed` 全部相等。
- `not_evaluated=4` 是**契约 case** 计数（pytest 不产生该计数），收据 `limitations` 第 5 条显式声明该语义（author 已知，且与 INTERFACES §2 单项状态规则一致）。
- 修复前后各复跑多次，counts 与 summary 均逐键相等（例如 `34 passed in 6.96s` 与 `34 passed in 9.74s` 两次同样一致）。
- 收据 schema：`test_p4_receipt_schema_exact_fields` 断言顶层 7 键与 §5.4 完全一致，`counts` 恰 5 键（含 `skipped`，按卡优先于 INTERFACES §7 示例的裁定已由 author 记录于 findings.md，审查者复核 card.md line 84 确认 `skipped` 是卡的冻结键名）。

### Check 3 — 真正 0 网络 / 0 模型：**PASS**

手工 socket 探针（审查者独立执行）：
```powershell
python -c "import sys; sys.path.insert(0,'tests/integration/test_p4_contract'); from support import netguard; netguard.install(); import socket; socket.socket().connect(('127.0.0.1',9))"
```
实测：
```
raised: support.netguard.NetworkAttempted
is AssertionError: True
is netguard.NetworkAttempted: True
msg: socket.socket.connect reached by P4 lane; the lane must never touch the network (card section 8)
attempts: ('socket.socket.connect',)
```
- 道内用例 `test_p4_socket_guard_records_attempt` 同样证明并记录 `code=p4_network_attempted`（收据 case 可见）。
- **session 级强制（本次修复新增，P4-R2）**：`sessionreport.finalize` 现在读取 `netguard.attempts()`，
  任何被记录的尝试 → 收据 `status=fail` + exitstatus≠0；本最终运行收据 `violations: []`（无任何尝试）。
- `sys.modules` 探针（审查者临时 pytest 插件，运行后删除）：
  `P4PROBE llm_client_modules: []` — 整个运行中无 openai/anthropic/llm_client/company_wiki.llm_client 等模型客户端。
  （`P4PROBE network_lib_modules` 含 `requests/urllib3`，系 pytest 插件依赖的**导入**；lane 自身 grep 无任何
  `requests/urllib/connect/openai` import，且连接入口已被守卫拦截，收据 finish 检查 0 记录。）
- 收据声明：`model_calls_zero` check pass（`downloads={"count":0}`、`model_calls={"count":0}`）、
  5 条 limitations 无任何"使用了模型/网络"的声称；`green-20261018.log` 亦无模型/下载相关用例失败。

### Check 4 — 未写入被测仓库：**PASS**

```powershell
git status --porcelain            # 审查结束时（最终 GREEN 之后）
```
```
 M docs/plans/parallel-packages-2026-10-18/P4-CONSUMER-CONTRACT/findings.md
 M docs/plans/parallel-packages-2026-10-18/P4-CONSUMER-CONTRACT/receipt.json
 M docs/plans/parallel-packages-2026-10-18/P4-CONSUMER-CONTRACT/task_plan.md
```
- 三条全部位于两个写集路径内；**write set 之外 0 改动**（含 `.gitignore`、`tests/conftest.py`、`src/**`、`config/**` 均未动）。
  注：`findings.md`/`task_plan.md` 的改动由**第三方（非本审查者）在审查会话期间**写入（mtime 18:12:09 / 18:13:33，
  内容为 author 风格的 PWF 追记）；审查者未 stage、未提交这两件，见 §4 观察项。
- 提交内容核对：`git show --name-only --format= cdf5be5a` 全部 40 个路径逐一断言 ⊆ 两个写集前缀，
  无 `OUT-OF-WRITE-SET` 输出；`025c0b71` 仅 3 个 lane 文件。
- 提交的 `fixtures/` 树无生成物：递归列举仅 `catalog/catalog.yaml + sources/{4 个文件} + expected.json + build_fixtures.py`；
  `Test-Path fixtures\catalog\state` → `no state dir`；`git ls-files` 对 `state|sqlite` 无命中。
  原因经代码复核：`p4_catalog_config` 把 fixtures catalog 整树 `shutil.copytree` 到 tmp 后才 `ensure_catalog_state(scan)`。
- 生产 config 未被写：对抗运行前后 sha256 均为 `3d159a4edc8e0e4d09b83afa95601c5ec885a18f7bd5d163579f3ff446e3f968`，
  `git status --porcelain -- config` 空；`tests/conftest.py` 的 `production_config_integrity` 会话断言亦通过。
- 消费端仓库：本交付未提供 `CWP_P4_FF_ROOT`/`CWP_P4_RF_ROOT`/`CWP_P4_CONSUMER_COMMANDS`，
  收据如实记 `not_evaluated`：case `consumer_run_readonly` = `not_evaluated`（reason `P4 requires CWP_P4_CONSUMER_COMMANDS`），
  limitation `CWP_P4_CONSUMER_COMMANDS was not set: ... no consumer process was executed.`，
  `consumer_manifest_missing` 同 reason 记 `not_evaluated`。无任何"消费端已核对通过"的虚报。

### Check 5 — 生产配置守卫不可绕过：**PASS（修复 P4-R1 后）**

对抗探针（审查者执行，逐条走 `support/environment.assert_catalog_config_allowed`）：
```
production (config/source_catalog.yaml)              → refused "must not point at production config"
traversal (fixtures\catalog\..\..\..\..\..\..\config\source_catalog.yaml) → refused（resolve 后命中生产路径）
relative   (config\source_catalog.yaml)              → refused
junction   (mklink /J fixtures\_probe_junction → config\) → resolve 为真实路径 → refused；rmdir 后目标未受影响
仓库根 config.yaml / pyproject.toml（fixtures 与 tmp 之外）→ refused "must be an absolute path under tmp_path or ..."
```
端到端（真跑 lane）：
```powershell
$env:CWP_P4_CATALOG_CONFIG = (Resolve-Path 'config\source_catalog.yaml').Path
python -m pytest tests/integration/test_p4_contract -q -p no:cacheprovider
→ ======================== 21 passed, 13 errors in 2.32s ========================   exit: 1
→ 收据 status=fail, counts={'checked': 34, 'failed': 13, 'passed': 21, 'skipped': 0, 'not_evaluated': 3}
→ 生产 config sha 前后不变、git status -- config 干净
```
- **发现并修复的绕过缺口 P4-R1**：原实现先 `samefile(production)` 后 `is_file()`，当指向的路径**不存在**时
  `Path.samefile` 抛裸 `FileNotFoundError`，逃出守卫设计的 `ProductionConfigRefused`（实测：
  `E FileNotFoundError: [WinError 2] ... fixtures\not-there.yaml`，21 passed/13 errors）。
  修复（`support/environment.py`）：存在性检查前置。复验：
  `======================== 21 passed, 13 errors in 1.92s ========================` exit 1，
  错误正文变为 `CWP_P4_CATALOG_CONFIG does not exist: ...fixtures\not-there.yaml`（pytest.fail 消息，非 OS 异常）。
- 语义备注：pytest 中 session fixture 内的 `pytest.fail` 按 pytest 分类记为 **error** 而非 failed；
  但 exit code=1、收据 `counts.failed=13`、`status=fail`——"唯一允许的硬失败"以非零退出 + 失败收据落地。

### Check 6 — RED 是确定的真实失败日志：**PASS**

`red-20261018.log`（UTF-16LE，19342 B，121 行）关键内容：
```
collected 33 items
...
================================== FAILURES ====================================
_______________ test_p4_receipt_counts_match_pytest_summary _________________
tests\integration\test_p4_contract\test_p4_consumer_readonly.py:131: in test_p4_receipt_counts_match_pytest_summary
    assert sum(summary.values()) > 0, (
E   AssertionError: no pytest outcome was recorded - pytest_runtest_logreport must feed sessionreport.record_outcome
E   assert 0 > 0
...
ERROR at setup of test_p4_ref_roundtrip ... support/cwp.py:138: in export_sources
E   ...CwpUnavailable: source export refused (2): {"reason":"catalog_unavailable",...}
============ 1 failed, 19 passed, 1 skipped, 12 errors in 4.86s ==============
```
- 是**断言失败**（AssertionError + assert 消息），不是 ImportError；12 个 error 是**缺失实现**（当时
  conftest 尚无 `pytest_runtest_logreport` 接线、fixtures 尚无 catalog state）产生的运行期错误，同属实现前状态。
- "实现前"有独立证据：RED 日志引用 `conftest.py:150` / `cwp.py:138` 与当前文件行号（175 / 139）不一致，
  且 RED 收集 33 项 vs 现 34 项（`test_p4_receipt_missing_file_is_refused` 为 RED 后新增）。
- 保留意见（转 known_limit，非阻断）：五类比较器/守卫类用例在 RED 时已通过（support 先于测试实现），
  author 已在 findings.md「RED 态与诚实记录」如实披露；task_plan 决策表
  「RED 用两个提交表达（提交 1 = RED 态）」为**过期陈述**——实际只有单提交 `cdf5be5a`，RED 仅以日志留档，无法 checkout 复现。

---

## 2. 缺陷、修复与复验

| ID | 缺陷 | 位置 | 修复 | 复验 |
|----|------|------|------|------|
| **P4-R1** | 指向不存在路径时守卫逃逸为裸 `FileNotFoundError`（`samefile` 先于 `is_file`），违反"唯一允许的硬失败必须是设计好的 refusal" | `support/environment.py` | 存在性检查前置，缺失路径一律 `ProductionConfigRefused` | 缺失路径运行：13 errors/exit 1，错误正文 `CWP_P4_CATALOG_CONFIG does not exist:`；生产/遍历/junction/越界四类探针仍全部 refused；env_guard 3 用例通过 |
| **P4-R2** | `support/readonly.py` 文档承诺"finalize 在 sessionfinish 复核基线、写在最后一测试之后仍失败"，但 `verify_unchanged()` **无任何调用**（死代码）；同样地 `p4_network_attempted` 只有定点探针读取，session 级无强制 | `support/sessionreport.py` | 新增 `_finish_violations()`：写收据**之前**复核只读基线 + `netguard.attempts()`；命中 → 追加 limitation、`status=fail`、`session.exitstatus=1` | 正向对照：进程内 `capture_baseline` → 写入写集内探针文件 → 检出 `git status --porcelain (worktree)` 变化；`record_attempt('socket.socket.connect')` → 检出 `p4_network_attempted`；清理后为空。最终 GREEN 收据 `violations: []` |
| **P4-R3** | `pytest_runtest_logreport` 忽略 teardown 报告：teardown error 会被**静默丢弃**，counts 与真实 pytest 汇总脱钩（check 2 的隐患） | `conftest.py` + `support/sessionreport.py` | teardown failed → `record_teardown_error(nodeid)`，`pytest_summary()` 把它计入 `error`（与 call 结果相加，复刻终端 `N passed, M error`） | 独立探针（TEMP 一次性用例）确认 pytest 终端语义 `2 passed, 1 error`；收据公式 `checked==passed+failed`、`failed==summary.failed+summary.error` 由既有用例继续断言通过 |

修复提交：`025c0b71`（`git add` 仅 `tests/integration/test_p4_contract/{conftest.py,support/environment.py,support/sessionreport.py}`，pre-commit 钩子通过，未 amend 作者提交）。

静态复验（修复后）：
```
python -m ruff check tests/integration/test_p4_contract   → All checks passed!        (exit 0)
python -m mypy    tests/integration/test_p4_contract      → Success: no issues found in 24 source files (exit 0)
```

未修（转 known_limit / 交 orchestrator 决定）：
- task_plan.md 决策行「RED 用两个提交表达（提交 1 = RED 态）」与 findings.md「以提交 1 复现」为过期陈述；
  两者均在 **PWF 叙事文件**中且审查期间正被第三方写入，审查者不改写他人 PWF 日志（README §3.10 一处只碰一次）。
- card §9 要求的 `handoff.md`/`handoff.json` 尚未存在（author task_plan Phase 7 明确排在本次审查之后；
  四张卡均未交 handoff）——ROOT 接收时须要求补交，并让 `file_bindings` 覆盖 `025c0b71` 之后的最终文件 SHA。
- 无 `BLOCKED_BY_SCOPE`：全部修复均落在写集内。

---

## 3. 最终 GREEN 验收（deliverable 3，最后一次运行）

```powershell
$env:PYTHONPATH = (Join-Path (Get-Location) 'src')
$env:CWP_P4_CATALOG_CONFIG = (Resolve-Path 'docs\plans\parallel-packages-2026-10-18\P4-CONSUMER-CONTRACT\fixtures\catalog\catalog.yaml').Path
python -m pytest tests/integration/test_p4_contract -q -p no:cacheprovider
```
```
============================= 34 passed in 8.26s ==============================   exit: 0
receipt.json (last run wins): generated_at 2026-10-18T17:38:56Z, status partial,
  counts {'checked': 34, 'failed': 0, 'not_evaluated': 4, 'passed': 34, 'skipped': 0}
  receipt sha256 = bd07a021b7a3ac524e89cec4f63791e7126f60d79c7f33e6897d86b1a11330a3
  finish/network violations: []
```
确认 **34 passed**，且 `counts` 与该运行的 pytest 汇总逐键相等。

---

## 4. 给 ROOT / orchestrator 的 known_limit

1. **handoff 缺席**：card §9 / INTERFACES §8 的 `handoff.md` + `handoff.json` 尚未交付（author Phase 7）；
   ROOT 验收清单 §6.2/6.3 依赖它，需在 author 补交后核 `file_bindings`（应含本审查报告与 `025c0b71` 之后的最终 SHA）。
2. **RED 仅日志、无 RED 提交**：`red-20261018.log` 真实且先于接线实现，但无法 checkout 复现（单提交交付）；
   task_plan 决策表相应行过期，建议 author 补记更正。比较器类用例在 RED 时已通过——author 已如实披露。
3. **`counts.not_evaluated` 计契约 case 不计 pytest 测试**（4 vs 34）：收据 limitations 已声明；ROOT 对照时按此读。
4. **消费端为真评估依赖 ROOT 输入**：无 `CWP_P4_CONSUMER_COMMANDS`/`CWP_P4_FF_ROOT`/`CWP_P4_RF_ROOT` 时，
   `cross_repo_readonly` 的消费端部分是空集通过（`consumer_roots=[]`），真实只读/映射结论只在 ROOT 提供清单后成立。
5. **PWF 并发写**：审查会话期间第三方改写了 `findings.md`/`task_plan.md`（未被审查者 stage）；
   请 author/orchestrator 确认来源后自行提交（同在写集内）。
6. **`ensure_catalog_state` 会对缺 state 的目录跑一次 `scan`**：fixtures 走 tmp 副本（提交树干净），
   但若 ROOT 供一个 tmp 下**无 state** 的 catalog，扫描会在其旁生成 state DB（仍限 tmp，符合路径守卫设计；
   README §2.2 的"不写 catalog"对**提交树**成立）。
7. **基于 porcelain 的只读核对看不见 gitignore 内的写**（fixtures 另有全量 digest 兜底）；
   lane 子进程均设 `PYTHONDONTWRITEBYTECODE=1`，实测无此类写。
8. **死代码**：`p4_consumer_repos` fixture 与 `support/consumer.git_state()` 当前无调用方（无行为影响）。
9. **pytest 分类备注**：生产 config / `CWP_P4_REQUIRE=1` 的硬失败在 pytest 终端记为 `errors` 而非 `failed`；
   exit≠0 与收据 `counts.failed`/`status=fail` 保证不被误读为通过。

---

## 5. bound_files_sha256（审查过且**未被审查者修改**的文件）

算法：`python -c "import hashlib,pathlib;print(hashlib.sha256(pathlib.Path(r'<path>').read_bytes()).hexdigest())"`
（于最终 GREEN 运行之后、本报告写入之前计算）。

| path | sha256 |
|---|---|
| tests/integration/test_p4_contract/__init__.py | c43a62f1a518dac7ad1d61c87353670b13f7ef4bd8226febb6a2ab983c61d0da |
| tests/integration/test_p4_contract/support/__init__.py | c36dd5591685385a8c5f989cc1adcfa171a7c048a6f584d8ba639527a3eca37e |
| tests/integration/test_p4_contract/support/checks.py | 267044e1762785b8a0a0da93b0865fcda220103afa3b0e143d37f466513c3796 |
| tests/integration/test_p4_contract/support/constants.py | 8163ce720f27dbef41fadfbfb4d3a9e740abc81aae76ce39d08dc358b1f1fc08 |
| tests/integration/test_p4_contract/support/consumer.py | 93c8fd9a0b7bb5ac7ccb2d15e300748b74179f2a356106b54a681c9bc6877c5c |
| tests/integration/test_p4_contract/support/cwp.py | 9c2b4e703359a336e0ce85539b9941b077539aad2de27c0c2e2e2fec11a860f2 |
| tests/integration/test_p4_contract/support/jsonio.py | d43efd465d00604e34e9d4e157cd7c15845d397c35f28ef4712ea24373fff8c4 |
| tests/integration/test_p4_contract/support/netguard.py | 8d0d6b78e58e14873674d1e4af586531028f7c66b27fd609ff168ddc6ce4d871 |
| tests/integration/test_p4_contract/support/observations.py | 3edbd8d67f96d7676f1842f0e481e8364fcff2e20402c3fa66fd0f769c9032c2 |
| tests/integration/test_p4_contract/support/readonly.py | b7d78ec4a1dcc278577769a254ec7f23a65cc44b65ccceb79d9c3034c60ee4c5 |
| tests/integration/test_p4_contract/support/receipt.py | ef1fe3b0049a0b2ab59d2e16235ce244465cd1ad8dd19d6bc7537ff3c291cd83 |
| tests/integration/test_p4_contract/support/report.py | 036c95ffe518ab95fc355fff9390f7b81f921713674630c6bad1c53374264d77 |
| tests/integration/test_p4_contract/test_p4_consumer_readonly.py | c29011763343353d7a1c27b0553a26c438f5d6808d27b8f7388130a852363f88 |
| tests/integration/test_p4_contract/test_p4_env_guard.py | ead9ee8cf5cfe0a08e8a734966885bd55342893c0b262bfa115487591035391b |
| tests/integration/test_p4_contract/test_p4_identity_period.py | edf2972e814c99caa1d3fc09cb420c22759e594775d28e63404067658b35cbf0 |
| tests/integration/test_p4_contract/test_p4_network_model.py | 3123600d585431753921d5b1635c952f6fad7dfaf4e299f5fa45c37d0c91fb10 |
| tests/integration/test_p4_contract/test_p4_observation_shape.py | 06f286b2e4c087bf7dd0e15512dfe5cfdf3b1151903a1b69964e83cd76016853 |
| tests/integration/test_p4_contract/test_p4_receipt_schema.py | e70c036a22ee996bdad70d5483f1819b99c8a7007f0639e07fe5244a7ee45d74 |
| tests/integration/test_p4_contract/test_p4_ref_roundtrip.py | e2ba9daed454be7beb9e6611c31f4647bcf7e4072cd940af71865c22d810cecb |
| tests/integration/test_p4_contract/test_p4_unit_grounding.py | 5e32d0d2a5f168ee00193826d91edaf59ee9331a089f32163f6ad24c6e4b6211 |
| tests/integration/test_p4_contract/test_p4_unknown_availability.py | 04b4a433d6610078f75191e7400e198eb22b463fa3d5bad4d9f6c0ad11d122cb |
| docs/plans/parallel-packages-2026-10-18/P4-CONSUMER-CONTRACT/card.md | 44e0dae5e67687239173fd72485c12e914840cecdd833632751b4f88dd13202c |
| docs/plans/parallel-packages-2026-10-18/P4-CONSUMER-CONTRACT/progress.md | 2d7d129b4d9cf917fd717834847ef737d8addbfd03ae697f3b21f4aba99972af |
| docs/plans/parallel-packages-2026-10-18/P4-CONSUMER-CONTRACT/red-20261018.log | 485de78bab8fa6ecc304dd3c2ed8b8da68ed17365fd6acb6243b949429afd789 |
| docs/plans/parallel-packages-2026-10-18/P4-CONSUMER-CONTRACT/green-20261018.log | c7e9c5f001071ebe88cc10de603a7193cb2457c51d078ebc56a927e00759497c |
| docs/plans/parallel-packages-2026-10-18/P4-CONSUMER-CONTRACT/green-allskip-20261018.log | 763356b0d4fe22f1f640f9476c7fa53aa289fdea1a5240e6883a96835bdf8232 |
| docs/plans/parallel-packages-2026-10-18/P4-CONSUMER-CONTRACT/static-ruff-20261018.log | af352a86840ad0af3d37ea0d9197f868363a6dac6b1c2ef5d2722f6b41d2d9af |
| docs/plans/parallel-packages-2026-10-18/P4-CONSUMER-CONTRACT/static-mypy-20261018.log | c29063cf0862d0194a9a684226adf9f83be7997ba3d005ce5b8b510949e8aff2 |
| docs/plans/parallel-packages-2026-10-18/P4-CONSUMER-CONTRACT/fixtures/build_fixtures.py | a8af68f3fa40d795160e4fdd7f714dc0c4aa4b1b09fbb61f900c23f645577ca0 |
| docs/plans/parallel-packages-2026-10-18/P4-CONSUMER-CONTRACT/fixtures/expected.json | 61c34c6bde64058db9df3c22944253ea1b2cc0b4895b364cadc921aff816d79f |
| docs/plans/parallel-packages-2026-10-18/P4-CONSUMER-CONTRACT/fixtures/catalog/catalog.yaml | 97f695c3a5d599945dd42f9936cb7eb685fd0a1f7d0a5b778ef2e9147486b973 |
| docs/plans/parallel-packages-2026-10-18/P4-CONSUMER-CONTRACT/fixtures/catalog/sources/annual-2025.txt | 184a7f6604c734973ccc8692ad50b5fa7633ff66b88345c312d9c54c0fdef101 |
| docs/plans/parallel-packages-2026-10-18/P4-CONSUMER-CONTRACT/fixtures/catalog/sources/annual-2025.txt.source.json | 07ff4969ff7c1777190e9350a948dc0a329b4968f0891b64d3616b6694fc40c0 |
| docs/plans/parallel-packages-2026-10-18/P4-CONSUMER-CONTRACT/fixtures/catalog/sources/disclosure.pdf | 0613c1f0bed7aea4674ff6e45db0d5814afc7ba375d1a5b363a9a0cbb17ded93 |
| docs/plans/parallel-packages-2026-10-18/P4-CONSUMER-CONTRACT/fixtures/catalog/sources/disclosure.pdf.source.json | 197194294dc227afbcdd2e9aafe592c1df115bb43e5964c3c6a638967d1705e0 |
| docs/plans/parallel-packages-2026-10-18/INTERFACES.md | b274baaa02fe9d54d68c275d3e53a66d2e89497c6cc5f076b3c84cccafa69c83 |
| docs/plans/parallel-packages-2026-10-18/README.md | 7e51add5966e35984587e4bd937a89c18b29365367b9195f976f7cd063bddf07 |
| tests/conftest.py（只读参照，写集外） | c8746a2694c3491688478d06e998935e403e0cef0c9f52afa886de4eafaad353 |

### 审查者修改的文件（post-fix SHA，提交于 `025c0b71`）

| path | sha256 |
|---|---|
| tests/integration/test_p4_contract/conftest.py | 8622b3862d72498d7c67b47fa7a04b12c2167e0f1716fdfbf3b03344eef8915b |
| tests/integration/test_p4_contract/support/environment.py | dc8356220aeff4b5c8b590d89491f6c2fb34d03434d13be4fe65277241450393 |
| tests/integration/test_p4_contract/support/sessionreport.py | 022d00b5867b9f83c6da173c73c7e4be9fb93b57392d7f3df003c23d1fae112e |

### 运行产物 / 审查期间被他人改动（不计入 bound）

| path | sha256 | 说明 |
|---|---|---|
| docs/.../P4-CONSUMER-CONTRACT/receipt.json | bd07a021b7a3ac524e89cec4f63791e7126f60d79c7f33e6897d86b1a11330a3 | 最终 GREEN（2026-10-18T17:38:56Z）生成，随本报告一并提交 |
| docs/.../P4-CONSUMER-CONTRACT/findings.md | 9f0a64d73d8ade5e888adef34c48ec105808bea30f0e25267067ad4be49db9d1 | 审查会话期间由第三方写入；审查者未 stage |
| docs/.../P4-CONSUMER-CONTRACT/task_plan.md | 92f3aae7982d1edc1523a1a5ed928917f2239c94803b1cac19e040bf4e571116 | 同上 |

---

## 6. 结论

六项强制检查全部 **PASS**；三项缺陷（P4-R1 守卫逃逸、P4-R2 只读/网络 session 级复核缺失、P4-R3 teardown 计数缺口）
已在写集内修复并复验，修复提交 `025c0b71`；最终 GREEN `34 passed`、收据 `counts` 与汇总一致。

**Verdict: PASS**
