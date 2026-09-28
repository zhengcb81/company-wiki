# company-wiki 清洁架构与 TDD 实施总图（2026-09-27）

> **状态：计划已冻结；Phase B / M1、Phase C / M2-derive 与 Phase D / M2-provider 已完成，Phase E / M3 施工卡与 E0 可信基线已完成，下一步从 E1 Automation DB v2/原子 Store 的 RED tests 开始。** 本页把 R4 数据湖、叙述证据、电话会议、Worker、跨仓消费和空间治理收束成一个施工顺序。历史计划保留证据价值；发生冲突时，以本页的层次、门禁和顺序为准。company-wiki 当前没有生产流量，允许重构内部接口、模块和派生 schema；财报、公告、招股书、再融资文件、投资者关系资料和电话会议原件不得丢失。

## 1. 第一性原理与不可破坏条件

### 1.1 系统只需要守住四个事实

1. **原件事实**：下载或导入的原始字节、SHA-256、来源 URL、抓取时间和来源身份必须可追溯。原件是唯一不可随意重建的层。
2. **版本事实**：同一字节的多个目录位置是副本；不同 SHA 是不同版本。目录、盘符和 root priority 不得改变来源身份或业务语义。
3. **派生可重建**：规范化文本、页块、表格视图、切片、摘要、索引、缓存和临时 staging 都必须能由原件与版本化代码/策略重新生成。它们可以删除、换 schema 和全量重建。
4. **消费可验证**：上层只按版本化 ID、哈希和 locator 消费；company-wiki 交付的字节必须再次验 SHA。StockWiki 和 revenue-forecast 不读取或判断 company/dayu/Dropbox 的底层路径。

### 1.2 本轮安全边界

| 对象 | 默认处置 | 实施约束 |
|---|---|---|
| canonical raw 原件与已登记外部原件 | 永久保留 | 本轮重构不删除、不移动；写路径仅限隔离测试根。 |
| source manifest、来源 SHA、版本/撤回记录 | 保留并可迁移 schema | 迁移须有前后计数、SHA 和引用映射；不得把来源版本合并丢失。 |
| normalized、全文 spans、selected evidence、摘要、FTS、缓存 | 可删除重建 | 删除前先证明原件可读、重建命令可运行、消费者已切换；以批次收据记录。 |
| staging、pytest basetemp、测试下载物 | 测试结束恢复基线 | 测试根独立；前后快照一致；异常退出也由 fixture/finally 清理。 |
| company-wiki 内部 Python API | 允许破坏式重构 | 先写公开行为测试；不为错误的未投产内部字段保留兼容别名。 |
| 跨仓 JSON/CLI 合同 | 版本化演进 | 先扫描真实消费者；语义不变可内部重构，语义变更才升版并提供限期 adapter。 |

### 1.3 明确不做的事

- 不在重构过程中启动生产 Worker、扫描生产目录或真实下载正文。
- 不把投资预测、估值、评级、仓位或研究结论写回 company-wiki。
- 不为 Koyfin、Seeking Alpha 或无增量价值的 provider 增加代码。
- 不以测试绿灯为理由删除原件；原件处置另走 D0–D5，且本总图默认 `retain`。

## 2. `reader` 的准确含义

`SourceVersionReader` 是来源系统的**只读交付端口**，不是 PDF reader，也不是摘要模型：

```text
SourceRef(document_id, source_id, content_sha256)
    -> catalog 精确版本查询
    -> 在已登记 locations 中选择可读的同 SHA 副本
    -> 打开并校验实际字节
    -> 返回 VerifiedContent / VerifiedVersionReceipt
```

它还可在不打开字节时返回 pathless candidate metadata。它不得下载、扫描、解析、摘要、改变 Worker 状态或向消费者暴露永久物理路径。跨进程 CLI 是这个端口的传输适配器；filing-fetch、RF 和 StockWiki 应依赖这个端口的合同，而不是导入 store/resolver/DAG 内部代码。

## 3. 目标分层与依赖方向

