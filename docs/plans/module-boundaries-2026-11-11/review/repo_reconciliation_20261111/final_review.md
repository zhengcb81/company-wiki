# A1 交付独立最终审查

日期：2026-11-11。结论：**PASS（A1 核销、有限接收、清理与后续归属交付）**。审查发现的两处当前状态冲突均已由 ROOT 修正并复核；没有剩余阻断项。本结论不表示全部分支已并线、全部工区干净、五卡已实施，或业务循环已恢复。

审查者未参与 ROOT 本轮清理、FF/Dashboard 接收或计划状态修改。本代理此前编写 CWP 只读调查报告；本次对 ROOT 汇总、执行证据与跨文档一致性作独立复核，不把自身旧调查当成第二次独立代码验收。未运行测试、安装、产品/供应商/模型入口，未修改外仓、Git、生产文件或旧收据；只写本报告。

## 1. 已核对的交付范围

- 子计划：README、reconciliation、task_plan、dispatch、boundary_matrix，以及五卡完整 A0 和相应写集合/基线/出口。
- 父计划：CURRENT_STATUS.md/json、HANDOFF.md 的当前入口和历史快照分界。
- 三份逐仓调查及 FF 独立接收报告；八仓 before/after 盘点、source-facts 机器清单/执行结果、stash、测试目录、空工区、RF 原字节归档、ET/FF 清理与本轮测试环境恢复收据。
- W13 当前 handoff.md/json、历史 review.md/json 与 measurement_caveat 的历史绑定。
- FF RED、最终受测日志；Dashboard 189 项日志、29 项/70 subtests 日志及 24 项缺 owner CLI 的原失败日志。只读取已有结果，没有独立重跑。

逐仓 before 数量来自 gzip 内完整清单；所有 390 个 ref 名均能在所属审查报告中定位，没有仅用总数替代分项表。工区完整路径及状态分别在 before 清单和审查表中；after 的实际工区数合计 246，与 253 减去 7 个旧空工区一致。本轮临时 FF 接收工区创建后回收，不增加净数。

| 仓库 | before refs / 工区 | after 工区 | 当前结论与剩余 owner |
|---|---:|---:|---|
| CWP | 62 / 8 | 8 | source-facts 重复源码与已吸收 stash 已处理；W13 只补历史文档；T-READ/CANON/B33/B34/N4/CONFIG 归 MB-CWP A0，账目 stash 归 ROOT |
| FF | 54 / 38 | 35 | d563b630df887219039b9340703217b68da48c69 已接收；旧 job/companion 不重复合，资料归档与原隔离任务归 MB-FF |
| RF | 96 / 62 | 61 | 主工区四个生成物已先归档再 restore；B37 合同差额归 MB-RF，研究材料回父计划，含原文/部署引用工区保留 |
| ET | 19 / 13 | 12 | refs 全是主线祖先；旧 eval 已清理；MB-ET 继续协议/worker 边界，不重做旧分支接收 |
| SID | 6 / 4 | 4 | 11 项 WIP 与 fixture 出处保留；MB-SID A0 先 RED、修状态/路径/tab 缺口，再接 typed error/metadata 工作 |
| StockWiki | 36 / 30 | 28 | ROOT 在 SW 自有隔离工区接收 C38/B03 最小公开合同；保留当前 source/F05；无 remote |
| Audit | 22 / 18 | 18 | refs 已吸收，ROOT 验公开消费，历史资料按归属归档；无 remote |
| Dashboard | 95 / 80 | 80 | 20493562f86b1351d97bc164bbc254efacddacdf 有限边界修复已接收；原 owner 接续，真实 stream 组合归 CWP T-READ + ROOT |

after 收据明确是“A1 动作之后、CWP 最终文档提交之前”。FF、Dashboard 的目标 main 与 origin tracking 均记录 0/0，其他有 origin 的目标也记录 0/0；SW/Audit 无 remote。CWP tracked 变化是本轮 PWF/W13 文档，SID 11 项仍在，其他主工区 tracked clean。这不等于历史各工区/全部未跟踪材料都已清空，也不证明远端完整 CI。

## 2. 安全处置与数据完整性

**before 原始盘点完整保留。** 独立解压 inventory_before.json.gz 到内存，实测 30,174,104 字节，SHA-256：

`4ecf6771e4417316c04da321f5eaee18d263547916a703f9e095a54d76fbd06e`

与 inventory_encoding.json 完全相同；压缩文件 1,535,403 字节。八仓数据可解析、refs/工区计数一致。审查报告中的引用均已改为 .json.gz，没有指向已删除未压缩文件的旧链接。没有为缩小证据删字段/裁记录。

**清理范围与收据一致。**

