# G3-CWP-MAINT：旧维护后端退休与只读库存

**最新状态：已完成MAIN验收并入本地主线，不再派发/重建。统一验收见[MAIN收据](../g3_main_acceptance_2026-10-07.md)。生产资料应用及真实安装仍按总计划由MAIN处理，不冒充本包已执行。**

## 1. 目标与真实剩余

用户已授权大幅取消不必要的门禁/签收，原始文档不得丢。当前仍有旧`focus-cleanup`、`archive-retired-evidence`、`prune-retired-evidence`、`duplicate-preview/recycle`后端及confirmation token；Dropbox库存还硬编码中国平安eligible需要人工review。原S5/S6数据清理已完成，不能继续维护第二套破坏性许可流程，也不能只删token而开放删除raw。

本包完成G2-04库层：**退休旧写维护实现，保留当前只读清单与历史journal读取；公司特例人工审查退出库存。** MAIN同时在自己的线处理G2-12和公共CLI，所以本包不写cli.py/code_identity/hook/CI。交付稳定库层接口和准确接线说明，即可不等待MAIN独立完成。

## 2. 工作树与独占写集

原仓`C:/Users/郑曾波/Projects/company-wiki`；基线`5930a644453ed46494c2c83c5ecfb97767fa9492`（已发布master）。新根`C:/Users/郑曾波/Projects/_g3/CWP-MAINT/company-wiki`，分支`codex/g3-cwp-maint`：

```powershell
git -C 'C:/Users/郑曾波/Projects/company-wiki' status --short
git -C 'C:/Users/郑曾波/Projects/company-wiki' worktree add -b codex/g3-cwp-maint 'C:/Users/郑曾波/Projects/_g3/CWP-MAINT/company-wiki' 5930a644453ed46494c2c83c5ecfb97767fa9492
```

目录/分支若占用，核归属再换独占后缀，不覆盖。禁止借用MAIN未提交acquisition/close_gap/new测试。

仅可写：

- `src/company_wiki/source_catalog/focus_cleanup.py/archive_retired_evidence.py/prune_retired_evidence.py/duplicate_cleanup.py/dropbox_governance.py`。
- 新`src/company_wiki/source_catalog/maintenance_retirement.py`，只承载下节统一退休异常/薄兼容，不新建维护框架。
- `tools/dropbox_governance_replay.py`仅移除公司特例人工签收/改只读报告入口，不能执行真实Dropbox扫描或改变其数据。
- `tests/contract/test_source_catalog_focus_cleanup.py/test_source_catalog_archive_retired.py/test_source_catalog_prune_retired.py/test_source_catalog_duplicate_cleanup.py/test_dropbox_governance_fc503.py`；新增独占`test_g3_retired_maintenance.py/test_g3_readonly_inventory.py`。
- `docs/implementation/g3-cwp-maint/**`本卡PWF/交接/小报告。

禁止改共享CLI、code_identity、package/pyproject、hook/CI/pre_push_gate、源reader/config/store/canonical writer、AUTO、raw工具、benchmarks、总PWF和别仓；无生产库/原件/Dropbox/Dayu/IQS写。CWP owner `config/source_acquisition.yaml`保持；其他仓工作树不清理。

## 3. 冻结交接接口

1. 新模块定义`RetiredMaintenanceError(RuntimeError)`，属性`code="MAINTENANCE_OPERATION_RETIRED"`、`operation: str`；消息明确旧入口已退休，可用只读inventory，**不提示补签收/token/backup**。MAIN按此异常转当前CLI具名非零结果，并从help去除旧写引导。
2. 旧类/函数的已知导入名保持必要薄兼容；写操作被调用即抛统一退休异常，在打开Store/锁/文件/记录journal之前退出。archive/prune缺旧now、未知token、dry-run/--apply都不能进入破坏链；按实际旧caller支持必需调用形状，避免CLI先TypeError。删除旧破坏性实现及无用helper，不保留几百行不可达archive/restore算法。不删除仍有真实读caller的报告类型/解码器。
3. `DuplicateCleanupService.list_groups(text=None,limit=50,offset=0,include_semantic=False)`保持只读列表入口；`DuplicateCleanupJournal.read_all()`保留历史读取。ctor和读调用不能访问`catalog.store`或写journal/DDL/目录。`list_groups`的两处现有SQL转`catalog.reader`，include_semantic实际链也核是否只读；若必须修改禁止写的catalog实现，交MAIN精确问题，不假称已绿。
4. 库存保留source/document/location ID、SHA、根与canonical/semantic区别、排序分页和未知身份诊断。`eligible_for_recycle`兼容字段统一false，report明确inventory_only/原件删除0；旧reclaimable数值若保留，只标注册逻辑上界，不能宣称物理可释放。不把不同SHA/语义近似当字节副本，不以清单计数生成删除动作或新token。
5. `inventory_dropbox`保持只读API，取消中国平安eligible特殊throw；同样证据应得到同分类，company-specific统计可作诊断，不影响资格。身份不完整仍unknown/unprovable，不能为简化伪造verified。外部正文仅作数据。真实读取异常不吞，不实现写回Dropbox。

