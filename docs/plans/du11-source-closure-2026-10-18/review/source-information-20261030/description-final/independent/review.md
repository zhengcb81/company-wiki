# 来源描述独立终审

结论：**PASS，工程范围内 OPEN=0**。最终 6 个运行／测试文件 raw/LF SHA-256 全量见 `review.json`、`final-hashes.json`；最终 27 项测试前冻结，签署时逐一复核一致。

独立 **27 passed / 0 failed / 0 skipped，pytest 1.75 秒，命令 3.56 秒**，日志/XML 为 `final.log/xml`。ROOT 的 3383P/11skip、mypy 与 ruff 为单独报告，不计入独立数量；此前本独立 20P/1.93 秒是中间版，不相加。

已修复七类实际问题：模板用途误授 receipt/composition payload；具名 process/impact 与前段财务粘连；未知逗号枚举丢失；英语经营影响否认缺失；流程规则前缀平方扫描；模板前出现 Product 标题名词即可绕过用途 guard；财务性质事件压掉其明确经营影响对象。原探针与具体数据保留，不靠删除反例签通过。

最终中英／繁体对照验证：未知枚举保持原文构成价值，不变制造或发行人事件；客户制造企业类别不成为实际制造；上市申请和条件未来保持原字句，实际卡片不夹带无关财务或致谢；成本事件对经营的影响可用，财务报表上的会计影响仍不可用；模板标题不能豁免，真实软件识别／处理模板的功能仍可用。实际 SourceCard 成员等于 support/context 并集，两个顺序均检查原始支持文本。

资源实证：N100/200/400 步骤的旧前缀扫描为 79,600/319,200/1,278,400 字符；最终为 3,208/6,408/12,808，调用次数固定 4，母账计费为 64,918/129,618/259,018，均在线性预留内。`resource-r1.json` 保留 RED，`resource-r2.json` 与 `resource-final.json` 分别保存 GREEN。一次探针误复用 RED 文件名，已从实际工具输出逐值恢复原 RED 并分存 GREEN，后续输出文件名显式指定。缓存重复读取零额外扫描／费用；未新建余额、任务库或提高额度。规则功能关联使用有界 160 字符窗口；policy/25 与 grammar hash 依赖可区分语义版本。

真实输入初筛：独立逐条读保存 real-r2 的 8 张卡，并验证 final real-r3 的 support/context/admission 文本完全一致、各任务 member 并集一致，详见 `real-content-review.json`。产品已售清单与超过300开发数量没有互换；客户链未变直接销售关系；收到问询／申请中止／资料更新后将申请恢复没有变成批准或已恢复；“未构成重大影响”与新闻／家电产品范围保留；VC无生产、股东联系、希望合作分开；751吨/年仍为项目建成后的产能规划。领先水平仍是管理层自述，3月11未擅补年份。

真实结果 source SHA 为 `221467c15a24180205a8226f96fea9bda0262c866d5ba8aa31889ec96e6466d7`，15 spans／8 cards，全文仍 partial、coverage_complete=False。这只是 8 卡输入内容初筛，不是完整召回 gold，更不代签正式摘要、实际 prompt／账单、重启或跨run cache、FF/RF、W21、US RPO、holdout 或总循环。raw_member_bytes 只是原文材料代理。

清理：只写本独审目录，脚本／探针／日志／XML 保留。Python `-B`、pytest `no:cacheprovider`，目录无缓存子目录；未改产品、作者测试、PWF、配置、hook 或其他仓。config diff 为空，原 hook 保持 0/0 内容变更的 mode WIP。未读原件、SDK、密钥、供应商、W21 或 holdout，0 外部 API／模型调用、0 下载。