- 四个 CWP + 三个 FF 历史测试根：收据逐项合计 4,971 文件、215,903,376 字节；没有混计为全盘空间释放量。
- 七个旧空工区：3 FF、1 RF、1 ET、2 SW，收据均记录只剩 .git 指针和祖先依据。保留四个含原文的 RF Temp 工区。
- source-facts：11 tracked 恢复、5 untracked 重复测试删除，机器清单的 16 路径和旧 blob 证据保留；7 份 .planning 审计材料明确保留。
- stash 删除绑定 SHA 5b1415d6e36cf8476943567f59faf6a80a8061ba；18ac0d0562 的独有费用差量仍保留，没有应用其 39 个历史删除。
- RF 四份归档实际存在，逐文件 SHA-256 均与 cleanup_rf_assurance.json 相符。清理源工区生成物不被写成修复旧 canary/bound-stale 失败。
- ET eval 与 FF 六个旧 job 重复源码/测试的动作有收据；.ff_jobs、配置、用户名单、工具记忆、独有 fixture 出处和部署引用工区均有明确保留规则。
- test_environment_restored.json 记录本轮自有 Dashboard/FF scratch 已移除（90+3 文件）；这是本轮测试恢复，与上方历史清理量分开。

本审核对收据、归档哈希与 after 元数据，不以读取真实原件、递归删除或再跑产品测试来重复验证。

## 3. 有限接收的表述准确

FF 当前接受的是明确 null 发布日期的逻辑候选小修，保留主体/期间/市场绑定；不是获得已验真原件或 as-of availability。ff_merge_review 绑定最终三个 blob，并检查 ROOT 新增四条绑定反例。已读日志为集中 176 passed / 2 existing skips / 38 subtests，以及最终 B34 23 passed；集合有重叠，文档没有相加。

Dashboard 静态审查覆盖原四项 WIP、异常 traceback 语义、同名测试冲突与动态 import 规则误报修复。dashboard_verified_tests.log 的通过标记为 189；adapter focused 明示 29 passed / 70 subtests。原 24 项真实 stream 用例的 setup 失败保留，明确缺 source_stream_cli.py，未删用例或造 fake owner 冒充成功；Queue.put lifecycle warning 也已归原 owner 的组合阶段。另一 harness 的 5a16ca7/c56e9ce/0addea2 提交没有被冒称 ROOT 作者成果。

W13 handoff 顶部和 JSON 的 root_reconciliation 明示：历史被审 852dff28、来源 6efd4fccb、main 已由 67439d0ac/819cef31a 演进、本轮未重测当前 gate。scope-report 只补历史 measurement_caveat；没有恢复旧 gate 源码或把历史全量测试写成本轮通过。

因此 A1 的 PASS 允许交付这次有限接收与清理结果，不补签 M1/M2、真实 stream、预测或收费恢复。

## 4. 本审发现并已关闭的问题

| ID | 初次发现 | 修复与复核 |
|---|---|---|
| FR-01 | dispatch「可同时启动范围」与 task_plan M1 仍限制 ROOT 对 SW “只准备 fixture”，但 reconciliation/HANDOFF 已要求接收 C38/B03，存在可导致漏做工作的职责冲突。 | 两处现明确 SW 由 ROOT 在 SW 隔离工区接收差额，Audit 只验证；ROOT不写五卡源码、不派竞争Dashboard作者。与reconciliation及父HANDOFF一致。CLOSED。 |
| FR-02 | machine matrix 仍用 root_verification_only；SW只有PENDING_COMPOSITION、Dashboard旧baseline/existing_wip=true，next_action仍写本轮未实施且遗漏A0。 | 已改 root_owned_work；SW为PENDING_ROOT_INTAKE_AND_COMPOSITION，Dashboard用2049356、existing_wip=false并保留historical_baseline；next_action区分本轮有限修复与架构五卡未派发、业务循环未恢复。父CURRENT_STATUS.json同步。CLOSED。 |

SID 卡现在明确允许在新工区按 A0 接受 11 项差量，并禁止改原 WIP 工作树；没有继续存在“禁止接收”与A0冲突。RF 卡明确允许 B37 19路径差额，不全树覆盖，也保留主线 job/来源端口；旧 release 禁止项不再阻断本轮明确的差额接收。

五卡均为 READY_TO_DISPATCH_NOT_STARTED，目标分支与新工区互斥；FF 基线已更新为本轮最终接收提交，CWP 使用完整已提交源码基线，A0与历史取证 refs 分开。父状态与 README/task_plan 明示业务循环仍暂停；旧M0/P3阶段文字已放在历史快照语境，不能覆盖当前入口。

## 5. 保留的后续工作，不是 A1 阻断

