# PDF-C3 独立工程复审进度

上一稳定 runner（LF `ab1ddce7e962934de75c41386da14c8cd334034b09047303a76f368f9787a607`）已完成审查：15 项定向测试通过，两个独立共因已关闭，4 个独立合成反例绿色。收据 `final-targeted.json/xml/log`、`independent-before-fix-probe-v2.json`、`independent-after-fix-probe-v2.json` 已保留。

实际 RED 来自已保存的历史已提交 HEAD（LF `dfdfcee660a56f37788cadfb7fea7b28c330b4b62f2599b71d1d56e842f375fe`）；初审400727只静态见相同缺陷，未精确回放该并发前快照。probe v1 为 harness 失败，v2 才是产品证据。held status FAIL 是故意停止于 source setup 的中性 sentinel，不是付费执行结果。

暂不封最终当前源码 SHA。父 agent 正新增完整 SourceRef 内容读取组合，以明确区分原件内容身份验证与历史财报选择资格。该增量待独立复核；原严格 query 条件不能放宽，未知日期不能补造；内容模式应把 filing identity/period/asof 明示 NOT_EVALUATED。

全部测试均只用自建合成源与合成 gold，未读 holdout/gold 正文，无外网/模型/生产配置写入。自有 `.c3irfinal`、`.c3irfix`、`.c3irt` 已清理。
