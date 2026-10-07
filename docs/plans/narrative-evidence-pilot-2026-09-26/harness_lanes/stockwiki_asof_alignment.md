# StockWiki 独立施工卡：叙述来源公开日合同对齐

状态：最小提案已实证GREEN，尚未批准外仓落地/未派发。唯一写入StockWiki独立worktree，本卡不接触当前quick-scan/IQS项目、identity数据或原件。CWP/RF/其他仓只读，写集与RF日期卡不重叠。

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
