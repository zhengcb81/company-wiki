# 实施者必读手册：小步执行、逐门独立复核、真实数据E2E

> **R4状态覆盖（2026-09-07）**：本文正文是R3历史方案/测试细节库，已不再作为活动执行队列。唯一活动编排为[R4实施计划](simplified-execution-plan.md)，测试见[R4矩阵](simplified-test-matrix.md)，原WP归属见[迁移表](r4-transition.md)。仅按迁移表继承领域步骤、反例与原始成果要求；不执行下文旧G0–G5依赖或95门DAG。历史review只签当时字节，本次新增状态头使当前文件hash变化，不能宣称旧签收绑定修改后文件。旧gate-dag.json及validate_execution_plan.py原样保留为R3历史工具，不用于R4验收。文档更新不授权产品实施。

状态：PLANNING_ONLY / NOT_IMPLEMENTATION_AUTHORIZED。本次只写文档；以下未来命令/产物/门均未执行。适用于较弱模型：一次只做一张卡的一个小步骤，不能凭常识补齐授权、真实样本、测试结果或版本号。

## 1. 文档权威与第一步

2026-09-07细化修订：G3受控真实进程测试与G4真实canary的不同准入以总计划R3第5.3节为准。WP06.G3不得要求尚待自身测试产生的S06，也绝不允许借此访问生产配置/DB/网络；隔离保证不足则blocked。各分手册的旧“R2”称呼指继承的DAG，R3隔离边界附加适用。

1. 用户当前授权/各仓AGENTS职责与安全边界最高；本手册不扩大它们。
2. 原始P01–P11/CA/ZR规定业务目标；[remediation-plan](remediation-plan.md)第5–6节规定精确门与授权；[gate-dag.json](gate-dag.json)是对应依赖展开，不是新的业务门。出现冲突停止并记录，禁止选择较宽松版本。
3. 任务分工：本目录编排三仓整改；v5目录独占worker版本合同/正式冻结和恢复协议；GP组保留历史批准/执行证据。WP06必须引用v5正式合同，不复制第二套。历史terminal/receipt/基线不就地更新。
4. 读[control-plane](execution-control-plane.md) WP00/11/12/14、[data-plane](execution-data-plane.md) WP01–07、[model-plane](execution-model-plane.md) WP08–10/13。全部是追加细节，不是互相可替代路线。
5. 首次实施前用户须批准DEV精确工作包及文件范围。建立未来独立实施run目录，不写回本审计证据；先完成WP00.G0/G1，再允许依赖门解锁的设计。不要一次同时“修15包”。

## 2. 每次模型接班的十二项核对（每次都记录）

| 顺序 | 必须做的检查 | 不满足时 |
|---|---|---|
| 01 | 用户授权证据、有效期、WP及当前G节点 | 停止，不把“继续”解释为网络/后台授权 |
| 02 | 重读本包task_plan/findings/progress最新checkpoint，区分计划与实际结果 | 找不到就读取原始run ledger，不猜上次做到哪 |
| 03 | 三仓完整HEAD、被测dirty/配置/schema/运行环境哈希与冻结baseline相同 | 漂移则rebaseline review，不覆盖别人的改动 |
| 04 | 当前步骤前驱门verdict及实际agent ID/hash有效 | pending/unknown/只有名字都不算通过 |
| 05 | exact allowed files/DB PK/source IDs，目标路径无越界reparse | 未解析/宽根/新增文件未经批准则停 |
| 06 | 当前动作分类及授权并集：manual/network/schedule/watchdog/delete/autostart | 不可归类默认deny |
| 07 | 输入真实来源manifest、预算、独立oracle、预期负例 | 缺数据保持blocked，禁止生成“像真的”文档 |
| 08 | argv/解释器/cwd/env允许键及输出路径已由G1审核 | 不直接复制旧部署命令，不试跑main或dry-run探权限 |
| 09 | 无副作用隔离边界与前快照已由独立operator确认 | 无确认不启动进程；无工具写unknown |
| 10 | 只执行一个步骤，保存原始stdout/stderr/rc/开始结束时间 | 不连串命令盖掉前一失败，未知结果先核事实不重试外发 |
| 11 | 后快照/输出/费用/测试与独立oracle逐项对账 | 一项越界即暂停，走已审恢复，不临时造回滚命令 |
| 12 | 写checkpoint：完成了什么、未做什么、下一个精确step、风险/需要谁批准 | 未获得独立review时节点保持review_pending，不自行推进 |

## 3. 每包run目录和必填合同

建议结构（将来创建，不是现在）:

```text
<approved-run>/WPxx/
  task_plan.md  findings.md  progress.md
  card.json  baseline.json  requirements.csv  command-manifest.json
  data-manifest.json  oracle/  tests/  evidence/
  reviews/G0.json ... G5.json
  checkpoint.json  rollback-contract.json  outcomes.json
```