```text
L7  durable jobs / worker orchestration
             |
L6  export + consumer adapters (RF / StockWiki / filing-fetch)
             |
L5  evidence products (selected evidence / source summary / coverage)
             |
L4  deterministic derivation (PDF/TXT structure / locator / classify)
             |
L3  acquisition application service (query / discover / fetch / admit)
             |
L2  read broker (SourceVersionReader / verified bytes / pathless metadata)
             |
L1  source catalog (identity / versions / locations / provenance)
             |
L0  immutable raw vault + manifests
```

依赖只能向下。各层对自己的结果负责：

| 层 | 唯一责任 | 禁止事项 |
|---|---|---|
| L0 Raw | 保存原件和捕获事实 | 不解析、不摘要、不按业务价值删除。 |
| L1 Catalog | 身份、版本、位置、来源字段 provenance | 不返回“可信路径”让上层自行打开。 |
| L2 Read | 选择同 SHA 副本并交付已验证字节/收据 | 不下载、不触发派生任务。 |
| L3 Acquire | query-first、metadata discovery、授权 fetch、canonical admission | 不做摘要；latest-as-of discovery 不下载正文。 |
| L4 Derive | 从指定原件确定性地产生结构和 locator | 不保存全量切片作为默认行为。 |
| L5 Evidence | 选择业务叙述、coverage、来源摘要 | 不生成投资结论；所有陈述绑定 locator。 |
| L6 Export | 版本协商、撤回传播、跨仓 DTO | 不暴露 root/path，不跨仓写数据库。 |
| L7 Jobs | claim、lease、retry、幂等提交、暂停 | 不把 LLMClient 在线程间共享，不让 worker 直接删除原件。 |

## 4. 当前测试失败的正式结论

### 4.1 已证明的分类

| 现象 | 结论 | 后续动作 |
|---|---|---|
| `.pytest_cache/lastfailed` 中 30 个节点 | 陈旧缓存，含已删除/改名测试和 Windows 路径乱码 | 不再作为失败清单；CI/阶段门从当前文件发现测试。 |
| pre-fix `251805c` 为 6 failed / 53 passed | 不是六个同类产品缺陷 | 按下列分类分别处理。 |
| reason taxonomy 缺项 | 真实集成缺陷 | 已补 registry/stage；保留合同测试。 |
| B10 两个 handoff 未登记 | 抽象层登记缺口 | 共享 metadata reader 路径保留；测试合理。 |
| FC905 三项 | 旧测试夹具缺正式 SHA/policy/evidence/signature | 更新夹具正确，生产 fail-closed 保留。 |
| stage taxonomy 预期 safety 未使用 | 测试预期过时 | 新安全映射存在，调整测试正确。 |
| narrative subprocess Unicode | Windows 测试输出编码问题 | 只改 harness；业务结果从 JSON/文件断言。 |
| normalized reader 拆分 | 行为不变的复杂度重构 | 保留原测试。 |
| `acquisition` 被 consumer/test 同改成 `acquisition_result` | **真实 producer/consumer 断裂** | 必须以正式生产者对象和 CLI E2E 重写测试后再实现。 |
| 将新大模块加入高复杂度 `FROZEN_MAX` | 临时豁免掩盖结构债务 | 不得作为 G0/G1e/G2 放行依据；按本计划拆层后降低或移除豁免。 |

### 4.2 为什么现有 88 绿灯仍漏掉缺陷

测试手写了一个仓库生产者从未输出的 `acquisition_result` 字段，consumer 恰好也读取这个字段，于是测试和错误代码同步变绿。正确测试必须至少跨过一个真实序列化边界：

```text
SourceEnsureResult / CloseGapResult
    -> to_dict()
    -> CLI 实际 wrapper
    -> source operation adapter
    -> pathless projection
```

测试不得复制生产 schema 常量或重新手写一份“看起来相同”的 payload 作为唯一正例。

## 5. 目标接口设计

### 5.1 内部类型与 JSON 边界分开

`source_operation.py` 不再同时做 wrapper 猜测、schema 解析、状态机、reader I/O、路径过滤和输出组装。拆成以下模块；文件名可在实施时微调，但职责不可合并回单个大函数：

