# 存储、来源读取与 AUTO worker 架构质量审查

日期：2026-11-01。父任务基线：HEAD `d38613bc`，runtime `7e10973e`。本审查只读分析当前 canonical `src/` 和指定维护工具；没有运行公司、Worker、LLM、下载、数据库迁移、PDF 转换或完整测试。仅本文件由本 worker 写入。`.githooks/pre-push` 的既有 mode-only 修改未触碰。

结论：本范围确认 4 项 P2 级问题/风险和 2 项 P3 架构债务。没有证据表明当前主读取/采集链仍要求逐材料人工许可；不能把旧字段名、必要字节校验、预算预留、租约 fencing 或 retired 写接口当作过度审批。下列 P2 中，SW-03 为有静态及纯函数证据的破坏性能力边界风险，尚未证明生产发生误删；其余也未测量生产损失。

## SW-01 — P2：精确公司查询受全库同类文档 20,000 条上限约束

- 位置：`src/company_wiki/source_catalog/source_reader.py:203–224`、`:289–368`；`src/company_wiki/source_catalog/service.py:238–261`、`:324–349`。
- 实际链：`query_local()` / `lookup_transcript_import()` → `_query_local()` → `_candidate_pages()` → `SourceCatalog.query_filing_candidates()`。SQL 只带文档类型和 active status；`_query_local:303–305` 始终传 `include_unknown_publication=True`，实际连发布时间条件也不推入。公司、身份、期间在逐行 metadata 读取后才过滤（314–328）。
- 触发：该文档类别累计达到 20,000 条，无论请求公司的资料只占一条还是其目标已在首批出现，枚举到上限均抛 `candidate_budget_exceeded`，无法返回已找到结果。20,000 恰好整页也无 EOF 探测，19,999 正常。它还把每次精确小查询变成全类 metadata 投影工作。
- 证据：仅 AST 提取 `_candidate_pages`，用不接触 DB 的假 catalog 输入 19,999 / 20,000 / 20,001 条，分别得到 `completed` / `candidate_budget_exceeded` / `candidate_budget_exceeded`；最后两组已 yield 20,000 条后才失败。没有导入 catalog/Store。
- 共因：读取选择的身份语义与 SQL 候选投影分离，依靠固定全局枚举上限承担边界。`service:255–261` 有明确历史理由：简单按显示公司名过滤可能隐藏身份冲突。因此不能仅传 `entity`、`fiscal_year` 或去掉预算即结案。
- 改法：在来源 owner 建立包含权威 source-fact correction、别名、冲突候选的可索引身份/期间投影，用有界候选超集查询和稳定游标；Python 保留最终 scope 判定。预算限制应约束相关候选/耗时，并区分真正截断和正好 EOF。
- 建议验收：20,000/20,001 无关文档夹具中精确旧期间可查；权威纠错、未知日期、身份冲突仍被保留/正确排除；查询数量随相关候选而非全库增长。本轮未运行这些数据库测试。
- 不确定性：未读取生产规模，因此不能声称已造成某家公司来源遗漏。

## SW-02 — P2：每轮批次轮询扫描共享存储，并把别的写入记到本 run

