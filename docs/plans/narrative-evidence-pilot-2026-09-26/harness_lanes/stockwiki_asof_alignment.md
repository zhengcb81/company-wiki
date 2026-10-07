# StockWiki 独立施工卡：叙述来源公开日合同对齐

状态：MAIN已完成并线与验收，不再分派。实际交接见[小收据](results/final_stockwiki_asof_handoff_2026-10-07.json)；下列基线/施工顺序保留为历史实施说明。

## 基线与语义

StockWiki master3fe5008，CWP848cacf/运行7aa88ae。8月1日公开、9月2日下载的资料，在9月1日as-of可以读取；当前CWP CLI已verified，StockWiki返回source_after_as_of。两仓同六个真实CLI用例，当前4pass/2fail；独立副本6pass/25.17秒。详见[联合收据](results/final_consumer_asof_audit_2026-10-07.json)、[StockWiki最小diff](results/final_stockwiki_asof_proposal_2026-10-07.patch)。只是日期合同，不是付费模型质量或生产全库处理证明。

## 独占写集与步骤

1. 最新master建立codex/独立worktree。先核owner HEAD/dirty和正在进行的独立项目；不重置、不恢复、删除owner文件，不整合其他WIP。若主线已前进，以现场代码定位_manifest并重新核规则。
2. `tests/test_narrative_source.py`先新增late-download成功反例（从既有wire fixture复制，保留真实retrieved_at），未来公开与非法日期反例；原`future`用例现在改retrieved_at，应改为published_date真正未来，不能丢未来公开拒绝、身份/期次/SHA/locator检查。先TDD RED。
3. 只修改`stockwiki/_narrative_bundle.py::_manifest`：合法UTC解析保留，取消下载日与cutoff比较，published_date cutoff不变。必要时更新`docs/narrative_source_consumer.md`的日期说明；不改reader DTO、SourceExport wire/golden、llm配置、quick-scan、identity、服务注册/进程容器等无关代码。
4. 集中跑narrative_source/source_cli责任包及既有source-reader回归；本仓现大节点门只跑一次，不另增全pytest/coverage/跨平台矩阵。MAIN最后统一六CLI联调；不每个小节点重跑PDF或所有StockWiki测试。
5. 正常提交、主线集成前重新核HEAD；测试新短根与配置副本退出恢复原样，不写CWP生产库或StockWiki研究库。合法后来下载成功，未来公开/未知公开/身份/SHA错仍拒绝，not_reviewed仍诊断，不新增人工审查。

## 独立交接接口

schema=cwp-consumer-asof-handoff/1，consumer=stockwiki；base_head/branch/code_head/changed_paths/public_wire_changed=false；red与green真实命令、计数和秒数；preserved_refusals（future_publication、unknown_publication、invalid_utc、identity、period、SHA）；owner状态/HEAD前后；原件和当前项目配置SHA保护；测试新根清理；主线集成SHA及本仓正式门/远端CI（若本仓无该CI则明确，不造成功）；remaining。小JSON及一页Markdown，不保存来源正文或API密钥。

未获跨仓实施授权或未实际集成前，不把本卡或独立副本GREEN称为已经修好当前StockWiki。

## 2026-10-07 授权实施与主线验收

用户“授权隔离修复并线”已执行。RF `e241389adeda37bc9cbb53d7831063718552a936` 正常快进 main、推送 origin/main，精确 CI 37574397700/job112639930230 全部步骤成功，用时30秒。StockWiki `9f552a6741dd093dc760ad6965458989cd027251` 正常快进本地 master；本仓没有远端，不声称已推送或有远端CI。

两仓先各获得2个真实语义RED（晚下载和公开日等于cutoff），再最小修改日期判断，保留 UTC/公开日/身份/期间/SHA/locator反例；没有改原件、公开wire或golden。RF责任58pass/1skip、快速门107pass及正常push门107pass；StockWiki责任113pass/1skip。StockWiki集中大节点首跑934pass/15skip/1个Windows长路径环境失败，同一失败用例改独立短测试根后1pass：共935个不同用例绿，coverage总81%、UI75.56%，不是单次全套全绿。未重跑全部长测。

当前CWP→实际两仓主线正式CLI六例6pass/29.63秒，逐条证据一致，RF只导出现场已提交HEAD，删除临时提案覆盖入口。这是日期合同的本地Replay E2E，不冒称新增付费模型或真实供应商下载；两个消费者自己的未来/未知公开日等分支另由责任包证明。

本次两个独立worktree和三个测试根恢复absent，移除136471537 B临时代码/测试资料，不计为生产清理收益。九原件SHA/size/mtime、生产DB完整SHA及六个配置/owner文件指纹保持。RF三owner日志和CWP source_acquisition用户修改不暂存、不覆盖；StockWiki owner工作树clean，quick-scan/IQS未改。两套安装技能仅在校验旧主线字节后同步本次两文件，其他本地内容保留，不宣称整套安装完全一致。

完整[主线验收收据](results/final_asof_implementation_2026-10-07.json)、[RF独立交接](results/final_rf_asof_handoff_2026-10-07.json)、[StockWiki独立交接](results/final_stockwiki_asof_handoff_2026-10-07.json)。历史RED/提案GREEN收据保留，不能替代本次实际主线结果。CWP本次测试/文档已正常提交推送：ee0d1e7，精确CI37575052423/job112641956369全部步骤绿70秒；六跨仓CLI为另行本地集中验收，不冒称日常CI执行外仓E2E。本轮必要施工全部完成。