| 模块 | 输入 | 输出 | 责任 |
|---|---|---|---|
| `operation_contract.py` | `SourceEnsureResult` / `CloseGapResult` 序列化 JSON | `EnsureOperationInput` / `CloseGapOperationInput` | 校验 schema、必填字段、request identity 和 producer 类型。 |
| `operation_projection.py` | typed operation input | `SourceOperationResult` | 纯状态投影；gap/not_found/ambiguous/completed 互斥。 |
| `source_reader.py` | `SourceRef` | metadata/verified bytes | catalog read port；不依赖 projection。 |
| `source_operation.py` | JSON + reader port | JSON DTO | 薄 facade，只编排 parse → project → serialize。 |

内部 dataclass 可以破坏式调整。外部 `operation_schema_version` 先保持现有版本，除非字段语义发生变化；若升版，必须在同一提交加入 consumer capability negotiation 和旧版拒绝/adapter 测试。

### 5.2 正式不变量

- ensure 只接受正式字段 `acquisition`；错误的 `acquisition_result` 不设兼容别名。
- producer、resolution、gap plan、attempt 中出现的非空 `request_id` 必须一致。
- `status=gap` 必须有 `acquisition.gap_plan`；有 gap plan 时顶层也必须是 gap。
- completed 必须恰有一个完整版本身份；reader 返回的 byte size/MIME 与 producer 声明冲突时失败关闭。
- 所有 schema version 显式验证；未知版本不猜测。
- output 任意深度不得出现永久 path/root/location/bundle 字段。
- `download_events` 是非负整数；latest-as-of metadata discovery 必须为 0。
- `policy_hash` 存在时为小写 64 位 SHA-256。

### 5.3 原件与派生存储合同

每个 source version 只需长期保存一份 canonical raw，其他同 SHA location 是可选副本登记。派生对象统一使用：

```text
artifact_id = hash(source_id, source_sha256, artifact_role,
                   producer_version, policy_version, input_hash)
```

派生数据不得复制原文全文到每个 span JSON。selected evidence 只保存 locator、必要短引文、text hash、类别、质量和 coverage；查询需要上下文时通过 L2/L4 按需读取原件。负例文档只保存分类/跳过收据，不建全文切片。

## 6. TDD 测试体系

### 6.1 测试金字塔

| 层级 | 目的 | 典型测试 | 运行频率 |
|---|---|---|---|
| U 单元 | 纯规则和状态机 | schema parser、request ID 一致性、gap/completed 状态、selector rules | 每个实现提交 |
| C 合同 | 真生产者/真序列化/真 consumer | `SourceEnsureResult.to_dict()` → projection；artifact schema；job state | 每个工作包完成时 |
| I 集成 | 临时 catalog + 真 store/reader/writer | 同 SHA 跨 root、hash 漂移、selected locator replay | 大节点前 |
| E 子进程 E2E | 真 CLI/进程边界/清理 | latest-as-of fake provider；open verified bytes；transcript import | 大节点验收 |
| X 跨仓 E2E | 真 consumer adapter | filing-fetch、RF、StockWiki 各一次 | M1/M4 |
| P 性能/空间 | 防止 46 GiB 重现 | 每文档新增字节、峰值、吞吐、并发恢复 | M2/M3/M4 |

### 6.2 测试必须遵守的写法

1. 正例优先由正式 dataclass/service/CLI 生成，不手写复制 schema。
2. 手写 JSON 只用于畸形输入、未知版本、缺字段、重复键、路径泄露等负例。
3. 每个 E2E 使用独立 `tmp_path`/run root；运行前后做递归文件哈希快照。预期新增的测试文件也必须在 `finally` 或 fixture teardown 中删除。
4. 真实样本只读；测试若需要下载，使用本地 fake provider 子进程。网络 canary 单独标记，不进入默认门。
5. 原件保护测试对 fixture raw 做前后 SHA；阶段验收对生产 raw 只做只读 inventory，不运行删除。
6. 失败注入覆盖：进程退出、超时、截断 JSON、错误 SHA、重复 ACK、lease 过期、writer 提交前后崩溃。
7. 不为每个小函数重复跑全量；在 M1–M4 大节点跑受影响全套与真实 E2E。

### 6.3 M1 必须新增的具体测试

先写红测，再实现：