- 位置：`src/company_wiki/automation/narrative_batch.py:1209–1255`、`:1263–1285`、`:1867–1931`。
- 实际链：`_run_owned()` 循环每轮 `guard.check()`（1875），末尾休眠 0.05 秒（1931）；`snapshot()` 对每个 path 重算 `_tree_bytes`，目录用 `rglob('*') + stat()`。路径包含整个 `catalog_dir/objects`、整个 `narrative-generations`、catalog DB/WAL/SHM 和本工作目录，而非本 run 新对象集合。
- 触发/影响：对象目录变大，即使 Worker 正等待网络，协调器仍重复全树遍历；理论最多约 20 次/秒（实际还受扫描与 DB 操作耗时影响）。同一 catalog 的另一个合法来源写者使共享 DB/objects 增长，会被算入本 run 的 `persistent_added_bytes` 并触发 `PERSISTENT_BYTES_EXCEEDED`。批次互斥锁按 AUTO DB 路径建立（1359），并不能保证共享 catalog 没有别的合法写者。
- 共因：全局物理空间观察、单 run 费用归属、频繁调度轮询绑定在同一个 guard。磁盘预算必要，但归属与采样责任混杂。
- 改法：对象 owner 在实际提交处返回写入字节/新建与复用结果，AUTO 按既有 run/reservation 记增量；全局容量观察独立低频采样，明示其为全局限制。保留预付费预留、单响应/临时文件/最终对象上限与全局硬边界，不新增第二任务库。
- 建议验收：大量历史对象、空闲长调用期间目录遍历次数有界；另一个来源写者不会挤占本 run 归属预算；本 run 自身写超限仍停止；崩溃恢复不退未知账。
- 不确定性：静态复杂度与归属已确认，未做性能基准或生产占用测量，不能提供节省百分比。

## SW-03 — P2：legacy prune 工具可删除任意当前/未来 parser 的全部 spans

- 位置：`tools/legacy_storage_retirement.py:50–55`、`:90–100`；`tools/legacy_storage/spans.py:17–46`、`:65–107`。
- 实际入口：CLI `prune-spans --apply` → `run_prune_spans(... dry_run=False)`。selection 仅要求 schema 和非空 `parser_name`；版本、source_ids、document_ids 都可缺省；`--keep-refs` 可省。最终直接在来源 DB 执行 `DELETE FROM evidence_spans WHERE parser_name=? ...`。
- 触发/影响：把正在使用的或未来 parser 名写入 selection，就能按名字全删其 spans。模块名和说明声称 legacy，但删除层没有 legacy 生命周期条件，也不验证当前 source/evidence 引用关系。完整性检查、原件事实不变和传入 keep-refs 完好，不能证明未被列出的当前 evidence references 仍有效。
- 证据：仅 AST 提取 `_parse_selection` / `_where`，输入 `future_parser_9` 且省略全部可选 scope，实际接受并生成 `('parser_name=?', ['future_parser_9'])`。未连接或修改数据库。现有 `tests/integration/test_p5_storage_retirement_spans.py:103–118` 只覆盖“选择旧 parser 时其他 parser 不受影响”，没有覆盖“主动选择非 legacy parser 被拒绝”。
- 共因：临时维护工具另写存储生命周期规则，绕过正常 owner 的引用/退役模型；这是数据范围边界问题，不是缺少人工授权流程。
- 改法：把 retire/prune 资格下沉到来源存储 owner，依据明确 legacy generation / parser lifecycle / referenced span 集合筛选；工具仅调用该端口。要求明确对象/版本范围或使用受保护、可复核的 inventory manifest；不增加逐材料审批、签收 JSON 或 canary。
- 建议验收：current/unknown parser、current referenced span 均不能被 legacy prune 删除；合法 legacy 定点删除及重复零变化成立；raw/source facts/新 narrative artifacts 保持不变。只用 tmp DB。
- 不确定性：破坏路径已证实；尚未证明生产存在误调用或已丢引用。现有显式 `--apply`、事务和锁仍有价值，不能当作证明该范围安全。

## SW-04 — P2：CAS 已有对象分支绕过有界读

- 位置：`src/company_wiki/source_catalog/narrative_artifact_store.py:155–182`，对照 `:188–202`。
- 实际链：`NarrativeArtifactStore.prepare:261` 或 `PaidResponseArtifacts.put` → `LocalNarrativeObjectStore.put()`。目标 hash key 已存在、或并发 hard-link 失败命中 FileExistsError 时，使用 `target.read_bytes()` 读完整已有文件，再校验长度/hash。正常 `read()` 则明确只读 `expected_size + 1`。
- 触发/影响：已有 hash key 对应的磁盘文件被损坏/异常变大时，即使本次输入很小，dedup 验证也先无界分配内存，可能进程退出而非正常返回 integrity error；调用方输入大小上限不能约束磁盘上异常对象。合法文件路径触发，不需假定外部攻击。
- 共因：同一对象完整性语义在 put/read 两条分支实现，只有 read 实施读取边界。
- 改法：将已有对象校验复用 owner 的有界读取 helper（expected length + 1，校验 size/hash），保留 atomic create-if-absent、fsync、并发冲突和不覆盖已有对象的规则。
- 建议验收：小输入/大已存文件、并发 FileExistsError 分支均仅作有界读取并报 integrity error；正常相同对象复用零写；损坏对象不被覆盖。
- 不确定性：静态确定存在无界读取，未制造大文件、未测 OOM。

