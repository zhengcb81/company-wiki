# 跨仓 planning 文档一致性独立审查

日期：2026-09-06。只读核对及文档建议；本文件不授权实施。审查者 sync_review 已完整读取 planning-with-files 技能。仅本文件由本审查者写入；主协调者负责实际同步及最终验证。

## 结论（同步前只读审查完成）

存在实质性状态冲突，不应改写冻结原文来消除。三仓 PLANNING_STATUS 仍将 GP-008 注册参数描述为未修复，引用9/3 daily 与 completed=0；新审计记录已观察9/5代码修复、daily period2及一个完成窗口。company-wiki 根入口仍写七份研报 sections=0，而 revenue 入口已写5/7。应将当前覆盖层统一至新审计，并保留旧快照。

历史 completed/accepted 需要明确为登记/窄范围历史完成，不能解释成原始痛点已解决。旧计划必须继续保留其时间和阶段语义；不得将117项机器账本改写或重签。

## 已读取范围

- 三仓 PLANNING_STATUS.md；活动 GP task_plan 全文。
- planning-sync-2026-09-04/verify_sync.py 全文及目录清单。
- worker v5 README；空间治理、章节提取、Portfolio 两组 CURRENT_STATUS。
- 本新审计 task_plan，包括用户本轮扩大文档同步授权。

## 第一批建议

1. 三仓 PLANNING_STATUS 加当前9/6覆盖，统一新审计/执行手册的权威路由。
2. GP六文档每份加一致的非执行性覆盖，旧批准与旧命令不自动继承为当前执行授权。
3. wiki四组 CURRENT_STATUS 按新发现补充“历史完成不代表原目标解决”；空间治理明确归档目录年龄不足以证明可安全 prune，worker恢复受阻。
4. v5仅活动入口与工作记忆可追加对接说明；baseline、import manifest、已签reviews不改。
5. verify_sync.py 是9/4快照校验，当前允许修改后其 company inventory hash 失败可能是预期漂移；不得改旧inventory hash来伪造原检查通过。应另做当前验证并保留历史检查器语义。

## 冻结证据与更新权限

已读取 plan_inputs 头尾、CA-306 card/receipt 相关正文及 test_ca306_terminal_closure.py 全文。该测试明确六个日期旧计划目录的历史字节和文件集合应保持不变，仅允许 TERMINAL_NOTICE 新文件；它实际测试存在弱点（前后自比较），并不使旧原文改写成为合理行为。

本轮直接使用 PowerShell 读取 manifest 并对每个唯一条目 SHA-256 复算：44 entries + 3 sources，其中 input_snapshot 重复，唯一46文件，missing=0、mismatch=0。不能把44说成全部唯一冻结文件。受保护范围包括 audit_review/README.md、PLAN_MANIFEST.md、input_snapshot.md；即使根README含“只能领取CA001”旧语句也不直接改写。三仓PLANNING_STATUS是外部覆盖层，负责说明它们不再是现行领取指令。

v5 baseline/import manifest/已签review保持原字节。其 README/三件套并非正式v5 manifest冻结输入，可以追加现行对接说明，不得把 V5-1/2 pending 改成完成。规划对接不代表旧v5正式冻结、更不代表worker恢复。

## 最小同步目标清单

