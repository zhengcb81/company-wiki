# G3：第二批独立施工包

**当前状态：三个G3包均已完成MAIN验收和本地主线并入，不再派发。** RF已正常推main，CWP正在发布；[统一验收](../g3_main_acceptance_2026-10-07.md)列准确代码/测试/CI与剩余。公共CLI和tmp包装MAIN接线已完成；真实技能安装与生产metadata应用不包含在本批，G2-12保留未提交，总目标paused。


**最新状态：三工作树已实际建立，RF/SOURCE-FACTS已有独立task_plan，尚未发现完整交接。不重复派发、不重建其目录；原卡的实现边界继续有效。** 创建时ready/未启动属于历史，不推断代码已完成。新增可分派包见[G4](g4_parallel_packages_2026-10-07.md)。

2026-10-07从当前PWF真实剩余拆分。旧G2-SW-DAILY、G2-SQA-CHECKS、G2-RF-TOOLS均已完成并线，不重新执行。本批不是新阶段门：代码包并入原G2 A/B大节点；调查包分别供应R2/R4，生产应用仍按G2→R2→R3→R4→R5顺序。

## 1. 单卡、目录与写入隔离

| 单卡 | 任务规模/交付 | 施工目录 | 冻结基线 |
|---|---|---|---|
| [G3-RF-ASSURANCE](g3_rf_assurance_and_packaging.md) | RF历史质量工具、checkout时间误拒、技能包装职责；代码+离线测试+交接 | `C:/Users/郑曾波/Projects/_g3/RF-ASSURANCE/revenue-forecast` | RF main `1a2f9428a599504eb8355fcaebf86c6cbcaccbb3` |
| [G3-CWP-MAINT](g3_cwp_maintenance_retirement.md) | 四类旧维护后端退休、只读重复清单、取消Dropbox公司特例审查；代码+责任测试+CLI接线说明 | `C:/Users/郑曾波/Projects/_g3/CWP-MAINT/company-wiki` | CWP master `5930a644453ed46494c2c83c5ecfb97767fa9492` |
| [G3-SOURCE-FACTS](g3_source_metadata_and_raw_space.md) | 九类真实文档来源事实/retired原因、CWP内部原件重复收益；只读工具/证据/小范围迁移提案 | `C:/Users/郑曾波/Projects/_g3/SOURCE-FACTS/company-wiki` | CWP master `5930a644453ed46494c2c83c5ecfb97767fa9492` |

三根互不包含，三个分支分别`codex/g3-rf-assurance`、`codex/g3-cwp-maint`、`codex/g3-source-facts`。后两卡虽然同属CWP，使用独立工作树，允许源码/测试/报告路径也不重叠；都不写MAIN的CLI、指纹、hook/CI和总PWF。SOURCE-FACTS不会更新生产库，也不会构建第二套source目录或全文切片库。各单卡包含完整上下文，单独交给harness即可。

## 2. 主线与外线的接口

MAIN独占CWP `acquisition.py/acquisition_service.py/close_gap.py/cli.py/code_identity.py`及其当前G2-12测试、FF接线和技能安装、生产目录/数据库、共享PWF、主线合入。G3-CWP-MAINT提供库层稳定退休异常与兼容读API，MAIN再接公共help/CLI与工程清单；该包不等待MAIN，只需自己的库层责任绿。G3-RF-ASSURANCE仅在自己的tmp安装根验证包装，实际三技能副本由MAIN发布后定点处理。SOURCE-FACTS提供数据提案与可核事实，MAIN在R2通过正式有限登记入口应用，不直接UPDATE、更不复活retired。

公共SourceRef/SourceExport v2/NarrativeRef不变；不新增权限、人工签收、授权token或新队列。库层实际读取/输入坏字节、来源身份、期间、公开日、locator、资源上限与工具真实退出码仍由责任层检查。

## 3. 开工和验收规则

1. 各卡先核原仓HEAD/status；从表中已发布commit创建自己的新worktree。基线之后有不相关已发布推进不必等待，但记录实际base。目录/分支被占用则选择新的独占后缀并报告，不能覆盖或reset。不要复制MAIN未提交G2-12代码作基线。
2. 代码包先行为RED再实现；调查包先把报告/schema/只读与计量反例写好，再跑真实核实。提交只便宜静态，开发只测责任包，每卡完工一个集中节点。MAIN并线一次核写集/责任，再接入原G2大节点；不增逐小步检查。
3. 单卡自己的`task_plan.md/findings.md/progress.md/HANDOFF.md/handoff.json`均位于自己的`docs/implementation/g3-.../`，不改本目录总PWF或别卡。JSON若被*.json忽略，只精确add本卡机器交接，不能因此修改owner .gitignore。
4. 测试根在本工作树`.planning/g3-.../scratch`；成功失败均finally恢复原状，明确absent/原清单。原件0删、测试新下载/副本结束删除；不进行全库备份恢复、广域clean/reset或未核绝对路径的递归删除。
5. RF原仓三日志、CWP owner `config/source_acquisition.yaml`均保留。StockWiki/StockQA已有其他owner线程，不分派；Dayu/IQS零写；SID未提交工作不介入。模型POST/收费/翻译0；SOURCE-FACTS可公开网页只读查询，响应与总量有界。
6. 代码/小报告正常commit；有remote可推自己分支，但外线不合主线、不安装到用户目录。每卡交付真实命令/exit/耗时/RED→GREEN/写集/剩余项，不按固定pass数量、coverage数值或旧签收判断完成。

## 4. MAIN接收顺序与剩余计划

MAIN继续G2-12：旧测试、期间语义、可选binding CLI、FF和跨进程/离线契约联调，集中发布。两代码包哪个先完成就先核交接，CWP-MAINT与MAIN CLI/hook/指纹同次接线发布；RF包装测试只在隔离根运行，实际安装不整套覆盖。随后G2其他退休家族及A/B→R2应用SOURCE-FACTS事实→R3正式有限摘要/消费者→R4依据真实内部收益作决策→R5压缩PWF与发布。

SOURCE-FACTS可先完成R4调查，但不自动提前执行迁移或删除；没有证明收益也可以按证据得出不迁移，不能用调查结束冒称R2生产已改或R3 final已产生。三个包互不等待；只有最终主线接线和生产应用由MAIN串起来。

## 5. 交接最低字段

各单卡重复给出可独立执行的格式：`schema_version=g3-handoff/1`、lane、base/head/branch/worktree、commits、changed_paths、tests（实际command/exit_code/seconds/counts）、behavior_changes、compatibility、protected_state、cleanup、external_effects、remaining、main_integration。不增加签名或trust TTL。SOURCE-FACTS另交metadata_proposals.json、raw_space_decision.json及证据索引，缺事实明确unknown/conflict。
