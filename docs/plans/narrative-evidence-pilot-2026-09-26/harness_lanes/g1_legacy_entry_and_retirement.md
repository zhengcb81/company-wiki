# G1-LEGACY：旧入口许可收敛与已完成运维工具退役

> 状态：**ready，可现在交给独立harness**。本卡只分派剩余门禁清理，不重复已交付W01/W04/FF-S3/ET-S3/SPACE-S5。MAIN同时负责来源读取规则与抽象层，最后统一合入。读本卡、仓库AGENTS和指定源码即可开工，不需要恢复历史几十个Phase。

## 1. 独占工作目录与基线

- 仓库基线：`C:\Users\郑曾波\Projects\company-wiki`，已发布代码提交 `1cfec10`；本轮计划文档基线 `376ed90`。
- **唯一工作目录**：`C:\Users\郑曾波\Projects\company-wiki-g1-legacy`；新分支 `codex/g1-legacy-entry-retirement`。
- 从 `1cfec10` 建隔离worktree，不从主线未提交配置复制。若该目录/分支已存在，先检查是否属于本卡；不reset、不清空不明目录。
- 局部PWF仅 `.planning/g1-legacy-entry-retirement-20261004/{task_plan,findings,progress}.md`，显式选择它。旧复制过来的总计划只读，不能成为另一份全项目状态。
- 原CWP、RF、FF、ET、StockWiki、IQS、Dayu、Dropbox、全局技能全部只读。不要在它们里面产生缓存/临时文件。

由harness在正常用户Git上下文创建自己的worktree/分支；不修改Git全局safe.directory或其他owner工作树。创建成功后所有实现、测试、commit都在本卡目录。

## 2. 已复现的问题与本包目标

`scripts/writer_policy.py` 仍把两个环境变量当兼容工具执行许可：`COMPANY_WIKI_WRITE_MODE=legacy` 和 `COMPANY_WIKI_LEGACY_WRITERS=allow`。`common.require_legacy_writer_permission` 的四个生产调用者均已永久退休，保留双许可没有业务收益。

入口还会受Python启动环境影响：普通 `python scripts/config_doctor.py --help` 返回0；`PYTHONPATH` 含 `scripts/` 时，sitecustomize加载同一策略却返回78。config_doctor是只读维护入口，这种环境差异应消除。

六个一次性运维脚本只由自身链/专属测试引用；现场一次退休流程已于2026-09-26完成，现存9份小事实记录共13,102 B。删除代码不动这些记录，也不运行退休/切库命令。

目标：支持的来源/维护入口无需人工环境许可；不再维护已完成一次性工具链。**研究/Wiki writer继续停用，这是CWP产品职责**。不把取消环境许可变成所有历史脚本无条件可执行。

## 3. 精确写入范围

可以修改：

```text
scripts/writer_policy.py
scripts/sitecustomize.py
scripts/common.py
tests/unit/test_writer_freeze.py
tests/unit/test_common.py
tests/unit/test_legacy_entrypoint_simplification.py  # 新增
.planning/g1-legacy-entry-retirement-20261004/**    # 小型局部PWF
docs/implementation/g1-legacy-entry-retirement-handoff.md # 新增交接
```

退役删除，仅限下面代码与专属测试：

```text
scripts/retire_source_catalog_db.py
scripts/cutover_source_catalog_db.py
scripts/audit_catalog_retirement.py
scripts/audit_catalog_consumers.py
scripts/retire_catalog_snapshot.py
scripts/retire_derived_archives.py
tests/unit/test_retire_source_catalog_db.py
tests/unit/test_retire_catalog_snapshot.py
tests/unit/test_retire_derived_archives.py
tests/integration/test_retire_catalog_snapshot_e2e.py
tests/integration/test_retire_derived_archives_e2e.py
tests/support/derived_archive_fixture.py
```

禁止修改：`src/**`、生产配置/原件/数据库/retirement记录、共享Contract测试、hooks/CI、AGENTS、CWP总PWF、其他仓库。`src/.../archive_retired_evidence.py` 和 `prune_retired_evidence.py` 有实际入口，**不在这次删除范围**。

如发现清单外真实caller，仅在交接里报文件/符号和建议修改；不自行扩张写集。专属测试删除必须随对应生产工具整条退出，不按“常常失败”删混合测试。

## 4. 固定对主线的行为接口

