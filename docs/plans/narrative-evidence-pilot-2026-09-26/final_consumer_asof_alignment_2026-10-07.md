# 完整核查：消费者历史日期合同对齐

RF main6e6b817a、StockWiki master3fe5008只读；CWP848cacf/user配置3609e707保持。StockWiki有独立quick-scan项目，不覆盖其目录/提交。本单属于总PWF，不新增人工review门或日常长测试。

## 发现与要求

CWP已按G1约定用来源公开日决定as-of；下载日期仅是来源事实。实际StockWiki `_narrative_bundle._manifest` 与RF `company_wiki_narrative_contracts` 仍把retrieved_at晚于cutoff拒绝，且StockWiki旧测试把“未来”定义为未来下载日。需先用真实CWP发布/公开CLI证实差异，不因静态怀疑立即写外仓。

合同：2026-08-01公开、2026-09-02下载的原文，在2026-09-01查询可用；2026-09-02才公开的资料不可用。未知/无效公开日、错误身份/期次/SHA继续拒绝。retrieved_at保留字段与合法UTC格式，既有wire不改；“当时本机是否已收集”的严格回放不是默认模式，不新建开关。

## 集中顺序与写集

1. CWP新opt-in手动Integration，六用例（RF/StockWiki × 早下载/晚下载/未来公开）。真实handler/outbox发布、CWP公开reference/read、两消费者当前CLI；模型为既有本地Replay，不外发。RF只读导出已提交六模块到测试根，StockWiki显式只读PYTHONPATH和-B，所有请求/配置/DB/raw均在独立tmp，finally恢复。
2. 小收据记录实际producer/consumer返回码和静态错误、当前HEAD/保护/清理，不保存正文、密钥或未知数据。RED需发生在语义断言，不因模块或夹具缺失。
3. 若证实差异，先在独立测试副本给出最小修正并以相同用例证明GREEN。不要修改原件或伪造retrieved_at迎合旧消费者；不把测试副本修正声称为生产已修。RF/StockWiki owner的落地方式另明确，不抢现工作树。
4. 更新完整需求表，保留未落地项。日常CI不加跨仓六CLI/真实PDF长测；本仓只提交测试、细则与收据，不能把旧绿收据当本缺口已解决。

## 当前状态

真实CLI已证实4pass/2fail（25.36秒），仅晚下载两消费者RED；最小独立副本相同六例6pass/25.17秒、Ruff绿，未来公开反例仍真实拒绝。当前两仓代码未改，不能宣布生产修复。原owner不写策略要求先明确授权，已异步询问；此期间完成本仓证据、可审查diff和两张互斥卡：[RF卡](harness_lanes/revenue_forecast_asof_alignment.md)、[StockWiki卡](harness_lanes/stockwiki_asof_alignment.md)。两卡未派发、不自动开新harness。首轮6个dict/to_dict夹具错误及首次副本导出未终态/缺已提交CLI provider配置的3个环境失败不计产品RED；依赖完整后真正GREEN。正式[小收据](harness_lanes/results/final_consumer_asof_audit_2026-10-07.json)保存当前/提案区分。

## 2026-10-07 实施授权已收到

用户明确“授权隔离修复并线”。MAIN执行两张卡，不新开harness；RF独立root cwp-lanes-20261007/rf-asof，StockWiki独立root stockwiki-asof。两仓基线未前进，RF三owner日志保持，StockWiki独立quick-scan代码保留。先写late下载/同公开日/未来公开/非法UTC责任测试，看到RED再实施，之后一次责任节点及真实六CLI，再正常并线/push与清理自身worktree。前述待答记录为历史，不再要求第二次许可。

## 2026-10-07 授权实施与主线验收

用户“授权隔离修复并线”已执行。RF `e241389adeda37bc9cbb53d7831063718552a936` 正常快进 main、推送 origin/main，精确 CI 37574397700/job112639930230 全部步骤成功，用时30秒。StockWiki `9f552a6741dd093dc760ad6965458989cd027251` 正常快进本地 master；本仓没有远端，不声称已推送或有远端CI。

两仓先各获得2个真实语义RED（晚下载和公开日等于cutoff），再最小修改日期判断，保留 UTC/公开日/身份/期间/SHA/locator反例；没有改原件、公开wire或golden。RF责任58pass/1skip、快速门107pass及正常push门107pass；StockWiki责任113pass/1skip。StockWiki集中大节点首跑934pass/15skip/1个Windows长路径环境失败，同一失败用例改独立短测试根后1pass：共935个不同用例绿，coverage总81%、UI75.56%，不是单次全套全绿。未重跑全部长测。

当前CWP→实际两仓主线正式CLI六例6pass/29.63秒，逐条证据一致，RF只导出现场已提交HEAD，删除临时提案覆盖入口。这是日期合同的本地Replay E2E，不冒称新增付费模型或真实供应商下载；两个消费者自己的未来/未知公开日等分支另由责任包证明。

本次两个独立worktree和三个测试根恢复absent，移除136471537 B临时代码/测试资料，不计为生产清理收益。九原件SHA/size/mtime、生产DB完整SHA及六个配置/owner文件指纹保持。RF三owner日志和CWP source_acquisition用户修改不暂存、不覆盖；StockWiki owner工作树clean，quick-scan/IQS未改。两套安装技能仅在校验旧主线字节后同步本次两文件，其他本地内容保留，不宣称整套安装完全一致。

完整[主线验收收据](harness_lanes/results/final_asof_implementation_2026-10-07.json)、[RF独立交接](harness_lanes/results/final_rf_asof_handoff_2026-10-07.json)、[StockWiki独立交接](harness_lanes/results/final_stockwiki_asof_handoff_2026-10-07.json)。历史RED/提案GREEN收据保留，不能替代本次实际主线结果。CWP本次测试/文档正常提交推送并记录对应代码CI后，完成最后发布收尾。
