# RF 独立施工卡：叙述来源按公开日过滤

状态：最小提案已实证GREEN，尚未批准外仓落地/未派发。唯一本仓写集为RF独立worktree；owner现目录及三assurance日志不得改。CWP、StockWiki、IQS、Dayu、ET、FF只读。本卡与StockWiki日期卡无重叠。

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
