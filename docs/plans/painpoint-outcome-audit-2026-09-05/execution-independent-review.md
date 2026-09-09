# 详细实施手册独立审查

日期：2026-09-07；审查者：sync_review（当前独立子任务）。本文件仅审计划与同步，不代表任何产品测试、真实E2E或实施已通过。

## 阅读与范围

完整读取 execution-handbook.md、execution-control-plane.md、execution-data-plane.md、execution-model-plane.md 及 remediation-plan.md 第5–6节。组合输出曾截断，已用单段补读08.10等缺口与文件尾；四手册均有完整结束段，未发现用量中断导致半句/半包交付。覆盖15包：控制面00/11/12/14，数据面01–07，模型面08–10/13。

已复核三仓PLANNING_STATUS、wiki四CURRENT_STATUS、archive状态、v5 README、filing E2E入口，以及GP七文档（含新ci_root_fix.md）均有9/6当前覆盖。冻结历史不逐段改写，通过外部入口解释；本复核不扩张为再次全文阅读全部历史文档。

## 初审结论：changes_requested（下列修订待回读）

### P1-EXEC-01：WP06.G3实际worker测试与自身S06门冲突

数据手册WP06 step08要求G3启动“实际产品CLI/单worker受控进程”；准入及总计划§5.3却要求真实worker动作先有S06，而S06定义为WP06.G3独立安全签收。按严格字面会自等；弱模型也可能把“隔离”理解成可跳安全门。WP04 step07“A/B/C独立进程”亦需说明不能在尚未通过WP06时偷偷启动实际worker。

要求：冻结明确的测试启动专属scope，或把实际worker运行移至G4。若选隔离测试scope，至少需WP01/02/04/05.G3及其安全签、v5版本/冻结合同、独立命令卡、DEV明确授权隔离测试进程、目标PID/目录/DB限定、LLM_OFF、自动prune=0、禁止生产路径/任务/自启动，且只证明S06能力不形成生产授权。必须同步总计划、手册与机器DAG，不能只在一处加例外。

### P2-EXEC-02：WP09.G1真实manifest与WP13隐性互等

model step09.03要求从“WP08/13真实manifest”选择，而WP13.G0依赖WP09.G1。虽可能只是复用数据，不是正式门边，但弱模型易等待WP13材料才完成WP09。

要求：本包G1独立建立真实source manifest，可复用已存在合格来源，不依赖WP13进度/签收；后续WP13引用本包输入。矿业真实执行继续按WP08.G3附加门，不降低数据资格。

## 已满足的设计要求

- 每包G0–G5明确独立agent角色、输入hash、oracle、逐小步检查点、停止与恢复；中断/未回复不算PASS，实施者不得自签。
- 真实数据资格区分机制fixture、真实本地、真实外部、自然持续；原字节/来源/locator/期间/单位、实际CLI和进程、独立数值oracle、独立OS与外部调用对账均明确。mock、手写pages、同公司改名、预填成功JSON、状态pass不能抵真实E2E。
- 三公司、四root、1→3→7、二次零调用、单角色失效、发布恢复、实际历史origin和自然7/2/1/1分别验收，不用总产物数替代。
- WP12a→WP13.G5→WP12b→12c→WP14分段避免原soak互等；缺真实样本和权限保持blocked，不逼迫补造证据。
- DEV/CANARY/AUTOSTART、network/manual/schedule/watchdog分开，旧批准不自动扩大；禁生产数据破坏、额外外发和默认启动。归档精确集合及不可撤销费用边界明确。

## 尚待独立复核

主协调者将补机器DAG/validator及上述delta；这些工具只验证计划结构，不证明产品门已通过。最终verdict在回读修订、检查机器结构和当前路由后追加，不覆盖本次changes_requested历史。

本轮读取中PowerShell对rg路径通配符报os error123，后改为Get-ChildItem精确枚举后核对；没有运行产品、下载、SQLite、worker、任务或修改其他文件。

## R3 delta最终复核：accepted_for_planning（2026-09-07）

