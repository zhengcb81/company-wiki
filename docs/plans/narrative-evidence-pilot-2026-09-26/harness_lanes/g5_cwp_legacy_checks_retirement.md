# G5-CWP-CHECKS：旧工程门禁与批处理外壳整族退休

**状态：ready，可现在单独开工；只在新工作树施工。** 本卡是 G2-07/P1 剩余范围，G3 旧维护、G4 Pipeline 已完成，不重做。MAIN 总目标 paused 不妨碍用户启动本卡。

## 1. 项目、基线和唯一工作目录

- 原仓：`C:/Users/郑曾波/Projects/company-wiki`，master；冻结基线 `5d0ad75504a9815febc1bddbe76ae2f667c3e74a`。
- 工作目录：`C:/Users/郑曾波/Projects/_g5/cwp`；分支 `codex/g5-cwp-checks`。发布本卡时该目录尚未创建。
- 最终合入由 MAIN 负责；不在原仓实施、不复制原仓未提交 G2-12、不自行合 master。

```powershell
git -C 'C:/Users/郑曾波/Projects/company-wiki' status --short
git -C 'C:/Users/郑曾波/Projects/company-wiki' worktree add -b codex/g5-cwp-checks 'C:/Users/郑曾波/Projects/_g5/cwp' 5d0ad75504a9815febc1bddbe76ae2f667c3e74a
Set-Location 'C:/Users/郑曾波/Projects/_g5/cwp'
# 已存在则核 Git HEAD/分支/归属；匹配本卡可恢复，不 reset/覆盖未知工作。
```

先读适用 AGENTS、本卡、`scripts/writer_policy.py`、下列六脚本、`tests/unit/test_hermetic_runtime.py`、`tests/acceptance/test_control_bootstrap.py`、`tests/helpers/gold_evaluator.py`、当前 `.pre-commit-config.yaml/.github/workflows/ci.yml/.githooks/pre-push`。CodeGraph优先定位结构；初始化授权已覆盖本项目。当前索引曾返回 G4 已删除的 Gate 节点，不据过期片段扩大写集；已打开文件的 import/命令字符串和冻结 Git 是具体迁移依据。

PWF 只创建一处：`<工作树>/.planning/g5-cwp-checks/`。在自己 shell 设置 `PLAN_ID=g5-cwp-checks`、`PWF_PLAN_ROOT=<工作树>`，用已安装 resolver，读取该目录三文件；禁止再造根 task_plan 或第二份 docs 镜像。

先创建缺少的三PWF，再在本工作树执行（已存在文件只恢复，不覆盖）：

```powershell
$env:PLAN_ID='g5-cwp-checks'
$env:PWF_PLAN_ROOT=(Get-Location).Path
& "$env:USERPROFILE/.agents/skills/planning-with-files/scripts/resolve-plan-dir.ps1"
```

## 2. 实际问题与最终结果

`semantic_gate` 把最少30来源/数值阈值当合格资格；`architecture_gate` 使用 regex/计数规则；`clean_env_gate` 复制整候选树并执行旧 Gate 命令；`gold_gate` 强制收据写在 artifacts/gates。旧 `test_framework/batch_process` 还保留已退休处理链的完整实现。它们不是现行叙述 Worker，不能声称正在逐份阻断生产，但继续保留会误导较弱模型并拖累维护。

最终六个旧 CLI 都仅为纯 stdlib 退休薄壳：直接调用（含 `--help`、旧参数、`python -S`）清楚报告 `LEGACY_ENGINEERING_TOOL_RETIRED` 并 exit78；import 和 main 均不复制目录、不写收据、不构造模型/Store/下载器。沿用 writer_policy 退休约定，不增加批准旧链的 flag。

**有用行为必须保留：** clean_env 的环境隔离确被当前 hermetic 测试消费；API keys/dotenv/意外外网隔离、实际错误退出码和来源引用反例不能随着旧门一起丢掉。gold evaluator 的真实定位/缺来源/更正/未来公开/重复等独立反例保留为测试，不再作为发布签收服务。旧阈值可以作为历史指标计算保留，不能成为当前资格门。禁止把错误资料的质量结果改成成功。

## 3. 独占写集与禁写集

可写/删除：

- `scripts/{semantic_gate,architecture_gate,clean_env_gate,gold_gate,test_framework,batch_process}.py` 六个文件。
- `scripts/writer_policy.py` 仅这六个名字的类别/退休说明，不重构其他类别。
- `control/architecture.json`（确认只有退休工具消费后删除）、`control/README.md`（历史/当前说明）。不新复制 archive。
- 新 `tests/support/isolated_environment.py`：迁移实际被测试消费的纯隔离 helper；不成为生产模块，不增加用户权限开关。
- 精确迁移：`tests/unit/test_{semantic_gate,architecture_gate,clean_env_gate,hermetic_runtime,common,legacy_entrypoint_simplification,writer_freeze}.py`，`tests/acceptance/test_control_bootstrap.py`，`tests/contract/test_{gold_evaluator,gold_mutations,legacy_caller_reachability}.py`。仅改本族责任，不删整份混合测试；`tests/helpers/gold_evaluator.py` 只在拆除 CLI 收据耦合确有必要时修改，保留真实评价算法。
- 新 `tests/unit/test_g5_legacy_checks_retirement.py`、`tests/integration/test_g5_legacy_checks_retirement_e2e.py`，本卡 PWF/交接。