## SW-05 — P3：wire contract 依赖具体目录服务，形成显式包循环

- 位置：`src/company_wiki/source_contract/source_export_v2.py:105–120`；`src/company_wiki/source_catalog/source_reader.py:77–109`、`:136–145`；`src/company_wiki/source_catalog/canonical_writer.py:605–624`。
- 实际链：V2 export builder 在 wire contract 包内部延迟导入 `SourceVersionReader`，并 `isinstance` 强制具体类；注释 112–113 明确说明这样是为规避 source_catalog 启动时反向导入的包循环。Canonical writer 为返回已经登记的 SourceRef，再构造高层 SourceVersionReader 查询一次。
- 影响：纯 SourceRef/VerifiedContent 类型归属到具体 reader 实现，contract、canonical writer 和高层服务相互依赖；新后端/只读替身必须继承具体类，难以在单一存储 owner 之上替换端口。当前不是生产功能失败。
- 改法：将纯身份值与已验证读结果放到无实现依赖的 source contract；export 用 narrow Protocol；writer 由登记 owner 返回已登记 identity，避免为组装返回值进入高层 reader。byte open 仍由 reader/storage owner 在实际 I/O 时校验。
- 建议验收：contract import 不引入 source_catalog runtime；替换只读 backend 可产生相同 wire；跨 root relocation、腐坏字节、错误身份、返回不可信结果仍拒绝。

## SW-06 — P3：同一次可信读取的字节 hash 在消费者再次全量计算

- 位置：`src/company_wiki/source_catalog/resolver.py:402–421`；`src/company_wiki/automation/narrative_source_guard.py:66–85`；`src/company_wiki/automation/narrative_select.py:300–307`；`src/company_wiki/automation/narrative_verify.py:248–255`；`src/company_wiki/source_contract/source_export_v2.py:143–162`。
- 实际链：reader 在磁盘流读时算 SHA → select/verify 马上 `validate_opened_identity` → guard 对同一不可变 bytes 再 SHA；export 对需要 spans 的同一读取也再 SHA。这不是多读一次磁盘，但随文档长度增加 CPU/内存带宽成本。
- 判断边界：select 和稍后的 verify 跨时间重新打开原件是必要的当前字节/TOCTOU 检查；不应删掉。Protocol 允许不可信或测试 reader，`VerifiedContent` 可直接构造，因此也不能不改合同就删消费者 hash。
- 共因/改法：byte 验证 owner 的可信结果没有封装边界，消费者因此自保。明确受信 owner 工厂/窄端口，已验证的进程内不可变 bytes 只做字段绑定，未受信 adapter / 序列化结果仍在入境处做一次实质 SHA；先用计数与破坏反例证明等价，按收益决定是否实施。
- 建议验收：可信 reader 同次打开只完整 hash 一次；错误 identity、伪造 reader、数据腐坏仍被唯一责任层捕获。未测性能，不能声称此项比解析/LLM 更主要。

## 已覆盖且应保留的控制

