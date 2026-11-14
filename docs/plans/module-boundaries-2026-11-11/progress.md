# 规划进度

## 2026-11-14 — 并线责任按模块归属

- 按用户最新要求明确：各模块 owner 在各自仓库完成未提交改动归因、分支适配、测试、提交、并线和推送；company-wiki 总控只负责 CWP 本仓工作、维护交接、只读核对公开接口和组合结果，不跨仓写代码或改 Git。
- StockWiki 正由另一并行项目修改，当前不触碰其工作区、计划或分支；等其 owner 最终交接后，由 StockWiki owner 自己处理并线。旧记录中“ROOT 在 StockWiki 工区接收”的表述已由 dispatch 当前规则取代。
- Dashboard 文档交接的三个历史 merge 已在用户澄清前完成，提交 `0b31f48`、`8111194`、`63f6820`，只包含文档；此后不再代 Dashboard owner 并线。
- 本次只更新 CWP 的 PWF 责任边界，没有跨仓代码修改或 Git 操作，也没有运行测试。

## 最新进展（2026-11-14）

- E01–E09 已关闭。发布最终 Dashboard `main@e1d1f92`，原件中断测试 3 项、独立审查通过。四个本轮测试工作树与四个测试目录已移除。父计划恢复半年报 R4 及后续业务验收。
- CWP 将来源目录状态留在读取 owner 中，消费端只拿所需能力。原件流只在实际字节验真与事务锁定后发出。独立审查通过后推送 `master@9e76592e1`。
- StockWiki C38/B03 与安装态公开来源读取进入本地 `master@21cf4891`。Dashboard 消费端移除了对 CWP 私有符号及源码布局的依赖。现有安装验收覆盖浏览、原件和摘要证据。
- 实跑 D4 跨仓 30/30、摘要缓存和恢复 36/36、真实募集说明书四根位置替换。RF → FF → CWP 三表新入口已由实际技能安装副本跑通，中微冻结快照两次复用均为零 HTTP，独立审查通过并推送 RF `fab819c2`。
- 当前版本及 E01–E09 验收见 [ROOT 组合记录](review/root_composition_20261114.md)。
- 续核本地改动时按实际 SHA 纠正了旧 Dashboard B-real 统计：120 条 staged path（108 同 blob、10 不同、2 个旧 UI 路径已迁移），没有整包合入。新增 C01证据、B-real模块适配、B03独审收据三张不重叠卡；R1的占位符及 `PENDING_ROUND4` 被登记为未完成，未冒称验收。RF `rf-impl` 历史工区已精确快进到当前 main；其他活跃证据、原件和 StockWiki remediation 保留。详见 [对账表](reconciliation.md) 和 [派发矩阵](dispatch.md)。
- CWP `.p3r-g3check-20261111` 精确回收16个派生夹具/DB文件（435,503字节）；MB-SID原11文件差异以SHA可复核gzip归档从53,423压至15,327字节；`revenue-forecast-audit` 两个已配套工具已本地提交 `fa0564f`，仓库无remote。CWP 本轮只改计划/交接和只读WIP归档，没有修改产品代码。

## A1核销交付（2026-11-11，历史）

- 用户新增授权后，三路独立agent逐模块审查Git refs、worktrees、dirty、PWF/交接/等价补丁；ROOT fetch六个有origin仓。StockWiki/Audit没有remote，未猜建。
- FF B34修复先复现当前main错误拒绝，独立候选保留当前市场/期次/issuer约束，相关回归176 passed/2 skip/38 subtests；追加4例后B34最终23 passed。独审PASS，d563b63快进main并推origin；候选工区回收。
- Dashboard既有4项WIP及边界测试整理，修同名收集冲突和过宽dynamic-import限制；189项平台/文档/预览与29项adapter/70subtests通过，独审PASS，2049356入main并推。审查期间另一harness接收的3个不重叠提交已观察保留，不冒称ROOT作者。24条真实owner stream setup仍缺CWP旧CLI，登记为未通过。
- 清理4个CWP、3个FF测试目录（4971文件/215903376字节）、7个空旧Temp工区、CWP source-facts 11+5重复源码、已吸收stash、ET旧eval、FF空placeholder。RF4生成文件完整保留原字节证据后restore。原始财报、费用stash、真实业务状态保留。
- 五张原卡加入A0逐项接收与测试边界；FF基线更新d563b63。RF B37、SW C38/B03、CWP历史端口差额明确分给对应owner/ROOT，SID有价值WIP先修再收。不新增重叠作者或逐步人工门。
- 完整30.17MB Git元数据快照无损压成1.54MB，字段/记录未裁，未复制任何源码树/原件。记录A1完成时M1/M2及原业务循环未启动；后续进度见下方新增条目。最终发布与清理结果看本轮review收据及Git记录。

以下为M0早先的历史进度，涉及“未测试/未改代码/未建工区”的描述仅对当时成立。

## 2026-11-11

- 用户要求先做完整模块路线图，再支持多个独立 harness。
- 已读父计划和当前收尾记录，选择本目录作为专门架构收口子计划；父计划仍保留业务主线责任。
- 调查和计划编制中；没有恢复源码实施。

