# 关键节点端到端测试与测试目录恢复方案

> 计划补充（2026-09-27）。只定义后续 G1–G4 放行测试；现在不执行下载、删除、Worker 灰度或生产写入。复用[大节点审查节奏](milestone_review_cadence.md)，不增加逐卡审查。

## 1. 强制边界

- 端到端测试从隔离输入走到该节点承诺的最终输出；不以单元测试拼接冒充端到端测试。
- 测试只操作本计划专属的运行根目录、临时 SQLite 和 fake provider。禁止将真实 `companies/`、生产 catalog、共享 derived/index、其他项目目录、正式 Worker 状态或全局 cache/log/lock 配成输出目标。
- 固定 fixture 是只读输入。真实年报、招股/再融资、IR、电话会议样本如需参加 E2E，先按样本 manifest 将其复制到本次运行的 `inputs/`，核对源 ID、字节数与冻结 SHA；执行期间只读该副本，不从生产目录直接解析或写回。
- 在线下载默认由 fake provider 模拟。G1e 的单份真实 canary 可先于下游 G0，但必须先冻结 transcript 专属的来源 URL、逐动作内容权利、provider API、限流和副作用边界，并取得该次精确 canary 授权；输出、配置、日志、锁和缓存都必须重定向到本次运行根目录。无法证明权利或重定向时禁止在线测试。其他 G 节点仍按各自 G0 门禁执行。
- 测试结果只保留短收据（运行 ID、代码/fixture 版本、命令与退出码、关键指标、前后清单摘要、清理结果）到本计划 `progress.md`；不保留下载正文、临时数据库、全部解析结果或重复日志。

## 2. 目录、基线和恢复协议

建议目录结构：

```text
tests/e2e/
  fixtures/                 # 小型合成输入、冻结 manifest、预期断言，只读
  .runtime/
    <run-id>.manifest.pending # 创建阶段短暂存在；run root 创建前原子完成正式 manifest
    <run-id>.manifest.json    # run root 的兄弟控制记录；清理后删除
    <run-id>/                 # 每次新建；运行时副本、临时配置/数据库、下载和所有产物
      inputs/                 # 从许可样本复制来的文档
      sandbox/companies/      # 仿真的 company-wiki 公司目录
      state/                  # 临时 catalog、WAL/SHM、cache、lock、日志、outbox
      outputs/                # package/export、摘要、临时索引等
```

.runtime/ 是预先建立的空测试运行容器，加入忽略规则；它本身不由单次 E2E 创建或删除。若该容器尚不存在，先由测试基础设施初始化并把它作为后续运行的起始基线；或改用已存在且可核验的显式 basetemp 父目录。fixtures/ 中的测试样本不得被执行器修改；大 PDF 不提交到 Git，运行时从显式 allowlist 复制，并用冻结 SHA 验证。每次运行使用不可复用的 run ID；测试运行根必须在开始前不存在。若目标已存在、manifest/fixture 与冻结版本不符，或运行根/其祖先含 junction、symlink/reparse point，立即拒绝运行，绝不先清理旧目录。所有可写依赖必须通过显式临时配置指向本次 run root；无法隔离的隐藏 cache、日志、锁、数据库或下载路径都视为阻断条件。

pytest 的 tmp_path 若位于独立、唯一的显式 --basetemp 下，也满足 run-id 隔离；这适用于沙箱默认 %TEMP% 不可写的情形。basetemp 必须一轮一目录、开始前不存在，且纳入同一快照/清理协议；结束后由调用方清除并核对不存在。不可复用或递归清空有旧资料的 basetemp。

**Windows 短路径要求：**本仓 `conftest.py` 会在绝对 basetemp 路径超过 60 字符时把目录重定向到 `%TEMP%/cw-pytest-basetemp/`。这类重定向目录可能受系统 ACL 影响，不能仅凭 pytest 的退出码视为已恢复。需要删除验证的测试应传入本仓可写 `tmp/` 下、运行前不存在且绝对路径长度不超过 60 字符的唯一 basetemp；核对 `CW-BASETEMP-DECISION` 为 `relocated=false`，测试结束后逐项检查并删除且只删除这个 run-id。若发生重定向，必须核对实际 `effective_basetemp` 并确认可访问和已删除，否则该 E2E 的 cleanup gate 失败，不能放行后续节点。

