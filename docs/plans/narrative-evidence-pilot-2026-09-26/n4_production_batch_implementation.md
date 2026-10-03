# N4：可运行的叙述批次、真实模型计量与持久恢复

> 2026-10-03 执行细则：scope已发布，节点A预算/模型/factory已验收，正式batch/终态降容/节点B+C未完成。G-A/N3a/G-C、B1/B3/B4已完成，见[实际整理收尾](harness_lanes/results/gd_b3_retirement_2026-10-03.md)；当前先按task_plan S0清旁路/hook，N4A scope在独占范围并行RED→实现。先按本文冻结接口，再实现；保留现有AUTO唯一任务库、Supervisor、三步handler/projector，不启动旧normalize Worker。只在三个大节点验收，helper不增加审查。原件及来源/版本事实保留。shared readonly migration snapshot竞态已修，复用既有32项两平台/CI收据，不重开同一修复。

## 1. 已核缺口与目标

1. `WorkerRuntime` factory、`NarrativeModelResponse` 实例目前只在测试；`automation.cli status/doctor` 固定 not_configured/AUTO-7。测试 replay 不代表生产模型能力。
2. Supervisor 只维护子进程/lease/readiness，没有 event materialize 或 narrative outbox dispatch。需要薄 composition，不能新建内存队列或另一个任务真相源。
3. claim、promotion、lease reaper、outbox 和 prepared reconciliation 没有本批 job 范围；小批 canary 可能触及其他文档。须先补范围。
4. summarize 的 tokens/cost/duration 固定零；无模型请求的持久费用预留。旧 `scripts/llm_client.py.chat` 有全局 CSV、旧价格、SDK隐式重试/可选 fallback，不能直接当新预算依据。
5. 持久 select/summary/verify result 和 effect payload 可能多次保存引用正文；419,428 B 的最终包不代表 AUTO 总增量。需要终态结果压缩为小收据与净总字节验收。
6. 现行 prompt 只描述约束，没有完整 draft 字段合同；真实弱模型不能靠测试 Replay 知道输出结构。生产 adapter 接入前给它明确、版本化的 draft 输出 schema/例子。

目标入口接受明确 SourceRef 列表、当前 catalog 配置、profile、文档/时间/token/费用上限；按 `event→DAG→worker→verify→outbox→visible artifact` 完成并返回 pathless 收据。退出/暂停/杀进程后可从原任务库继续；不自动下载、翻译或生成投资判断。

## 2. 固定接口与文件归属

### N4A：本批 scope（可先实施，无 schema 升级）

- `AutomationStore.claim_next_ready/claim_next_outbox/promote_ready_jobs/reap_expired_attempts` 增加可选 keyword `allowed_job_ids: tuple[str, ...] | None = None`。None 保留原 daemon 语义；空 tuple 表示无工作/无状态修改，不能回退全库。非字符串、空/带边缘空白 ID、超界输入拒绝；去重后最多 900 ID，SQL 参数绑定，不拼 ID 值。
- scope 在读取候选的同一事务 SQL 中筛选，不先领取再放回。终止依赖传播也只更新 scope 中的 child；scope 外 parent 仍可只读判断依赖。
- `Worker`、`WorkerProcessSpec`、`SupervisorConfig` 贯通同一个 `allowed_job_ids`；默认 None 兼容现有工位。Supervisor 的 maintenance 必须同 scope reap/promote。
- `NarrativeEffectDispatcher` 接收可选同 scope；claim、ACK 后 prepared reconciliation 都不得激活非本批 job 的 effect。catalog prepared 列表需先按本批 effect ID 过滤再 LIMIT，避免前 100 个外批对象导致本批饥饿。
- 修改归属：AUTO store/worker/process/supervisor/projection 与 catalog 的 prepared 列表窄过滤；对应 `tests/unit/test_automation_batch_scope.py` 和 `tests/integration/test_narrative_batch_scope_e2e.py`。不改其他仓库。

### N4B：composition / 计量 / 模型（N4A 后）

