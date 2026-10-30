# QA 范围闭包独立终审

结论：**PASS，审查工程范围内 OPEN=0**。签署本轮 8 个源码／测试文件的实际工作区字节，包括最后的 object identity 类型修正。完整 raw/LF SHA-256 在 `review.json` 与 `final-r4-hashes.json`；测试前冻结，签署时逐一复核一致。

最终独立 **15 passed / 0 failed / 0 skipped，pytest 1.98 秒，命令 4.01 秒**，日志/XML 为 `final-r4.log/xml`。没有重跑全仓，ROOT 的领域测试、mypy、真实保存材料复验不计入独立测试数。

七类 P2 已修复并复核：带显式发行人前缀的后置限制脱离正向卡；隔着财务段的限制未回绑且携带财务成本；因果只剩解释半边；scope 注册未计费复制累计 contexts；原 partial QA 被授 whole support；普通中英礼貌语借业务卡付成本；同一对象多限制链被误判为多个对象。原 RED、探针与 XML/log 全部保留。

独立检查实际 SourceCard.support 与成员，而非仅比较选中 span 数：必要限制／因果两端同时进入原文支持；无关财务／纯礼貌语不进 prompt 成员成本；member 等于 support 与 context 的并集。真实 pipeline trace 证明声明 context 在目标 scope.fact 前就属于该 owner，问题不会进入语义上下文。已知同一对象链闭合，两个实际原始对象仍保持歧义 partial；缺问题的 partial QA 原文可读但没有 admitted 卡。

静态核对旧物理入口仍默认 `qa_sequence=False`，原 source/basis/角色/页码/turn/段落/section 与 leading-deictic 验证未放宽。新 QA 语义闭包使用受证序列与实际 original object span 身份，不伪造 physical adjacency。含义 context 单项私有登记，不再复制累计映射；重复缓存零语义扫描，预算耗尽在成员读取前停止。显式 child owner 被实际阅读消费，generic 扩大后的最终支持重新 assessment；新模块进入 recipe 依赖，公开 relation wire 和 raw IDs 未改。

历史不累加：初始独立 8 项 4F/4P（2.15 秒）；首轮修后 11P（1.96 秒）；对象身份修后 13P（2.16 秒）；补真歧义／收费屏障后 15P（1.86 秒）；最终类型修正字节 15P（1.98 秒）。另有 `observations-r1.json` 的 4 个短公共输入（0.307 秒），不计单测。一次多限制探针在打印不存在的包属性时失败，后已更正输出；不作为产品失败或通过数。

本 PASS 仅覆盖 QA 闭包工程。真实 roster 中孤立产品列表／化合物数量／审核中止等 unknown/context-only 召回缺口仍 OPEN；正式摘要、费用与恢复、跨 run cache、FF/RF 采用、W21、US RPO、holdout 及总循环均未代签。ROOT 最终领域包正在进行，本独立短包不替它声明全绿。

清理：只写此独审目录；脚本、探针、日志、XML 保留以复现。Python `-B`、pytest `no:cacheprovider`，目录无缓存子目录。未改产品、作者测试、共享 PWF、配置、hook 或其他仓；config diff 为空，原 hook 仍为 0/0 内容变更的 mode WIP。未读 PDF 原件、密钥、SDK 或 W21，0 外部 API／模型调用、0 下载。