每次运行先对唯一随机 run ID 做冲突预检，再在 .runtime/ 下以 CREATE_NEW 创建该 ID 专属的 manifest.pending；写入完整控制记录并 flush/fsync 后原子改名为 manifest.json，最后才创建同名运行根。控制记录至少包含 run ID、唯一运行根相对路径、canonical path、启动 PID 与进程启动时间、测试代码/fixture manifest 版本、起始 fixture 与 .runtime/ 树摘要、获准输入 allowlist 及每个源的 SHA/字节数、允许写入根。此顺序保证正式 run root 不会在有效 manifest 之前出现；manifest 只是运行记录，不授权访问其中列出的根外路径。

每个 E2E runner 遵循同一生命周期：

1. **开始前快照**：记录专用 `tests/e2e/` 树和任何预先存在的运行容器/显式 basetemp 父目录的相对路径、类型、字节数、SHA-256、修改时间及 Windows 文件属性；记录本次 run root 不存在。固定 fixture 只读，且在 runner 外完成 fixture SHA 校验。若 `.runtime/` 起始不存在，不得为单次测试临时创建它；改用已存在且已快照的独立 basetemp 父目录。设置 `PYTHONDONTWRITEBYTECODE=1`、禁用 pytest cache 或把所有缓存明确重定向到唯一 run root，避免 `__pycache__`/`.pytest_cache` 改动固定测试目录。只哈希本次 allowlist 样本，不遍历/重哈希 46 GiB 生产目录。
2. **写入隔离**：所有输出路径经 canonical path 检查，必须落在唯一运行根下；fake provider 拦截网络。真实 canary 下载也只落在 sandbox/companies/{entity}/...，不碰正式公司目录。调用 earnings-transcripts 时必须通过与生产相同的 filing-fetch 调用边界，但把 provider/tool 替换为 fake；不得直接绕过编排器调用解析器来冒充端到端覆盖。只有能隔离其 CLI 配置、transcripts output、cache、log、lock 时才可运行真实 CLI。
3. **正常/失败收尾**：finally 中先停止并等待所有子进程，确认退出后关闭 SQLite 连接并 checkpoint，再清理唯一 run root。Worker 并发 E2E 还必须验证 child process 全部退出、没有活动句柄后才清理；单元/合同测试不能替代这条跨进程链路。
4. **强制中断恢复**：新增运行前若发现遗留 manifest/run root，不启动新测试，也不按时间或通配符清理。对 manifest.pending，只允许在同一随机 run ID 的 run root 尚不存在时删除这一个精确 pending 文件，因为协议保证有效 manifest 完成前不会创建 run root 或任何输入/下载；若 run root 已存在则保留现场并失败关闭。对正式 manifest，只有校验 run ID、项目归属、预期父目录及“起始时该 run root 不存在”后，且原 PID+进程启动时间确认已退出、run root 内没有 reparse point/越界链接，才允许 cleanup。进程仍活、manifest 损坏、路径不匹配或检测到越界时保持现场并失败关闭，需人工排查。机器断电/强杀测试必须验证这些分支。
5. **只删本次运行物**：因为运行根在开始时不存在且从开始到结束由本次 run 独占，cleanup 只按已验证的 canonical path 删除这个精确目录及其已验证的同 ID manifest；不得按 manifest 任意路径逐个删除，也不得按通配符清理 companies/、项目根、transcripts 仓库或共享 cache。输入副本、模拟/真实下载 TXT、翻译/摘要副本、临时库、WAL/SHM、锁、日志、索引及中间产物均应位于该根内并随之删除。若发现 run root 以外发生写入，停止自动清理、记为失败并逐项调查，不让通用 cleanup 猜测删除外部文件。
6. **结束后核对**：重新比较完整 `tests/e2e/` 树及所有预先存在的运行父目录：路径、类型、内容 SHA/长度、修改时间和属性必须与基线一致；fixture 起始 SHA 仍相同，运行容器本身及其起始条目逐项不变；开始时不存在的下载路径、唯一 run root、同 ID manifest/pending 必须不存在；遗留进程/文件数必须为 0。若为清理本轮唯一子目录而导致预先存在的父目录时间/属性变化，只恢复这几个已快照目录元数据，再重核；不得覆盖恢复 fixture 内容。任一差异、清理失败或路径越界均判该 G 节点失败并暂停后继放行。

