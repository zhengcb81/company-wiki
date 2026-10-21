# 首家 holdout initial：四路独立审查封存

日期2026-10-21；本页为大节点事实索引，不是通过签收。原运行 `revenue-forecast-audit/runs/r1-20261021-cn-wuxi-apptec`，manifest `ee08753799d7d2a849dd3fd9c811e7c0e83d20d7538f978218245fdf98dca458`，639工件/36,665,980B，独立hash核对一致。

四位实际独立agent先互盲完成，storage在看输出前从原件冻结21个目标。共73检查，26 findings：15P1/11P2。四报告均FAIL，执行仍partial；来源与费用事实不因诊断工具通过而升级。

| 角色 | findings | 报告 |
|---|---:|---|
| 来源/解析 | 7 | [storage](storage.md) / [JSON](storage.json) |
| 采集/复用 | 8 | [fetch](fetch.md) / [JSON](fetch.json) |
| RF流程/数字 | 6 | [process](process.md) / [JSON](process.json) |
| 买方模型 | 5 | [analyst](analyst.md) / [JSON](analyst.json) |

主要共因候选：新批次仍默认0.8，正式输出不含0.9共享context；业务遗漏及c4跨分部30%口径拼接；FF不识别有效blocked/unavailable/nonzero业务JSON且请求过的companion误报not_requested；本地discovery无目标范围，先集齐全部旧历史路径才登记，第17项触16候选上限；已取得Q1未消费、最新H1/指引及经营桥/校准缺。最新原因是local_candidate_limit，早期publication_unknown不应冒充最终原因。

数字边界：85引用实读；baseline97/stress105参数；1276独立数值比较0算术差错；3952数值叶子均分类，其中2676只是复制/声明，不是2676独立事实。45个未来增长率与压力幅度未独立校准；未来actual不造数。场景低于管理指引本身可以成立，但需要已读最新来源和独立反证/经营桥，不能机械抬到guidance。

原生audit check=needs_remediation且26 issue待根因映射，符合当前状态。coverage按默认128files/1MiB每file/8MiB总/30s完成，quality_status=not_evaluated；26 gaps是待disposition。证据诊断126个MISMATCH全是JSON locator未解析（如把多pointer用分号串在一个locator），不是126个数据错或原件hash变动；大numeric ledger2.67MB超机器单file观察上限但process实际全量读/复算。ROOT两次超工具参数上限的失败保留，第三次改用原生默认成功；不能把ROOT参数错误当产品缺陷。后续报告用每条evidence一个可解析locator，不增加人签。

本目录8报告为原始封存字节副本，SHA及实际命令见[four-review-observation.json](four-review-observation.json)。完整raw/命令/consumer/复算仍在本机run，未宣称fresh clone已经可全复验。专家独占run/diagnosis、remediation建立完整issue→根因→包→测试映射；ROOT接收后直接施工。不得回写旧execution或报告来洗绿。旧NVDA与未来八家目标继续承接。