**禁写：** `src/company_wiki/**` 全部，公共 CLI/acquisition/close_gap/code_identity；`scripts/common.py`、`config/**`、pyproject/hook/CI/总PWF；`tools/pre_push_gate.py`；G3/G4已交付实现、production/原件/外仓。尤其别混同旧 `scripts/architecture_gate.py` 与 `src/company_wiki/source_catalog/architecture_gate.py`；后者不在卡内。

发现 caller 超出白名单：交 `main_wiring.md` 中的准确路径/符号/变更理由和可复现反例，不跨线修改。MAIN同次完成工程清单/指导/指纹接线；没有引用就记 no_change，不为清理造新检查。

## 4. 实施步骤（TDD，完工一个集中节点）

1. 建本卡三 PWF；记原仓 status/有关 owner SHA、自己的基线/实际源码范围。列每个旧函数的 caller 与去向：retire / migrate test helper / preserve behavior。不要按文件名删掉 source-oriented 测试。
2. 先写行为 RED：六 CLI 的旧参数与 -S 在独立空 cwd 下应 exit78、无新文件/HTTP；import 时故意禁项目依赖仍应成功且零初始化；迁移后 helper仍剥离假 key/阻止dotenv，不读取真实凭证。
3. 实现纯 stdlib stub 和精确 writer_policy 类别；迁隔离helper和有关 import。删除 regex/source-count资格/候选整树复制专属测试，保留实际来源质量/失败传播反例；人工 receipt/固定来源数不再成为条件。
4. gold CLI专属“只允许artifacts/gates收据”测试改为退休零写；现有 pure evaluator/mutation 测试继续验证真实错误会降指标或拒绝输入。无需新增一套 quality service、签名schema或替代 Gate CLI。
5. 集中跑下节责任与真实子进程，正常静态/commit。交实际写集和 remaining；不要固定 pass 总数或重跑全契约/真实模型。

## 5. 测试包与恢复

开发只跑反例所属模块；完工一次集中执行新 unit/integration、保留的 hermetic/common/writer-freeze/legacy caller、gold evaluator/mutations。若某旧专属测试文件已正确退休则不把不存在文件传给 pytest。据最终文件集给出可直接复制的完整命令，不能写省略号。

E2E：六真实脚本 direct/main/import/-S；独立 tmp cwd 内放“若被写就失败”的小哨兵资料/配置；不把源码整树复制到候选。stub无生产路径、零 receipt/派生/HTTP/模型调用；隔离helper的 subprocess反例使用假 key。env/net能力只限测试，不能改变用户真实LLM配置。

短工作树测试根：先创建父目录 `.planning/test-tmp`，运行前记 `<工作树>/.planning/test-tmp/g5-checks` absent，pytest `--basetemp` 指这里。finally 等子进程/HTTP/DB退出后只删自己根（先核 absolute/包含/无reparse）；原先不存在的副本/下载/日志恢复 absent。`.planning/g5-cwp-checks` 小交接文件需提交，不能当 temp 删。不完整恢复备份，不加入日常长CI。

## 6. 输出接口、正常交付与 MAIN

在 `.planning/g5-cwp-checks/` 提交：`task_plan.md/findings.md/progress.md/HANDOFF.md/handoff.json/main_wiring.md/retirement_map.json`。retirement_map逐函数记录原位置、真实caller、处理、替代位置/反例，不是人工签收表。

`handoff.json` 必需字段：`schema_version="g5-handoff/1"`、`package_id="G5-CWP-CHECKS"`、`repo/worktree/branch/base_commit/implementation_commit`、`owned_files`、`public_contracts`、`tests`（命令/exit/pass/fail/skip/耗时与HTTP替换边界）、`protection`、`cleanup`、`main_wiring`、`remaining`、`delivery_status`。每项是事实或显式 not_run，不写自指 delivery SHA（从Git tip读取即可）。新行为至少说明实际 RED→GREEN；不能拿pytest setup错误当产品RED。

字段类型/列表结构见只读 [统一交接格式](g5_handoff.schema.json)。schema只规定交接格式，不是运行权限/人工审批；填实际40位commit和可回放命令，未知事实用not_run/null，不造计数。

正常commit；可推自己的分支（不能 master）。失败先查真实基线/工作根，不跳hook、不启长全套凑绿。MAIN收取完整提交历史，接不重叠工程清单/说明，再一次集中验收并 master发布、核精确代码CI、更新总PWF。其他族/完整G2-12未完要明确，不宣称全面门禁都已取消。