- `SourceVersionReader._read_context:147–166`：自动发现的 rollout 文件不再决定能否读取；旧 expected policy pin 是 lineage，真实 root/byte 在 open 时复核。旧 config/terminal/partial-cache 修复不重报。
- `source_reader.py:675–784`：当前 SourceRef、active 版本、注册 root、relative locator、防越界、size、真实 hash、文件读取期间变化，以及必要的资料范围校验是来源系统职责。
- `canonical_writer.py:626–655`、`:731–747`：staging 归属、candidate/receipt binding、实际字节及复制后校验是不同 I/O/提交边界，不能只因多次 SHA 就删除。已存在 root relocation/dedup 对抗测试，未报旧 absolute-path dedup 问题。
- `Worker` 的 claim/heartbeat/finish、AUTO generation fencing、outbox ack→prepared→visible 和事务外 handler 执行负责崩溃幂等；它们不是人工许可。`WorkerStore` Protocol 窄接口已存在。
- `NarrativeRunStore` 使用现有 AUTO 表，构造只 inspect schema，未新建独立任务库；paid-response body 是 CAS 字节，AUTO reservation 保持唯一收费归属（`narrative_paid_response.py:1–5`）。unknown usage 不退账必须保留。
- `narrative_artifact_store.py` 当前未 import automation/provider/investigation；对象位置限定在 owner。`_require_bound_current` 只查 parent relations，不打开或重解析原件。不能依据历史版本报反向依赖。
- `authorization.py:90–115` 已明确历史 plan_hash/now inert，实际只限定请求目标和额度；采集不要求这份对象。`canary_registry` 的字面搜索未在 `src/scripts/tools` 找到生产调用，仅残留定义：视为 dead/兼容负担，不是活阻断。
- `DuplicateCleanupService` 已只读，`maintenance_retirement.py` 明确永久 retired 的旧写路径。SW-03 是另一独立工具的现存风险，不将退役的旧函数当仍可写。
- `terminal_receipts.py` 已有发布终态压缩，旧 partial/cache 重复付费与终态处理问题不在本报告重开。

## 体积膨胀观察与证据限度

- AUTO 中间选择/摘要/验证结果、最终 narrative CAS、paid 原始响应具有不同恢复责任，不能仅见多份相似 JSON 就全删；终态压缩已存在。
- `NarrativeArtifactStore.prepare:258–270` 明确先落 CAS，再登记 DB；在 source change/登记失败时可留下未引用对象，这是崩溃恢复设计的真实可增长路径。此次未追踪全仓 GC/retention，也未扫描生产磁盘，故仅记待进一步按引用图盘点的机制，不报“泄漏已实测”或虚构节省。
- `narrative-generations` 目前是指向既有 AUTO run 的小恢复 locator（`narrative_batch.py:2006–2046`），不是第二任务状态库。其 absolute AUTO DB locator 对迁移的影响未完成端到端确认，不列已证实 finding。
- 只读人类 inventory/legacy CSV 的物理 path 与外部 SourceExport v2 的逻辑 ID 不是同一合同；没有把前者一概判为原件路径泄漏。

## 审查执行与停止点

使用 CodeGraph search/context/files 定位后按具体文件读取；未调用 explore，未开新 agent。CodeGraph 返回 `validate_opened_identity` 无 caller，但已打开的 select/verify 文件中有直接调用，因此报告用明确源行，不把图边缺失当 dead 证据。

只读验证仅编译 AST 提取的 `_candidate_pages`、`_parse_selection`、`_where`，用内存假输入确认 SW-01/SW-03。未执行任何整个业务模块/Store 构造。一次 Windows rg 的目录 wildcard 语法失败，改为 `rg <dir> -g '*.py'` 后得到结果，无写入。

有界审查到此 STOP。以上建议为下一轮 PWF 实施/验收候选，未修改源码、配置、原件、数据库、索引或主计划；未重跑已修域、全量测试、公司 E2E。

补充：`automation/policy.py:25` 的 `allow_network=False` 是缺省能力限制；正常 CLI `automation/cli.py:66` 与 batch `narrative_batch.py:1707` 均显式 `PolicyConfig(allow_llm=True, allow_network=True)`，不构成当前正常入口的人工权限拦截。结束时 `git diff --name-only -- config src tools` 为空；全仓另有大量既存 untracked 证据/计划文件，未清理或归属为本轮产物。