- 新 production factory 是 importable module-level function `create_runtime(spec: WorkerProcessSpec) -> WorkerRuntime`；只在 child 构造 reader/model/本地 connection。compute 不持模型；model/mixed 一个模型实例，首版模型并发 1。
- 新 batch application/CLI 复用 scheduler、Supervisor、runtime controller、dispatcher。部署路径只在 composition options；业务 DTO 只用 SourceRef / ID / hash。优先一个明确的 `company-wiki-narrative-batch`，不把只读 transport 变 writer。
- request：`schema_version=narrative-batch-request/1`、`sources`（1–100 精确 SourceRef、重复折叠）、`profile=P1|P2|P4`（默认 P1）、`max_seconds`、`max_tokens`、`max_cost_usd`、模型配置的非秘密标识。配置/refs/hash 校验后确定精确 DAG job IDs，持久 run ID/输入 hash；相同 run 恢复，输入/模型/prompt/selector 版本变化具名冲突或新 generation，不能悄悄复用。
- 同一 AUTO store 同时一个 batch coordinator。所有权是自动运行互斥/lease，不是人工授权合同；不能抢已有活跃 owner，不能 pause 其他活跃运行。沿用runtime generation；把主动有限批次与后台暂停明确分开，迁移LegacyWorkerControl调用者后删除旧新互锁，开始/退出/恢复有测试；不长持 CatalogOperationLock 等待解析/HTTP。
- `NarrativeModelResponse` 增加明确 usage/elapsed 信息；无 usage 标 unknown，不能用 0 伪装。现有 replay fixture 可明确为测试计量，产品不引用它。
- 一个薄 OpenAI-compatible HTTP adapter，一次 `generate` 至多一次 provider 请求，无隐式重试、fallback、全局成本日志。凭证从指定 env 在 child 读取，不进入 request/options/日志；网络 timeout、请求/响应字节 cap、错误体限长/脱敏。429/timeout 按既有 Worker retry；无 key 预检具名拒绝。
- 在 AUTO 原数据库新增最小 versioned migration（run/budget 与每 attempt model reservation）。金额用整数 micro-USD、token 用整数，避免 float 累积；同事务预留，两个进程不能超额。绑定 run/attempt/request SHA/model/pricing version，成功记录 provider usage + 配置价格估算，未知 usage/超时/进程失联保留保守 reservation。已结束请求结果无有效摘要也计量；输出截断具名失败。
- reserve 在 HTTP 之前、settle 在 decode/summary 校验之前；不把失败费用丢掉。输入上界按实际 UTF-8 request bytes 加 framing 的保守 token 上界，输出由 provider token cap 决定；供应商 usage 超声明上界则记异常并停止后续外发。不承诺外部 paid call 恰好一次；未知 reservation 不自动释放或伪造 0。
- pricing 是显式配置的带日期/来源费率，计量标 `estimated_usd`，不是供应商账单。2026-10-03 官方[MiniMax PAYG 页面](https://platform.minimax.io/subscribe/token-plan?tab=api-enterprise) M3 ≤512K 标输入 $0.3/M、输出 $1.2/M、cache read $0.06/M；首版保守按所有输入非 cache 计，不从旧 `_PROVIDER_PRICING` 推断新模型价格。仅作为本次候选配置，不自动购买套餐。
- prompt 明确 draft 完整 schema、字段值范围、引用/角色/情态、同语言/不翻译/只给来源摘要；从现行 summary contract 核对后版本升级。不增加模型自我审查第二轮调用。

### N4B：终态中间结果降容

- 只在本来源整个 DAG 终态、effect ACK 且对应工件 visible / binding 匹配后压缩中间正文。active/retry/prepared/ACK 丢失窗口一律保留；skip 保留小 coverage/skip 收据。
- 保留 job/event/source/version/attempt/error/usage/hash 与 final artifact/effect ID，不重复 quote。读取完成工件走已发布 transport；恢复不能从已压缩 result 重新计算依赖，若 lineage 变化生成新 DAG。保留最小 trace，不写第二份 bundle。
- scope 精确、幂等、停机后可继续；旧 evidence/span ID 与 B3 archive 退役另按 G-D，不借此删历史事实。

### N4B：避免再次积累大体积记录

- 原件一份、可用最终叙述包一份、小型来源/usage/失败收据一份；AUTO终态和outbox不再保存同一quote/bundle正文。全文转换只作有期限的解析临时文件；不要重新给全部财务表格/单元格建立百万级span。skip只留原因/coverage/来源引用，不留全文派生。
- 默认不自动生成完整catalog备份、gzip退休span或zstd旧库。确有一次性schema迁移时使用原有维护机制，迁移节点成功后立即按绑定收据收尾，不把同一内容无限保留多份。原文和来源/版本事实仍保留。
- 新批次只增加三个可配置空间预算：单文档最终持久正文2MiB、新叙述流程累计持久增量1GiB、所有该批临时文件峰值2GiB。原始下载和现存legacy目录不占“新增”额度，也不能因额度不足被删。开跑前记录既有目录基线；HTTP前预留本次输出上界，存储不足具名停该批，不循环重试/复制全文。若优质长文确实超过单文档额度，报partial与被截内容的coverage，不静默丢失、不伪报完整；由配置调整下一批。
- 可恢复的active/prepared工作继续保留；退出先清本次临时解析目录，失联目录由现有run/lease状态回收，无活跃owner才能删除。测试也只用独立短根；交付前清自己创建的根，历史工作树在交付并线后及时移除。日志只记ID/hash/状态/字节/token/费用，不重复正文；错误体仍沿用现有限长。
- 测试目录创建、pytest运行和finally清理使用同一OS账号。2026-10-03旧临时树实证：pytest owner-only ACL让另一账号读不到，不是生产权限门；不要因此放宽生产ACL或把不可读统计当零。正常用户发布/测试优先正常用户短根；若用sandbox跑隔离测试，就在同一sandbox清其精确根。Windows/Linux各清自己的run root；测试失败也执行finally并记录残留路径/bytes，不把反复排错基线留在仓库。该要求只并入现有节点B/C恢复原样检查，不增加审查门。
- 总容量统计包含新artifact、AUTO数据库/WAL、metadata、运行日志和临时峰值，不能只报最终bundle很小；SQLite逻辑prune和文件体积分别记录。与原文目录/旧库空间分别出数，避免把全仓45GB误认成46GiB旧DB反弹。预算/重复正文/临时恢复清理测试并入下方节点B，不新增小节点审查。

## 3. TDD 与三个大节点

### 节点 A：scope 与持久记账

先 RED：更高优先级外批 READY；外批 RETRY_WAIT / terminal-parent child / expired attempt；外批同类 outbox；前 100 个外批 prepared；空 scope；真实 spawn factory 收到 scope。预算再覆盖双进程 reserve、相同 attempt 幂等/冲突、kill-before-request / kill-after-request-unknown、失败/坏JSON仍收费、micro-USD 上界。v2→v3 小库 migration、回滚/原表事实保留。实现后集中相关单元/集成，无全仓 coverage。

### 节点 B：正式 batch 端到端（隔离，无付费）

使用正式 production factory、真实独立 CLI 和本地 HTTP stub（测试服务，不是 production replay），走完整 DAG/outbox/transport。多文档 + skip；中英输出不翻译；同 run 恢复无重复调用；源 hash 改变拒绝；ACK 丢失和 worker kill 后复原；费用不足不发请求；stdout/日志无 key；外批任务/DB rows不变。本地服务给真实格式 usage 与错误/timeout；不要求每 helper 审查。

终态降容加入同节点：before/after artifact/ref 读取一致、prune 前后 resume 幂等、pending 不 prune、正文不会在 attempt/effect 重复保留。总增量算 final objects + AUTO DB/WAL + metadata/logs/temp（非仅 bundle size）。有 SQLite freelist 时区分逻辑记录缩小与实际文件释放。

### 节点 C：真实小批与发布

固定独立测试根复制 P01 年报、P04 招股、P07 IR、T01英文TXT，只读原件；P1 基线，P2/P4仅在同批显示实质提升/内存预算内后选择，不以进程数承诺更快。live 模型最多小批明确预算（首次最多 $0.10、60,000 tokens、1 个模型进程；超过只停该批），先检测当前实际 key 可用性，不输出 key。不调用付费 FMP。

自动校验 citation/hash/locator/语言/来源摘要 schema；记录实际模型 usage/估算费用/elapsed/失败、逐份 coverage 与 needs_review/partial 诊断。若真实模型不能稳定遵守合同，保留红证据修 prompt/adapter，不删断言、不开全库。复用 G-C consumer 对新真实产物读取，不重复旧四份 Replay 验收。

所有测试配置/控制/DB/cache/temp/log 均在 unique run root；finally 仅删除本次创建子树，原件 SHA/mtime 与生产配置/控制 fingerprint 前后相同，目录恢复基线。不得把外发凭证写计划或收据。普通 commit/push、已有精简 CI 绿后记录发布。通过并不自动启动无限 daemon；先有限显式批次，再按吞吐/增量逐批扩展。

## 4. 顺序与完成定义

1. G-C来源消费及B1/B3/B4已完成；现在按task_plan先S0收口、N4A独占并行，不重新恢复/重hash已删除归档或重做旧checkout整理。
2. N4A scope 先 RED→GREEN；与独立模型 HTTP 新文件可以并行，共享 Store/schema/prompt 只由一条 owner 实施。
3. N4B 计量/预算/模型 prompt/factory/batch/retention→节点 A+B 集中验收。
4. N4C真实小批→消费者读取→普通发布，再更新 G-D B2 调用者清单和生产可清理批次。
5. 复核已完成B3收据，不重做旧span墓碑/恢复；不能将N4最终包2%样本比率当总空间已验收。

N4 完成必须有生产代码入口、正常/故障真实 CLI 收据、usage/未知请求账本、batch isolation、恢复与总占用实测。只新增测试 factory、仅 status 变绿、仅保存几份 Replay bundle 均不算完成。