访问时间可能因只读读取而变化，不作为差异；路径、内容、长度、文件/目录修改时间和属性必须一致。基线 fixture 一律只读，不能自动覆盖恢复：若发现基线文件变化，先停止并报告；只有能证明是本次测试执行器造成且具备运行前校验副本时，才可恢复测试目录中的该 fixture 并留下事故记录。任何生产/外部路径变化均不得由通用 cleanup 猜测或删除。测试收据只记录清理状态和 hash，不保留下载正文、临时库或大体积解析产物。

## 3. 各放行节点的端到端用例

| 节点 | 隔离端到端路径 | 关键断言 | 大节点放行条件 |
|---|---|---|---|
| **G1 来源到叙述证据包** | 年报/半年报/季报、招股及再融资、IR、英文 transcript、低价值格式文件的 manifest 样本副本 → resolver/分类 → 轻量解析 → 选择/coverage → 摘要草稿 → package → locator 从同一 raw 副本回读。Transcript acquisition E2E 待正式 companion schema/provider adapter 冻结后，从 filing-fetch 新版 public orchestration 进入 → fake adapter 在受控边界返回精确期次 → sandbox staging → canonical writer → 解析/选择/英文摘要/package。 | 源身份/哈希、角色、时点、语言、否定和限定词保留；locator 从同 SHA canonical TXT 回读；标准财务表不被写成业务摘要；TXT 不翻译；全量 normalized/span 零增量；负例可跳过，未覆盖/解析失败不伪报完整。Transcript `provider_payload_sha256` 与 `canonical_file_sha256` 按冻结内容/编码规则分别验证；正文未翻译且 locator 回读，sidecar 的来源 URL 必须是有效 HTTPS；已有 transcript resolver 命中时 provider 调用为 0；transcript 失败不抹掉成功的 filing 子结果；未授权时零 provider 调用/零写入。 | 本节点承诺的 G1 集成 E2E、冻结探索卡/关键负例和 locator 回读全部通过；未选范围召回门槛按 W0 盲测结果判定。Transcript acquisition E2E 依赖独立 transcript contract gate，不依赖 RF 下游 G0；不要求 live canary。fixture、runtime 树恢复相同且无遗留进程/文件。 |
| **G2a 叙述证据包消费** | G0 合同、R4 B.AR 与相应 C.local 基础 reader AR 已通过，且 W5 正式 selected package 可用后，从来源 export/selection artifact → 本仓检索/预览/resolve → StockWiki 与 revenue-forecast 的叙述消费入口。StockWiki 使用待新增的路径无关 SourceExport v2 strict reader；revenue-forecast 走其获准的来源消费入口；两者都不接收 pilot 的 source→raw path 表。当前 pilot `narrative-evidence-selection-bundle/0.2.0` 不是任一消费者的正式输入。 | `source_id`、原始 SHA、原子 `evidence_id` 与 locator 可从隔离 raw 回读；同 SHA 跨 root、priority 置换、首选副本失踪或云占位、目录移动不改 export/evidence ID、标题或业务结果；不同 SHA 不换版，权限拒绝不因换 root 放行；版本/撤回/as-of 状态失败关闭；`needs_review`、`partial` 不伪装成全覆盖。 | **复用** R4 L01–L12/P01–P03 与 C.local 的未变 reader 收据，只增验 selected package 的真实跨仓消费；只有本仓模拟 harness 或现有 v1 `--source-root` dry-run 时只记合同/兼容测试，不宣称新版端到端消费。临时 export/fixture 派生产物清理后目录基线一致。 |
| **G2b invest-quick-scan 身份互操作** | 仅测试可选的 company-wiki 证券/实体身份快照 → quick-scan 的实际身份映射入口；分别覆盖已映射、未知/歧义、`company_wiki_ref=null`。不得把叙述包、原文或摘要接入 quick-scan。 | 身份映射有版本/hash 与歧义失败关闭；缺少 company-wiki 身份时扫描仍可运行；不读取/保存公司文档、原文正文或 SelectedEvidence。 | 只在 quick-scan owner 合同允许并使用真实 reader 时记跨仓 E2E；否则只记本仓 identity contract fixture。身份快照临时副本清理后目录基线一致。 |
| **G3 Worker 受控并发** | 临时 source catalog/job store + fake provider + 1/2/4 文档负载 → 持久 enqueue/claim → parse/select/summary → artifact prepare/visible → export；在 provider 返回、文件 fsync、DB commit、outbox ack、暂停/恢复和进程退出点注入故障。 | Windows 真子进程验证无重叠 claim/重复 accepted artifact；丢失/超时 job 可重试或进入明确定义的终态；暂停后没有新网络/claim/激活；同 key 幂等、共享限流生效；失败产物不提前可见；所有 child process 和句柄可收敛。 | 串行基线及 1/2/4 并发 E2E 均跑完；故障注入后的队列状态、artifact、outbox 可对账；吞吐/资源达到 W0 门槛；runtime 无 child process、锁、WAL、outbox 或文件遗留。只在 scratch store 运行，不连接正式队列。 |
| **G4 原文处置/物理删除** | 只在运行时复制的 scratch company tree 上走资格判定 → 引用/副本检查 → intent → 删除 scratch 副本 → receipt/恢复；在 intent 前、删除后、receipt 前中断并恢复。 | 低价值唯一来源、重复副本、混合业务材料、OCR/附件缺口、旧 locator 等反例按合同失败关闭；删的是清单中精确 scratch path；原始 fixture 和生产清单/哈希不变；崩溃后状态可识别/恢复。 | 所有处置门槛、负例、重启恢复和基线相等通过后才可提交 G4 审查；测试通过不构成生产删除批准。测试树清理后 fixture 完全不变、runtime root 不存在。 |

