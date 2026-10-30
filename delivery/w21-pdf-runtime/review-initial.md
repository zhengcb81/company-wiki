# W21-PDF-RUNTIME 独立初审报告（review-initial）

- 审查员：独立 agent（不属于实现团队，未修改任何代码/测试/收据；仅运行只读核查、测试与临时目录内的对照实验，用后已删除临时 worktree）
- 审查时间：2026-10-29 深夜～2026-10-30（本地）
- 被审 commit：`5a33d923cde6e0329a856c7fab426a6e9313678c`（分支 `codex/w21-pdf-runtime-20261029`，基线 `bb5d09c056ca36bba8061d761b5469d87aa6e5e0`）
- 方法概述：以施工卡为唯一契约，逐项执行 `git diff bb5d09c0..HEAD --name-status` 边界对照、生产 diff 精读、guard 正反例的本机实证、六文件测试实跑（含 12 文件导入面超集）、五组收据逐字段核对、ROOT 只读 SHA 核算与 `find -newermt` 核查、基线 detached worktree 失败集对照（用后已 `worktree remove`）、icacls/收据 stderr 根因链复核。所有命令与关键输出摘录见各节。

---

## 1. 边界合规 — PASS

命令：`git diff bb5d09c0..HEAD --name-status`，共 **33 文件**：

| 类别 | 文件 | 状态 |
|---|---|---|
| 生产 | `src/company_wiki/source_catalog/narrative_pdf_enhancement.py` | M（+60/−7） |
| 探针 | `tools/pdf_runtime_probe/cold_runtime_probe.py`、`run_cold_probe.py`、`synthetic_e2e.py` | A |
| 新测试 | `tests/unit/test_w21_pdf_runtime_launch.py`、`test_w21_pdf_runtime_probe_guard.py` | A |
| 本卡 PWF | `construction_card.md`/`task_plan.md`/`findings.md`/`progress.md` | A |
| 收据 | `receipts/`：b-red-initial + cold-rev1..5 各4件 + synthetic-e2e×2 | A |

全部落在卡的"独占改动边界"（生产 launch owner、`tools/pdf_runtime_probe/**`、新增 `test_w21_pdf_runtime_*`、本卡 PWF/delivery）内。卡允许的"相关 pdf 测试"（test_pdf_runtime_environment.py 等）与 `_paragraph_worker.py`、`narrative_pdf_environment.py` 未改动（`git diff bb5d09c0..HEAD -- <两文件>` 为空，符合"无缺陷不强改"）；未新增 `narrative_pdf_runtime_env.py`（卡允许但不强制）。

**禁止清单零改动**：`operating_states/`、`assertion_roles`、`narrative_business_*`、`narrative_operating_relations`、`narrative_support_use`、`narrative_reading`、`narrative_pdf_reading*`、`_bounded_process.py`、`_process_tree.py` 均不在 diff 中。探针以只读方式 import 既有 `company_wiki._process_tree.WindowsJob`（复用，非修改），符合边界。ROOT 共享 PWF（`.planning/c3-20261028`）零接触（见第 6 节 SHA 核算）。

## 2. 生产改动质量 — PASS

`narrative_pdf_enhancement.py` 全部改动为两个 hunk：

1. 新增私有段：`CHILD_LAUNCH_FLAGS=(-I,-X utf8)`、`_CHILD_ENV_ALLOWLIST`（13 个 OS 必需变量）、`child_launch_command()`（`-X pycache_prefix=<repo>/__pycache__/pdf-paragraph`，前缀不可建时回退 `-B` 零写入）、`_child_bytecode_prefix()`、`_child_temp_root()`、`child_environment()`（allowlist + 显式 offline/线程/编码变量）。
2. `enhance()` 三个调用点替换：`env = child_environment(...)`（原 `dict(os.environ,…)` 整体继承）；`TemporaryDirectory(dir=_child_temp_root())`（原默认父 %TEMP%）；`self._runner(child_launch_command(...))`（原 `[python,"-B",worker]`）。

