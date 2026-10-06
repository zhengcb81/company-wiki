# S6：当前入口、门禁与运维说明收尾

## 2026-10-06 施工范围

RF main与origin/main均6e6b817a，两份owner日志SHA未变。本节点只写company-wiki代码/文档；原件、来源库、用户source_acquisition配置及外仓不改。生产存储清理已完成，不再重复执行。

实读发现README仍推荐冻结的collect_news/ingest与旧MiMo模型；来源目录说明还称derived/span未清；control目录仍要求独立Reviewer与人工lock；两个无调用者的旧cron包装器忽略子命令失败，最后echo导致假成功。pre-push精选里四项仍验证退出生产的全文producer。

## 实施顺序

1. 查当前命令help及正式合同，重写README、OPERATIONS、architecture，更新source-catalog与AGENTS的目录/provider/并发描述。旧GATE_SYSTEM、使用说明书、legacy-caller审计明确标为历史；不复制历史归档，Git保留原文。
2. 实际调用者核查无引用后，移除control中的acceptance/lock/known_bad/work_units/full-pytest旧文件；architecture的旧proposal人工审批、冻结writer强制接线和全scripts零文件写入规则退出，只保当前配置/有限runtime接线和上游不依赖下游检查。移除无调用者的run_collect/run_download壳；不删自动来源/SHA/原件/预算/lease校验。
3. 用当前叙述证据、引用回放、语言或检索的快速行为测试替换四个旧producer smoke，不新增日常测试量；保留曾实际CI回归的六项、无人工review诊断和read-chain测试。扩展测试只在本节点运行一次，不把全Contract加回commit/push。
4. 大节点验收：当前公共help、有关职责/冻结/门禁策略测试及更新后的同一fast smoke；隔离测试根finally恢复原样。文档链接/代码diff/配置SHA一并核对，正常commit/push，代码精确SHA CI绿后S6收尾。

## 交接与完成标准

现行说明只指向实际受支持的入口，不宣称未完成的N4C真模型批次、自动failover或live FMP导入。下载开关区分只读与明确有界获取，不变成人工签收门。当前维护资料只留机器行为约束；历史文档不再发出开工/审核指令。S6完成后下一步N4C，累计token预算答复仍独立待定，不冲销旧未知usage。
