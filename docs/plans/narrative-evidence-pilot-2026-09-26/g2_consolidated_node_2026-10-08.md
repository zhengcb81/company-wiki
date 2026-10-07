# G2 最后两个大节点：覆盖对账与实施（2026-10-08）

目标 active。本卡补 G2 当前组合行为；R2 生产元数据、R3 真实模型、R5 收口仍未完成。

## 十四组当前对账

| 组 | 责任 | 当前实现 | 既有证据 |
|---|---|---|---|
| 00 | 默认 steady 与现场小迁移 | 已发布 | [核心](harness_lanes/results/g2_core_implementation_acceptance_2026-10-07.json) |
| 01/01b | 有效与精确来源读取指纹 | 已发布 | [精确来源](harness_lanes/results/g2_exact_source_binding_acceptance_2026-10-07.json) |
| 02 | 机器错误、版本化零重工恢复 | 已发布 | [核心](harness_lanes/results/g2_core_implementation_acceptance_2026-10-07.json) |
| 03 | 冻结 Pipeline 整族退休 | 已发布 | [G4](g4_main_acceptance_2026-10-07.md) |
| 04 | 旧维护公开入口退休 | 已发布 | [G3](g3_main_acceptance_2026-10-07.md) |
| 05 | RF 可选工程工具及数字诊断 | 已发布 | [RF](harness_lanes/results/g2_revenue-forecast_main_acceptance_2026-10-07.json)、[G3](g3_main_acceptance_2026-10-07.md) |
| 06 | StockWiki 日常检查 | 已合本地主线 | [SW](harness_lanes/results/g2_stockwiki_daily_main_acceptance_2026-10-07.json) |
| 07 | CWP 六旧工程入口及清单；固定哈希登记门退休 | 六入口已发布；哈希门收尾中 | [G5](g5_main_acceptance_2026-10-07.md) |
| 08 | FF 单意图与保留用户文件的安装 | 已发布、实际安装 | [G2-08](g2_ff_installation_acceptance_2026-10-07.md) |
| 09 | 实际 provider 能力与单网络意图 | 已验证；文案另核 | [实际链](harness_lanes/results/g2_chain_e2e_accepted_2026-10-07.json) |
| 10 | StockQA 统一短检查 | 已发布 | [SQA](harness_lanes/results/g2_stockqabyllm_main_acceptance_2026-10-07.json) |
| 11 | 摘要质量单一投影 | 已发布 | [核心](harness_lanes/results/g2_core_implementation_acceptance_2026-10-07.json) |
| 12 | 统一 ensure 与 FF→ET→CWP | 已发布 | [单意图](harness_lanes/results/g2_single_intent_main_acceptance_2026-10-07.json) |
| 13 | Store 轻构造、按 run 账目 | 已发布 | [Store](harness_lanes/results/g2_store_initialization_acceptance_2026-10-07.json) |

disabled/402/缺密钥是实际能力；未发现 ET 新的人为签收。不强加外仓任务。保留真实 SHA、身份/期间/公开日、locator、资源界限与跨仓只读。

## A/B 已有覆盖与补测

A 已有新库 steady、标签稳定/真实准入拒绝、版本化恢复、Store 零全库深检、退休 CLI，以及真实 TXT 迁 DB/raw/objects 根。B 已有实际 FF/CWP CLI 和 ET supervisor/worker 离线链、二次零 provider；RF/SW 公开日六正式 CLI；两套真实安装 help、重复零写及逐仓源码 CI。

仍补一次当前组合：S07 真实业务 IR PDF、S09 原语言 TXT、真正的中微 IR 管理办法，经登记、实际 batch 子进程和本地 HTTP，正式 ref/read/search/exact、当前已提交 RF/SW consumer，再同 run 零新 POST 恢复。旧两语言测试用合成 PDF，旧 R6 固定历史 RF，不能冒充当前组合。

**核读修正：**S08 周大生仍有黄金产品结构业务事实，不能当纯流程跳过。新易盛文件名叫“管理制度”，正文却是泰国产能、800G/LPO 等业务调研；不得仅凭文件名判无价值。补同节点真实错标题样本，验证仍有精选业务证据。真正纯流程原件是中微公司管理办法，SHA 76e146985388c926f2683e24af47e6a1ab0ce8a156864fb16e7df9a2cc99b678、167252 B、7页。核读页首/正文/尾页，原件不写。

## 写集与测试方法

新增 opt-in tests/integration/test_gate_simplification_source_chain.py；复用现有隔离目录、CLI、loopback、reader fixtures。显式只读原件/consumer 环境未给则准确 skip；MAIN 验收必须零 skip。真实字节复制到独立根，fixture Acme 身份/公开日明确不代表真实生产元数据。所选样本 SHA 校验，不下载、不翻译。

