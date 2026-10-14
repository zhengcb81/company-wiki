# DU3-DEPENDENCIES 交接（handoff）

分支 `codex/du3-dependencies-20261014`，工作目录
`C:/Users/郑曾波/Projects/_harness_worktrees/shared-reading-completion-20261014/dependencies`，
base `195aba20b0aecc2d661d7d04c5ba72f982bc02d0`，实现提交
`bc63a74eac1f73e6184a87a4b1bb65044840c1ad`（14 个文件、3807 行，真含代码与测试）。

## 一、做了什么

新增纯组件 `src/company_wiki/document_understanding/decision_dependencies/`，公开两个
冻结函数：

```python
def freeze_decision_dependencies(trace, *, limits=None) -> dict
def compare_decision_dependencies(frozen, current, *, limits=None) -> dict
```

它回答的只有一个问题：**这一个源的本地选择决策，还是不是同一个决策？**

卡的前提是：只 hash 最终送出的策略无法保证选择缓存——参与过决策但没赢的候选（同域内
改优先级、改匹配信号、被查验但未匹配的组件）变化后可能成为新赢家。因此本组件冻结的是
**决策本身**而不是决策结果：本源决策域的父/子 scope、实际查验的全部组件（含未匹配者与
败选者）、完整候选 membership（含 eligible）、以及实际采用的算法版本。

`same` **不等于 CACHE_HIT**。ROOT 仍要做原文/locator 读取校验，AUTO Store/CAS 的复用
决定权也在 ROOT。

## 二、边界（越界即违规，本包都没做）

- 不发现真实候选，不重实现 router/selector；
- 不调用 selector、registry、Store、source_catalog、automation、document_normalization；
- 不读 catalog、文件、系统时间，不联网；B 节点有 AST 导入检查证明这一点；
- manifest 里不保存政策正文、原文、DOM、all-units；不含 API 密钥/env 名、路径、run ID、
  当前时间、费用/timeout（key 集合封闭 + `versions` 键名筛查双重保证）；
- 不创建授权 JSON、签收或 canary 文件；不做安装动作；不改父包 `__init__`、profiles/
  registry/router、structure、selection_bridge/summary_input、source_catalog、automation、
  Store/SQL、ROOT PWF、其他 tests、依赖/CI/config。

`git status` 只有四个排他路径；`git diff --name-only <base>...HEAD` 未触碰任何外部文件。

## 三、字段与资源上限

**输入** `du-decision-trace/1`：`schema_version`、`scopes[{scope_id, regime, family,
form_type, purpose}]`、`components[{component_id, version, content_digest, matcher_digest,
scope_ids}]`、`candidates[{candidate_id, scope_id, component_ids, eligible}]`、`versions`、
`inventory_complete`。

**freeze 输出** `du-decision-dependencies/1`：`schema_version, status(complete|partial),
scopes, components, candidates, versions, decision_digest, diagnostics`。

**compare 输出** `du-decision-comparison/1`：`schema_version, status(same|changed|
unavailable), changed_component_ids, added_candidate_ids, removed_candidate_ids,
diagnostics`。

**digest**：对 `{schema_version, scopes, components, candidates, versions}` 做 canonical
JSON（sort_keys、`(',',':')`、`ensure_ascii=False`、`allow_nan=False`）后取完整小写
SHA-256；`status/diagnostics/digest` 本身不入 digest，所以同一决策在更大预算下达成时
身份不变。跨两个独立 Python 进程稳定，数组重排稳定。

**资源上限**（DU3/1 冻结默认，caller 只能下调）：64 scopes / 512 components /
4096 candidates / 2 MiB 输入编码 / 200000 work units。每个循环和每个大容器（含引用列表、
版本表）都计实际 work；行数与 canonical 字节另有独立上限。任一到限都给 `partial` +
具名诊断，不产生半图 `complete`，也绝不给 `same`。上调、负数、非整数、未知键、非 mapping
的 limits 一律拒绝。

## 四、怎么复跑

```powershell
cd C:/Users/郑曾波/Projects/_harness_worktrees/shared-reading-completion-20261014/dependencies
python .planning/du3-dependencies/run_nodes.py
```

该脚本依次跑 A/B/ALL 四个节点，把命令、exit code、耗时、摘要写进
`.planning/du3-dependencies/evidence/nodes.json`，并把两份小收据写进同一目录。

单节点：

```powershell
python -m pytest tests/unit/document_understanding_decision_dependencies/test_a_completeness_honesty.py tests/unit/document_understanding_decision_dependencies/test_a_mutation_matrix.py -q
python -m pytest tests/unit/document_understanding_decision_dependencies/test_b_engineering.py -q
python -m pytest tests/unit/document_understanding_decision_dependencies/test_c_catalog_replay.py -q
```

静态检查：`python -m ruff check src/company_wiki/document_understanding/decision_dependencies tests/unit/document_understanding_decision_dependencies tests/fixtures/document_understanding_decision_dependencies`
（exit 0）、`python -m mypy src/company_wiki/document_understanding/decision_dependencies`
（exit 0）。pre-commit 五个 hook 全过（dependency-declarations skipped、ruff Passed、
mypy skipped、config doctor skipped、host-assumption-guard Passed）。

## 五、A/B/C 三个大节点

| 节点 | 命令 | exit | 耗时 | 结果 |
|---|---|---:|---:|---|
| A | pytest test_a_completeness_honesty.py + test_a_mutation_matrix.py | 0 | 3.107s | 55 passed |
| B | pytest test_b_engineering.py | 0 | 3.458s | 37 passed |
| C | pytest test_c_catalog_replay.py | 0 | 3.156s | 19 passed |
| ALL | pytest tests/unit/document_understanding_decision_dependencies | 0 | 3.554s | 111 passed |