不为 G0 增加全链 E2E：G0 的目标是冻结接口/门槛，使用静态只读 contract fixtures。G1–G4 各集中执行一组覆盖范围明确的 E2E；日常小改只跑受影响的单测/contract test，只有影响 G 节点结论的输入或实现变化才重跑相应 E2E。E2E 作为大节点审查的一部分，不为每张 W/N/D 实施卡增加签收；实际运行失败时可针对失败修复跑目标回归，最终放行仍重跑该 G 节点的完整 E2E 组。

### R4 B/C.local 的同一运行协议（不增加 G 编号）

[R4 优先实施卡](../painpoint-outcome-audit-2026-09-05/r4-data-lake-priority-rollout-2026-09-27.md)的 B.VR/B.AR、C.local.AR 基础来源 reader，以及 W5 后本专题 G2a，均使用本文件 §2 的唯一 run-id、输入 allowlist、前后树快照和只删本次运行目录规则。B 的端到端从**真实原生目录布局**或 P06 同 SHA 四隔离副本进入正式 adapter/catalog，经 `query_local→verified open→locator` 到最小通用读取结果；B 不等待 filing-fetch/RF/StockWiki 接线。C.local 才分别调用 filing-fetch、RF、StockWiki 的真实**基础来源**入口并核查原文字节与目录迁移后的业务结果；G2a 待 W5 产物完成，复用已验 reader 并加测 selected evidence package。B/C.local 各留一份大节点结果包，G2a 仅增量结果，共用样本与清理协议，不复制 46 GB 生产库、完整恢复备份或每张子卡另建测试目录。StockWiki 现有 `validate` 只核 SourceExport v1 合同、现有 `sync --dry-run --source-root` 只作旧兼容回归；新路径无关 SourceExport v2 的 strict reader/CLI 必须无 raw path 入参，并在隔离 root 的新版 dry-run 实际验原文字节，否则该消费者栏 hold。真实云离线、真实修订和 `future_lake` 原生样本未具备条件时分别记 pending，不能用故障注入或改名副本冒充。

## 4. 放行收据

G1–G4 的现有大节点收据统一增加以下字段，而不是再设小节点签字：

- `run_id`、测试根 canonical path、代码 commit/dirty 状态、fixture manifest SHA、配置/parser/selector/summary/worker 版本；
- 测试命令、退出码、使用 fake/live provider、样本类型/数量、关键质量/空间/并发指标；
- 开始/结束文件树条目数与总字节、baseline equality 结果、遗留进程/文件数、cleanup 退出码；
- 失败和恢复记录、已授权的 live canary 范围、放行或 hold 范围。

真实 canary 生成的原始文档与全部临时派生文件在清理后不保留；收据保留来源标识和 hash 即可。若需保留文档作为新的固定 fixture，必须另行走来源许可/fixture manifest 审查，不能从 E2E 输出目录直接留下副本。

## 5. 当前实现状态（2026-09-27）