核对结果：
- **公共门面不变**：`enhance()` 签名、`PdfReading`、response binding 校验、`reading_execution`/coverage 键集均未动；`temporary_root_restored_absent` 等 diagnostic 键为基线既有（`git show bb5d09c0:…` 第 212/278 行同名键）。
- **无新人工门禁进生产**：src 全树无 `addaudithook`/审批/授权逻辑；新增仅是启动机制。
- **fallback 语义未变**：`native_fallback`/`unaligned_native_fallback`/`partial_*` 判定与 `_observe_failure` 原样；测试 `test_enhance_launches_through_isolated_owner_and_keeps_parent_env` 以 runner 抛 ValueError 验证仍落 `native_fallback`+reason=ValueError。
- **recipe 键集未变**：`orchestration_sha256`=对本模块文件内容 SHA（基线/HEAD 同名同位），自动反映真实启动实现；E2E 收据 `recipe_keys` 24 键与基线配方块一致（v2 binding 来自未改动的 environment 模块）。
- **异常观测不变**：`CWP_PARAGRAPH_STAGE`/worker_error/returncode 提取逻辑未动。
- INFO：env 不再设 `PYTHONDONTWRITEBYTECODE`（由 `-X pycache_prefix`/`-B` 回退承担，字节码写入被约束在 owned 前缀内）——有意的语义替换，非回归。

## 3. guard 正确性 — PASS

审查员在本机（Windows，`os.devnull='nul'`）对 `classify_open`/`_is_discard_device` 实测（临时脚本，已删）：

```
'sub/NUL'     is_discard=False  → persistent_write   ✓
'NUL.txt'     is_discard=False  → persistent_write   ✓
'./nul'       is_discard=False  → persistent_write   ✓
'nul_backup'  is_discard=False  → persistent_write   ✓
'NUL'/'nul'/'Nul'（大小写变体）is_discard=True → 放行（仅精确设备名）
os.devnull 'r+b'/'w'/'wb+'/'a' 及 O_RDWR|O_CREAT int flags → 放行   ✓
fd=3 / None → None（不适用文件规则）✓
'annual.pdf' r → original_or_secret；'x/.env' r → original_or_secret ✓
```

设计为"字面量严格匹配（nt casefold）+ realpath 设备归一"双条件，方向保守：**没有任何真实文件写入能借设备名放行**。

INFO（语义备注，非缺陷）：Windows 上 `Path(os.path.abspath("sub/NUL")).resolve()` 实际也归一为 `\\.\NUL`（Win32 把路径末段设备名当设备），即 `sub/NUL`、`./nul` 的写物理上同样是丢弃设备写。guard 仍拒绝它们（findings.md 明确记录了该实测与"先严格字面量"的决策）。后果仅是探针侧偏严，无放行风险；rev5 `guard_rejections=0` 说明对 dill/torch 真实行为无误伤。

- **audit hook 只在探针**：`grep -rn addaudithook src/ tools/`——src 零命中，tools 下仅本探针与无关的既有 `source_root_portability`/`storage_footprint` 测试夹具。
- **表述不夸大**：探针 docstring 与 handoff 均限定"Python 可观测事件，非 native 系统调用拦截"；handoff 未声称 native 拦截。
- RED 真实性：`b-red-initial.txt` 显示 8 failed（旧 guard 复刻对 devnull 正例误拦 4 项 + `child_environment`/`child_launch_command`/`CHILD_LAUNCH_FLAGS` 缺失 4 项），符合卡"先 RED"要求。

## 4. 测试真实性 — PASS

命令：`PYTHONPATH=src python -m pytest tests/unit/test_w21_pdf_runtime_launch.py tests/unit/test_w21_pdf_runtime_probe_guard.py tests/unit/test_pdf_paragraph_runtime.py tests/unit/test_pdf_runtime_environment.py tests/unit/test_pdf_paragraph_reading_integration.py tests/unit/test_pdf_page_checkpoints.py -q`

结果：**137 passed, 0 failed**（11.39s）。分文件：launch 5、guard 15、paragraph_runtime 10、runtime_environment 18、reading_integration 9、page_checkpoints 80。

卡要求断言逐条在场且实跑有效：
- 毒化包不可达：父进程注入毒 `PYTHONPATH`/`PYTHONHOME`/`PYTHONUSERBASE` + 同名 `docling.py`/`shadow_probe.py`，断言 child `poison_path_entries==[]`、`shadow_origin is None`（真实子进程 sentinel）。
- parent env 不变：两处 `assert dict(os.environ) == before`。
- `-I`/`-X utf8`：builder 断言 + enhance 捕获断言；sentinel 实测 `isolated/safe_path/utf8_mode=True`、`user_site=False`。
- pycache 前缀在 repo 内：`prefix == Path(owner.__file__).parents[3]/__pycache__/pdf-paragraph`，`"site-packages" not in prefix.parts`，父级预建、前缀内无源文件。
- env 无 PYTHONPATH/PYTHONHOME：builder 与 enhance 捕获双断言（另无 PYTHONSTARTUP/PYTHONUSERBASE）。
- TEMP 在 prefix/tmp：`temp.parent.name=="tmp" and temp.parent.parent.name=="pdf-paragraph"`，TEMP==TMP==TMPDIR。
- 真 worker 身份段在隔离 flags 下存活：stderr 含 `CWP_PARAGRAPH_STAGE=INPUT` 与 `=IDENTITY`。

