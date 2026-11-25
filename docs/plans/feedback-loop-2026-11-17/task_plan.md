# 工程反馈循环总调度 PWF

2026-11-25。此页是反馈工程的唯一调度入口。S2、S3/S4 以及接续的 F4 现场范围均已验收。12 仓沿同一个 Windows 恢复任务运行，新失败按原责任边界进入反馈。历史缺证与业务主线按各自状态接续。 [F4 现场验收](f4-resume-runtime-20261125.md) · [原失败覆盖审计](failure-coverage-20261121.md) · [分仓上线范围](f4-rollout.md) · [父计划](../du11-source-closure-2026-10-18/CURRENT_STATUS.md) · [验收进度](progress.md)

## 负责什么

真实公司运行、单模块 E2E 和独立业务审查都能留下运行步骤及可重现的偏差。每个模块先记录观察，再由能修复它的责任仓确定根因、在本仓 PWF 安排改进、用本仓技能修复并固化回归。修复后由最早观察到问题的消费方验证真正采用的版本。跨仓只传公开值。ROOT 负责协议、宿主调度、组合验收、异常恢复和跨仓联动，业务模块分别拥有原件、研究判断、运行及问题登记。

## 实施顺序和验收

| 节点 | 实施者与具体工作 | 可核对的交付 |
|---|---|---|
| F0 分仓设计 | ROOT 核当前分支、在写文件、原生收据和公开接口。冻结[最小格式](interfaces.md)，在 12 个自有模块的 PWF 写入口、原生场景、范围、TDD 和回告。Dayu 经 CWP 适配器观测。 | 各卡能独立启动。总控和外派写集合互斥；历史 RF 周跑、CWP 重复限额、投资者关系摘要归属三类可区分。 |
| F1 总控离线实施 | ROOT 先写重放、反例和并发/中断测试，实现读取专用 JSONL、保留原始发生身份、分诊、幂等派发、修复版本回到发现方、写回责任仓。现有宿主承担持久作业，ROOT 可以从同一输入重建进度。 | 给一份观察，公开命令可驱动一次处理。重复或中断不会多开修复；合法拒绝不开单；未知费用只核对；旧消费版本不能关闭问题。大节点独审在最终代码上复核。 |
| F2 本仓接入 | ET、SID、IR、FF 短请求、MC 转录发布均已签收。StockQA、StockWiki、IQS、Dashboard 已按正式交付顺序验收。后续重叠写入在原线排队。[分工与施工包](dispatch.md) | 各 owner 交专用观察、成功和偏差/未知样本、离线复现、清理、修理技能及独审版本。STOP 或发布状态按实际远端或本地主线记录。 |
| F3 无人值守真实试点 | ROOT 接入可按 action ID 查询和幂等提交的实际 agent 宿主。依现有授权、模型配置和唯一预算运行 P1，依次比较自动选材、正式生成、同 run/跨 run 恢复、RF 采用。 | [CWP 试点](company-wiki.md)记录真实 run、版本、引用、用量及 RF 消费版本。停一次总控后恢复，断言未重复付费和下载，登记日志占用。把合法对照与未参与修复的第二文种/公司交独立审查。 |
| F4 扩展与运维 | 12 仓统一任务、原动作恢复、CWP 强停补投和分诊诊断交接已验收 | 指定场景验证原动作恢复与回告。现场收据保留旧缺证、未知费用及在线服务依赖。 [现场验收](f4-resume-runtime-20261125.md) · [宿主上线范围](f4-rollout.md#统一运行与接续) |

## 启动和恢复

实施人员先读[当前进度](progress.md)和[调查依据](findings.md)。正常路径为运行出观察 → 本仓有据分诊 → 责任仓修复 → 发现方复验 → 责任仓登记。存储在 owner 现有运行区或问题卡中。总控仅消费明确交付的观察和可核对宿主作业。已知过期配置、服务不可用、有效预算耗尽分别保留原因和恢复条件。重放的版本、来源或材料不足时保留未验证。旧失败和付款状态按原事实读。

F3a 的真实只读 agent 和 FF 原生复用经中断恢复。F3b 将真实新摘要送入公开复验和 RF 正式模型。ROOT 在各 owner 正式交接后逐项组合验收。固定公司池按业务父计划运行。[真实宿主收据](f3a-host-acceptance.md) · [真实业务收据](f3b-live-acceptance.md)

F3c 用已有真实响应修正草稿限定与精选，并用 A 股、港股、美股的五份原文复验。F2 首批三仓已把公开观察接入 ROOT 只读导入。F4 已在 CWP 与 FF 核验缺终态对账和一条无人值守修理与回告链，其他 owner 按[分工](dispatch.md)接续。业务线按父计划在下一家公司验证现版本的生成与采用。[保存响应验收](f3c-saved-response-acceptance.md)

真实宿主选型、异步接线、原始作业核对、实际 P1 故障与消费复验的执行顺序见[ROOT 施工细则](host-integration.md)。

## 2026-11-24 日志与错误可复现性深度审计补充（F5）

S1 的 CWP、ET、SID 等补修见[分仓发布台账](s1-p0-blackhole-plan.md)。S2 计划节点已验收，发布证据见 [S2 收尾台账](s2-closeout-20261125.md)。S3/S4 的本轮分仓实现、独审、发布和行为回归均已接收。[S3/S4 分仓台账](../module-boundaries-2026-11-11/s3-s4-owner-rollout-20261125.md)

**背景与根因**：2026-11-24 对全部 12 个自有模块（1,654 个生产 Python 文件 + Dashboard 前端）做只读源码审计，查明此前“若干次错误未被记录、无法复现”的四类共用根因（完整逐行证据见 [全 12 模块深度审计报告](../module-boundaries-2026-11-11/review/full-12-module-architecture-logging-audit-20261124.md)）：

1. **系统性标准日志真空**：9/12 仓零 `logging` 处理器/文件配置（CWP 233/243 含 `except` 文件无日志、FF 0/63、Audit 0/45、IQS 0/315、IR 0/8、RF 0 配置、StockWiki 0 配置、Dashboard HTTP/Service/Feedback 0 日志）；**`StockInfoDLSimple/src/logger.py:15,39` 导入期空句柄短路导致 `config["logging"]` 永久失效（零日志文件写出）**；**`MeetingConverter/engines/mimo.py:137` 存在线上 P0 Bug（调用未定义 `logger.warning`，首次重试即抛 `NameError` 覆盖真实错误）**。
2. **安全脱敏误伤本地诊断（“先销毁堆栈，再返安全码”）**：CWP 95 处 `raise ... from None` 前未落本地日志；ET `transcript_api.py:804,1142,1404` 吞全部异常为裸 `unexpected_provider_failure` 且 `retrieval_runtime.py` 崩溃后立即删 `worker_stderr.log`；StockQA 10 处丢 `from e` + 61 处 `logger.error` 缺 `exc_info=True` + LLM Provider 仅记异常类名并重试代码 Bug；RF `filing_fetch_client.py:373` 报错不读 `stderr`、`rf_job_facade.py:940` 丢 `from exc`；StockWiki `documents.py`/`llm_usage_ledger.py` 宽泛吞错返 `None`/`{}`；IQS 62 处宽泛静默吞错；Dashboard `adapters/common.py:fail()` 丢 cause 且前端 `api.ts` 丢弃 `correlation_id`。
3. **子进程 `stderr=DEVNULL` 黑洞**：CWP 7 处（`tools/feedback_loop/local_host.py` 4 处、`intake.py`、`hook.py`、`isolated_ocr.py`）、FF `ff_scheduled_windows.py:153`（双 `DEVNULL`）、StockQA `quick_scan_owner_research.py:462`、Audit `run_pool_progress_e2e.py:218`。
4. **F4 反馈旁路写失败静默吞异常**：CWP/FF/StockWiki/Audit/IR/Dashboard/MC 旁路写盘异常均被静默吞掉（MC `core/feedback.py:1086` 甚至吞 `BaseException`），缺少 stderr 兜底告警，磁盘/权限/序列化异常会导致业务日志与 F4 观察双归零。

### F5 实施范围与状态

| 节点 | 实施内容 | 可核对交付 |
|---|---|---|
| F5-1 P0 黑洞止血（S1） | 修 MC `mimo.py:137` `NameError` 与 `BaseException`；修 SID 死文件日志与 `browser.py:645` 分页截断；清 CWP(7)/FF(1)/StockQA(1) 业务子进程 `stderr=DEVNULL`；修 ET `transcript_api` 静默吞错与 `worker_stderr.log` 提前删除；修 RF `filing_fetch_client` 丢 `stderr`、StockWiki 解析/计费静默返 `None`、StockQA LLM Provider 仅记类名。 | 每项先写 RED 复现用例，修复后能从新进程/轮转日志精确读出原异常类型、脱敏原因链与堆栈。 |
| F5-2 双层日志（S2，局部切片已验收；全入口目标未完成） | 统一本地故障记录、脱敏和 F4 公开观察的字段语义，沿现有入口分仓实现。 | 每仓一个 F4 试点节点已用真实故障入口、合法对照和新进程冷查验收。[S2 验收记录](s2-closeout-20261125.md)。**2026-11-25 复审：0/12 仓实现全入口本地轮转日志，多仓旁路写失败仍无 stderr 告警，见 F5-4/S5。** |
| F5-3 回归覆盖（S4，本轮已验收） | 在已复现的失败边界补行为用例，对明确且可归因的越层行为沿已有接口检查复验。 | 覆盖正常输入、CLI/HTTP 格式、诊断失败时的业务结果。受验版本和组合测试绑定分仓台账。 |

## S3/S4 收口后的 F4 接续

S3/S4 的本轮分仓接口、回归、正式版本及组合验收已完成。F4 沿用 [S2 收尾台账](s2-closeout-20261125.md) 和 [既有宿主验证](f4-rollout.md) 的合格证据。日常故障继续由发现仓记录、归因和复验。

11 月 25 日 10:39 UTC 的原有 11 仓任务处理 307 条，299 个包待续。接入 StockWiki 后仍是同一当前用户任务和原两类触发，12 仓首轮定时实际处理 437 条，369 个包待续，唤醒零。待续数是状态快照。有新证据时按原相关号回查。存在缺证的旧记录保留原状态。[现场时间和范围](f4-resume-runtime-20261125.md)

StockWiki 已用同一正式公开入口在隔离环境验证实际故障和冷读，接入任务时使用独立的原生收件路径。历史 76 条保留旧路径，其中三条已知是隔离 Dashboard/IQS 负例。新路径等原工作自然产生日志，旧记录仍按原编号可查。

本轮接续项已核验。最终宿主 `fc2e0f31c` 通过独审、同版 CI 和真实定时收件。原 CWP 分诊只启动一次，原错误能从成对的原生观察和诊断提取为结构化事实。Dashboard 的在线快扫读路径随业务站点可用性运行，冷读已验证。具体缺证保留在原回执与[现场台账](f4-resume-runtime-20261125.md)。后续业务按父计划 W12 的原范围接续。

| 先后 | 责任与动作 | 完成证据 |
|---|---|---|
| 1 | 各 owner 核对正在运行的检出、安装包及配置引用，优先 StockWiki 与 Dashboard 原线。ROOT 对照 S3/S4 的正式采用证据和当前统一 Windows 恢复任务。StockWiki 先从其本仓公开入口确认正式观察，合格后接入同一任务。 | 同一任务查回各仓原观察，第二次查询无新增。服务返回、前端相关号、所属仓原因和原作业能贯通。 |
| 2 | RF 与 Audit 查回 W12 已记录的原会话和原作业，取回待证的隔离分诊终态。FF 与 ET 按原动作核对历史部分成功和用量未知。保留来源记录确实无法还原的历史原因。 | 从公开查询冷读原 ID、最终状态及费用含义。恢复新增下载、转录、模型请求与费用均为零。未能确认的费用继续写为未知。 |
| 3 | ROOT 用现有宿主和观察/动作库完成一次实际无人值守端到端。受验故障含 CWP 已知的断点，原失败已提交到 SQLite、进程在观察投递前终止。之后查回原动作、分诊、修复、复验与持久回告。拒绝先审视门禁是否必要。 | 独审同一最终版本。原调用、故障、重启后补投、结算与回告可逐项核对。重复恢复沿用相同观察身份。确认故障关闭后再转入父计划的真实公司和业务摘要剩余项。 |

**CWP 强停验收细则**

1. 在隔离 AUTO 库中起一个已租约的原尝试，强停 Worker。回收进程完成原尝试的失败写入后，在观察发布前强停该进程。旧版有 `LEASE_EXPIRED` 而没有 ready 观察，记录为回归的失败对照。
2. 在原 AUTO 尝试终态事务中保留同一失败的待投递标记与脱敏证据。维护过程先提交，再通过现有 native 发布器投递。同一观察标识复用既有文件，F4 确认后即使 ready 标记已消失，也应能查回已发布正文。只有现有 native 接收路径读得回观察时才清除待投递标记。历史未记录的行不补造，普通 stdout 和可选追加日志不参与确认。
3. 同一隔离库和收件目录重启两次，查到一个原失败观察并从正式反馈读取端复核原因。再复现观察已落盘、确认前强停，仍只有一个原观察。并发回收、限域维护和普通业务重试保留原语义。如果宿主停止时业务 supervisor 也已退出，仍须证明 F4 能通过 CWP 公开维护口只补投观察。使用本机宿主复验与回告，不接触真实付费供应商。与原 `AutomationStore` 的作业和费用记录逐项对照。

[当前 F4 现场复验](f4-resume-runtime-20261125.md) · [S3/S4 分仓交付](../module-boundaries-2026-11-11/s3-s4-owner-rollout-20261125.md) · [此前故障复原证据](replay-coverage-20261123.md) · [业务 W12 父计划](../du11-source-closure-2026-10-18/CURRENT_STATUS.md)


## 2026-11-25 S5 修复与实机对齐

实现次序和跨仓接口见 [S5 实施计划](s5-closeout-plan-20261125.md)。[逐项台账](s5-verification-20261125.md)记录真实故障、已经修复的观察、正式版发布与实际启用。复审报告为当时的调查输入。

完整证据（精确 `file:line`、提交号）见 [S1–S4 实施后全 12 模块复审报告](../module-boundaries-2026-11-11/review/s1-s4-post-rollout-12-module-audit-20261125.md)。此前“S2、S3/S4 已验收”仅指局部切片；下列缺口须在 S5 收口，每项沿 RED→GREEN、由责任仓修复。

| 优先级 | 节点 | 内容 | 验收 |
|---|---|---|---|
| P0 | S5-10 现场与全局技能对齐 | 各仓采用本轮已验正式版。统一 RF 的 `report` 和 `reconcile` 源码，保留原状态目录和旧回告查询。FF、IQS、StockQA、IR 采用各自正式入口；保护有在途修改的主工区。Audit 补安装副本。核查 RF 旧 SQLite canary 是否仍存在于受管部署。Dashboard 当前 F4 使用正式隔离检出，新版本沿该部署职责切换。 | 原作业可冷读，受影响技能与发行文件一致，部署可重复。真实下载、转录和新计费为零。 |
| P0 | S5-2 高危新缺陷 | StockQA `Authorization: Bearer` 漏脱敏、stderr 取头部、`_environment` 漏改；RF 10 个新测试补入 `CI_TESTS`、恢复 `filing_fetch_client` stderr 本地日志；MC `transcribe.py` 死配置、CLI 优先级倒置、`normalize_config` 绕过校验、`ffmpeg` 退出码、`HTTPError` 未关闭；ET worker `stderr=DEVNULL` 与 `--report-usage` 关闭日志、`scraper.py` manifest 失败仍退出 0、`transcript_feedback.py:1439` 捕获 `BaseException`；Audit `exported_without_journal` 漏存 failure；Dashboard 幽灵 `correlation_id`；CWP `triage_diagnostic` 丢非内建异常；FF `_BUILTIN_EXCEPTIONS` 抹除异常；IR `JSONDecodeError` 误判重试；IQS `post_json` 漏捕 `IncompleteRead` 及同阶段去重吞故障；StockWiki `complete()` 跨库提交顺序；SID `setup_logger` 句柄泄漏及 `company_wiki_adapter_cli` 零文件日志。 | 每项有失败复现与同入口复验。 |
| P1 | S5-3 全入口本地轮转日志 | 为 CWP、FF、RF、Audit、StockWiki、IQS、Dashboard、IR、MC、ET、StockQA 补轮转脱敏日志；F4 旁路写失败统一 stderr 告警（FF、RF、StockWiki、ET、IR、Dashboard）；`from None` 前先记日志。 | 新进程冷查可读出原异常类型与脱敏因果链。 |
| P2 | S5-4 静态门禁与 CI | 修复 `layer_boundary_scan.py` 六个盲区；FF 边界测试改为全目录扫描；补 ET、SID、IQS、Dashboard、IR 远端 CI；StockWiki/StockQA 新测试入日常清单。 | 门禁能区分合法实现与已证绕行。 |
