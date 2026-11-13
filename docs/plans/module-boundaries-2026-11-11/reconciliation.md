# 工作区、支线和接收顺序（本轮唯一处置表）

2026-11-11。用户明确授权：逐模块弄清未提交改动，删除确认无用内容，尽量接收未并线成果，余项加入原施工包。本轮完成调查、有限修复接收和清理；随后ROOT继续并入RF B37中可独立验收的compare及部署/来源回归切片。RF剩余scope/subject/verified-compare未并入；其他四张MB架构卡也未开始。原业务循环仍暂停。不得将本页写成“所有分支已合并/所有本地文件已清空”。

## 2026-11-13 ROOT最终并线状态补记

五条 MB owner 卡已完成审查、并线、推送：CWP / FF / RF / ET / SID。历史表格中“待实施/待派发/未并线”只描述2026-11-11的检查时点，均由本节及 module-boundaries-2026-11-11/progress.md 后续收据取代。各自详细测试、审查和远端ref见其 MB 卡 handoff 与总控 boundary_matrix.json。

整条模块化计划仍未完成：StockWiki C38/B03公开合同接收尚待ROOT执行；E01-E09组合矩阵保持 NOT_RUN；Dashboard adapter 的两个旧私有导入适配问题仍列在ROOT/消费者工作。不得将五卡完成说成整个模块计划或业务循环完成。

## 已实际执行

| 模块 | 本轮结果 | 下一步归属 |
|---|---|---|
| CWP | 62 refs、8工区、2 stash逐项查过；多数是主线祖先/已吸收。清理4个pytest目录、旧source-facts的11个tracked副本+5个重复测试、已吸收stash。补入W13历史最终独审/交接，明确不回退旧gate代码。 | MB-CWP A0：历史公开接口与当前owner接收，详下表。费用stash及独有审计材料保留。 |
| FF | B34明确null发布日期修复已受测接收为 `d563b630df887219039b9340703217b68da48c69`，CI清单接线为 `ac798a250b2310e0c2714053b08246ad94fffd0c`，main已推origin。旧job功能由57351d0/7d8392e吸收；其6个重复源码/测试已restore。删除3个pytest目录、空占位脚本和3个空Temp工区；本轮候选工区已回收。 | MB-FF不重做B34/job/旧companion；A0归档剩余旧交接材料，随后原六operation隔离工作。 |
| RF | 96 refs、62工区；未并线release有实际能力，不能全树覆盖新main。主工区4个assurance生成文件原字节存入本轮review/retained/rf_assurance，随后定点restore；删除1个空Temp工区。之后ROOT在MB-RF工区将compare与部署/来源测试切片并入RF main，当前远端head `6341759b9cdfd13e8aa7d51d5c755e361046da0c`。 | MB-RF剩余scope/subject/verified-compare按B2重做；研究草稿归父研究计划。四个含原文的残缺Temp工区保留。 |
| ET | 19 refs全部已为main祖先；删除旧翻译eval_results.json和1个空Temp工区；工具记忆保留。 | MB-ET没有旧分支漏并任务，继续原协议/worker边界任务。 |
| SID | 6 refs全部已为v2-clean-rewrite祖先；11项dirty属于旧下载器改进，有价值且有真实缺陷，保留；fixture生成脚本是独有出处。 | MB-SID A0先补RED并修复接收，不能直接commit旧WIP或恢复掉。 |
| StockWiki | 36 refs、30工区；18条非祖先主要共享C38/B03家族，存在公开身份/研究接口差额。删除2个空Temp工区。无remote。 | ROOT在StockWiki自己目录接收C38/B03最小合同，保留新source consumer/F05，不修改IQS或真实数据库。 |
| Audit | 22 refs全部已为main祖先；没有新代码需并线，无remote。 | ROOT只验公开消费；小型历史脚本/材料归档后回收。不强造改造卡。 |
| Dashboard | 原4项WIP及有限边界测试已接收为 `20493562f86b1351d97bc164bbc254efacddacdf`，main已推origin。修复同名测试收集冲突及“所有动态import一律禁止”的过宽规则。审查期间另一个harness接收了5a16ca7/c56e9ce/0addea2f，ROOT观察保留并验证，不冒称作者。 | 原Dashboard owner/D00；ROOT协同公开版本组合。24条真实stream用例缺少旧owner CLI工区，尚未通过，映射CWP T-READ。 |