补充（超过 handoff 所述面）：12 个导入变更模块相关的测试文件（含 narrative_batch_recovery、source_reading_layers、pdf_reading_boundary、pdf_paragraph_demand、du11_document_work_policy 等）**237 例全过**。ruff 0.15.18 与 mypy 1.19.0 对全部改动文件复跑均干净。

## 5. 收据一致性 — PASS

`docs/plans/w21-pdf-runtime-2026-10-29/receipts/` 全部 26 件存在。逐字段：

- **cold-rev5.json**：`done_no_document=true`、`guard_rejections=0`、`seconds=16.222824`(<30)、`scratch_restored_absent=true`、launch_command=`[python.exe,-I,-X utf8,-X pycache_prefix=<repo>\__pycache__\pdf-paragraph,probe]`、BOOT flags `isolated/safe_path/utf8=true`、`prefix_name=env`、stdout 终态事件 `DONE_NO_DOCUMENT`、峰值 `peak_job_commit_bytes=615,989,248`（handoff"616.0MB"一致）、`probe_sha256=685dbbcd…`/`controller_sha256=5a9c7065…` 与当前文件 SHA **逐字节吻合**（审查员重算）。stdout 无 GUARD_REJECTED。
- **synthetic-e2e.json**：`status=native_fallback`、`reason=ChildFailed`、`last_stage=PAGE_1`、`worker_returncode=1`、`completed_pages=[]`、`cleanup={scratch_restored_absent:true, pdf_deleted:true, config_deleted:true}`、`source_preserved=true`、`enhanced_claim_valid=false`、`alignment_scope=no_aligned_groups_documented_honestly`、`environment_sha256=c84a984c…` 与配置一致——与 handoff"canonical E2E"表述逐条一致。
- **synthetic-e2e-ascii-alias.json**：`status=unaligned_native_fallback`、`completed_pages=[1,2]`、`stream_complete=true`、`peak_job_commit_bytes=3,250,298,880`（=3.25GB，<4GiB 界）、`seconds=42.39`（总 43.16<120）、`actual_engine=docling/2.96.0`、`model_sha256=00333a43…`、`converter_instances=1`、`rejected_groups=2`、`python_origin=ascii_alias_diagnostic`、cleanup 两项 true——与 handoff 一致。
- rev1–rev4 收据齐全且与根因链对应（见第 10 节）；`cold-revN.marker.json` 各自存在、互不覆盖；controller `run_cold_probe.py` 对已存在 receipt/marker 拒绝重跑（单次防重逻辑在场）。
- 敏感信息扫描：对 receipts 全目录 grep API 密钥类模式（api[_-]?key/secret/token/password/sk-…），仅命中测试文件名（test_secret_audit 等），**无密钥泄露**。

INFO：canonical E2E 的 docling 原始报错文本（"filename does not exists"）未在任何收据中留存（见第 10 节建议）。

## 6. ROOT 无损 — PASS

只读核算 `C:/Users/郑曾波/Projects/company-wiki/.planning/c3-20261028/pdf-sdk-isolated/`：

- `runtime-isolated.json` sha256 = `bcc427114955f6d045c5848b1885b24f1ec1666d1397bfb60ba4f404a225ff2a` ✓ 与要求值一致（rev5 收据 profile_sha256 同值）。
- `cold_probe.py` sha256 = `bb67326ad942a865d95b26ba60f0390ab83809d36dc2f651d7b520967470b06b` ✓。
- `single-cold-attempt.json`：`attempts=1`，键为 {attempts, timeout_seconds, profile_sha256, probe_sha256}，原文未改 ✓。
- `find env/Lib/site-packages -type f -newermt 2026-10-29` → **零输出**（env 今日零写入）✓。
- 附加：`handoff.json`/`deployment.json`/`cold-probe.json` 在场完好；env 目录 `icacls` 确认 Low 标签未变。

## 7. 清理 — PASS（附 2 条 INFO）