| 接口 | 本包交付后的行为 |
|---|---|
| `enforce_direct_cli` | 签名保留；支持入口按实际功能类别执行，不检查两枚环境许可；永久退休命令退出78 |
| `legacy_script_execution_allowed` | 签名保留，包括薄兼容`environment`参数；环境许可值不改变结果 |
| `is_legacy_script_cli` | 保留可解释的入口分类；读维护/来源pilot与永久研究writer分开 |
| `common.require_legacy_writer_permission` | 兼容现有调用方式，但不再有“两个因素必须齐全”的授权语义；永久退休caller仍False |
| `legacy_writer_authorized` | 无真实caller后删除；不要保留另一套无用授权函数 |

支持集合去掉六个已删除工具，加入已确认纯只读的config_doctor；保留当前仍支持的来源pilot。`collect_reports.py`、`test_framework.py` 等未完成正规化的混合旧入口不能因为“不在永久列表”就自动放行；报告它们的分类，由MAIN处理真实迁移需要。工具支持列表是实现能力，不增加用户角色/签名/逐文档许可。

sitecustomize与脚本自身guard应一致。永久退休脚本即使用 `python -S`，也须在配置/LLM/网络/写入之前退出。不要依赖“启动时刚好导入sitecustomize”来保证职责边界。

## 5. 实施步骤与一次集中验收

1. 读基线和写集，用CodeGraph核caller；对 literal 环境变量/旧文档使用rg。复现普通/PYTHONPATH两种config_doctor启动模式，只用`--help`，不执行生产维护。
2. **先RED**：新增专属测试，框住支持工具不需要许可、环境值不影响结果、永久退休不可复活以及启动模式一致性。
3. 收敛入口策略与common兼容函数，退役六脚本及其唯一测试链；保留未相关的原件/状态/网络隔离断言。
4. 一次运行下列责任包，修复具体红灯；更新局部PWF和交接，commit/push自己的分支。不要跑全Contract/coverage，不增加小节点审查。

```powershell
$env:PYTEST_ADDOPTS='-p no:langsmith_plugin'
python -m pytest tests/unit/test_writer_freeze.py tests/unit/test_common.py tests/unit/test_legacy_entrypoint_simplification.py -q
python -m ruff check scripts/writer_policy.py scripts/sitecustomize.py scripts/common.py tests/unit/test_writer_freeze.py tests/unit/test_common.py tests/unit/test_legacy_entrypoint_simplification.py
git diff --check
```

测试至少证明：

- 支持工具在无环境许可、两变量齐全、仅一个变量、普通启动与scripts在PYTHONPATH时结果一致。
- 永久退休入口在普通/`-S`启动仍退出，配置、LLM、网络均未初始化；隔离夹具原件与状态不变。
- 六工具/专属导入链已退出，已支持来源pilot `--help`可运行。
- 删除不涉及生产记录；本包只删worktree内的指定Git代码。

所有夹具/日志/cache使用本线隔离临时根，同账号创建/执行/finally清理；预置keep文件保留，本次生成副本原先没有则删除。禁止测试写穿生产YAML。分支push若触发现有轻量门照常运行，不绕过真实红灯。

## 6. 交付接口与MAIN接线

交付 `docs/implementation/g1-legacy-entry-retirement-handoff.md`，只含base/head/branch、精确改动清单、支持/永久退休分类、公开函数行为、测试命令/结果、临时根恢复、未完成事项。不给原件/大日志/密钥/备份进Git；不自行合master。

以下明确由MAIN合入时处理，本包不改：

1. `tests/contract/test_legacy_caller_reachability.py::test_non_r1_source_compatibility_keeps_explicit_override_contract` 仍是旧两变量合同，MAIN改成新静态支持/退役语义，保留其余原件/永久退休反例。
2. `scripts/clean_env_gate.py` 中旧变量清理随MAIN统一收口；网络、密钥、dotenv隔离保留。
3. AGENTS/总PWF历史引用与源层archive/prune CLI漏`now`的入口缺陷由MAIN处理，不留“已简化”但真实CLI不能用的状态。
4. MAIN核diff、跑一次G1受影响责任包，普通合入并推主线。外包交付后冻结本分支，避免验收时追加改动。

完成标准：双许可机制退出、支持入口启动行为一致、一次性工具链退出、永久职责边界与原件不变、集中责任包GREEN及短交接。没有签名授权文件、固定coverage线或逐helper签收。