before快照总计390个分支/remote refs、253个登记工区，另7个RF tag、2个CWP stash；含同一tip多个别名，不能据此计作390个待办。StockWiki/Audit没有remote是事实，不猜建或伪报已推送。全部目标：CWP/SW=master，FF/RF/ET/Audit/Dashboard=main，SID=v2-clean-rewrite。

此次确定删除的测试目录共4,971个文件、215,903,376字节（约205.9 MiB，约216 MB），另删除ET旧生成物等小件；不是全盘释放量。7个空旧worktree只有.git指针。本轮没有把原始财报当垃圾；RF Temp里的msft-20260630.htm等仍保留。历史日志、账目、作业数据库、工具记忆、密钥、报告/原件分别登记，不能靠git clean或reset掩盖未知用途。

## 接收路线与有限出口

只在实际需要的公开合同上接差额；旧实现已被更好的主线替代时，移植仍有用的反例并记录替代依据即可关闭，不制造第二套实现。祖先关系、补丁等价、同blob历史吸收、语义替代、未吸收能力分开记录。

| 顺序/责任 | 精确候选与工作 | 如何结束 |
|---|---|---|
| 本轮 ROOT（完成） | FF `53285c2`最小修复；Dashboard已有边界WIP；CWP W13历史文档；确定垃圾/重复源码清理 | 上表已执行结果、独审和定向回归；不是整个架构计划完成。 |
| MB-CWP A0→A/B/C，同一作者 | T-READ `3199adab`/X-C04流协议映射当前`stream_version`；T-CANON `62602102a`；T-B33 `dc837a21f`；T-B34 `29b562dac`；T-N4 `2b5bec914`；T-CONFIG旧M3四文件反例 | 先按review/cwp_review.md逐项重放当前公开行为，保留主线预算/解析/R7语义。支持的端口通过真实owner组合；已替代的候选给明确映射。B33历史独审未完成不能称旧包已验收。 |
| ROOT StockWiki（仓内独立接收） | `4532b0da` C38：43个touched产品路径，37 main缺失/6变化；`652f6a48` d00-b03只比三文件公开assessment差额。精确路径见research_review §4。 | 用既有CLI/contracts先验证，再按需移植，保留master当前source/F05与单一identity owner。用tmp状态证明读取/恢复/撤回；不对生产执行repair/apply。对应公开行为与当前消费者同时绿。无remote时交付本地master及原因，不假推送。 |
| MB-RF A0→A/B/C，同一作者 | `28d646d3` B37：19路径中6缺失/9变化/4相同；ROOT已把compare模块/CLI `e060a8607` 与部署/来源测试 `058be4fd6` 并入RF main，最终PWF提交 `6341759b9`。本轮171 passed、1 skipped，独立审查PASS。scope/subject候选私调私有符号、固定IFRS/12-31/单分部并会移除 `import-rf-job`，不原样接收。 | 下一步B2先设计公开DTO和TDD，覆盖不同会计准则/财年/多分部，再通过owner公开reader接线，保留job命令。旧公开compare合同/current job/source/目录回归通过后按模块并入；不并rf-input-prep的118个研究产物、不重跑预测。 |
| MB-SID A0→A/B/C，同一作者 | 11项旧WIP+fixture出处，路径/请求状态/tab范围先RED，按职责拆提交 | 新请求不继承旧CONFIRMED_EMPTY，路径按组件而非子串/反斜杠，空active tab不借另一tab；stdout仍单JSON，原配置/下载协议不回退。再完成原typed-error/metadata边界。 |
| MB-FF/ET | 已吸收旧分支不再合；登记历史资料与部署状态，执行原边界卡 | 当前公开runtime隔离测试与独审；历史收据不是当前测试。 |
| ROOT + Dashboard既有owner | 在上述owner交付后选择实际HEAD/CLI/schema/config/data-root组合；通过公开接口联调 | 重跑缺owner的24-case stream以及RF/SW公开入口；不猜路径/不复制邻仓内部。组合绿后才切本地配置引用和回收release工区。 |

除最后一行真实组合依赖外，五个模块各自在自己的工区A→B→C，可以并行。ROOT接收StockWiki与五卡写集合不重叠；CWP源码及组合runner继续遵守单作者安排。旧支线存在不自动阻止独立模块做TDD；新增共享协议变更由ROOT与相关owner对齐即可，不增加逐步人工许可。

## 已跑的测试与已知限制

