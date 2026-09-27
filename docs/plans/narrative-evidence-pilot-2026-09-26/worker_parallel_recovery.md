# Worker 并发与丢任务恢复：设计补充

> **背景设计，未实施，也不解除 Worker 暂停。** 事务、文件路径、进程、测试和门禁以 [多文档并发实施手册](worker_parallel_execution_plan.md) 为准；本文只保留问题与故障分类。此处的“多 agent”指独立的模型任务角色，不表示现在启动多个生产 Worker。

## 1. 代码核查所得的约束

- `worker.py` 的 `run_cycle` 依序调用 scan、normalize、fingerprint、sections、summarize、export；`service.py` 对 normalize 和 summarize 等**整个调用**持有 `CatalogOperationLock`，其中可包含长 PDF 解析或远程 LLM 等待。直接多开现有 Worker 只会争锁，并可能放大重试/成本。
- `store.py` 使用 SQLite WAL、`BEGIN IMMEDIATE` 和单线程写入模型；可作为短事务提交入口，尚不能把现有服务对象/连接直接跨线程共享。
- `processing_demand.py` 的 claim/heartbeat/expire 是**纯内存**，进程消失后队列和租约丢失。`worker.py` 的 JSON state 是周期统计，`producer_attempts` 是成功/失败审计，两者均不是每个文档/阶段的权威任务账本。
- `scripts/llm_client.py` 持有 `_last_call_time`、`_call_count`、fallback/client 状态；项目规范明确其非线程安全。解析器已有隔离子进程、超时及父进程存活监测，可复用其隔离思路，不能仅为并发再套一个线程池。
- 46 GiB 空间问题主要由大规模永久 EvidenceSpan 等造成；增加并发只改变吞吐量，**不会自动减少空间**，还可能更快写满磁盘。选择性切片与配额先行。

## 2. 推荐架构与并发边界

```text
immutable raw + manifest
    ↓
既有 automation jobs/attempts（R4 C05 唯一持久任务入口）
    ↓
调度器：需求优先、各类型公平、预算/暂停、有限在途量
    ├─ 隔离解析进程：PDF/TXT 结构候选（可跨不同文档并行）
    ├─ 独立模型执行进程：选择/摘要候选（每进程独立 client，共享限流配额）
    └─ 校验任务：来源/角色/时间/locator/摘要支持（确定性优先）
    ↓
单一受控提交入口：catalog 短事务 + AUTO effect/attempt 跨库对账
    ↓
版本化导出 + 待发布事件/游标，消费者按 ID/hash 幂等读取
```

默认并发单元是**不同文档的独立阶段**。同一文档内遵守 `source→outline→selection→summary→verification→export` 依赖，长招股书可先按章节做独立候选，再由一个文档级汇总/校验任务消重和核对风险配对。原文扫描、分类、source manifest 和 catalog 提交保持串行受控；PDF 解析用进程隔离，网络/LLM 等待可多进程或每进程有限异步，不能共享 `LLMClient` 实例、SQLite connection、可变模型上下文或全局限流状态。各进程的限流/每日预算需要一个**共享**令牌或单一请求代理，否则每个 client 独立限流会合计超额。

**多 agent 的使用范围**：简单季报/格式通知走规则与一个抽取任务；招股书、再融资、密集投资者问答等高价值且结构复杂的候选可按需调用“结构提取→业务证据选择→独立事实核验”三个角色。最终摘要只能基于已校验的 evidence ID；独立核验者只能提出 `accept/reject/needs_review` 及错误原因，不能直接改原文、来源身份或投资结论。是否使用第二模型核验由复杂度/不确定度和实测收益触发，不能每份文件默认多 agent。模型之间意见分歧进入 `needs_review`，不以多数投票代替原文回查。

## 3. 可恢复任务协议的归属

`src/company_wiki/automation/` 已有 `jobs/attempts/effects/outbox` 表与 `job_key` 身份公式，但目前未接 source-catalog 生产 Worker，claim、attempt finish 和 outbox 原子性仍有缺口。本专题只在 R4 C05 的唯一入口上增加 narrative job；catalog 保存来源/产物，不再新增任务表。两个 SQLite 库之间不声称一个原子提交，而以 effect、内容寻址文件、版本化 catalog 产物和重启对账实现可重放 saga。具体状态转移、崩溃点及放行测试见 [实施手册 §3–§7](worker_parallel_execution_plan.md)。

保证为**至少一次计算、至多一个被接受的逻辑产物**；远程 LLM 超时后的实际调用/费用可能未知，必须记录并受预算限制。outbox 可重放，消费者以版本/哈希去重。失败不应占住整个队列。

## 4. 暂停、崩溃与“丢包”的明确定义