CWP 历史公开接口、RF B37、SW C38/B03、SID 11项修复、Dashboard真实stream组合和独有账目/资料归档均有 owner、输入与有限出口，且已进入原五卡A0/ROOT队列。五卡未派发，M1/M2未完成，业务循环未恢复。最终 CWP 文档提交/推送属于 ROOT 的正常发布收尾；本报告不虚构它已发生。

不要求重跑已绿的无关全量套件、真实下载或付费预测。若 ROOT 仅补本审报告/发布SHA，既有行为验收无需重跑；若修改产品行为，则按相关 owner 的受影响测试验证。

## 6. 最终文档内容绑定

以下为修正后复核文件的 SHA-256；路径相对 C:/Users/郑曾波/Projects/company-wiki/docs/plans/module-boundaries-2026-11-11。后续仅补发布收据时应说明增量，不把本审绑定冒充后续源码测试。

| 文件 | SHA-256 |
|---|---|
| `README.md` | `5781b7d66e4d3b040141fb82b977ef9471c60b44df4fd4c5221e3b49c069c73e` |
| `reconciliation.md` | `ed265f1f5ed5a8b7ff7522e34d5591bb7d94c97431a325ba751f4accf74adfc3` |
| `task_plan.md` | `dac3be8ab6bcb4e7d025e338de570ad6c9058ecc959a00ee400bf9d26b6f7417` |
| `dispatch.md` | `58b26e04aef993d05cf3944e34df7232ff2d789d0d6f4a143bc36ca0ac8a8492` |
| `boundary_matrix.json` | `af57521becbf7441a1bc16dc9a591c91c011be1d3f5ab76ab5e56a3f9afb1592` |
| `harness_lanes/MB-CWP.md` | `a48ca4f5f4a0941a407254e9d5c0c043068ab90b817c99482d3138e2cf0e62b8` |
| `harness_lanes/MB-FF.md` | `022ad9bbbec263235fdd3563174dc338d83b2332f6712d6ce14eb8e10e85d23b` |
| `harness_lanes/MB-RF.md` | `1ee03d062ec1cc1efe8f33102081d538c20835a806e2523326e37b8a175fc579` |
| `harness_lanes/MB-ET.md` | `6ef92039ed83df269646b15c9e0aa72ed8839690bb1824df6eac768ec70d4d88` |
| `harness_lanes/MB-SID.md` | `e53bc3d3177299bbdfa91e9fd000019691500a2266724eee66894b7b7c6d7b5a` |
| `../du11-source-closure-2026-10-18/CURRENT_STATUS.md` | `842887f24b0325d2484765e25508c99265bb03cfce78995b55cf0e117f016ca4` |
| `../du11-source-closure-2026-10-18/CURRENT_STATUS.json` | `1d31957bcfaa391b17dd5fbef21def84f1c0a5abafc99ce7a3a0c0c80062700a` |
| `../du11-source-closure-2026-10-18/HANDOFF.md` | `1a7b4dd68ea3f00f649402a4f4017dfc93354080ffd2afe4752a230e102d106e` |

## 7. FF CI 接线追加复核（2026-11-11 20:38 UTC 之后）

**PASS；无新增阻断。** 仅复核最终小提交 `ac798a250b2310e0c2714053b08246ad94fffd0c`，未重跑整轮审计或任何测试。该提交直接继承产品接收 `d563b630df887219039b9340703217b68da48c69`；只修改三文件：`tools/ci_tests.py` 的既有 `CI_TESTS` 增加 `tests/b34/test_unknown_publication_candidate.py` 一个成员，`tests/test_ci_tests.py` 的既有清单合同增加同一必含成员，owner handoff 追加说明。没有放宽原断言或改变固定日常 smoke；两个产品文件与 B34 测试文件相对 d563 字节不变。

只读 Git 核对时 FF `main`、`origin/main` 均为 ac798。MB-FF 基线及 worktree 命令、boundary_matrix 的 lane/接收版本、父 CURRENT_STATUS.json 均已同步 ac798；reconciliation/progress 保留“产品修复 d563，CI 接线 ac798”的顺序。此增量明确取代上方较早的 FF 当前基线及相关文档 SHA 绑定，不改写原审查历史。远端完整 CI 仍未核验。

已读 `ff_ci_registration_final.log`：38 passed in 1.25s。首轮 `ff_ci_registration.log` 保留 1 failed / 37 passed，错误发生于继承 CWP pytest 根的 JUnit 前缀断言；提交未改该断言，改用仓外 Temp 后通过。`test_ci_environment_restored.json` 记录两个自有 probe scratch 均已清理，每处 9 文件。以上是 ROOT 执行收据，本审没有独立重跑。新增 B34 回归现在纳入既有完整 CI 清单，原 A1 PASS 保持。
