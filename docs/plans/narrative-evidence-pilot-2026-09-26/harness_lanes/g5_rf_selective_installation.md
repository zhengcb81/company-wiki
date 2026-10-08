# G5-RF-INSTALL：定点安装同步与失败恢复交付

<!-- CURRENT_PWF_NAV -->
> **历史施工/调查材料：**当前状态与唯一下一步见[总计划](../task_plan.md)。下方旧待办、暂停、人工签收和预算只是当时记录，不自动恢复；R3/R5的真实剩余范围以总计划为准。

**当前状态：complete，MAIN已验收、并线并推送（2026-10-07）。** 不重新开工；原卡冻结输入、写集和工作树命令仅为施工历史。实际交付/当前测试、兼容接线、真实安装和未做范围见[MAIN验收](../g5_main_acceptance_2026-10-07.md)。下文原ready/未创建/paused说明不覆盖本结论，三个交接工作树保留。

## 1. 冻结项目与独占目录

- 原仓 `C:/Users/郑曾波/Projects/revenue-forecast`，main，基线 `ab7a7a4434bbb4c52a5bd2a6cd6ed710d7151eee`。
- 新目录 `C:/Users/郑曾波/Projects/_g5/rf`，分支 `codex/g5-rf-install`，发卡时未创建。
- 原仓3个owner日志 `assurance/runs/{daily_alert.jsonl,weekly_alert.jsonl,weekly_manifest.json}` 保持；不复制未提交资料。

```powershell
git -C 'C:/Users/郑曾波/Projects/revenue-forecast' status --short
git -C 'C:/Users/郑曾波/Projects/revenue-forecast' worktree add -b codex/g5-rf-install 'C:/Users/郑曾波/Projects/_g5/rf' ab7a7a4434bbb4c52a5bd2a6cd6ed710d7151eee
Set-Location 'C:/Users/郑曾波/Projects/_g5/rf'
```

占用先核归属/HEAD；不reset。PWF唯一 `<工作树>/.planning/g5-rf-install/`，`PLAN_ID=g5-rf-install/PWF_PLAN_ROOT=<工作树>`，用resolver读本处三文件，不造docs镜像。原仓无AGENTS.md，按适用父级/技能规范，不猜文件。

先建缺少的三PWF，再在本工作树设置两项独立env并解析：

```powershell
$env:PLAN_ID='g5-rf-install'
$env:PWF_PLAN_ROOT=(Get-Location).Path
& "$env:USERPROFILE/.agents/skills/planning-with-files/scripts/resolve-plan-dir.ps1"
```

先读：本卡、`tools/sync_installations.py`、`tools/tests/test_sync_installations.py/test_g3_skill_package.py`、G3 `docs/implementation/g3-rf-assurance/MAIN_ACCEPTANCE.md`、SKILL以及runtime file-set说明。G3的闭包、JSON合同、预测与来源规则不更改。

## 2. 真实调查与范围

MAIN零写 `installation_diff` 已核：`.agents/.claude/.codex/skills/revenue-forecast`各8个runtime差异，config差异0。每份相同8文件：

```text
.gitignore
SKILL.md
agents/openai.yaml
references/extended-models.md
references/input-construction.md
references/model-library.md
references/schema-migration-3.6-to-3.7.md
scripts/revenue_forecast.py
```

共24个实际更新候选。当前工具`--apply`仍先stage所有owned runtime再逐个replace，未提供指定文件模式，帮助文案还称atomic whole-skill。它是逐文件原子，并非三安装/整个package同时原子；无需为此造全局签收服务。

实现既有工具的**显式文件范围、零写计划、仅差异写、准确partial失败与幂等续跑**。保留unknown/output/config、当前runtime闭包和旧API。实际三份定点更新由MAIN收到合入版本后执行，不提前覆盖home安装。

## 3. 独占写集

可写仅：`tools/sync_installations.py`、`tools/tests/test_sync_installations.py/test_g3_skill_package.py`、新`tools/tests/test_g5_selective_install.py`、自己的PWF。

禁写：`scripts/**/config/**/references/**/agents/**/SKILL.md`等shipped runtime与公开预测/来源合同；RF hook/CI/prepush、实际home安装、owner日志、CWP/FF/ET/SID/Dayu/IQS、总PWF。`tools/sync_installations.py`只在仓内，是安装维护工具，不能加入runtime manifest或复制tools/tests到用户技能。

## 4. 小接口的确切行为