- 两个离线 G1 pilot CLI 已支持 `--run-root`，在该模式下强制 manifest、样本 raw、临时 JSON 测量文件、metrics、claims 与摘要报告都留在同一 run root；新增 `--package-output` 只允许与 `--run-root` 联用，输出到 run root 的 `outputs/`，默认计划模式不允许持久化原文包。
- `tests/e2e/test_narrative_g1_pipeline.py` 用唯一 pytest 临时树复制 P06 定增说明书与 T02 英文电话会议，端到端运行选择、locator 回读、摘要草稿与包内检索；另在 12 件 manifest 样本上检索锚点并回放全部已选证据组。bundle v0.2.0 内含 replay_contract，resolver 只接收调用方的隔离 source→raw path 映射；校验 SHA/source ID 后按包内 parser/selector contract 回放，并逐组核对 evidence IDs、locators、parser 和文本 SHA；不从 bundle 读取原件路径。越界输出被拒、T02 不翻译、包小于 raw 合计、测试 tree 复原。此项仍非 G1 全量放行：没有接生产 catalog/export、真实 transcript provider、LLM 或 Worker。
- `NarrativeEvidenceSearch` 只在进程内建立 query-local BM25 postings，不写数据库、FTS 或持久索引；配套的 `NarrativeEvidenceResolver` 是 pilot-only 同进程回放器，不是 catalog 查询 API。bundle v0.2.0 内含 replay_contract；resolver 只需调用方显式 source ID→raw path 映射。该 pilot bundle 与 StockWiki 严格 Source Provider v1 结构不同，不能直接接入其 reader。正式来源授权/撤回、历史时点过滤、持久查询 API 与消费者合同仍未冻结。旧 `EvidenceQueryService.lookup` 仍只查旧 `evidence_spans`，不能代替新 package resolver。
- Transcript acquisition E2E 尚未实现/执行。earnings-transcripts 工作树已有未提交的精确期次 `transcript_api.py` 和 stdin JSON `transcript_tool.py`，但当前 Motley Fool 自动抓取路径与其官方条款冲突，不能接生产；FMP 当前 key 的 transcript 返回 402。filing-fetch `resolve_filing()` 仍只返回单份 filing handle，request schema 1.2 拒绝未知 companion 字段。必须先冻结 provider 逐动作权利表、原始 HTML/TXT 与派生 TXT 的 parent/hash 关系、独立 transcript companion 合同及新版 filing-fetch orchestration，再运行 E2E；这个上游合同不依赖 revenue-forecast 下游 G0。测试 fake 必须替换正式 adapter/provider 边界，并覆盖拒绝路径零正文落盘，不能绕过 filing-fetch 直接调用解析器。
- G2 只读接口审查（2026-09-27）：StockWiki 当前 Source Provider v1 reader 对 bundle、manifest、span 使用严格版本和字段校验，且 `config/source_provider.yaml` 当前 disabled；pilot v0.2 bundle 不是其直接输入。invest-quick-scan 合同只允许可选身份关联，不读取叙述证据包。详见 `cross_project_coordination_2026-09-26.md` 与 `findings.md`；G2a/G2b 尚未实施或放行。
- 历史 G1 smoke 为 45 passed。此前 v0.2.0 回归中 12 样本 selected-anchor/raw-replay E2E 曾通过，但同一轮 P06/T02 对旧 bundle 0.1.0 的断言失败；断言已修正，并在最终代码上完成合并回归：12 个检索/回源单测 + P06/T02 双样本 E2E + 12 件样本 selected-anchor/raw-replay E2E，**14 passed in 122.56s**；`ruff check` 通过。pytest 治理器实际 basetemp 已删除并复核不存在，`tests/e2e/.runtime/` 运行前后均不存在，样本副本、package、metrics 与临时 JSON 均随唯一 run root 清理。该回归验证的是已选证据的内部定位/回放和两样本链路，不证明未选内容召回率/精确率、盲留出集、p95、生产 resolver/API 或 G2 消费合同。
- 当前工作树复跑（2026-09-27）：同一 12 个单测 + 两个 G1 E2E 为 **14 passed in 130.77s**。本次请求和实际 basetemp 均在唯一 `%TEMP%` 路径；两者结束后不存在，`.runtime` 运行前后均不存在，`tests/e2e` 文件 SHA 集合不变。该收据不扩大上述测试范围，也未连接生产服务、消费者或 Worker。
