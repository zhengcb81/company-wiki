> 当前：真实来源预检发现CF1–CF4，正式付费未执行。运行器清理及unknown费用根修59P主机；journal绑定增量3RED后12P/旧母账2P通过（重叠），最终独审PASS，准备发布；历史静态NOT_READY由最终独审单列更新，不能说来源/摘要/RF已通过。

# 新v4正式摘要与恢复（待执行）

本节点接续source/input来源验收，不覆盖旧MSFT formal-v4（旧wrapper显式v5排名）。用现有phase_c_runner/production worker唯一入口、当前配置MiniMax及原SourceRef；明确reading-model-input/4，新output独占，单次上限100,000 tokens/$0.10，在累计10M/$20内含unknown。

顺序：精确483cb2a5 CI全绿、独立跨市场预检及运行器独审→零POST生产预检→新正式v4请求→实际逐任务语义检查→activation_pending/恢复无重复POST或费用→FF原文复用/RF source+narrative实际读取。完整RF预测和四路公司审查仍另记OPEN，不以这个接口检查替代。

原始文档及旧收据不改，不翻译，不复制raw；临时数据湖由runner恢复为空。provider/model/options必须与Config.load实际配置相等，不另造HTTP客户端、预算库或供应商override。若源侧预检出现必需信息缺口或预算耗尽，先定位根因，不强行付费。

## 故障后费用恢复（工程入口，不是人工许可）

如果结果标记`native_usage_reconciliation_required`，真实费用差额应为unknown/null。既有母账先保存整次请求的保守占额，已落账的实际用量按run抵扣，不重复计费。诊断sidecar写入失败不能阻止母账持久化，落账/观察失败不能阻止自有临时湖清理。

如果原AUTO临时库已删除，但本次`RUN.native-usage.json`在失败时已保存并由同账本fallback绑定SHA，可以离线恢复：

```powershell
.venv/Scripts/python.exe tools/document_understanding_benchmark/phase_c_runner.py --mode live --output <本次输出目录> --usage-ledger <原母账usage.jsonl> --reconcile-run-id <RUN>
```

该命令只读持久化用量并追加原母账，不开AUTO库、不下载、不调用模型。重复执行无重复费用。缺失/变更/未绑定用量，或已记录POST却为空时，保留全额unknown并明确报错，不猜测为零；不是增加一份人工批准JSON。正常原AUTO库仍在时，原`append_native`按实际reservation落账。

当前真实母账没有触发以上故障；本节点都是隔离模拟，0新增费用/下载/原件副本。59项主机结果在journal绑定增量之前，新分支另有12项针对性通过及旧母账2项通过，不把它们相加伪装成一次全量结果。