本地 HTTP 回答仅引用 prompt 片段，证明管线与回放，不代表真实供应商质量（R3负责）。三业务文档各一 POST，制度零 POST。三个原件与错标题原件、生产配置/DB、消费者 owner 文件只读保护。从 Git 导出已提交 consumer 到 owned 短根，不执行 owner 未提交代码，不写邻仓。

单次集中跑新组合 E2E 与已有公开退休 CLI/维护合同，不全 Unit、全九样本、付费、覆盖率或旧获取链。若产品失败，先保留反例再修所属层；没有新增行为时不制造产品改动。短根 .planning/g2ab 初始 absent，fixture finally 恢复子目录，结束再清完整 basetemp。小收据只保存 ID/SHA/版本/计数，不存正文或密钥。原核读 PNG 位于 .planning/g2ab-review，节点后清理。

## Next Step

MAIN 实施上述单次节点，核当前指导；通过后写结构化收据、标 G2 A/B 收口并回 R2。正常提交推送测试/指导/PWF，不增加 CI job 或小节点签收。

## 实际发现与先测后修

首次43项节点为42通过/1失败，零模型调用：同一制度再次有限登记后误报 capture.document_kind 冲突。根因不是身份或原件变化；scanner 的元数据合并把派生 document_kind 反写进 acquisition 原始声明，次轮又拿原 sidecar 比较，制造矛盾。四个独立反例 ir_policy/meeting_notice/10-K/Annual_Report 全部真实 RED。

登记层修复：分类与声明对齐共享同一显式类型映射；没有被分类器采用的原始类别不得被派生列覆写。实际 document_kind 比较沿用分类器大小写语义，真正不同声明仍记录冲突并由 reader 拒绝。不是在 reader 忽略所有冲突或新增放行表；旧已存在的冲突不自动擦除。当前生产零变更，R2按正式入口处理。

集中责任包增加既有 scanner、scoped registration、融资分类、B05 metadata provenance/shared reader；之后只重跑未通过的组合 E2E，42条未变的退休合同沿用首轮绿色结果。该发现是在原G2大节点内，不增加逐步签收。

## 本地主节点验收

当前60责任项8.13秒全通过，-W error无警告；42旧退休合同首轮通过沿用。最终组合E2E1项61.65秒通过、零skip，三业务POST/制度0POST，四份source定位回放与当前已提交RF/SW读一致，同run0新POST。包含真实错标题业务样本，不修改原文/S08 golden或把它误当skip。三个夹具错误在修复后已过，与四个真实产品RED分开记录。

[结构化收据](harness_lanes/results/g2_consolidated_node_2026-10-08.json)、[临时恢复](harness_lanes/results/g2_node_temp_cleanup_2026-10-08.json)：18owned项恢复absent，实测23373994B/440文件，18保护SHA不变，raw/owner删除0；五个历史根及交接工作树保留。源码发布和精确CI仍待本次正常提交推送；之后G2收口回R2，不声称全部PWF完成。

## 正常提交发现的最后一项人为门禁（组07）

正常提交被旧 host_assumption_guard 拒绝：真实制度与错标题业务原件的64位SHA未登记人工白名单。这不是原件不一致，也不是宿主路径问题；仅凭摘要字符串无法判断被哈希的载荷是否依赖宿主，人工登记又无法证明它。因此整条固定哈希许可规则及11项旧登记文件退休，不新增白名单、不拼接SHA逃检查、不跳过钩子。

先补独立行为测试：大小写SHA可直接用于验真；缺失或损坏的旧登记文件不阻断；同时存在真实宿主路径仍拒绝；当前路径基线损坏仍报错。旧实现5个反例失败、1个真实基线校验通过（1.16秒），之后移除哈希扫描/登记读取，保留AST路径、未守护能力、语法与不可读文件检查。整个28项责任包与正常提交钩子验收；此前通过的60项登记责任包及真实组合E2E没有行为变更，不重复跑。更新收据后正常提交推送、看精确HEAD的既有CI，不扩张CI。

首轮完整责任包27绿/1红，原因是路径基线含已于73de6be正式删除的cold_start/worker测试9条，不是新路径问题。核Git删除记录后仅减9条，71→62、新增0；11项哈希登记文件整份退休。最终28项4.67秒全绿，零skip/-W error，Ruff通过。真实字节SHA、身份/期间/locator及既有坏字节拒绝均未放松；未重跑已通过的大E2E，也未把新长测试加入提交钩子。

哈希门收尾另6项临时根/报告也恢复absent；本节点累计24项、23415676B/518文件，减项不涉及任何原件、owner或交接工作树。
