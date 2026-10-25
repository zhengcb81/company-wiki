# W18-CWP-HOLDOUT 冻结基线发现（2026-10-25）

生产代码基线 `ba8f8543`（只读分离 worktree），manifest/gold 冻结提交 `5e4488bb`。
8 样本全部回放成功，原件前后 SHA 不变，零模型 POST、零下载、零网络。
本文件是源侧观察，不是摘要质量或业务验收结论；全部 96 目标 `not_reviewed`。

## 基线总览

| 维度 | 结果 |
|---|---|
| 回放样本 | 8/8 ok（observe-only 与 observe+compile 两个 attempt 均完整保留） |
| 机械可见性（选中 span 支持锚点） | 10/96 |
| 机械可见性（编译模型输入含锚点） | 16/96 |
| 既无选中支持也无模型输入可见 | 73/96 |
| 锚点页未读/不可读 | 0/96（全部页面已解析，缺口不在可读性） |
| DU-BENCH 独立评估 | 8 PASS / 41 FAIL / 22 PARTIAL / 25 NOT_EVALUATED |
| 任务编译（零 POST） | 6/8 compiled；2/8 保留原始失败原因（见 F1/F2） |

逐样本明细见 `baseline-summary.json`；完整原始记录在两 attempt 目录（attempt.json +
逐样本 result.json，含每个锚点的 selected_locators/model_input_task_keys/on_read_page）。

## 产品 finding（交 ROOT，本卡不修生产代码）

**F1｜招股书 675 页：configured 批处理选择链拒绝编译（parser_incomplete）**
`w18-cn-beigene-ipo` 任务编译返回 `HOLDOUT_PREFLIGHT_SELECT_PARSER_INCOMPLETE`，
而同一原件在直连观察路径（parse_pdf_bytes + select_narrative_evidence）可选出
160 spans/2970 candidates。两条路径行为不一致：批处理 SourceVersionReader→
NarrativeSelectHandler 链的完整性门槛拒绝了该载体。原始原因已保留在
attempt 记录，未重试、未改判。

**F2｜海康 DOCX 电话会：批处理链语言抽取失败**
`w18-cn-hikvision-call-2024h1` 任务编译返回
`NarrativeLanguageError: SOURCE_LANGUAGE_TEXT_EXTRACTION_FAILED`。直连观察路径
（按 manifest 的 document_kind=investor_call_transcript 走 parse_transcript_text
路线，53/53 candidates 选中）成功。差异指向隔离湖 catalog 登记得出的 document
kind 与 manifest 声明 kind 的路由分歧（scan 登记未把该 DOCX 识别为电话会）。

**F3｜选择覆盖：73/96 业务目标既无选中支持也不进入模型输入**
六个业务样本均存在大面积缺口（百济 H1 0/14、港股年报 0/13、招股书 0/11、
紫金 2/13、百济 IR 2/14、Alphabet 1/13）。页面全部已读（unread_or_opaque=0），
缺口在候选生成/选择层，不是解析失败。注意：这不是调参依据——本卡金标是
冻结盲测集，ROOT 修复后须以新候选 commit 重跑本工具对照（H10 attempt 机制）。

**F4｜disposition_context 目标在 native 观察下 NOT_EVALUATED**
DU-BENCH 对 disposition_context 维度读取 `context_evidence` 层；基线观察无此层，
23 个该类目标如实报 NOT_EVALUATED（另有 2 个 document_meta 目标 basis 检查
NOT_EVALUATED）。这是观察层缺口，不是样本问题。

## 独立审查与 gold v2 修正（2026-10-25）

三个未参与实现的独立审查 agent 完成审查（原报告在 delivery/w18/review/）：
源侧 gold 审查 113/113 锚点全部逐字验证通过，发现 1 项 P2（招股书样本一条
must_not_assert 误禁真命题"百泽安先于百悦泽在中国销售"——原文"分别于2020年
6月和2020年3月"映射百泽安更早）与 5 项 P3；工程审查确认 H01-H11 全部 PASS
与 6 项 P3；独立重放验证 PASS（重放确定性逐字节成立、失败/清理/不覆盖链
完整、否定/条件与期间单位错配双反例确认词匹配不代签业务通过）。

按 H10 版本化流程处置：v1 oracle 内容归档于 tools/holdout_replay/gold/
archive-v1/（工作树拷贝与冻结提交内容一致；字节级 v1 以冻结提交 5e4488bb
的 git blob 为准，仍可重放），v2 修正逐项源侧理由记录于
tools/holdout_replay/gold_corrections.json（F1 禁令方向反转、F2 引句补全、
F3 为未覆盖数值补锚/扩跨、F5 恢复原文措辞、F6 真值对照移出禁令串；
96 目标/116 锚点全部重新独立验证）。工程 P3 修复：D1 选择器版本双盖章
（observe 路径跟随生产默认、compile 路径钉 0.9.0，逐工件记录
selector_versions）、D2 零网络字段注明 by-construction、D3 manifest 拒绝
跨样本重复原件 SHA、D4 bootstrap-lake 越界路径 JSON refused、D5 worker 结果
损坏按原始错误记录不崩收据、D6 DU-BENCH 模块 import 根入档。

## 观察口径说明（H08）

- 机械可见性 = 锚点引句出现在选中 span 文本或编译任务材料文本中；词匹配
  不等于业务事实 PASS，模型输入可见性不等于摘要覆盖率。
- 全部 96 目标 summary_status=not_reviewed：无模型响应、无独立语义审查。
- DUB 评估中的 PARTIAL/NOT_EVALUATED 语义与既有 DU-BENCH 相同。

## 边界

- 百济 IR 的 2 个 disposition_context 目标（ir-phase3-cost-share、
  ir-ms-btk-forecast）有选中支持但 DUB 报 NOT_EVALUATED：两套口径（机械
  可见性 vs DU 维度评估）都原样保留，不互改。
- 11 个目标仅在模型输入任务材料中出现（含任务上下文），不在选中 span 行中；
  已逐项标注 model_input_support=true/selected_support=false。
- 选择器代际披露（D1）：直连观察路径用生产默认选择器，compile 路径按 v4
  scoped projection 要求钉 0.9.0；两条可见性口径实际测的是不同 selector 代，
  两个版本号已逐工件盖章（result.selector_versions），F1/F2 的路径差异分析
  不得忽略该因素。attempt-3（gold v2）起该披露生效。
