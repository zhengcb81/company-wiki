# RF 独立施工卡：叙述来源按公开日过滤

状态：MAIN已完成并线与验收，不再分派。实际交接见[小收据](results/final_rf_asof_handoff_2026-10-07.json)；下列基线/施工顺序保留为历史实施说明。

## 基线与已证明缺口

RF main6e6b817a，CWP848cacf/运行7aa88ae。真实CWP发布原文：公开2026-08-01、下载2026-09-02、as-of2026-09-01；CWP read0/replay verified，当前RF read2/source_after_as_of。不是原件、身份、期间或版本错误。相同CLI的独立副本移除下载日截止后通过；未来公开仍拒绝。

证据和两行级提案：[联合收据](results/final_consumer_asof_audit_2026-10-07.json)、[RF diff](results/final_rf_asof_proposal_2026-10-07.patch)。RF不能修改资料retrieved_at掩盖问题，不能加开关/签收、放宽公开日/原件SHA，不能只改测试期望让旧拒绝通过。

## 独占写集与实施

1. 最新main建立codex/分支独立worktree。核当前HEAD及未提交owner记录，不reset、不clean、不合无关WIP。若基线前进，重新只读确认同一_manifest规则及其调用，保留新增代码。
2. 先在`tests/test_company_wiki_narrative_reader.py`增加真实golden派生的late-download成功反例（保留retrieved_at原值）；新增未来公开和非法UTC反例。先RED。已有`future_capture`拒绝断言改为独立“future_publication”反例，而不是删除未来信息校验；保留nonutc_capture、身份、period、body/receipt SHA等旧反例。
3. `scripts/company_wiki_narrative_contracts.py::_manifest`只取消retrieved_at与cutoff比较，保留合法UTC解析和published_date截止。参考附diff，不照搬其他文件或当前owner日志。不改公开wire/golden、配置、source preparation其他路径、模型/预算。
4. 集中跑reader/transport责任包一次、Ruff与本仓现快速门；跨仓六案例统一由MAIN跑，不在每个helper重复。允许同公开日/后来下载；未来公开/未知公开/身份/SHA不符必须拒绝。
5. 正常commit/push并记录精确SHA CI；MAIN决定当前主线快进/合并，集成前再核HEAD。测试目录短且新建，全部finally恢复，原件/owner配置无写。不得跳正常钩子，不新增CI矩阵/日常真实长测。

## 交接接口

新小JSON：schema=cwp-consumer-asof-handoff/1，consumer=rf，base_head、branch、code_head、public_wire_changed=false、changed_paths、red（命令/失败数/具体业务断言）、green（责任包命令/计数/秒数）、preserved_refusals（future_publication/unknown_publication/nonutc/identity/period/SHA）、protected（owner三日志SHA前后）、cleanup（每个新根初始/最终absent）、ci（实际code SHA/id/全部步骤）、remaining。不要写正文/密钥或复用另一commit的CI。

本卡落地验收与当前提案GREEN不同，未实际并线前不得标main_passed。

## 2026-10-07 授权实施与主线验收

用户“授权隔离修复并线”已执行。RF `e241389adeda37bc9cbb53d7831063718552a936` 正常快进 main、推送 origin/main，精确 CI 37574397700/job112639930230 全部步骤成功，用时30秒。StockWiki `9f552a6741dd093dc760ad6965458989cd027251` 正常快进本地 master；本仓没有远端，不声称已推送或有远端CI。

两仓先各获得2个真实语义RED（晚下载和公开日等于cutoff），再最小修改日期判断，保留 UTC/公开日/身份/期间/SHA/locator反例；没有改原件、公开wire或golden。RF责任58pass/1skip、快速门107pass及正常push门107pass；StockWiki责任113pass/1skip。StockWiki集中大节点首跑934pass/15skip/1个Windows长路径环境失败，同一失败用例改独立短测试根后1pass：共935个不同用例绿，coverage总81%、UI75.56%，不是单次全套全绿。未重跑全部长测。

当前CWP→实际两仓主线正式CLI六例6pass/29.63秒，逐条证据一致，RF只导出现场已提交HEAD，删除临时提案覆盖入口。这是日期合同的本地Replay E2E，不冒称新增付费模型或真实供应商下载；两个消费者自己的未来/未知公开日等分支另由责任包证明。

本次两个独立worktree和三个测试根恢复absent，移除136471537 B临时代码/测试资料，不计为生产清理收益。九原件SHA/size/mtime、生产DB完整SHA及六个配置/owner文件指纹保持。RF三owner日志和CWP source_acquisition用户修改不暂存、不覆盖；StockWiki owner工作树clean，quick-scan/IQS未改。两套安装技能仅在校验旧主线字节后同步本次两文件，其他本地内容保留，不宣称整套安装完全一致。

完整[主线验收收据](results/final_asof_implementation_2026-10-07.json)、[RF独立交接](results/final_rf_asof_handoff_2026-10-07.json)、[StockWiki独立交接](results/final_stockwiki_asof_handoff_2026-10-07.json)。历史RED/提案GREEN收据保留，不能替代本次实际主线结果。CWP本次测试/文档已正常提交推送：ee0d1e7，精确CI37575052423/job112641956369全部步骤绿70秒；六跨仓CLI为另行本地集中验收，不冒称日常CI执行外仓E2E。本轮必要施工全部完成。
