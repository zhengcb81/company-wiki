# 主线接手指南 — 暂停，候选未验收

只看[CURRENT_STATUS](CURRENT_STATUS.md)/json与本文件恢复，旧施工日志不覆盖当前暂停。当前整合失败，不得把Q01–Q14小域GREEN当稳定主线已整改。

## 第一件事：隔离返修，而非真实公司重跑

1. 选择`PLAN_ID=du11-source-closure-2026-10-18`、`PWF_PLAN_ROOT=docs/plans`；读[收尾](review/architecture-quality-20261101/implementation-results/pause-closeout.md)、[整合失败](review/architecture-quality-20261101/implementation-results/CWP-failed-CI.md)与[台账](review/architecture-quality-20261101/implementation-results/STATUS.json)。用户恢复前不实施。
2. CWP候选`6668bc978d3ea2217a9aff30be69bde456894c04`已在远端`codex/architecture-rectification-20261101`保留，工程runtime c97d4fbd；完整CI41305132919为FAIL/63项，公开annotation4096字截断，日志API403，未取Git缓存凭证。不能认为63项全是测试债或全是63独立缺陷。
3. master安全隔离revert为`dbfec3beb0948006475701e2131c4d95e0586556`，源码/测试/依赖树与1909286a一致。**未来从最新master建新的隔离修复branch，在该branch正常revert此隔离commit以重施候选，再修复。不要在master直接重施；不要只merge旧candidate branch，原commit已在祖先且已被revert，merge不会重施完整改动。** 不用reset/clean/force或恢复原件备份。
4. 按共因优先修旧接口消费/层边界、迁移版本语义、经营相关性/套话财务负例和Linuxoffline失败。先在正确owner明确真正行为，再写去公司化正反例，区分公共兼容责任与测试耦合私有实现。禁止公司/ticker/页码名单、增加额度、任意修改expected或恢复跨层reader耦合来换绿。
5. 跑受影响快速域；独立大节点审查后对master的PR触发**一次完整unit/contract CI**。现有CI仅master push/PR，旧candidate branch直接push不会自动产生完整CI。全域绿后才并线，不新增逐小节点许可或每commit全量测试。
6. RF957c6283向后兼容wire扩展已main/origin、精确CI41304681319 success，2物理/3逻辑单runtime安装、repeat0/fresh进程通过；保持该结果，其他技能drift不覆盖。StockWiki381811e5本地已并线，历史无remote，不擅建仓。

## 整合通过后才继续来源/C真实验收

在structure owner修带收尾引号的编号完整句/真正“备注N”标题和actor scope，参考[R4-context-investigation](review/architecture-quality-20261101/implementation-results/R4-context-investigation.md)，保留原文/locator，不提高16M/112。当前只是调查，产品/测试未实施。

冻结最终源码/oracle，使用`.planning/architecture-quality-20261101/real-acceptance/`的schema2 runner单次H1 canonical handler、90s有界，核12原文unit、全部native成员ID/SHA/坐标及9context配对当前view/member索引。v1旧代码12/111不代最终版本；v2 handler失败23.170s保留。原字节输入快照与小收据在[real-source-receipts](review/architecture-quality-20261101/implementation-results/real-source-receipts/README.md)，无PDF/DB备份，不在archive路径直接执行runner。

DB/WAL/原件bytes与mtime严格相同；SHM仅相同存在/size/SHA下允许mtime同步。观察不可实例化生产AutomationStore（构造会迁移）。SourceRef经owner读取原件，不复制PDF/旧DB。两旧P1临时配置已absent；C-preparation规定新的独立catalog/AUTO引用原件，不能冒原地可复跑。

来源通过后做新正式摘要、prepared中断恢复、same/cross-run零追加、RF参数/公式/报告/snapshot实际采用及独立经济检查，旧sealed artifact不能冒新版本结果。只在实际输入变化时按配置付费；未知费用保留。

## 原目标与隔离边界

AUDIT根`C:/Users/郑曾波/Projects/revenue-forecast-audit`，RUN `runs/r1-20261021-cn-wuxi-apptec`，attempt `r1-remediation-04`。四报告在reports同attempt，六issue映射在diagnosis，内部细则唯一为remediation同attempt/implementation.md。R4封存585件64240251B/manifest75f2871b…c568不改。原ghost-formula预检/signed期间补集、scope真实记录/质量/检测演进仍OPEN；72实际argv/output为R4，旧R3只是描述，不为它收费重跑。ET unsupported、Q&A时点和独立经营幅度/持续性未知不编数。

账1965633tokens/762082microUSD估计、unknown8+prior7不变。预算config10M/$20、公司150k/$1软目标。宿主`C:/Miniconda/python.exe -B -X utf8`，定点部署沿canonical installer不改ACL。原件/生产配置/旧R3/R4、RF四assurance WIP/CWP hook mode/未审定历史产物保留；Dayu/IQS/Dashboard不动，不扩包。所有agent已STOP，native goal paused，不标complete。固定八家、泛化、同有效版本三家clean和W21等全部责任继续保留。

## 唯一下一步

用户恢复后从最新master建立隔离修复branch，先正常revert安全隔离提交dbfec3beb0948006475701e2131c4d95e0586556以重施候选（不得在master直接重施），按CWP-failed-CI.md先修整合回归的共用根因。受影响快速测试/独立大节点审查和PR完整CI绿后并线，再修note结构并做最终H1/新摘要/恢复/RF验收。当前不执行。
