# V5-2 冻结记录（2026-09-09）

状态：**FROZEN_FOR_INDEPENDENT_REVIEW**（PLAN_ONLY，未实施；本记录不构成实施授权）
冻结时点 HEAD：`436ecd38509ef87199b2a3133f08994bfdaec18f`（本记录与冻结产物随其后一次提交入库）

## 1. 冻结产物与哈希

| 文件 | sha256 | 字节 | 角色 |
|---|---|---|---|
| `plan_manifest.v5.json` | `027f7a5c0bc2004f72af303915fff5bd5e0d66a0f3685b36fba4aa9a5d6aab74` | 13541 | 冻结 manifest（自排除） |
| `plan_freeze_check.v5.txt` | `88f407ae28477df99c8f1f6aa14242e040d3ff478dba390f79db528d1de8f083` | 172 | 预冻结检查 stdout（0 个 CR） |
| `plan_manifest.schema.v5.json` | `aa3897a007086e5138408919b9a4d8db62cf4a051b72e29e9cb1d3e7bd6da359` | 6486 | 治理件（冻结集） |
| `tools/v5_plan_consistency_check.py` | `97084c1e0cbbe3e90daed6e26803cc25477dfdb91c5b949c0d3810f4a9e67d85` | 25638 | 治理件（冻结集） |
| `.gitattributes` | 见 manifest 首项 | 172 | 治理件（冻结集） |
| `tools/v5_freeze_manifest_build.py` | `38137c46ac608ef45cea70b2809b836eef14016d51ac130410040cd95bf2b00c` | 6171 | 生成器（**不入冻结集**） |
| `tools/v5_version_reference_scan.py` | `ab46623873e4c52969d52888b020c52a74f1323ff15022bbc83a02f342206407` | 10057 | 证据工具（manifest 绑定） |
| `tools/v5_equivalence_check.py` | `c29e19ad1d9392fcd546f3a2be163d0134ce85828927b9a429c239ac105a0874` | 3035 | 证据工具（manifest 绑定） |
| `v5-version-reference-inventory.json` | `b64b9e67c011c0897592cbd15f8f9725fd0eab5b4bfe163aef68e345160f39d8` | 29954 | 证据（可复现） |
| `v5-baseline-equivalence.json` | `79ac6ca49ad7a7085cefcceeded65cc9d7fe2ae9f4bfcb26d608f20d867a0c67` | 2970 | 证据（可复现） |
| `import_manifest.v5.json` | `da7d116e8c692d6311411c7390bec4278b59666a771823672f53e9b0f6567e4a` | 34238 | 捕获记录（manifest 绑定） |

冻结集构成：**51** = 导入计划输入 48（`baseline/plan/**`）＋ v5 自有治理件 3（`plan_manifest.schema.v5.json`、v5 checker 入口、`.gitattributes`）；自排除 1（manifest 自身）。
等价性：`v4_exact` 21 / `crlf_only` 17 / `unproven_new_baseline` 10（与 `v5-baseline-equivalence.json` 及事故报告表一致）。

## 2. 协议 B1–B6 执行结果

| 步骤 | 结果 |
|---|---|
| B1 冻结前逐文件哈希 | 51 个文件，快照于 `frozen_entries()` |
| B2 运行全套一致性检查 | 预冻结：`PASS: 7658 checks; {"fixed_nodes":115,"schemas":29,"tests":315,"vectors":18}` |
| B3 冻结后重哈希 | 51/51 哈希与字节数一致；`baseline/plan/__pycache__` 不存在（见偏差 D2） |
| B4 `.gitattributes` 入集且属性全 unset | `git check-attr text eol filter working-tree-encoding` × 51 路径 = 204 行，全部 `unset` |
| B5 旧目录检查 | 旧目录存在（38 个已跟踪文件、工作树干净、mtime `2026-09-07T18:08:52.8971277Z`），显式处置记录 = 本目录 `v5-freeze-boundary.md`；无冻结项落在旧目录内 |
| B6 记录 HEAD / index | HEAD 见上；v5 目录冻结前已跟踪 74 个文件，冻结产物随后入库 |

后冻结复验：`--verify-manifest` → `PASS: 8866 checks; {"fixed_nodes":115,"schemas":29,"tests":315,"vectors":18}`；`--self-test` → **17/17** 负例被拒。

## 3. 负例 N1–N17 自测（`--self-test`）

每条负例在临时副本上施加一次定向变更并断言对应编码被拒；输出逐条 `SELF-TEST N<n> PASS`，汇总 `SELF-TEST: 17/17 negative cases rejected`。

