# W13/W14/W15 ROOT接收与三仓收尾

日期：2026-10-24。本文记录作者交付、ROOT接收、实际并线及剩余边界。机器摘要见同目录`receipt.json`；三包总状态见`harness_lanes/20261024/dispatch.json`。

## 总结

三张包均已完成ROOT接收，但接收方式不同：W13只接收经过独立测试的ROOT有界适配，不照搬会让宽范围push等待过久的作者最终策略；W14快进进入并推送Revenue Forecast主线；W15快进进入Audit本地主线后，ROOT在真实移位回放中发现并修复Windows文本换行令固定SHA漂移的问题。三包工程验收不等于真实公司内容、真实下载、正式摘要、cache恢复或收入预测质量验收。

## W13 — CWP推送调度

- 作者包：`C:/Users/郑曾波/Projects/company-wiki-w13-gates`，分支`codex/w13-cwp-gates-20261024`，实际HEAD `6efd4fccb31c71bf732d401aacb5dbe49eca0035`；作者审查代码commit为`852dff283ed9f18dd4e0dd1376c4ca89a52b1795`。作者handoff JSON的`final_head`陈旧，不能把它当实际HEAD；这项差异在ROOT接收元数据中明确保存，未改作者工作目录。
- 作者最终策略中移除了此前的32个目标上限，而包实测宽范围357目标需628秒并触及既有600秒上限，与本项目“日常提交快速反馈”的目标冲突。因此ROOT没有整分支合并，而是在主线保留有界策略：≤32目标可做本地受影响测试；目录、动态、未知或更宽范围转固定smoke/CI。
- ROOT提交`67439d0ac13ddf3e3b4fa4f8ef20cf1a4e87999c`补入精确节点去重、保留同文件其他快速节点，并修复`smoke-only`标签不应冒称affected测试通过的问题。回归明确保留>32 defer。
- ROOT验证：W13聚焦套件154通过，独立策略探针18通过，真实本地Git ref/push检查5通过，Ruff通过；没有重跑8千全量。此前Git hook执行位模式仍单独按精确CI收据处理。
- 当前状态：已提交，随本批PWF提交正常push后检查准确绑定新HEAD的CI；未通过CI前不写成远端通过。

## W14 — RF三仓离线链

- 作者最终分支/ROOT快进HEAD：`aa19b653da18566e582e802269f5908471c456db`，ROOT已快进RF `main` 并成功推送，main与origin/main一致。
- 作者独立静态、运行、反掩盖审查及delta/义务复审均批准。审查代码commit `3bc0508e2a1ae97df2d0d67458fe288f677030a5`；handoff明确范围为合成夹具下的离线跨仓端到端工程复现。
- 22项相关回归通过；独立pre-push门禁595 passed、1 skipped、36 subtests passed。Ruff通过。耗时在并行争用时显著增加；不重复运行整套W14端到端。
- 验收范围不含真实provider下载或真实公司预测，S1实际下载未运行，不能外推成生产业务验收。RF原有三份脏assurance文件与生成的untracked `output/`保留，未暂存。

## W15 — Audit移位回放

- 作者分支HEAD `9bc2248f7d66636a7ce5e5d23933b0f7ac12eb49`，独立reviewed code commit `77d1264f8e3e7fdd9418e304ee5a621d738ec883`，所有包内发现均已复审关闭；Audit没有配置remote。
- ROOT快进Audit本地`main`后，真实隔离回放发现fixture manifest以CRLF字节SHA固定文本，但干净Git checkout得到LF字节，导致28项中1项失败。ROOT以`.gitattributes -text`固定需按原字节回放的fixture/export，并将输入manifest SHA改为canonical Git blob检出字节SHA；这修的是跨平台根因，不是放松校验。
- ROOT提交`37e12e6ff4674fa1989b2616cff3c31faa4d8cb0`。最终28项聚焦测试通过，真实adoption replay `outcome=complete`、8 counterexamples、`cleanup_verified=true`；所有14个fixture SHA匹配。测试创建的三份临时路径均删除。
- 状态：仅本地提交；无remote，故未推送，也不虚构远端交付。

## 发布后下一步

1. 将CWP的W13修复与本接收记录一起正常push，再只看绑定新HEAD的精确CI结果。不得通过全量本地套件替代该CI，也不得把历史CI复用为当前结论。
2. RF的W14代码已推送；其ROOT PWF状态一并提交推送并观察CI。保持三份既有assurance变更和untracked输出不动。
3. Audit只有本地main；保持其无remote事实。将ROOT验收收据提交本地，不伪造push。
4. 回到唯一主线任务：跨市场真实样本正式摘要、来源引用/限定、同源缓存命中、进程中断恢复以及RF按source/hash消费和四路审查；测试按实际责任边界做定向+关键E2E，不重复全量慢检。

## 留存边界

- 原始资料未改动；本批未下载原件、未调用外部模型/provider、未产生外部费用。
- CWP `.githooks/pre-push`仍有既存mode-only工作树diff；CWP大量无关untracked `.planning`、临时目录均未清理或暂存。
- RF三份assurance脏文件和untracked `output/`未动；Audit两份无关untracked预算脚本未动。
- W13作者handoff stale字段只作为接收差异记录；不改写作者工作树。作者review与ROOT review分别绑定各自实际源码版本。