| 故障/时点 | 预期结果 | 必测方式 |
|---|---|---|
| claim 已提交、任务消息未送到执行者 | 租约到期可重新 claim；无重复 accepted artifact | 丢弃派发消息后推进测试时钟 |
| 执行者死于解析/模型调用 | 子进程树受控退出，租约过期重试；别的任务继续 | 在每个阶段强杀进程/父进程 |
| 心跳丢失、慢执行者随后返回 | 新 epoch 接管；旧 epoch 提交被拒，暂存结果可审计 | 两个执行者交错提交 |
| 文件 rename 后、DB 事务前崩溃 | 发现孤儿内容寻址文件，验证后复用/清理；账本仍待完成 | 故障注入在两个写入点之间 |
| catalog commit 后、AUTO finish 前崩溃 | 对账以 work key/hash 补 finish，不重新调用模型；发布可见性和 outbox 顺序依实施手册 | 丢弃 ACK/通知再启动 |
| 网络响应丢失或 HTTP 429 | 标记不确定调用结果、有界退避和预算核算；不产生无来源摘要 | 超时/429/半响应模拟 |
| SQLite 忙、磁盘满、文件损坏 | 不把任务标 `completed`；保护原文，进入可恢复错误或停止写入 | busy/disk-full/坏 hash 注入 |
| 用户设置持久暂停 | 暂停状态写入并递增暂停代际后不再 claim；旧代际提交拒绝，执行进程停止/排空；不自动恢复 | 在 claim、计算、提交临界点并发发暂停 |
| source 变 `retired` 或新版本替代 | 提交再验证来源状态与 SHA；旧候选失效/撤回，不混入新源 | 暂存后变更来源状态再提交 |

“丢包可复原”应写成上述可测试保证，而不是宣称没有消息丢失。`pause` 自身的控制状态写入是唯一必要的停机写入；其线性化点之后不得继续提交来源产物、发下载请求或自动恢复。测试需记录具体时序、DB 行、文件和外部调用次数。

## 5. 分阶段推进与启用条件

| 阶段 | 内容 | 放行到下一阶段的证据 |
|---|---|---|
| R0 | 基线：在临时 catalog 测文档类型的解析/模型/锁等待、CPU/RAM、成本、积压时龄和真实空间增量；确认现有 Worker 恢复计划的暂停门禁 | 知道瓶颈和可容忍延迟，完成 W0 任务协议审查 |
| R1 | **仍单执行者**，先实现持久账本、epoch、对账、幂等提交、暂停、故障注入 | 第 4 节每个断点/丢包场景通过；13 探索卡无退化 |
| R2 | 并行准备：不同文档的解析/候选/模型计算在隔离进程执行，catalog 仍单入口短事务提交；先 2 个在途任务，再按实测增量考虑更高上限 | 吞吐量提高且错误率、RAM、模型费用、SQLite 锁等待、证据质量不越 W0 门槛；收益不成立即保留 R1 |
| R3 | 仅对复杂高价值文件按需使用多 agent 交叉核验；比较单任务与多角色结果 | 盲测留出集减少严重漏收/误归因，额外成本和延迟在冻结预算内；否则关闭多 agent 路由 |
| R4 | 在独立上线门禁下做有限公司/类型的生产灰度，观察恢复演练和撤回 | 真实 backlog、p95、失败重试、存储增量、人工复核量稳定；用户原有暂停需另行明确解除 |

不预设最终线程/agent 数。`workers=1` 是可靠基线，后续仅在同一批样本与机器上逐级测 2、4 等上限，记录吞吐量、长尾延迟、错误、费用和磁盘压力；收益曲线趋平或风险上升即停止扩容。先完成选择性切片，避免并发放大 46 GiB 问题。

## 6. W6 的新增审查清单

- **接口**：现有长时间 `CatalogOperationLock` 调用如何拆为“短 claim/commit + 锁外计算”？`store.py` 单线程连接和现有 producer attempt 写入如何保留？SourceOnlyStage 白名单如何覆盖新任务而不引入研究 writer？
- **可靠性**：唯一 `work_key`、epoch fencing、原子 claim/提交、恢复对账、outbox/消费者游标、暂停代际，是否均有代码和失败测试对应？
- **安全/质量**：执行进程只读 immutable raw，写入暂存区隔离；LLM client/限流/预算不跨线程共享；模型角色无权直接发布或写投资状态；每条摘要仍可回原文。
- **运营**：仪表至少显示 ready/running/retry_due/terminal_failed、最老任务时龄、租约过期数、重复抑制数、孤儿文件数、p95 阶段耗时、429、token/费用、SQLite 锁等待、暂停状态。异常告警只提示人工，不自行解除暂停。

任何一项缺证据时，只保留 R1 单执行者或隔离影子运行；不得为了吞吐量绕过可靠性门禁。
