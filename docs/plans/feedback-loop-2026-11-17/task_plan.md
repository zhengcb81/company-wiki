# 工程反馈循环总调度 PWF

2026-11-21。此页是反馈工程的唯一调度入口。12 个本机模块的端口和原有指定场景已验收。逐仓故障注入确认 12 仓的日常入口都有覆盖缺口。当前优先修原执行原因丢失、业务失败误判和失败写入丢失。业务数据可用性和公司池以父计划为准。 [最新失败覆盖审计](failure-coverage-20261121.md) · [分仓上线范围](f4-rollout.md) · [父计划](../du11-source-closure-2026-10-18/CURRENT_STATUS.md) · [验收进度](progress.md)

## 负责什么

真实公司运行、单模块 E2E 和独立业务审查都能留下运行步骤及可重现的偏差。每个模块先记录观察，再由能修复它的责任仓确定根因、在本仓 PWF 安排改进、用本仓技能修复并固化回归。修复后由最早观察到问题的消费方验证真正采用的版本。跨仓只传公开值。ROOT 负责协议、宿主调度、组合验收、异常恢复和跨仓联动，业务模块分别拥有原件、研究判断、运行及问题登记。

## 实施顺序和验收

| 节点 | 实施者与具体工作 | 可核对的交付 |
|---|---|---|
| F0 分仓设计 | ROOT 核当前分支、在写文件、原生收据和公开接口。冻结[最小格式](interfaces.md)，在 12 个自有模块的 PWF 写入口、原生场景、范围、TDD 和回告。Dayu 经 CWP 适配器观测。 | 各卡能独立启动。总控和外派写集合互斥；历史 RF 周跑、CWP 重复限额、投资者关系摘要归属三类可区分。 |
| F1 总控离线实施 | ROOT 先写重放、反例和并发/中断测试，实现读取专用 JSONL、保留原始发生身份、分诊、幂等派发、修复版本回到发现方、写回责任仓。现有宿主承担持久作业，ROOT 可以从同一输入重建进度。 | 给一份观察，公开命令可驱动一次处理。重复或中断不会多开修复；合法拒绝不开单；未知费用只核对；旧消费版本不能关闭问题。大节点独审在最终代码上复核。 |
| F2 本仓接入 | ET、SID、IR、FF 短请求、MC 转录发布均已签收。StockQA、StockWiki、IQS、Dashboard 已按正式交付顺序验收。后续重叠写入在原线排队。[分工与施工包](dispatch.md) | 各 owner 交专用观察、成功和偏差/未知样本、离线复现、清理、修理技能及独审版本。STOP 或发布状态按实际远端或本地主线记录。 |
| F3 无人值守真实试点 | ROOT 接入可按 action ID 查询和幂等提交的实际 agent 宿主。依现有授权、模型配置和唯一预算运行 P1，依次比较自动选材、正式生成、同 run/跨 run 恢复、RF 采用。 | [CWP 试点](company-wiki.md)记录真实 run、版本、引用、用量及 RF 消费版本。停一次总控后恢复，断言未重复付费和下载，登记日志占用。把合法对照与未参与修复的第二文种/公司交独立审查。 |
| F4 扩展与运维 | 原分仓接线已验收。ET、SID、MC 三张日常失败覆盖卡接收、独审、发布并接入定时恢复 | 指定场景的原动作恢复与回告已验证。全入口的覆盖和各仓余项见[最新分仓结果](failure-coverage-owners.md)。[宿主上线范围](f4-rollout.md#统一运行与接续) |

## 启动和恢复

实施人员先读[当前进度](progress.md)和[调查依据](findings.md)。正常路径为运行出观察 → 本仓有据分诊 → 责任仓修复 → 发现方复验 → 责任仓登记。存储在 owner 现有运行区或问题卡中。总控仅消费明确交付的观察和可核对宿主作业。已知过期配置、服务不可用、有效预算耗尽分别保留原因和恢复条件。重放的版本、来源或材料不足时保留未验证。旧失败和付款状态按原事实读。

F3a 的真实只读 agent 和 FF 原生复用经中断恢复。F3b 将真实新摘要送入公开复验和 RF 正式模型。ROOT 在各 owner 正式交接后逐项组合验收。固定公司池按业务父计划运行。[真实宿主收据](f3a-host-acceptance.md) · [真实业务收据](f3b-live-acceptance.md)

F3c 用已有真实响应修正草稿限定与精选，并用 A 股、港股、美股的五份原文复验。F2 首批三仓已把公开观察接入 ROOT 只读导入。F4 已在 CWP 与 FF 核验缺终态对账和一条无人值守修理与回告链，其他 owner 按[分工](dispatch.md)接续。业务线按父计划在下一家公司验证现版本的生成与采用。[保存响应验收](f3c-saved-response-acceptance.md)

真实宿主选型、异步接线、原始作业核对、实际 P1 故障与消费复验的执行顺序见[ROOT 施工细则](host-integration.md)。

## 2026-11-24 日志与错误可复现性深度审计补充（F5）

**当前入口**：S1 八仓原批次均有提交，七仓按各自发布线推送，StockWiki 为本地主线。CWP、ET、SID 补修见[S1 分仓发布台账](s1-p0-blackhole-plan.md)。S2 已通过首站验收，当前按 [S2 分仓接续台账](s2-owner-continuation-20261124.md) 推进。S3/S4 仍为计划。

**背景与根因**：2026-11-24 对全部 12 个自有模块（1,654 个生产 Python 文件 + Dashboard 前端）做只读源码审计，查明此前“若干次错误未被记录、无法复现”的四类共用根因（完整逐行证据见 [全 12 模块深度审计报告](../module-boundaries-2026-11-11/review/full-12-module-architecture-logging-audit-20261124.md)）：

1. **系统性标准日志真空**：9/12 仓零 `logging` 处理器/文件配置（CWP 233/243 含 `except` 文件无日志、FF 0/63、Audit 0/45、IQS 0/315、IR 0/8、RF 0 配置、StockWiki 0 配置、Dashboard HTTP/Service/Feedback 0 日志）；**`StockInfoDLSimple/src/logger.py:15,39` 导入期空句柄短路导致 `config["logging"]` 永久失效（零日志文件写出）**；**`MeetingConverter/engines/mimo.py:137` 存在线上 P0 Bug（调用未定义 `logger.warning`，首次重试即抛 `NameError` 覆盖真实错误）**。
2. **安全脱敏误伤本地诊断（“先销毁堆栈，再返安全码”）**：CWP 95 处 `raise ... from None` 前未落本地日志；ET `transcript_api.py:804,1142,1404` 吞全部异常为裸 `unexpected_provider_failure` 且 `retrieval_runtime.py` 崩溃后立即删 `worker_stderr.log`；StockQA 10 处丢 `from e` + 61 处 `logger.error` 缺 `exc_info=True` + LLM Provider 仅记异常类名并重试代码 Bug；RF `filing_fetch_client.py:373` 报错不读 `stderr`、`rf_job_facade.py:940` 丢 `from exc`；StockWiki `documents.py`/`llm_usage_ledger.py` 宽泛吞错返 `None`/`{}`；IQS 62 处宽泛静默吞错；Dashboard `adapters/common.py:fail()` 丢 cause 且前端 `api.ts` 丢弃 `correlation_id`。
3. **子进程 `stderr=DEVNULL` 黑洞**：CWP 7 处（`tools/feedback_loop/local_host.py` 4 处、`intake.py`、`hook.py`、`isolated_ocr.py`）、FF `ff_scheduled_windows.py:153`（双 `DEVNULL`）、StockQA `quick_scan_owner_research.py:462`、Audit `run_pool_progress_e2e.py:218`。
4. **F4 反馈旁路写失败静默吞异常**：CWP/FF/StockWiki/Audit/IR/Dashboard/MC 旁路写盘异常均被静默吞掉（MC `core/feedback.py:1086` 甚至吞 `BaseException`），缺少 stderr 兜底告警，磁盘/权限/序列化异常会导致业务日志与 F4 观察双归零。

### F5 实施范围与状态

| 节点 | 实施内容 | 可核对交付 |
|---|---|---|
| F5-1 P0 黑洞止血（S1） | 修 MC `mimo.py:137` `NameError` 与 `BaseException`；修 SID 死文件日志与 `browser.py:645` 分页截断；清 CWP(7)/FF(1)/StockQA(1) 业务子进程 `stderr=DEVNULL`；修 ET `transcript_api` 静默吞错与 `worker_stderr.log` 提前删除；修 RF `filing_fetch_client` 丢 `stderr`、StockWiki 解析/计费静默返 `None`、StockQA LLM Provider 仅记类名。 | 每项先写 RED 复现用例，修复后能从新进程/轮转日志精确读出原异常类型、脱敏原因链与堆栈。 |
| F5-2 双层日志（S2，实施中） | 统一本地故障记录、脱敏和 F4 公开观察的字段语义，沿现有入口分仓实现。 | 用真实失败、合法输入和新进程冷查验证。[S2 首站和分仓顺序](s2-unified-logging-plan.md) |
| F5-3 回归覆盖（S4，计划） | 在已复现的失败边界补行为用例，必要时对明确且可归因的越层行为使用已有检查。 | 保留正常输入、CLI/HTTP 格式、诊断失败时的业务结果。无按语法统一拒绝的门禁。 |

## Next Step

按 [S2 分仓接续台账](s2-owner-continuation-20261124.md) 签收 IR 与 MC，使用各自真实入口做一次组合冷读。Dashboard 相关号沿原 M0 写域接续。S1 补修见[发布台账](s1-p0-blackhole-plan.md)，业务 W12 按父计划。