已回读总计划R3 §5.3、handbook追加说明、data WP04/WP06修改及model09.03。P1-EXEC-01已闭合：WP06.G3明确隔离受控测试许可、WP01/02/04/05.G3与独立G1安全卡，OS禁止生产写/网络、全部路径隔离、无生产控制文件/调度/自启动、LLM_OFF/自动prune0；无法保证则blocked。其结果才形成S06，G4不得继承隔离许可。WP04机制进程明确不是worker loop/parser/LLM。P2-EXEC-02已闭合：WP09自己建立真实manifest，不等待WP13。

完整读取新增validate_execution_plan.py及结构化展开全部95门/作用域规则。独立执行 `python -B docs/plans/painpoint-outcome-audit-2026-09-05/validate_execution_plan.py`：exit0、passed=true、95门（90阶段review+5安全review）、15包、cycle/unknown/empty三个负例均拒绝、13链接存在、errors=[]。人工核关键边与§5.2相符，12a→13→12b→12c→14无环。作用域安全门是附加规则，不是主拓扑输出自动执行；本脚本明确不验证操作授权、实际case资格、生产侧效或自然时间，不能当运行放行器。未来G1仍须实际操作级授权/安全祖先验证器及相应RED，当前结构PASS不能抵其结果。

补核v5活动三件套和旧planning-sync三件套都有9/6覆盖。GP新增ci_root_fix.md仅观察到现行覆盖，来源为并发任务，**不是本主协调者或本审查者所写的同步成果**。未发现已核活动入口遗漏；冻结历史与不可读临时范围不扩张为全文重审。

签收仅指本次新增细化计划与R3修订可作为后续授权、设计冻结和实施输入；不是实施授权、v5正式冻结通过、产品验收或worker恢复批准。所有产品门保持pending。本审查者仅写本文件和前次document-consistency-review，没有产品副作用。

### 最终审查输入SHA-256

| 文件 | SHA-256 |
|---|---|
| execution-handbook.md | acc0cff7319d4ddc3ede5210aaadafde5362c25f1274f9697d25861c14bf1a35 |
| execution-control-plane.md | d5403f00348e63f5492fccb210b10e4e5d1fcec1139e92d8882b11c746c9b09b |
| execution-data-plane.md | 916a4a331cb74b4c18179046be7b11bd5a482f7bfa3f9f6f43984b492d736136 |
| execution-model-plane.md | 28c958673cffb6dfefbb2577c1927718fb6d3b2ad5b6818816ddfdae1d29628d |
| remediation-plan.md | 168ba61f1b2f29d333c0f787efca5d65c31bde70c78fff41b3ff16293d9ecd4b |
| gate-dag.json | 51e5e278c256369c4832f6c3b1063281e9928f6c50d3124042f279f137937afd |
| validate_execution_plan.py | 7b02b17f3548ba7fcec836b1cddc59a3b007322baa27cce1283503d42d7f39e1 |

## 9/7并发事实覆盖独立核对

已读取current-delta-2026-09-07.md、最新daily_manifest/report、两个legacy_periods原始JSON及revenue `git diff 2ff20d9 6682ecf`相关源码/文件状态。结论：delta表述与这些原始证据一致，没有把其他任务动作追认为本审计实施或获准验收。

- latest_run_id=20260906T210001Z、period3、ok=false、三仓triplet为空；report同样记录空HEAD/manifest_missing。不能把observer推进视作T2整体成功。
- revenue JSON有两个ended_at窗口且close_allowed=true；wiki JSON保留历史period1–6且close_allowed=false。源码DEFAULT_PERIODS从revenue路径改到wiki路径，证明当前默认选择改变，不证明迁移连续性/观察质量已获验收；不能混用两ledger绿灯。
- Git确证删除4旧工具与5测试，quality旧closure step移除，并新增pre_push_gate/ci_root_fix；daily Git命令加单次safe.directory=*、Dropbox改用Projects上级推导。此处仅证实diff，不认为宽白名单安全或新自然运行已正常。
- delta明确不重复删除、不恢复旧工具、不依据日志追认授权，原目标与未来G0重取证要求保留。7份已签手册不因运行事实变化自动视为新版本产品通过。

这次仅追加事实同步检查，未重审7份手册、未运行产品，也未查询任务或触发任何进程。当前路由的覆盖存在性由主协调者最终文档校验负责；本审查直接核的是delta与上述Git/JSON事实的一致性。