- junction `C:/Users/Public/cw-w21-ascii-env`：`ls` 与 `cmd dir /AL` 双查均**不存在** ✓。
- 工区 `__pycache__/pdf-paragraph/tmp/`：**空**，无残留 run 目录 ✓（前缀内为 bytecode 镜像：Miniconda 8.2M + Users 152M（apparent）/约 180M 分配，属设计内 git-ignored 缓存）。
- `git status --short`：`M docs/plans/w21-pdf-runtime-2026-10-29/progress.md`（PWF 进展+事故记录）、`?? delivery/w21-pdf-runtime/`、`?? receipts/full-unit-summary-current.txt`——均为等待提交物，与预期一致，无其他未解释变更 ✓。
- INFO-1：系统 `%TEMP%\cw-paragraph-diag`（2026-10-29 23:11 创建）为**空目录残留**，handoff 未提及；建议终审前删除。
- INFO-2：handoff 称缓存"95MB"，实测 apparent ~160MB（du --apparent-size：Miniconda 8.2M + Users 152M），数字过时/失准（见第 9 节）。

## 8. 基线对照（40F+60E） — PASS

`receipts/full-unit-summary-current.txt`：collected 9524，**40 failed, 9400 passed, 24 skipped, 60 errors**（982s）。

分布（按文件归组）：60 errors 全部在 `document_understanding_selection/test_source_support_use.py`；40 failed 分布于 `test_financial_statement_public_regressions`(18)、`du4_operating_states/test_a_real_observation`(7)、`du4_source_signals`(4)、`du4_table_measurements`(4)、`document_understanding_root/test_du2_policy_registry`(3)、`test_du2_strategy_binding`(1)、`test_cross_market_suite`(1)、`test_g5_legacy_checks_retirement`(1)、`test_main_ocr_selection`(1)。**与 W21 改动面零交集**（W21 相关面 186/237 全过）。

审查员以 detached worktree 抽查（`git worktree add --detach --no-checkout <tmp> bb5d09c0`，选择性 checkout src+tests，跑后已 `worktree remove --force` 删除）：
- 基线运行 `test_du2_policy_registry.py + test_a_real_observation.py + test_real_observation_fixtures.py`：**14 failed，失败集与当前逐条相同**（diff 为空，"IDENTICAL-FAILURE-SETS"）。
- 基线运行 `test_source_support_use.py`：16 failed + 60 errors——60 errors 基线同样存在（基线该文件失败比当前还多，方向排除 W21 回归）。

结论：40F+60E 为基线已有状态（ROOT 侧 WIP/稀疏缺数据），非本包回归；审查员独立判断与 handoff 初判一致。

## 9. handoff.md 草稿准确性 — PASS（含 6 处需终稿更正的数字/表述，均非阻塞）

逐节核对，以下表述**准确**：身份表（commits/基线/未推远端——`origin/codex/w21-pdf-runtime-20261029` 确不存在）；改动面描述（生产唯一文件、worker/env 未改、未新增 helper）；guard 测试描述（15 例与实跑一致）；rev5 数字（16.22s/616MB/guard=0/flags/prefix）；两个 E2E 的"各证明了什么"边界（canonical=PARTIAL、ASCII 别名=诊断性验证、未拿 engine 成功签业务召回、对齐验收归 ROOT、`alignment_scope` 如实）；根因链编号与因果方向；"证明/未证明"边界总体克制；stash 事故如实记录（progress.md 全过程，ROOT stash 未 drop）；`orchestration_sha256` 入 recipe 身份的表述与实现一致。

需在终稿更正（全部为数字/措辞级，不影响结论）：
1. **改动范围统计失准**：handoff"30文件，+794/−7"→ 实测 `git diff --shortstat bb5d09c0..HEAD` = **33 files, +930/−7**（代码+测试+工具 6 文件 +765/−7；PWF+收据 27 文件 +165）。
2. **缓存体量失准**："95MB bytecode缓存" → 实测 apparent ~160MB（分配 ~180M）。
3. **"与卡内~3.10GiB特征一致"无出处**：卡内与 ROOT 材料均无 ~3.10GiB 数字；收据峰值 3,250,298,880B = 3.25GB = 3.03GiB。建议删除该比照或改写为"4GiB 界内"。
4. **新测试计数表述含混**："新18+15例" → 实际新测试 = launch 5 + guard 15 = **20 例**（18 是 RED 时点收集数）。
5. **"test_pdf_page_checkpoints.py（53例）"** → 实际收集 **80 例**（全过）。
6. **handoff.json 尚不存在**：卡要求交 `handoff.md` **和** `.json`；当前 delivery/ 仅 md，且"icacls 证据在 handoff.json"为悬空引用——终审交付时必须落盘 json 并附 icacls 输出/SHA。