- `test_source_operation_v2.py`
  - 真 `SourceEnsureResult.to_dict()` 的 gap 能保留 gap hash、request ID，零路径。
  - 错误 `acquisition_result` 被拒绝。
  - 未知 producer schema 被拒绝。
  - resolution/gap/attempt request ID 不一致被拒绝。
  - 真 `CloseGapResult.to_dict()` completed 绑定 reader 返回的精确版本。
  - byte size/MIME 漂移、非法 policy hash、负 download count 均失败关闭。
- `test_source_version_reader_cli.py`
  - exact reuse：零下载、原件 SHA 不变、legacy 输出与 pathless 输出各自稳定。
  - latest-as-of：本地 fake discovery 子进程返回新期次；CLI 输出 gap，fetch 日志为 0，staging 不存在，测试树恢复。
  - provider unavailable：输出 gap/provider_unavailable，不谎称 not_found/up-to-date。
  - catalog location 被替换为错误字节：reader 拒绝，stdout 不泄露原文。
- 跨 root 集成
  - 同 SHA 放在 company/dayu/Dropbox，首选位置失踪后切换同 SHA 副本。
  - 不同 SHA 不回退；root priority/目录移动不改变 source identity。

## 7. 实施阶段与精确施工顺序

### Phase A：冻结基线和破坏预算

**目标**：让后续实施者知道哪些可删、哪些必须保留，避免为了兼容错误代码继续堆层。

1. 记录 company-wiki HEAD、RF `origin/main` 与 dirty worktree；只读扫描跨仓真实 consumer 字段。
2. 生成 raw inventory：文件数、逻辑字节、manifest 数、缺 SHA/冲突数；不重算或复制 46 GiB 旧库。
3. 把所有高复杂度临时豁免按生产启用顺序列为 blocker：read/operation → provider/transcript → narrative selector → worker。
4. 固定 M1–M4 的测试命令、独立 basetemp 和 cleanup verifier。

**产物**：本页、阶段基线收据、失败分类。

**完成条件**：Git clean；未改产品；raw 零写入；RF 零写入。

### Phase B：重构来源身份、读取和 acquisition operation（M1）

1. 按 §6.3 写 RED tests 并保存失败原因。
2. 新建 typed contract/projection 模块，把 `source_operation.py` 缩成 facade；删除隐藏 `_acquisition` 临时键和 wrapper 猜测。
3. 让 `_read_only_ensure_result` 与 `SourceEnsureResult` 共用同一个 serializer/DTO builder，停止手写第二套 acquisition envelope。
4. `SourceVersionReader` 只保留 query/describe/open/verify；把根选择与字节校验封装在 read broker 内部。
5. 完成 fake-provider latest-as-of CLI E2E；任何 fetch 调用都使测试失败。
6. 运行 M1 大节点测试并更新复杂度基线：新模块每函数 custom complexity 与 Ruff C901 均不高于 10；`source_operation.py` 从临时冻结表移除或显著下调。

**允许改动**：`source_catalog` 读取/acquisition/CLI 模块和对应 tests。

**禁止改动**：生产 raw、RF、StockWiki、Worker 启动状态。

**停止条件**：正式 producer 与 consumer 仍需手写 schema 才能互通；CLI E2E 有 staging/raw 残留；跨 root 不同 SHA 可被替代。

### Phase C：重构确定性派生与叙述证据（M2）

1. 将 `narrative_evidence.py` 的文档路由、候选生成、表格/问答分组、优先级、预算和 coverage 拆成小模块；先以 12 件样本和留出集写行为测试。
2. PDF/TXT adapter 只读原件，输出统一 `DocumentStructure`；PDF 保留页/块/表双视图，TXT 保留行/字节 locator。
3. selector 只持久化 selected evidence 与 coverage，不默认写全量 spans；一般格式文档输出 `skipped_no_business_narrative` 收据。
4. summarizer 只读 selected evidence，逐条绑定 locator；输入为空或 blocked 时不调用 LLM。
5. 建空间基准：每份文档 raw 字节、临时峰值、派生永久字节、索引字节、token 和耗时。长文档不得因页数线性复制全文 JSON。

