# P1版本合同与已知影响选测收口

2026-11-01：候选独审PASS / 0 OPEN，正常新发布与精确远端CI仍由总控实查。

93f561ef远端CI41261403683的三个失败在本机原节点3F/6.66s复现：两个测试固定旧allocation/1，新实现已经明确/2；另一个将有意升级的/5紧凑请求与旧私有HTTP捕获比较。旧捕获文件逐LF字节未改，/4与/6继续精确历史比较；/5另有完整四字段精确fixture，绑定原selection及predecessor SHA，不以删断言或任意hash接受迁移。相关54例通过。

直接漏检共因：旧自导入`__import__(__name__)`被当不确定动态执行，直接全量推荐；日常gate为速度把全量推荐全部折为smoke，连已知消费者也丢了。只改成等价sys.modules自引用仍有416推荐/36.88秒，再度全丢。现复用同一个AST reverse图，默认保守推荐不变；日常known_only不把仓内无关dynamic当种子，保留已变whole unit、再按最短静态距离/稳定路径，最多32个已知文件＋原去重smoke，余项明确延期。无新AST图/缓存、固定失败清单、全量commit、人工许可或CI配置变化，进程总时限仍180秒。

真正TDD6F/1P→7P；集中选测域185P/1个旧策略期望失败。该旧例其实同时新增失败unit与config，新策略理应捕获；改为先绿baseline，仅改配置、无可证明Python变更的真实未知范围，fast诚实延期而explicit full发现失败。初版tomllib会误伤Python3.10，已去不必要解析依赖，最终单例1P/24.33s。新的真实Git hook反例在185P中：未知动态源仍保留已知消费者，值回归阻止local bare remote推进。保留旧失败而不假报某次全186P运行。

真实旧push路径的当前静态probe10.64秒，32/352已知unit保留、320延期，另279非unit归大节点/CI。source_priority进入，但atomic_summary_recipe仍在旧范围32外；**这只是有界部分覆盖，不能保证所有远端失败都被hook捕获**。当前修复把这两个测试本身修改，距离0会优先。root源测试54P已明确运行，不能拿部分hook替代它或完整CI。

产品唯一后续变化是等价sys.modules自引用，免费重放两份真实POST的request data、完整draft/execution完全一致。原运行签名保留；相对原付费版累计四个实现依赖SHA变化（source_cards/execution_contract/allocation/protocol），不同时间的两依赖/三依赖报告仍是当时增补，不重写成今日签名。源码/测试14文件raw与LF SHA、独立AST/合同及4组known/caller正反探针在receipts/independent，0新模型/下载/原件解析。

独审只签代码/版本迁移/选测；不预告远端绿，不代签完整公司研究。W12 r1-remediation-03原公司回归保留2026-10-21截止日，目前独立executor免费preflight，缺call及隔离catalog元数据继承缺口按实记录。精确CI绿后继续原计划，不扩施工包。