未发现把 ASCII 别名 E2E 宣称为 canonical 验收的表述；"replay 不重启模型"一句仅出现在 progress.md（收据 `replay_verified=0`、0 spans，replay 实际未承载证明），handoff.md 本身无此声明——建议 PWF 措辞一并收敛。

## 10. 根因链复核 — PASS（#5 的直接错误文本建议补存）

审查员独立取证：
- **#1 guard 误拦**：b-red 复刻测试固化旧规则误拦 devnull；ROOT handoff.md 原文记录 17.78s `GUARD_REJECTED(persistent_write)` 于 dill `open(os.devnull,'r+b')`。rev1 `guard_rejections=0` 通过该点（rev1 转为 ChildTimeout@30.0s，即 #3）。自洽 ✓
- **#2 完整性标签（Low IL）**：审查员直跑 `icacls`——env `python.exe` 与 `Mandatory Label\Low Mandatory Level:(I)(NW)`；W21 工区根、ROOT 仓根/src、env 目录均 `Low Mandatory Level:(OI)(CI)(NW)`。rev2/rev3 stderr 为 `FileNotFoundError: No usable temporary directory found in […Medium %TEMP% 候选…]`，与"Low child 不可写 Medium %TEMP%"一致；rev4 将 TEMP/pycache 指向 repo-local Low 树后该点消失（rev4 推进到 #4）。"Medium→Low 向下写总是允许"与 Windows 完整性策略一致。**自洽 ✓**。备注：rev2/rev3 收据中 `guard_rejections=701/700` 是探针 guard 对 tempfile 候选探测的拒绝计数——即使去掉 guard，OS 也会拒绝同样候选；两条机制交织但修复方向（可写 Low 根）对两者同时正确，无矛盾。
- **#3 字节码重编译**：rev1 30s 超时（faulthandler 栈停在 transformers 元数据扫描，8.6s CPU/25s wall，IO-bound）与"-B 全量重编译 >30s"一致；rev5 pycache_prefix 后 16.2s DONE。端点收据齐全（67.4s/54.5s/26.7s 中间测量值为实现侧自报，未独立复跑，与端点不矛盾）。自洽 ✓
- **#4 getpass 崩溃**：rev4 stderr 原文 `getpass.py … OSError: No username set in the environment`，调用方为 torch inductor `default_cache_dir()`→`getpass.getuser()`，与 handoff 完全一致；rev5 allowlist 补 USERNAME 后通过。自洽 ✓
- **#5 docling-parse 非ASCII路径**：差异证据强——canonical（profile 原 python 路径）PAGE_1 ChildFailed vs ASCII 别名同 env 同模型同配置全管线完成，唯一变量是部署路径的 ASCII 性。仍可质疑的环节（INFO）：①docling 原始错误串（"filename does not exists"）未留存在收据，当前仅 progress.md 文字转述；②fopen 对照实验（GBK 字节 OK / UTF-8 字节 FAIL）无 receipt 工件。建议终稿在 handoff.json 中固化 child stderr 摘录（含 SHA）与对照实验记录，使 #5 可独立复核。

---

## 结论

**可进入终审。**

10 项必查全部 PASS，无阻塞项。阻塞项数量：**0**。

纯 INFO 清单（终稿顺手处理即可，不构成返工要求）：
1. handoff 数字更正 5 处：30文件/+794 → 33文件/+930；95MB → ~160MB apparent；"~3.10GiB"无出处（3.25GB=3.03GiB，建议删除比照）；"新18+15"→20 例；"53例"→80 例（第 9 节）。
2. 终审交付必须落盘 `handoff.json`（卡要求 md+json），并固化 icacls 证据（当前为悬空引用）（第 6/9 节）。
3. 建议在 handoff.json 固化 canonical E2E 的 child stderr 摘录与 fopen 对照实验记录，使根因 #5 可独立复核（第 10 节）。
4. 删除空残留目录 `%TEMP%\cw-paragraph-diag`（第 7 节）。
5. 语义备注：Windows 下 `sub/NUL`、`./nul` 物理上也是丢弃设备，guard 拒绝属偏严策略（无放行风险，findings.md 已记录决策）（第 3 节）。
6. progress.md"replay 不重启模型"一句在 replay_verified=0（0 spans）下不承载证明，建议收敛措辞（第 9 节）。