**完成条件**：12 件探索样本、分层留出集、P03/P07/P08/P05/P06/T01/T02 反例通过；raw SHA 全不变；新派生净字节有实测。

**停止条件**：关键叙述召回下降、locator 不能回放、摘要含无来源断言、跳过决策无法解释。

### Phase D：电话会议与 provider adapter（M2 同批）

详细施工、测试矩阵和收据格式见 [Phase D / M2-provider 实施细则](phase_d_m2_provider_implementation_spec_2026-09-28.md)。该施工卡先于代码冻结，Phase D 实施不得绕过其依赖方向和停止条件。

**状态：已完成 company-wiki 侧分层和 fake-provider 验收。** 真实 `earnings-transcripts` 当前 `/2` 的 HTML `canonical_content_sha256/content_bytes` 表示 provider 提取正文，而 CWP 表示从 raw 确定性重建的材料文本；只读 spike 已证明两者不同。这个跨仓 producer 语义升级属于 Phase F，在修复前不得把 fake-provider 全绿解释成真实 E-T 已可导入。

1. 把 provider discovery、candidate authorization、fetch、result validation、canonical admission 分为不同端口。
2. `earnings-transcripts` 保持英文原文、翻译默认关闭；filing-fetch 只编排显式 companion request。
3. company-wiki importer 只接收 schema `/2` provider 原件并重算 SHA/MIME/URL/FY/Q；长期 raw 只保存一份。
4. fake provider 子进程 E2E 覆盖 discover→授权→fetch-candidate→stdin import→reader replay，拒绝和超时均零残留。

**完成条件**：无真实付费 provider 依赖；不新增 Koyfin/SA；`provider_use_policy.py`、`transcript_import.py`、`transcript_import_cli.py`、`transcript_material.py` 的 38/41/23/19 临时复杂度豁免移除，或全部下调至实际不高于 10；fake provider 全链必须通过正式 verified reader，而不是直接打开 canonical path。

### Phase E：重构 Worker 为多文档并发、单文档有序（M3）

详细文件级顺序、schema、原子 API、故障矩阵、真实数据 E2E、空间预算和两个集中审查点见 [Phase E / M3 Worker 详细施工卡](phase_e_m3_worker_implementation_spec_2026-09-28.md)。该卡覆盖下方概述；若旧 `worker_parallel_execution_plan.md` 与施工卡冲突，以施工卡为准。

1. 复用唯一 `automation` job/attempt/outbox，不新建任务数据库。
2. 先以测试固定原子 claim、lease generation、心跳、幂等 commit、outbox/reconcile 和 pause 线性化。
3. 同一 source version 的 DAG 串行；不同 source version 用独立进程并发。每进程独立 LLMClient、临时目录和预算。
4. catalog writer 单写者短事务；解析/选择/LLM 在锁外计算。提交绑定 input hash + producer/policy version。
5. 故障注入：worker kill、ACK 丢失、重复领取、lease 过期、提交后进程死、catalog 锁、429/超时。
6. 1→2→4 workers 基准；只有吞吐改善且错误/峰值受控才扩级。

**完成条件**：任务不丢、同 work key 最多一个 visible source-quality artifact、暂停后不再领取或发布、重启可恢复；原件零改动。

**停止条件**：需要共享非线程安全 LLMClient、长事务包住解析/LLM、重试产生多个 accepted 结果。

### Phase F：跨仓瘦 adapter 与消费验收（M4）

1. filing-fetch 只调用 query/ensure/open/transcript companion，不碰 CWP 路径或数据库。
2. RF 只消费 source/evidence DTO；不导入 CWP DAG，不把绝对路径当证据。
3. StockWiki 只接收版本化 source/evidence export；投资语义留在 StockWiki。
4. 每仓做一次真实 consumer E2E；新 root 只改 CWP 配置，consumer 代码零改动。
5. 旧兼容 adapter 在所有真实 consumer 切换后删除；不长期双轨。

**完成条件**：跨仓 E2E 全绿、撤回/版本不匹配失败关闭、RF dirty 工作树未被本项目覆盖。

**停止条件**：consumer 仍需 permanent path、直接读 SQLite、导入 CWP 内部模块或写 CWP 数据。

### Phase G：派生清理与空间封顶