card字段不得为空：wp_id/step_id/owner/implementer/independent_reviewers/原条款ID与hash/allowed_files/forbidden_paths/dependency_gates/integration_scope/authorization_refs/stop_rules。路径须绝对解析到获批隔离根；只给“Projects/*”无效。

command-manifest逐命令：真实entrypoint与源hash、python绝对路径/版本、argv数组、cwd、env键名单（秘密值不落盘）、输入hash、允许写集合、外发destination与字节/token/费用预算、timeout/子孙清理、预期exit与业务状态、证据路径、独立批准。没有实际可运行接口时先实现并审查接口，**禁止伪造现成CLI参数**。

checkpoint字段：三仓输入hash、last_completed_step、current_gate、pending_review、produced_files+sha、actual side effects、failed/unknown、next_step、需补授权；worker desired_state不作为进程存活证据。

review字段：实际agent/task ID、非实现者/非oracle作者声明、阅读输入hash/范围、独立命令与结果、逐finding severity/closure、verdict、时间。额度中断/未回复不是PASS；需换独立reviewer从同一输入接续，不让实施者代签。

## 4. 真实数据E2E资格：四层必须分开

| 层级 | 必须具备 | 能证明 / 不能证明 |
|---|---|---|
| D0诊断 | 合成fixture、mock/spy/fault、独立数学负例，明确标签 | 定位/验证拒绝机制；不能真实E2E |
| R1真实本地 | 已有真实PDF/HTML/报告raw字节+来源/日期/hash/locator；真实生产CLI/进程/DB schema在隔离副本；全调用链不替换 | 真实数据在真实代码链结果；不证明线上provider/生产部署/自然调度 |
| R2真实外部 | R1加当前批准真实provider/LLM/市场、真实响应/调用账本/成本；不使用录制响应或fake返回值替代外部阶段 | 当前获批case的外部链；不是无限后台运行授权 |
| R3真实持续 | R2或明确无需外部的真实case，加平台自然触发事件、正确SID/Action、真实时间与完整窗口、告警到达/ack | 当前组合自然运行资格；修改HEAD/config后重验适用门 |

已有来源本地只读解析属于R1，不必为“真实”再次下载。缺本地源只能记blocked或另申请获取，不能浪费性重下。网络失败不是算法必错，但不能计通过。SQLite一致真实副本可以用于R1；带真实业务数据不等于可直接写生产库。

### 每条真实E2E的强制证据包

- run_id/company_id/root_id/source_id/original URL或来源说明/reporting period/as_of/raw hash/size；三公司必须不同真实公司及不同原文，不改entity字符串复用一个document。
- 独立Data-Agent先建立source→页/表/cell→事实/单位/期间→预期参数的oracle，不导入被测提取器来造期望；模型数值由独立手算/Decimal核对，不能结果自勾稽。
- pipeline trace：真实identify→resolve/acquire→normalize→quality review→artifact→demand/attempt→export→parameter→engine→render/publication各段入口、输入输出hash与时间。明确无需运行的阶段及原因；不可跳过缺失阶段仍称全链。
- 独立观察：进程树/OS写与网络事件、DB审计/前后hash、provider账单或调用ID、实际artifact/registry可见状态，不能只信应用自己的calls=0。
- 正向第一次、exact第二次零download/parser/LLM、单source/policy/parser/prompt变更的最小失效；多root/多period/amended/partial/missing/safety拒绝；失败重试账实一致。
- 每case单独verdict：source缺失、字段缺失、安全拒绝、未授权为明确终态，不用总体7/7掩盖。安全拒绝可证明负例正确，**不算所拒绝正向能力已交付**。
- 清理/恢复限定隔离输出allowlist，保留原始失败与费用事实。不得以“测试结束”删除生产数据或复位worker。

## 5. 审查安排与停止条件

每个WP每个G0–G5均有独立agent，详见总计划；小步骤内的检查点失败会阻止进入下一个步骤，即使还没到阶段末。G1先审oracle，G2审每个小批diff和caller，G3第二checkout独立重跑，G4每真实case/每1→3→7放量节点独立Ops签，G5逐原目标证据资格。实施者永不自审；允许同一独立人跨门但G5不得原oracle作者，不能用换名字伪独立。

硬停止：越root/PK/cohort写、未经批准外发、未知费用、bad source/hash、lease fencing失效、真实source被mock替换、必需测试skip、工具无输出却rc0、基线漂移、超timeout无法取消、归档恢复集合不一致。先停止当前获批进程并核实际状态（停止动作亦按操作卡），记录故障；不得为了“跑绿”删case/抬门/生成新golden/忽略安全拒绝。

纯文档审查与机器计划校验可在本轮执行；产品测试/E2E本轮**全部未执行**。将来若真实数据、工具或权限不足，交付局部修复加blocked清单，不谎称整体完成。不存在让弱模型绝不犯错的保证；本手册通过明确定义、独立门和禁止静默降级降低跑偏风险。