| 目标 | 推荐修改 | 保留与禁止 |
|---|---|---|
| 三仓 PLANNING_STATUS.md | 统一9/6时点、HEAD快照/证据来源，链接新审计与新执行手册；明确旧accepted/GP完成非原目标验收 | 不改state/receipt/冻结manifest；历史观察需标日期 |
| revenue GP task_plan/findings/progress | 在旧9/5覆盖前加9/6覆盖；GP001–010参照gp-audit逐项PARTIAL/CONTRADICTED；消除“只剩部署时间”现行含义 | 保留9/2–5日志；原“唯一发现台账”只属旧GP范围，不排斥新审计 |
| revenue GP deployment guide | 明确参数源码已修，实际Action/自然触发仍未知；新daily不能证明自动任务触发 | 旧注册/手动运行/真实weekly下载命令是历史参考，当前不得凭文档直接运行 |
| revenue GP cohort request | 链接防cohort越界、安全终检及真实worker需求链；summary拒绝不是待绕过缺陷 | 历史批准与已处理产物保持；旧“DELETE即可回滚/无外部副作用/数据泄露无”不得用于当前方案 |
| revenue GP n1_r9 request | 一个历史完成窗口、close_allowed=false；列验收门缺陷而非只等另一窗口；旧批准需按新范围重新核对 | 不执行旧§3.2删除，不改批准签名、不把旧日历时间当放行 |
| wiki四组CURRENT_STATUS | 空间治理H01；章节5/7而非0；Portfolio已有B但跨root完整消费未解决；链接对应WP | 不重开Strategy A、不移动D盘、不把旧测试数更新成伪造当前结果 |
| wiki v5 README/task_plan/findings/progress | 加入新计划的对接与worker恢复前置说明，注明授权仍待定 | baseline/reviews/import manifest零改；V5-1/2仍pending |
| filing e2e/E2E_DESIGN.md | 可仅补链接，明确现有synthetic suite保留T1价值，不能替真实多root三进程T2/T3 | 不为了用户真实E2E要求把已有synthetic描述改成真实；不改代码/expected |
| wiki docs/archive/CURRENT_STATUS | 可补现行入口；维持研究型writer禁恢复 | 旧研究投资内容不复活 |
| 9/4 planning-sync任务/发现/进度 | 添加后继9/6状态路由与当时快照说明；原核验结论继续归属9/4–5 | 不重算company-inventory以抹掉导入hash漂移；历史审查报告不伪造新版verdict |

## 关键冲突的精确解释

1. **调度参数**：旧入口描述 --run-daily 未修，当前新gp-audit记录run-daily已修。纠正源码状态，但OS部署未知仍保留；不把一个新manifest推断为真实自然触发。
2. **观察窗口**：旧zero complete不再对应新观测，但ended_at完成窗口和status=observing应分开解释；仍close_allowed=false。保持“真实窗口+审核有效性”双门，不按时间自动放行。
3. **章节产物**：wiki根sections=0是旧快照，新审计5/7是后续历史执行记录；本轮没有生产重跑。两者不是同时间冲突数据，当前入口应用后者并注明来源日期。
4. **总完成**：117 accepted仅机器账本，不等于117原目标全部RESOLVED。GP005 197 passed缺fixture/oracle绑定，全绿不能压过新反证。
5. **v5唯一维护**：v5“唯一worker恢复目录”与新跨仓计划并非必须互斥：v5管历史输入/待冻结worker合同，新计划管全痛点实施依赖；两个入口应互链，发生冲突停在G0，不自行选宽松者。
6. **旧执行授权**：旧cohort批准和N1批准保留事实；本轮“同步+细化计划”不等于再次授权下载、API费、DB修改、删除、任务注册或恢复。

## 并发保护与验证建议

同步前观察到已存在dirty：wiki旧v1–v4文件删除、.tmp-build-registry.py删除、llm_cost_log.csv、section_extractor.py及contract test修改；filing E2E_DESIGN.md已修改；revenue GP六文件均已修改。不可reset/stash/checkout或全文覆盖。对拟写doc先记录当前bytes/hash，apply_patch插入覆盖；写前若hash变化，重读合并或停该文件，不能按旧缓存整文件重写。

同步后应另建当前文档验证：新入口链接存在、受保护46hash保持、v5导入保持、全部当前入口指向同一授权边界、修改清单只含授权文档、GP旧快照明确不是最新。旧verify_sync.py不应修改来强迫PASS；其company inventory包含活动v5三件套，合法同步会导致预期快照差异，应独立列清，不当作产品失败也不掩盖。

## 本审查局限与错误记录

本文件是修改前建议，不代表主协调者已完成同步，也不是最终新增执行手册审查。未重新全文读所有历史包（沿用9/4覆盖清单）；对冻结manifest46文件本轮重算hash。没有运行产品、SQLite、测试、下载、任务或worker。两个推测路径 contracts/CA-306* 与 tools/uc/terminal*.py不存在；随后改用实际receipts/CA-306和已存在test文件定位契约，未创建文件或重复失败。Git用户ignore读取Permission denied不影响tracked状态读，但不因此声称全目录绝对无遗漏。