1. 根据 M2/M4 收据生成 derived 删除候选；canonical raw 与 manifest 全部排除。
2. 先在隔离副本删除/重建，比较 source/evidence/export/query 结果和磁盘净字节。
3. 分批删除旧 normalized/spans/cache/index；每批有 intent、完成收据和失败恢复。
4. 建空间预算：永久派生字节/原文字节、单文档上限、月增长、临时峰值、超限报警。
5. SQLite 物理缩容只在逻辑删除和 consumer 切换完成后执行；按文件级空间收据验收。

**完成条件**：原件数/SHA/manifest 不变；已选证据可回放；净磁盘下降；新流程不会回填全量 spans。

**停止条件**：任何候选无法从原件重建、消费方仍引用旧 artifact、空间变化不能归因。

## 8. 四个大节点验收，避免过度复核

| 节点 | 一次性审查内容 | 不重复做的事 |
|---|---|---|
| M1 读取/acquisition | U+C+I+CLI E2E、跨 root、schema/路径/哈希、复杂度 | 不为每个 helper 单独签收。 |
| M2 派生/证据/provider | 真实样本+留出集、locator replay、摘要来源、空间/token | 不在每个文档后跑全仓。 |
| M3 Worker | 状态机、故障注入、1/2/4 并发、暂停/恢复 | 不在每个 job stage 做人工审批。 |
| M4 跨仓/清理 | 三个 consumer E2E、撤回、derived 重建、空间净额 | 不保留永久双轨或按文件逐个复核。 |

每个节点只需要：一份测试命令清单、一份机器可读结果、一页结论与未覆盖范围。小步骤只跑最小红/绿测试。

## 9. 复杂度与代码卫生门

- 新模块的 Ruff C901 和仓库 custom complexity 均不高于 10。
- 当前为本专项临时加入 `FROZEN_MAX` 的模块不得以“未增长”作为发布条件；进入其生产阶段前必须拆分并下调/移除豁免。
- facade 可依赖 application/domain ports；domain 不导入 CLI、Path 配置或跨仓代码。
- 不允许 `_foo` 隐藏键在函数间偷运 typed state；内部使用 dataclass/enum，JSON 只在边界出现。
- schema 常量由 producer 单一所有；consumer tests 从 producer 生成正例。
- 删除无调用者兼容层前用 CodeGraph impact + literal schema consumer scan；不因“可能有人用”无限保留。

## 10. 阶段命令与测试目录规范

实施时将实际命令登记到 `progress.md`。最低门如下：

```powershell
python -m pytest tests/contract/test_source_operation_v2.py -q --basetemp <独立临时根>
python -m pytest tests/contract/test_source_version_reader_cli.py -q --basetemp <独立临时根>
python -m pytest tests/contract/test_b10_read_chain.py tests/contract/test_source_operation_v2.py tests/contract/test_source_version_reader_cli.py -q --basetemp <独立临时根>
python -m ruff check <本阶段修改文件>
git diff --check
```

大节点才运行受影响全套。测试 wrapper 必须：

1. 将 run root 解析为系统临时目录下的绝对路径并验证 containment；
2. 运行前删除同名旧测试根；
3. `try/finally` 清理 requested/effective basetemp；
4. 复核测试前不存在的 raw/staging/catalog 文件测试后仍不存在；
5. 输出 exit code 和 cleanup receipt。

## 11. 跨项目协调

- 每个 Phase 开始只读核对 RF `origin/main`、活动分支和 dirty diff；不修改 RF 文件。
- RF 已提交合同优先于其 `.planning/execution_runs` 一次性收据；未提交实现只作为冲突预警，不作为 CWP 依赖。
- 如果 CWP 外部 DTO 字段变化，先更新本页的 consumer matrix，再在 CWP 完成 provider contract 和 fake consumer；跨仓代码放到 Phase F。
- StockWiki 与 filing-fetch 同样只通过 adapter 集成，不允许为不同目录复制业务分支。
- earnings-transcripts 的 provider 能力由其仓库拥有；CWP 拥有 canonical admission、source identity 和读取合同。

## 12. 实施者逐阶段检查表

任何模型开始一个 Phase 时按固定顺序执行：

