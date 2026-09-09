# V5 冻结边界重验（V5-2 第 1 项）

日期：2026-09-09。状态：PLAN_ONLY。本页回答 V5-2 第 1 项：「明确稳定审查边界；不把仅有前后 hash 或 `.gitattributes` 当作不可变性证明」。

## 1. 本次实测（只读）

| 项目 | 实测值 | 命令 |
|---|---|---|
| v5 目录 Git 跟踪 | **已跟踪**，`git ls-files` = 74，`git status` clean | `git ls-files` / `git status --porcelain` |
| 本目录属性 | `.gitattributes` = `* -text -eol -filter -working-tree-encoding` | 文件内容 |
| 属性生效 | normative 文件与 `.gitattributes` 自身的 `text/eol/filter/working-tree-encoding` **均为 unset** | `git check-attr` |
| 旧目录状态 | **已复活**：38 文件、tracked、clean、mtime `2026-09-07T18:08:52Z` | `git ls-files` / `Get-ChildItem` |
| 仓库全局 | `core.autocrlf=true`（三仓一致） | `git config` |

## 2. 为什么这些**不足以**证明不可变

1. **hash 只证明"某一时刻的字节"**：v4 事故即 `pre-commit` 在并行提交时对 tracked 文件做 checkout/patch 恢复，导致冻结后字节漂移；事后比对前后 hash 只能发现漂移，不能阻止它。
2. **`.gitattributes` 只防转换、不锁文件**（本目录 README 原话）：它保证 checkout 不做 EOL/filter 变换，但任何进程仍可直接写文件。
3. **本目录已被 Git 跟踪**：v4 事故时 v5 目录未跟踪、因而躲开了 hook 的 tracked-file 恢复；**该保护已失效**——这正是 V5-2 必须先重验边界的原因。
4. **旧目录复活**说明"退役"不是不可逆事实：同一 hazard 会在任一时刻重新出现，必须每次冻结前显式检查（N9）。

## 3. V5-2 采用的边界协议（机器可验，写入 v5 checker）

冻结/检查的每次运行都执行：

| 步骤 | 检查 | 失败处理 |
|---|---|---|
| B1 | 记录 51 项冻结集合的逐文件 `sha256/size`（运行前） | 任一文件缺失 → FAIL |
| B2 | 运行全套一致性检查（见 [v5 checker](../tools/v5_plan_consistency_check.py)） | 任一检查红 → FAIL |
| B3 | **重新计算** 51 项哈希并与 B1 逐项比较 | 任一漂移 → FAIL（并发修改检测，对应 v4 事故类别） |
| B4 | 校验 `.gitattributes` 在集合内且属性仍为 unset | 不符 → FAIL（N14） |
| B5 | 校验旧目录存在性并记录其状态 | 存在且无显式处置 → FAIL（N9） |
| B6 | 记录 Git HEAD 与 index 状态（`git rev-parse HEAD`、`git status --porcelain` 是否 clean） | 记录但不自动失败（供冻结 manifest 的 `plan_freeze_git_head`） |

**残留风险（如实声明）**：B1→B3 之间仍存在"读文件→写文件→恢复"的极窄窗口，任何进程级写事件审计都不在本次范围内。因此本协议给出的是**强一致性检测**，不是文件锁；冻结 manifest 是"在该窗口内字节未变的声明"，不是不可变性证明。正式审查时审查者必须独立重算哈希并自行判断。

## 4. 对冻结流程的约束

- 冻结 manifest 的 `pre_freeze_check.stdout_sha256` 必须来自**同一次** B1–B6 运行的 stdout（不得跨运行拼接）。
- 冻结后立即重跑 `--verify-manifest`，并把两次输出都留档；任一 red 则冻结作废。
- 三路独立审查（SQL/性能、生命周期/安全、测试/DAG）各自独立重跑 B1–B3，不共享同一份哈希快照。

## 5. 机器可验的旧目录处置（N9 载荷）

退役副本不是靠"路径存在 + 有一个文件"判定的，而是靠下面这个 **机器可读块**：checker 会解析它、按 `inventory_sha256`（对全部文件**按相对路径的 case-sensitive 排序**后，逐条拼接 `相对路径\0sha256\n` 再取 SHA-256）与 `file_count` 复算，并要求 `docs/plans/` 下**任何**候选目录都出现在 `retired_dirs` 中。候选判据（两条任一）：
1. 目录名含 `source-catalog-worker-recovery`（改名后仍会被认出）；
2. 目录内（含子目录）存在计划标记文件 `plan_consistency_check.py` / `gate_dag.v4.json` / `plan_manifest.v3.json`（改名标记但保留目录名仍会被认出）。

本文件自身的字节由 manifest 的 `boundary_record.sha256` 绑定，因此"改写退役副本 + 同步改写申报摘要"会同时触发 N9 与 manifest 绑定失败。

**判据边界（如实声明）**：目录名与标记同时被改写的副本、以及放在 `docs/plans/` 之外的副本不在机器判据范围内（见 `v5-freeze-record.md` §6 残余风险）。

```json
{
  "disposition": "NON_AUTHORITATIVE",
  "retired_dirs": [
    {
      "path": "docs/plans/source-catalog-worker-recovery-2026-08-22",
      "file_count": 38,
      "inventory_sha256": "da927ee294978a2578d459e285bbd00f7e7abea87ae6e42a0294a588f9a8c81b"
    }
  ]
}
```

判据含义：该目录及其自带的一整套 manifest/schema/checker 载体**不构成任何权威**；冻结集、取代链、`plan_directory`、`investigation_source` 均不得指向它（N2/N11/N9 机器检查）。

## 冻结时点复验（2026-09-09，B1–B6 实测）

- 冻结时点 HEAD：`436ecd38509ef87199b2a3133f08994bfdaec18f`；v5 目录冻结前已跟踪 74 个文件。
- 旧目录：**仍存在**，38 个文件、工作树干净、mtime `2026-09-07T18:08:52.8971277Z`；处置载荷见上（NON_AUTHORITATIVE）。
- 属性：`git check-attr text eol filter working-tree-encoding` 对 51 个冻结项共 204 行，全部 `unset`。
- B3 重哈希：51/51 哈希与字节数一致；`baseline/plan/__pycache__` 与 `tools/__pycache__` 均不存在（见记录 D2/D8）。
- 预冻结输出：`PASS: <n> checks; {"fixed_nodes":115,"schemas":29,"tests":315,"vectors":18}`（LF、0 个 CR，字节哈希由 manifest 绑定）。
- 后冻结复验：`--verify-manifest` 全绿；`--self-test` 17 例 / 27 个变异全部被拒（含隔离模式）。
- 本文件在冻结后不再修改（其处置载荷是 N9 的判据输入）；后续状态与结论记入 `v5-freeze-record.md` 与三份独立审查。