- RF B37安全切片：合并compare/job/recovery/source-port/部署/来源组合 **171 passed、1 skipped、71.41秒**；部署文件单测 **38 passed**；独立审查PASS；两次推送前Ruff与固定smoke均通过，smoke各12 passed。代码/测试和PWF已推送并进入RF main。scope候选失败及原因见RF卡，不计为绿或完成。
- FF：旧main RED真实复现；相关四文件176 passed、2 existing skips、38 subtests/15.24s；最终B34含4条新反例23 passed/0.50s。两集合重叠，不相加。独立静态审查PASS；正常pre-commit ruff/mypy/host guard通过，push smoke11 passed。
- Dashboard：平台/文档/预览189 passed；两个adapter29 passed、70 subtests。独审PASS。旧24-case真实owner stream因找不到配置所需source_stream_cli入口在setup失败，没有删除用例或造fake owner转绿。另有既存Queue.put lifecycle warning，交原owner在stream组合阶段复核，不谎称全量绿。
- 初轮Dashboard同名测试收集冲突、ROOT忘建basetemp父目录均分别记录并修正；环境设置错误不归因成产品缺陷。
- W13仅补历史最终独审/交接：审于852dff28，后来main67439d0ac/819cef31a已替代旧gate实现；没有重跑旧全量测试。
- 本轮无真实下载/模型/付费操作，无全局技能部署。Git fetch/push发生。测试产物恢复及实际main/remote状态以review内最终收据为准。

## 剩余本地资料的处置，不留无主文件

| 资料 | owner/处置 |
|---|---|
| CWP M3/W04独有反例、T-CONFIG，R1的552份resume记录 | MB-CWP A0：反例映射现行语义；原始失败/审查资料去重归档。98个JSON只是clean-filter等价，不能当新源码合并。 |
| CWP剩余stash `18ac0d0562` | ROOT账目归档：保留独有llm_cost_log差量；两测试已吸收，39个旧删除不再执行。无需运行LLM。 |
| RF rf-impl的233份已与main同blob staged文件，余5个历史PWF；旧W04研究说明 | MB-RF A0先保留5份独有历史证据，再精确核销已吸收副本；研究说明回父计划，不能覆盖当前SKILL。 |
| SID11文件、capture_byd_fy2024_fixture.py、公司名单 | MB-SID按A0接收；公司名单是用户输入，保留；fixture脚本不得当生产公司特判执行。 |
| FF W06/W07输入/测试材料、旧job协议文档；SID G4镜像 | 对应MB卡A0归档唯一证据再回收，不能用旧complete/16case替代后来的41case收据。 |
| Dashboard all31组合110个已吸收blob、余10个旧文档/被替代UI；B03 repair_chain；m5独审补记 | Dashboard原owner核销/归档，B03等待SW对应公开协议；m5独审是有效证据，不能当临时文件删。 |
| RF/SW配置引用的release工区；含原文的RF Temp；.ff_jobs、StockWiki data、RF delivery/output、工具状态/记忆 | 明确保留，有实际部署/原件/业务状态/历史用途。接收成功并通过公开组合后才迁换引用；不做全量恢复演练或复制整库。 |

## 证据入口

逐ref/工区/文件的完整调查（before快照，不会在每次清理后改写历史）：

- [CWP](review/repo_reconciliation_20261111/cwp_review.md)
- [FF/ET/SID](review/repo_reconciliation_20261111/acquisition_review.md)
- [RF/StockWiki/Audit/Dashboard](review/repo_reconciliation_20261111/research_review.md)
- [FF本轮独审](review/repo_reconciliation_20261111/ff_merge_review.md)
- [本轮清理与计划一致性独审](review/repo_reconciliation_20261111/final_review.md)

执行结果、最终主线/remote与清理收据在同目录。完整before Git清单压缩保留为inventory_before.json.gz（无丢字段/裁记录）；Python标准库gzip.open即可读取。未来只更新本页及各卡A0状态，不另开一套平行“签收许可”。


CI接线补记：FF `ac798a250b2310e0c2714053b08246ad94fffd0c` 已推main，将B34回归加入既有显式CI清单（原日常smoke不变）；CI清单+B34共38 passed/1.25s。首轮把scratch放在CWP内导致pytest根/JUnit前缀污染，仓外新Temp复验通过，未放宽断言。MB-FF基线采用该最终提交。完整远端CI尚未核验。


## 2026-11-13 临时工区清理补记

五条已并线 MB delivery worktree 和三个 ROOT 集成 worktree 均已确认 clean 后回收，远端/本地交付分支保留。FF 可重建 scratch 另回收 5,030 个文件、18,119,347 字节。未清理其他公司工作区的未跟踪计划、业务输出、工具状态、原件、密钥、用户输入名单或审计证据。