| 编码 | 负例 | 自测结果 |
|---|---|---|
| N1 | 把 `plan_manifest.v4.json` 当作当前活动 manifest | 拒绝 |
| N2 | `plan_directory`/`pre_freeze_check.command` 指向已退役旧目录 | 拒绝 |
| N3 | 版本轴混用 | 拒绝 |
| N4 | `schema_version`/未知字段/缺必填字段 | 拒绝 |
| N5 | normative sha256/size 与冻结记录不符 | 拒绝 |
| N6 | `equivalence` 类别与复算不符 | 拒绝 |
| N7 | 导入 artifact 被改名/改字节/改 `$id` | 拒绝 |
| N8 | 用旧 checker 输出冒充 v5 预冻结检查 | 拒绝 |
| N9 | 旧目录复活且无显式处置 | 拒绝 |
| N10 | manifest 自身进入 normative 集 | 拒绝 |
| N11 | 取代链不指向 v4/v3 manifest | 拒绝 |
| N12 | `investigation_source` 不在 v5 目录内 | 拒绝 |
| N13 | normative 集缺项/计数不符 | 拒绝 |
| N14 | `.gitattributes` 不在冻结集内 | 拒绝 |
| N15 | generation 与 capture manifest 不符 | 拒绝 |
| N16 | v5 治理件未绑定为 `v5_own` | 拒绝 |
| N17 | `evidence_tools` 哈希不符 | 拒绝 |

## 4. 与合同/既有语料的偏差与决策

| 编号 | 偏差 | 理由与影响 |
|---|---|---|
| D1 | 历史哈希钉按布局解析 | 基线 `IMMUTABLE_HISTORY_SHA256` 期望 `plan_manifest.v3.json` 位于 checker 的 `ROOT`；v5 导入把它放在 `baseline/history/`。checker 用同一期望哈希做布局感知解析（实测 `9ee84acd…` 等于钉值）。不改导入字节、不改冻结集。 |
| D2 | 禁止字节码写入 | 用 `importlib` 加载基线 checker 会在冻结目录内生成 `baseline/plan/__pycache__/*.pyc`（实测发生过一次并污染证据集）。checker 置 `sys.dont_write_bytecode = True`，B3 边界检查断言该目录不存在；证据工具永久排除 `__pycache__`。 |
| D3 | 预冻结输出强制 LF | Windows 文本模式 stdout 产出 CRLF（实测 172 字节含 2 个 CR）。checker 统一 `reconfigure(encoding="utf-8", newline="\n")`；生成器在捕获含 CR 时中止。现产物 172 字节、0 个 CR。 |
| D4 | 证据范围收紧 | v5-1 证据范围含 v5 根目录活动文档（`README.md`/`task_plan.md`/`findings.md`/`progress.md`），而合同 §88 明确这些文档「活动，可更新」；两者冲突会使每次状态更新都让冻结证据失效。现范围 = `baseline/**`（54）＋ v5 根冻结输入（`.gitattributes`、`plan_manifest.schema.v5.json`）＝ **56**；排除活动文档、`v5-freeze-*` 记录与审查、两个冻结产物、`reviews/`、`tools/`、`import_manifest.v5.json`、`verify_import.py`、`__pycache__`。该偏差改变证据计数（56/54/2），不改变任何导入字节或冻结集。 |
| D5 | 生成器不入冻结集 | `tools/v5_freeze_manifest_build.py` 有写权限，不进入 48+3=51 的冻结集；manifest 的判定完全由 `--verify-manifest` 与 `--self-test` 承担。 |
| D6 | schema 路径正则放宽首位 `.` | `.gitattributes` 以点开头，原 `^[A-Za-z0-9]…` 无法表达冻结集首项；改为 `^[A-Za-z0-9._]…`。只放宽合法路径集合，未放宽任何语义约束。 |
| D7 | 合同计数行更新 | `v5-version-contract.md` 原写「54＋5＝59 份」，随活动文档漂移；按合同 §34「以扫描时点为准」，该行改为指向冻结证据 `totals`。 |

## 5. 复现命令

```bash
cd <repo>
python docs/plans/source-catalog-worker-recovery-v5-2026-09-03/tools/v5_plan_consistency_check.py
python docs/plans/source-catalog-worker-recovery-v5-2026-09-03/tools/v5_plan_consistency_check.py --verify-manifest
python docs/plans/source-catalog-worker-recovery-v5-2026-09-03/tools/v5_plan_consistency_check.py --self-test
python docs/plans/source-catalog-worker-recovery-v5-2026-09-03/tools/v5_version_reference_scan.py --check
python docs/plans/source-catalog-worker-recovery-v5-2026-09-03/tools/v5_equivalence_check.py --check
```

## 6. 残余风险（不隐瞒）

1. 冻结只覆盖**规划文档完整性**，不覆盖 worker 实现、配置、数据库、任务；v5 仍是 PLAN_ONLY。
2. 旧目录是**独立第三份副本**（38 文件，干净）。本冻结只把它标为「非权威 + 显式处置」，未删除、未加锁；任何人仍可复活它并绕过本 manifest。
3. `plan_manifest.v5.json` 的不可变性依赖 Git（N10 用 `git hash-object` vs `HEAD:blob` 检测改写）；未跟踪状态下的改写无法被本地检测。
4. 证据可复现性依赖「冻结后不变的扫描范围」；若将来修改 `baseline/**` 或两个冻结输入，`--check` 会失败——这是设计意图。
5. 本记录、审查记录与边界记录本身不在冻结集与证据范围内（避免自指），其完整性只由 Git 与三份独立审查背书。
