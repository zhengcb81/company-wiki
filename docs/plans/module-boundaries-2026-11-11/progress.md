# 规划进度

## 最新：A1核销交付（2026-11-11）

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