**A 先 RED 后实现**：实现前跑同一组测试得 `51 failed in 1.80s`，根因 `ModuleNotFoundError:
No module named 'company_wiki.document_understanding.decision_dependencies'`，收据
`.planning/du3-dependencies/evidence/a_red.json`。测试自己不算 hash、不镜像实现、不只断言
字段存在；每个正例都配了反向对照（顺序不变、无关域不变）。

**A 的正反例**：败选组件 priority/content/matcher 变化、zero-match matcher 变化、显示版本
变化、组件从 inventory 移除、候选新增/删除/eligible 翻转/component membership 变化/移入
范围、child scope 新增/变更/删除、算法版本新增或变化 —— 全部 `changed`；只调数组顺序
（scopes/components/candidates/引用列表）—— `same`；无关域正文不需要加入当前 trace，也不
改变本域身份；重复 ID、同 ID 不同内容、悬空 scope/component 引用、行内重复引用、错误类型、
截断 digest、未知字段 —— 明确拒绝；缺 trace/legacy schema/缺 inventory_complete/零候选
membership —— `partial`/`unavailable`，绝不给 `same`。

**B 的集中工程**：freeze/compare 确定性、finite JSON 往返、非有限版本拒绝；输入（两侧、
两个入口）都不被修改；digest 跨两个独立 Python 进程稳定、数组重排稳定；manifest key 集合
封闭、无运行时/密钥字段可达、`versions` 键名筛查、把路径塞进 scope_id 也漏不出字段名；
完整 SHA-256 才是身份、短版本仅展示、截断 digest 被拒；零 work / 1 字节上限 / 缺 inventory
都 `partial` 且非 `same`，每行都计 work；limits 只能下调；两侧引用完整性；manifest 与 trace
的类型辨别；AST 导入守卫（包无法触达 selector/registry/Store/IO）；100-source manifest 编码
体积实测。

**C 的独立快照回放**：用**真实**安装的 `reading_catalog.json`（SHA-256
`29bfefbe270cb8d2035bcd203dcf9b1226934dce7d0fd338132d9d559e18b46c`，24 families /
14 facets / 15 bindings，回放前后 SHA 一致）取身份，构造**合成**合法 scope/candidate
inventory，实际跑相关/无关变化矩阵：

| 变化 | 结果 |
|---|---|
| 域内策略内容改动（family:administrative_document） | `changed` |
| 败选候选 membership 改动（candidate:administrative） | `changed` |
| 域外无关策略改动 | `same` |
| 只调数组顺序 | `same` |
| 整个 catalog 当一个决策域 | `partial`（78 scopes / 38 components，`SCOPES_LIMIT_REACHED`） |

小收据 `.planning/du3-dependencies/evidence/c_replay_receipt.json`。

## 六、真实覆盖 vs 合成覆盖

**真实**：安装 catalog 的身份（组件 id、版本、content digest、matcher digest、applies-to
元组）；整个 catalog 当决策域时 78 scopes 超出 64 上限这一实测事实；100-source manifest 编码
体积实测（2 scopes / 4 components / 6 candidates 每源：mean 2042.2 B、min 1970 B、max
2128 B、合计 204216 B）；两个独立 Python 进程 digest 一致。

**合成**：决策 scope id、"实际查验了哪些组件"、候选 membership 与 eligible。catalog 不记录
某个源的 router 到底查验过哪些策略，这部分仪器属于 ROOT；卡也明确允许合成合法 scope，不需
ROOT 正式 trace。

**明确界限**：见收据的 `boundary` 字段。`certifies_production_reuse: false`。

## 七、哪些仍没证明

1. **无法认证外部漏报**：若 caller 声明 `inventory_complete: true` 却真的漏记参与者，本包从
   输入内部无法发现——trace 是唯一证据，又不允许读 catalog 交叉核对。卡要求把这一点写成文档
   而不是遮掩；完整性由 ROOT 的 router/selector instrumentation 真正确立。
2. **零候选 membership 的域永远不能 `complete`**。这是刻意的（它是 winners-only 清单的可检测
   形态，而且确实无可复用之物），代价是真正空决策会被记 `partial`、走重算而非复用。
3. **整个 catalog 不能当依赖单元**：实测 78 scopes 超上限，必须按源建域。
4. **compare 不读原文、不验 locator**；`equal` 不等于 CACHE_HIT，ROOT 仍要做 read_reuse_pin
   的原文/定位校验。
5. **正式 0POST/CAS/恢复由 ROOT 的 B 节点验收**，本包不因 compare 绿就认证它们。
6. 100-source 体积是代表性形状的体积上界，不是生产量预测。

## 八、原始资料与临时环境

- 未读任何公司原件；产品模块与测试都不打开原件。
- 生产配置未读未写。
- 安装的 `reading_catalog.json` 只读，回放前后 SHA-256 相同。
- 临时目录只有 pytest `tmp_path`；无下载/截图/db/新数据库；无安装动作；无授权/签收/canary
  文件。
- 测试运行同时跑了既有 DU 五个单元包作回归：`607 passed, 17 skipped`（20.26s），无回归。

## 九、ROOT 接下来做什么

在真实 router/registry/选择处记录完整的 `du-decision-trace/1`（含曾参与匹配但未匹配的组件与
匹配但落败的候选），提供当前同域 inventory，把 `freeze_decision_dependencies` /
`compare_decision_dependencies` 接进既有 AUTO 两阶段 generation CAS，再做真实 0POST/恢复
验收。本包不越界改这些文件。

按卡要求：**STOP 等 ROOT**，不并 master、不推主线、不改生产默认。