### 调查与完整草案

- 三独立agent已完成只读CWP、采集侧、研究/消费者侧调查；ROOT核Git状态、现有测试/包边界与过期PWF口径。
- 当前CWP实际源清单479项已保存，旧索引461项缺口不冒逐文件审计。已证实缺口与仅需验证的风险分开列入boundary_matrix。
- 完成architecture/interfaces/acceptance/dispatch/handoff/runtime_verification、五张独立卡与source_inventory；没有建worktree、启动源码施工、网络/模型或全量测试。
- 方案独审提出fixture等待与旧B34可移动语义两问题，ROOT已改；canonical安装参数补清。等待最终复核。
- 父PWF CURRENT_STATUS/md/json、task_plan、HANDOFF、长期目标已转向本子计划优先，旧D4/D5/P3证据保留并限定范围。

### 规划交付

- 方案独审最终PASS，无未关闭本范围问题；两原阻断及三建议已修复并复核。报告review/plan_independent_review.md。
- 所有JSON解析、文档相对链接、五工区唯一性及14项责任唯一owner检查通过；git diff --check通过。没有运行pytest或生产端到端。
- 五卡状态READY_TO_DISPATCH_NOT_STARTED；M0完成，M1/M2待实施。原生goal经get_goal确认为paused，本轮未恢复源码实施。
- 本次只提交该子计划和父PWF的对齐文档；无源码/配置/原件修改，没有建工区、下载、模型调用或全局技能同步。提交/远端版本由Git记录，避免在文档中嵌入自身HEAD。


CI接线补记：FF `ac798a250b2310e0c2714053b08246ad94fffd0c` 已推main，将B34回归加入既有显式CI清单（原日常smoke不变）；CI清单+B34共38 passed/1.25s。首轮把scratch放在CWP内导致pytest根/JUnit前缀污染，仓外新Temp复验通过，未放宽断言。MB-FF基线采用该最终提交。完整远端CI尚未核验。

## 2026-11-11 — ROOT并入MB-RF可安全接收的B37切片

- 以RF最新main `33d880826` 为基线解决MB-RF PWF重叠，不改RF生产代码；部署及publication-source回归提交 `058be4fd6`，独立审查PASS后推送分支并快进RF main。
- 合并后B37相关suite为171 passed、1 skipped；部署用例38 passed；两次push smoke均12 passed、Ruff通过。最终PWF提交 `6341759b9` 已同步到 `codex/mb11-rf` 与 `origin/main`。
- 不合入B37 scope候选：发现私有跨模块调用、固定IFRS/12-31/单分部和无配置依据的结果上限，并会移除既有`import-rf-job`。已将根因、公开DTO及跨财年/多分部TDD范围记入MB-RF卡；不把未通过的scope测试标绿。
- 四张其他MB卡没有启动，ROOT仍负责StockWiki公开合同差额与最终跨模块组合；原业务主线goal保持paused。


## 2026-11-13 — 五条 owner 施工卡已并线

- MB-CWP：master 代码并线 ref 3ee8d0e；owner 138、exact history/stream 16、readiness history 4 均通过；root 修复 0a03b588 独审 PASS。Dashboard adapter 22/24，2项为消费端引用不存在于 CWP baseline 的私有名称。
- MB-FF：main 代码并线 ref 41acdc8；真实主线隔离套件 26 passed；包级 CI 1012 passed/2 skipped；独审 PASS。
- MB-RF：main 代码并线 ref 6b045b7；完整卡 561 passed、2 failed、3 skipped、31 subtests。两失败已在基线 6341759 复现，分别为历史 subprocess allowlist 和 B34 identity fixture；独审 PASS，不放宽断言。
- MB-ET：main 已包含交付；主线受影响测试 174 passed。包级唯一失败在 baseline 003c1c0 可复现；独审 PASS。
- MB-SID：v2-clean-rewrite 代码并线 ref 53b9358；集成单测 340 passed；独审 PASS。后续 PWF 收尾 commit 为 6742eda。
- 五条线的测试日志、主线ref和WIP处置均已进入各自PWF；原始业务/用户资料仍按各仓清单保留。
- 剩余不是交付包：StockWiki C38/B03 ROOT intake、E01-E09 public-interface composition，以及两个 Dashboard adapter 的 private-import compatibility failures。完整组合仍 NOT_RUN，不冒称模块阶段全结束。


## 2026-11-13 — 专用工区与 scratch 回收

- 已回收五个 MB delivery worktree 与三个 ROOT integration worktree。移除前逐一核实 clean；本轮仅回收这些精确命名工区，分支引用保留。
- FF handoff 指定的 mb11-ff-scratch 已核对仅含 pytest/review/runtime 测试产物后删除，共 5,030 个文件 / 18,119,347 字节；仓内最终日志与 manifest 保留。
- 原主仓数据、用户输入名单、业务状态、密钥文件、工具记忆、其他历史 PWF/未跟踪证据均保留。
- 当前 MB lane 文档的 worktree 字段表示历史交付路径；最新回收状态见 boundary_matrix.json。