1. 在既有CLI增加可重复`--file <relative>`，增加`--plan`零写JSON输出以及`--json`供check/apply输出下面result；兼容原默认check/`--print-manifest/--apply/--import-from`，保持现公共函数旧位置参数可用。`--plan`与apply/import/print-manifest互斥；`--file/--json`不与import-from/print-manifest混用，错误参数在任何写入前拒绝。plan本身总是JSON；各JSON模式stdout仅一个值，诊断stderr。不要引入authorization/binding/approval/expiry文件。
2. file范围必须属于`installable_files(canonical)`，去重/排序；拒绝absolute、..、超闭包/目录/逃出target的symlink/reparse，拒绝真正坏输入不是人工权限。所有scope先验证，错误时零写所有destination。
3. 没有`--file`时保留完整runtime check和显式apply的原义；有file时check/apply只对选中集合，未选中drift如实诊断但不能使已完成selected同步错误失败。不能在subset完成时输出整个runtime MATCH。
4. plan针对每个target/relative输出operation(new/replace/unchanged)、before_sha256或null、source_sha256、size；schema `rf-install-plan/1`，每target含selected_drift和unselected_drift计数。plan是机器事实，不是签收/资格文件；不用提供plan文件才能apply。默认missing安装“不漂移”的旧check语义保持；显式plan可把选择文件报告new。
5. apply只stage/write真正不同的selected文件；相同bytes的文件mtime/size/内容不变，无临时copy。source/target在本次操作中改变需现场核SHA后明确冲突，不根据曾生成的plan覆盖新用户改动。checks是实际字节并发正确性，不是人造policy hash。
6. 每文件os.replace原子；失败返回非零、报告已写/未写/冲突清单，不报全成功，不承诺整批回滚。不完整恢复备份、不建第二事务库；再按当前实际差异重跑，已完成文件不再改、余文件收敛。只清自己stage/.syncing；不能清glob中其他进程文件。
7. 输出`rf-install-result/1`可选择JSON，含target/selected/written/unchanged/failed、remaining_selected_drift、remaining_unselected_drift、status=completed|partial|failed；旧默认人读check可保持。`--plan`的JSON schema和selected成功退出码必须有测试。隐式同步仍不允许用户运行预测时发生；只是显式工程工具。

## 5. TDD与一次集中测试

先写RED：实际CLI选两个files时不支持/仍改其余file；重复同步会改相同bytes文件的mtime；复制故障partial误报/临时残留（若某项旧版已正确则记已有GREEN，不伪造RED）。先框上述行为，再最小扩展现工具，不另写installer。

unit：scope规范/排序/重复、未知路径零写、missing target、selected与unselected退出码、plan零write/不造目录、同bytes不replace（mtime证据配合spy，不靠sleep）、source/target读取后变化、失败准确写集及自己临时清理、rerun只补剩余、output/用户config/工程残留保护。

E2E：三个**tmp**安装根，用Git导出的冻结runtime建立闭包，再把这8个文件制造与真实调查相同的drift（明确是合成差异，不称真实安装已更新）；另外置未知用户文件/config/output哨兵。真实 `python tools/sync_installations.py --canonical <冻结runtime> --destination <三个tmp父目录> --file ... --plan`零写；apply每根只写8差异；第二次写0且mtime不变；插入一次受控replace/权限错误报告partial，重跑收敛且哨兵完整。之后实际installed `scripts/revenue_forecast.py --help/--version`应运行，不能从原仓PYTHONPATH偷导入。

参考集中入口（依实际新增名字保持本卡文件名）：

```powershell
python -B -m pytest -q -p no:cacheprovider tools/tests/test_sync_installations.py tools/tests/test_g3_skill_package.py tools/tests/test_g5_selective_install.py
```

真实home只能只读stat/SHA/文件名计数，不展示配置/凭证正文；不把真正用户安装当pytest fixture。实际drift若不同于8个则报告事实，不扩大live更新名单。原3日志SHA前后相同。dev跑有关反例，完工一个集中unit/CLI节点；不全UC、不paid/live、不扩coverage/CI门。若正常prepush需邻仓，使用既有`FF_V2_CODE_ROOT/CWP_V2_CODE_ROOT`显式已提交只读入口，不删检查凑绿。

新短root `<工作树>/.planning/test-tmp/g5-install`先建父目录/记absent；child退出后finally只删owned临时installed/copied/PDF/SQLite/log，原不存在则恢复absent。小PWF交接提交，不复制整备份/工程包到home。

## 6. 交接与MAIN应用

唯一 `.planning/g5-rf-install/`交三PWF、`HANDOFF.md/handoff.json/main_wiring.md/install_delta.json`。install_delta逐target/这8个文件记录live before/source SHA与size、canonical commit、预期更新范围，未知文件/配置只记保护方法；不包含密钥正文，日期事实不是有效期门。

handoff统一`schema_version=g5-handoff/1/package_id=G5-RF-INSTALL`，字段`repo/worktree/branch/base_commit/implementation_commit/owned_files/public_contracts/tests/protection/cleanup/main_wiring/remaining/delivery_status`；tests记录完整命令/exit/耗时/实际RED-GREEN/skip/替换边界，说明三tmp安装与真实三份尚未同步的区别。不得自指交付SHA循环提交。

字段类型/列表结构见只读 [统一交接格式](g5_handoff.schema.json)。plan/result与handoff是不同schema；前二者是工具实际JSON输出，后者是工程事实交接，不作人工许可。

正常commit，可推codex分支，不自行并main或apply真实home。MAIN收取后集中验收/并RF main/精确CI，现场复读3×8差异，将已发布代码按24条范围定点同步（原config/output/未知文件保留），核真实技能入口再更新总PWF。该应用不要求新review receipt；若发生本机工具审批，说明准确24文件事实和既有授权，由MAIN处理。不在本卡假称生产预测已运行，不影响其他两卡。
