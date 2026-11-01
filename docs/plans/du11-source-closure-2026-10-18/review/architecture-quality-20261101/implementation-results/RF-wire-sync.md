# RF R5 阅读完整性 wire 窄同步

2026-11-01。RF基线main `b093cdb9186b7aac46c92faeab2f3598be97d32e`。实现曾位于自有稀疏工作树 `C:/Users/郑曾波/Projects/revenue-forecast-r5-wire-sync`、分支 `codex/r5-reading-wire-sync`；完成并线后两者已正常清理。

当前：**独审、正常发布、main快进、单runtime定点部署、repeat零写、fresh-process与WIP保护全部完成，STOP**。发布commit为`957c6283d3381d23c39515afd3a09147d8201c7b`，本地/远端main一致。不得把本页当公司循环/真实摘要通过。当前用户要求收尾后暂停，未运行原公司或新公司。

## 接口与边界

与CWP作者直接核对 `reading-context-wire/1.1`：

- `du-production-reading/4`可选`source_processing_complete`；出现时必须严格bool。旧wire缺字段保持缺失，不默认True；schema1/2/3仍不接受这个字段。
- 新diagnostic code仅`source_grammar_unavailable/source_grammar_scope_limit/source_assessment_incomplete`。精确shape为`code,count,phase,dimension,external_model_cost,known_unit_ids,known_unit_count,known_unit_ids_limited`。
- phase/dimension均`source_readability`；external_model_cost必须False；count正整数非bool；known_unit_ids最多16个canonical narrative-unit ID；known_unit_count严格int且>=1及实际列表长度；limited严格bool且等于total>sample。没有添加重复ID/排序审批或新事实语义。
- 旧selection预算诊断、旧schema字段、物理路径限制、引用绑定和资源上限保持。新扩展表达来源处理完整度，不提升覆盖率或成为用户权限。

RF只消费版本化wire DTO，没有import CWP实现。3个交付文件：

1. `scripts/company_wiki_narrative_contracts.py`，仅上述两处合同分支。
2. `tests/test_source_readability_wire.py`，正反例与旧wire兼容。
3. `tests/fixtures/source_readability_wire/cwp-handler-r5.json`，15,153B，从真实CWP handler golden提取context/spans。

源golden为CWP本计划`CWP-handler-processing-golden-r5.json`，67,411B、SHA`0bec092a852adacdbacf93806ff3ebf540925cd48c67e35d2acdefccdf9781ae`。complete/deferred均经真实HTML normalizer、0.9 selector、NarrativeSelectHandler与内存VerifiedContent port生成；deferred只模拟tagger LookupError，handler成功。RF使用自身合同验证该context/spans，同时用已有完整公开response夹具验证字节重签/传输路径。未伪造模型summary/receipt，也未将子合同golden联调冒称全公司E2E。

## 验证

宿主`C:/Miniconda/python.exe -B -X utf8`；`PYTHONPATH=scripts;tests`。

- RED：新测试27例中5F/22P，2.45s，当前RF拒绝合法新字段/diagnostic。
- 首GREEN：103P/3.87s；Ruff指出测试单行if格式，已格式化修正。自查补上非字符串diagnostic code短路判断，避免list/dict触发TypeError。
- 最终：`pytest tests/test_source_readability_wire.py tests/test_shared_reading_narrative_contract.py tests/test_reading_support_use.py -q --disable-warnings --tb=short`，**109P/4.57s**。
- Ruff两改动Python文件PASS；既有mypy入口`scripts/contracts/`及schema_compatibility/filing_fetch_client/trust_anchor/company_wiki_narrative_contracts，共14源PASS。
- 无模型、下载、生产DB/原件操作；测试只在自有worktree/pytest tmp内。

## 原仓WIP保护与自有工区

操作前4个既存WIP SHA（不暂存、不恢复、不stash）：

| 路径（assurance/runs/下） | SHA256 |
|---|---|
| daily_alert.jsonl | 8eaad095f964b3553df3e842a16383a50c87f540eeb2f7165072552f35e6b570 |
| monthly_manifest.json | 56d630107429cbcb646a951306dd1ea445dd5b3146236f34d0e8df953c103b9a |
| weekly_alert.jsonl | fc9ec2335b48d42921ca9c14c63363efca3b3096f967733e366f4dd463e4b7ed |
| weekly_manifest.json | e2e57f28fec7477af06029adcf187468701ab0305024993bfb2953bbd43cc5c0 |

普通沙箱Git在兄弟仓报`must be run in a work tree`；宿主Git正常，后续Git只用获准宿主。无RF AGENTS.md，不把缺文件报故障。

初始worktree add漏用`--no-checkout`，意外checkout50,607个已跟踪文件；观察后已立即sparse，仅代码/测试/运行时小目录，未第二次完整复制。之后只读测得自有树16,047,372逻辑B，不冒称峰值或实际释放物理B。正确后续方式是`--no-checkout`后先sparse；本次不是备份/恢复演练。发布后已核对绝对路径和Git clean，只用`git worktree remove`删除该自有树、`git branch -d`删已合并临时分支；原仓与原件不动。

## 独审、发布与安装收口

独立review_a已PASS，见`independent-wire-r5.md`及其probe/evidence；CWP真实handler18P、RF新32P，额外真实response验证schema1/2/3旧基线、schema4未知字段拒绝、golden与CWP原context/spans完全一致。不累计重叠检查。

正常commit钩子ruff/public-contract mypy/host-assumption均PASS；正常pre-push/CI同命令 **690P/1skip/36subtests，101.79s**，未no-verify。为避免相同提交重复推送测试，从干净工区一次`git push origin HEAD:main`将远端b093快进到957c6283，再在原main`git merge --ff-only codex/r5-reading-wire-sync`仅更新这3文件。最后`git ls-remote origin refs/heads/main`和local HEAD都为完整957c6283。子任务未观察远端CI run，不用本地绿冒称远端CI已完成。

canonical安装严格`--file scripts/company_wiki_narrative_contracts.py`，只向`.agents/.codex`两个物理目标各写1文件；`.claude`逻辑alias同实物。宿主`C:/Miniconda/python.exe`运行原canonical安装器，配置/output不参与。repeat同命令共0写，3个逻辑入口分别在`-I -B -X utf8`独立新进程加载安装runtime并消费complete/deferred真实handler golden，全部PASS。

作者工区候选runtime SHA为`ea05ba59fb06fcb64887591472041b76fa376396c52fee3f235296e591f0227e`（CRLF）；Git按既有规则归一LF后的main/installed SHA为 **`6ee455d2a8a4b48654c146a8f611ff2e2d8492c07c33630f9703ccfd584bfba7`**。这是标准源码换行规范化，不修改已冻结CWP原golden。安装目标原SHA为`14c3d5d6d3c88c4f8862b6cc464480555655cfa36492dad732151eb05fa7d02f`。

最初以候选工区为canonical的plan显示12项unselected drift，未对其apply；最终以发布main为canonical的apply/repeat报告unselected drift=0。未逐项调查两种canonical物理表示的差异，不把这个数值变化说成额外修复；实际written始终只有所选runtime。无整套覆盖/重建技能。

小收据：`RF-wire-install-apply.json`、`RF-wire-install-repeat.json`、`RF-wire-published-verification.json`。记录2物理写、repeat0、3fresh入口、完整commit及4WIP前后完全相同SHA。最终原main tracked status仅保留上表4项外来WIP，无本线遗留源码/测试未提交；自有工作树已不存在。本线按用户要求STOP，不恢复真实H1/摘要/模型/RF分析。
