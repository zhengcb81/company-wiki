# N6 MAIN：最终业务E2E施工细则

## 当前状态与边界

上一目标回合为progress：冻结兼容测试/33点业务解释已提交并推，0947cea精确CI80秒绿，文档ccd9589已推。当前RF main仍6e6b817a；owner dirty新增daily_alert.jsonl，连同weekly_alert/weekly_manifest保护，不能恢复。N6三worktree仍为已分派bootstrap，未收到完整交付，不声称有确认live进程。

MAIN独占新增tests/integration/test_n6_business_cli_e2e.py与现有test_narrative_batch_cli_e2e.py的私有_invoke timeout参数；不写三线模块/PWF/测试，也不改RF。复用现有_prepare/_invoke/isolated_batch_directory/loopback_model_server/r6_protected_inputs和consumer_bootstrap，不复制AUTO/任务库/消费者。

## 两步验收，只有一次最终质量节点

1. 先验证测试施工框架：三个小型合成业务原件（年度PDF、IR PDF、英文TXT），真实configured CLI/Config.load→子进程Worker/HTTP→outbox→正式RF读取及public search/exact→同run恢复。配置是独立明确的stub/loopback profile，8192输出、温度1，与生产文件隔离。0供应商/费用，不把mock usage记入真实campaign。
2. 两质量线实际合入并完成MAIN规则/版本接线后，同一测试入口用已登记真实P01/S01年报、P07/S07 IR、T01/S09英文电话会字节执行一次。要求最终可回放的EPI客户量产验证、境内约22%结构变化、中试线计划、管理层供需约束；沿正式读取的最终EvidenceSpan核不可变golden，不用新selector输出造答案。原件公司身份/期间使用明确Acme fixture，不能称真实生产身份验收；原文/语种不变。

真实节点由CWP_N6_RUN_REAL_E2E=1明确启用；日常CI默认不跑这条长Integration。真实运行必须同时配置CWP_RF_PROJECT_ROOT，RF导出精确已提交main六模块到scratch，不导入对方WIP或写owner。没有三线新交付前不运行新实际质量节点，也不重复9样本全表基准。

## 定位与标准

PDF golden是PDF页序号，可直接与正式final span的page坐标核对。电话会golden的原始TXT line/byte不能直接当规范化material行号：先核原字节范围与quote SHA，再通过正式transcript_byte_bindings把原始byte区间映射到已回放的span IDs/material行区间，最后核quote完整。RF验证这些绑定但在context投影中不返回明细；MAIN以同一reference调用CWP正式read，核stdout的artifact SHA及回放收据、与RF的evidence_spans完全一致后，从原bundle读取绑定。source_byte_ranges是start/end对象列表，不是二元数组。不得人为改原golden行号、生成假locator或删除未命中断言。

模型stub只摘录已有selected行，不改语言，并使用原角色/保守uncertain情态；这证明路径、引用和恢复，不证明真实供应商语义质量。真实经营点由final spans/golden和原字节独立验收，不能用第一条mock摘要冒充业务召回。S08混合文档及其余9类全面质量继续由不可变9样本基准覆盖，不缩小整体目标。

## 资源与清理

合成框架采用原40秒批次/60秒subprocess默认；真实PDF节点显式180秒batch/240秒subprocess，不提高生产默认，不把限时关掉。保持2MiB final/既有有限存储预算，0真实key，显式test max tokens仅为mock账。整个pytest节点可异步执行并周期汇报，不阻塞长sleep。

finally关闭catalog/子进程、删除隔离raw副本、RF六模块、DB/WAL/SHM/config/work-dir，独立root恢复原有keep.txt。原件、生产config/catalog、CWP用户config、RF三owner日志前后指纹核对，不做原文下载/46GB恢复演练，不修改系统ACL。只集中跑框架一次和合入后真实节点一次，不逐文档人工门。

## 执行

```powershell
$env:CWP_RF_PROJECT_ROOT='C:/Users/郑曾波/Projects/revenue-forecast'
$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD='1'
python -B -m pytest -p no:cacheprovider --basetemp tmp/n6bp tests/integration/test_n6_business_cli_e2e.py -k synthetic
# 以下只在两质量线合入后运行
$env:CWP_N6_RUN_REAL_E2E='1'
python -B -m pytest -p no:cacheprovider --basetemp tmp/n6be tests/integration/test_n6_business_cli_e2e.py -k real
```

框架complete：首次RED为既有私有测试helper缺少timeout_seconds参数（不是产品失败）；新增可选参数保持原默认60秒。首次框架1 passed/27.79秒；检查RF已提交实际context后发现绑定投影假设与range形状不符，修正并在合成TXT中实测原字节→material映射，最终1 passed/27.65秒、1真实节点deselected、Ruff绿。三份合成原件/3次本地POST，恢复不重复调用；RF六个已提交模块只导出到tmp。无真实供应商调用或费用，无日常CI新增长测。最终真实质量节点pending，仍待新selector代码。同步沿用上一轮冻结compat9项，合入后才重跑。