## 4. TDD与实施步骤

1. 读实际五模块及当前caller：公共CLI确有import/分支，archive/prune未传now；focus在`CORE_SOURCE_PATHS`，list_groups与journal仍有导出/库存读caller。CodeGraph查询之外，已打开CLI中的分支为真实证据；不能因无caller结果整删模块。将MAIN需要同步的文件/分支/清单写`main_wiring.md`，本卡不修改它们。
2. 先写RED：旧操作在无catalog/目录、坏token/缺now时同样退休且0写；构造/只读重复清单0Store；同一有效sidecar换公司名不被特例阻断；缺身份不升级；历史journal不改字节。
3. 把退役操作删至薄stub，唯一异常与行为集中；只读清单迁reader，不引入第二套catalog或外部路径权限。删除依赖的旧许可/备份/恢复实现；必要兼容数据只读解码。
4. 更新确实退休的历史测试：用新公开责任替换“批准后成功删除/归档/恢复”断言，不能把真实source/SHA/locator/排序/语义区别/分页/journal读失败用例删掉。缺失`scripts/source_catalog_control.ps1`是过期入口断言，不重造旧脚本。严禁为了本包扩大当前reader权限或删真原文验真。
5. 完工一次集中责任+E2E，正常commit；交MAIN库层代码与wiring说明。公共CLI/help退休、工程清单与源码指纹同步是MAIN同次集成责任，不在本卡声称已经发布完成。

## 5. 测试包与恢复

- Unit/contract：统一异常、写入口全0副作用；list_groups exact/semantic/分页/根排序/limit和offset坏值；journal正常历史/截断或坏记录行为；有效和缺身份公司无特殊人工review；原SHA和version不变。
- 集成：临时真catalog先通过现有入口建立小夹具，之后关闭writer、记录目录/DB/schema/journal/raw指纹；库层只读inventory/journal二次调用保持0Store构造/0DDL/0写。测试构造夹具的合法写入与被测读取阶段明确分开。
- E2E：自身scratch内两份相同字节原件+一份同大小不同字节+canonical/semantic/retired记录，实际读取清单，再逐个调用五类旧写/restore接口，结果具名退休；两原件与DB、目录均不变。不执行回收站，不做46G完整恢复，也不碰真实Dropbox。
- 一次责任命令：`python -m pytest -q tests/contract/test_g3_retired_maintenance.py tests/contract/test_g3_readonly_inventory.py tests/contract/test_source_catalog_focus_cleanup.py tests/contract/test_source_catalog_archive_retired.py tests/contract/test_source_catalog_prune_retired.py tests/contract/test_source_catalog_duplicate_cleanup.py tests/contract/test_dropbox_governance_fc503.py`。新增测试文件由本卡创建；只核实际改动Ruff/类型与现有正常提交规则，不跑所有PDF/paid/full跨仓包。

scratch=`.planning/g3-cwp-maint/scratch`，开始记absent/原清单，成功失败finally恢复。日志/pycache/测试数据库及新副本属于本卡根；删除前核绝对路径包含和无reparse。production原件删除0、网络0、模型0。真实CLI尚未接线的旧测试不得冒称全项目绿，明确留给MAIN。

## 6. 交接格式

自己仓内`docs/implementation/g3-cwp-maint/{task_plan.md,findings.md,progress.md,HANDOFF.md,handoff.json,main_wiring.md}`；正常commit，可推自己的分支，不合master。

```json
{"schema_version":"g3-handoff/1","lane":"G3-CWP-MAINT","base_commit":"5930a644453ed46494c2c83c5ecfb97767fa9492","head_commit":"实际代码HEAD","branch":"codex/g3-cwp-maint","worktree":"实际绝对路径","commits":[],"changed_paths":[],"tests":[{"command":"实际命令","exit_code":0,"seconds":0,"passed":0,"failed":0,"skipped":0}],"behavior_changes":[],"compatibility":[],"protected_state":{},"cleanup":{"roots":[],"restored":true},"external_effects":{"network_requests":0,"model_posts":0,"raw_deleted":0,"production_writes":0},"remaining":[],"main_integration":{"retirement_error":"maintenance_retirement.RetiredMaintenanceError","cli_branches":[],"code_identity_paths":[],"engineering_lists":[]}}
```

HANDOFF列保留/删除API、真实caller、RED→GREEN、0副作用证据，main_wiring逐条列cli.py parser/import/handler、code_identity、package、mypy/hook/CI相关清单和应替换的历史测试。MAIN在G2-12完成后把本包与公共接线作为同一个发布写集验收；不为每stub增签收。