1. 读本页、`task_plan.md`、`progress.md`、`findings.md`。
2. 只读记录 CWP/RF Git 状态；确认无未知未提交改动。
3. 用 CodeGraph 查目标 symbol 的 caller/impact；literal schema 再用 `rg`。
4. 写最小 RED test，证明当前缺陷或缺少的行为；记录实际失败。
5. 完成该层重构，不修改相邻层内部状态。
6. 跑最小 GREEN tests、Ruff、diff check；清理独立测试根。
7. 到 M1–M4 才跑大节点集成/E2E/性能门。
8. 更新 planning-with-files 收据；提交但不推送。发现原件写入或跨仓冲突立即停止。

## 13. 当前下一步

按已冻结的 [Phase E / M3 Worker 详细施工卡](phase_e_m3_worker_implementation_spec_2026-09-28.md)进入 **E1 Automation DB v2 与原子 Store**：先写 migration、claim/heartbeat/finish/reap/effect+outbox fencing 的 RED tests，再重构 Store；E-A 通过前不实现多进程 Supervisor，E-B 通过前不建议生产 enable。E0 已把缺失/损坏/非法 legacy control 改为默认 paused，并修正两处陈旧 review fixture，未放松生产 review gate。Phase E 不修改 revenue-forecast/filing-fetch/StockWiki，不启动生产 Worker，也不删除历史派生数据。

### M2-provider 完成收据（2026-09-28）

- provider policy、逐动作 use policy、prefetch admission、postfetch validation、`/2` transport、canonical admission、英文 material/lineage、preflight service 与 CLI 已按单向依赖拆分；四个 38/41/23/19 复杂度冻结项移除，新模块和 facade 顶层函数均不高于 10。
- 完整 fake provider 子进程 E2E 覆盖 HTML/TXT：discover → discovery preflight → candidate preflight → fetch-candidate `/2` → stdin import → verified reader → selector/locator replay；第二次先 resolve，fetch 计数保持 1，原件/sidecar 各一份。
- 集中失败矩阵覆盖 discovery/candidate 权限拒绝、timeout、坏 JSON、超限 stdout、effective URL 漂移、fetch 后 policy 漂移和 reader 原件 hash 漂移；拒绝链 raw/sidecar/catalog source/staging 均为零，timeout child 已回收。
- Phase D 核心门 **51 passed**；selector 定向回归 **3 passed**；Phase C 真实样本 E2E **2 passed**；E-T 自有 producer/translation-control 离线测试 **31 passed**。pre-commit 的 Ruff、scoped mypy、config doctor、host-assumption guard 全绿。
- synthetic HTML/TXT 空间收据分别为 raw 343/266 B、sidecar 3131/3125 B、catalog 249856 B、selected 3551 B。短样本固定元数据开销使 selected/raw 比率大于 1，不能用于估算长文档；Phase C 的 12 件真实文档 1.0533% 才是当前长文档派生比例证据。
- 所有 `C:/cwt/m2p-*` 测试根按精确父目录/名称校验后清理；RF 保持 `fcap@ee0a82bf` 且原 dirty 工作树未改，E-T 保持 `codex/transcript-companion-adapter@1a48f66e` 且原未提交工作未改。

### M1 完成收据（2026-09-27）

- 正式 `SourceEnsureResult` / `CloseGapResult` 生成正例，错误别名、未知 schema、request ID 漂移、哈希/大小/MIME 漂移均失败关闭。
- `operation_contract.py` 负责边界校验，`operation_projection.py` 负责纯 pathless 投影，`source_operation.py` 缩为 parse → project facade；新模块复杂度上限为 10，未加入冻结豁免。
- read-only ensure 改为复用正式 `SourceEnsureResult.to_dict()`，不再手写第二套 acquisition envelope。
- latest-as-of fake provider E2E 覆盖发现新期次和 provider unavailable：均为零 fetch、零 staging、原件 SHA 不变；底层异常文本不进入公开 DTO。
- M1 合并门共 **115 passed in 38.25s**；另有 Ruff、strict mypy、`git diff --check` 全绿。测试只使用 `%TEMP%/cw-m1-*` 独立根并在 finally 中清理。
