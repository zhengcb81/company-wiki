# CWP 架构与代码质量独立审查交接（2026-10-13）

状态：仓内实施及集中验收完成，交 ROOT 接收；没有推送或修改安装副本。基线 `eeca43dd`；提交 `d71c8e4f9ad38034dd0be5b80253116970481343`，工作树 `C:/Users/郑曾波/Projects/_harness_worktrees/architecture-quality-20261013/company-wiki`，分支 `codex/aq-cwp-20261013`。17 文件变更，正常提交 hooks 全绿。不能把这次工程接收理解为 DU 已发布或母计划真实 G2/G4/G5 已完成。

> 2026-10-13 第二次收口完成：ROOT 已接收首 commit `d71c8e4f`；追加 commit `1f9f0673b23513640ca9e0e3c46ace28fa1b1136` 已正常提交，独立 worktree 干净，待 ROOT 接收。固定样例 route overlap 阻断及便携 hook 问题均已实际修复，不再留作后续。第二次集中验收 178 pass / 1 个既有 symlink 能力 skip，9.31 秒，正常 current-PATH POSIX hook 启动，ruff/mypy/config-doctor/host guard 全绿。

## 1. 调查范围与方法

先读工作树 AGENTS 和 ROOT 质量计划，再用 canonical CodeGraph `status/files/context/search/callers` 做结构全景，随后读取确定文件及字面配置、异常、路径、临时文件、测试和历史契约。索引有 1,097 个 Python 文件；canonical index 部分新模块尚未覆盖，`no callers` 不能证明动态注册、回调或新模块没有使用。当前工作树 AST 普查覆盖 `src/company_wiki` 全部模块：调查时 268 个 Python 文件、83,298 行、2,916 个函数/方法；这是结构扫描，**不是宣称逐行审查全部 83,298 行或彻底无缺陷**。具体深读如下。

| 层/入口 | 调查到的真实职责与调用 | 处理 |
|---|---|---|
| pyproject 的十个公开 CLI | source-catalog、source-read/query/export-v2、identify、transcript-import、narrative-read/batch 等分别进入所属应用层 | 保留公开契约，未增加入口 |
| config / policy / runtime-policy | `load_catalog_config` 支持 YAML 1.0；`load_root_policy_2x` 默认仍用 YAML 1.0；`load_root_policy_3x` 严格接受 3.0 并调用共享 2x loader；信息标签不提供外发/阅读许可 | 修复共享配置形状规则分叉 |
| service / scanner / registration_scope / adapters | SourceCatalog 组织 scan/register/read/export；scanner 负责真实 SHA、manifest、群组和登记，adapter 负责布局元数据，reconcile 原来再实现一次布局 | 将有限 issuer 布局发现交回现有 adapter |
| acquisition / acquisition_service / canonical_writer / journal | 查询优先，缺源 discovery/stage，在目标锁及目录锁内入库，失败清理和计费/错误观察有明确责任 | 修复 writer 去重还信旧绝对路径；保留已有锁/失败清理 |
| source_reader / resolver / source_read_policy | v2 SourceRef 无物理路径；读层根据当前注册根定位并验真实字节；v1 resolver/handle 是显式兼容结果，不等价于已开原文；旧 read-policy pin 仅 lineage | 下沉共享相对定位/realpath containment，旧私有别名保留 |
| source_contract / canonical_ingest / SourceExportBundleV2 | immutable manifest/parser evidence/export，SourceExport v2 只有原文 UTF-8 text shape 可以直接独立 grounding；PDF 等叙述通过其拥有的 narrative/replay 通路 | 保留证据语义；不将仅 hash 通过谎称内容正确 |
| normalizer / document_normalization / parser_adapters | 原格式解析、进程隔离、结果交换、页/表/段落/QA；最终交换路径本来用每请求 mkstemp，不是 PID 共用 | 合并交换文件 atomic commit，不改解析算法/DU 目录 |
| narrative_document/evidence/context/group/budget/replay | 源选择、完整上下文、原语言摘要、locator 回放；已有多个针对性修复，文档策略合并由 DU 主线接线 | 只审查职责/关联项，不创建第二文档引擎 |
| automation worker/supervisor/execution_snapshot/store | 有界子进程；claim lease/generation、heartbeat、outbox、原子 finish 保证丢包恢复；客户端每 worker 独立 | 保留已有 AUTO 状态库，不新建 scheduler/queue |
| narrative_run_store/model_caller/http_model | 实际配置模型的有限请求；调用前 conservative reservation，未知费用不自动归零；请求/响应/时间有边界 | 广泛异常在 ledger/协议/进程边界有实际含义，不一概删除 |
| narrative_artifact_store / transport | 内容地址对象与短 DB 事务，失败可重用已写对象；公开 transport 重新验 source/artifact/locator | 保留跨进程交界的验证；内层源路径查找共用化 |
| ingestion/graph/wiki 兼容 | canonical `ingest.py` 导出 source-only service；legacy helpers 仅 `__getattr__` 明确加载；AGENTS 的 legacy writers 冻结，旧类型 graph 仅兼容 | 没有按 grep 字面粗暴删除仍有 import/测试的对象 |
| hooks/CI | commit 静态，push 受影响快测，CI 五分钟单 Python；真实网络/模型审查是大节点 | 不新增网络 CI、许可 JSON、人工签收或每小节点全套测试 |

CodeGraph 结构证据包括 `SourceCatalog` service 108（索引基线）、`SourceVersionReader` source_reader 148（索引基线）、`CanonicalSourceWriter.import_staged`、`SourceAcquisitionService.ensure`、`SourceResolver.read_verified_bytes`、`Worker/WorkerStore`、`Controller/NarrativeArtifactStore`、`NarrativeBatchRequest/PolicyConfig/AutomationSupervisor`。该索引行号可能早于最新基线；下方修复证据使用交付 commit 的文件/符号位置。

## 2. 已实施的四组共用根因

### AQ-CWP-01：写入侧虚拟化没有贯通（P1）

旧 `canonical_writer._existing_original` 查询 catalog 的 `locations.absolute_path` 并相信数据库中历史 `roots.kind`。当前根迁移后，它找不到原件而漏掉去重；旧根仍在或从配置撤下时又会采用不属于当前根的旧目录。先运行四种反例全失败：移动当前根、历史目录仍存在、撤下旧 root_id、恶意 relative locator 被 valid absolute_path 掩盖。

现在 `canonical_writer.py:578` 只查询**当前配置 canonical root_id** 的 active/original location，将 `relative_path` 交给 `source_location.resolve_source_location:61`，再验实际 SHA。没有将只读 external 根升级为 writer 目标。`source_location.inside_configured_roots:32` 是从 resolver 原函数下沉的同一个纯 `realpath/commonpath` 实现；resolver 保留 `_inside_configured_roots` import alias，reader 保留 `_relative_segments` alias，避免复制实现和基础层反向 import 上层 resolver/service。

新增完整验收：原件/sidecar 搬目录而不 full scan → 再次入库 deduplicated_after_download → 同一 SourceRef 在公开 reader 正确打开 → source/sidecar 字节仍相同；坏 SHA 仍拒绝。无需再签 hash 许可。

### AQ-CWP-02：多套 PID 临时文件互相覆盖/误清理（P1，产物完整性）

service MD/CSV、normalizer 交换 envelope、canonical provenance、official projection 各自实现相似 `path + PID.tmp`。同进程多线程共享 staging，同 PID foreign staging 会被覆盖并在失败 finally 中删除。RED 两项失败，保留目的文件的 serialization-failure case 原本已绿。

现在基础设施 `company_wiki._atomic_file.atomic_output:17` 使用独占、同目录唯一临时文件，关闭再 `os.replace`，finally 只清理本次文件。四类调用方分别复用：`service._atomic_write:1327/_write_csv:1332`、`normalizer._write_parser_envelope:276`、`canonical_writer._write_provenance:649`、`official_json_projection.persist_projection:805`。

**语义没有混淆**：immutable 原文/provenance 的 preexisting/conflict 规则和 CatalogOperationLock 留在 writer；helper 不负责许可或业务事务。provenance/projection 保留原本 fsync=True；普通 derived/export 不加默认 fsync。raw copy 仍在既有串行目录锁下独立验证，未改为无条件普通覆盖。normalizer 最终结果路径原本每请求 `mkstemp('.parser-result-*.json')`，这里保留，没有把不同请求结果都塞到同一文件。CSV UTF-8 BOM 与 CRLF 精确 bytes 保持。

测试实际两个线程写同一目标并对真实 replace 协调，不仅检查字符串；同时验证 distinct staging、foreign staging、replace/body/CSV failure、目的文件完整与清理、sync opt-in。普通 CI 新用例不创建真实网络/模型调用。

### AQ-CWP-03：配置版本复制后校验规则分叉（P1）

1x 已有 `_require_boolean`，2x/3x 却接受 `reusable_for_filing: "false"`、整数或容器，最后 `bool("false")` 为 True，导致复用状态与用户配置相反。2x 只检查 unknown fields，不检查 required subset；少必需字段得到裸 `KeyError`。RED 15 fail/15 pass。

现在 `policy_2x.py:54` 复用 config 的 `_mapping/_require_boolean`，移除重复 `_mapping`，检查必需字段完整，错误明确为 CatalogConfigError。3x 经现有 shared loader 同步修复。合法 True/False/None、老 defaults、schema 分支保持。该项是数据入层形状验证，不是人工权限；不创建 authorization、expected-config hash 或消费者跨层复核。

### AQ-CWP-04：本地缺源发现重新写了一套布局分支（P1）

`local_reconcile._discover_source_groups` 自己分 `root.kind == company_raw/dayu_portfolio`，与已有 adapter 重复，directory 根即使配置 `company_raw_v1` 也不发现已有未登记原件，会让上层认为缺源。既有 `test_future_root_config_only`/`test_fc1201_root_hardcode_gate` 在基线就捕获该问题；本次没有把文件加 allowlist 或删/放宽它们。

现在 `local_reconcile.py:325` 只按配置调用 `adapter_dispatch.discover_issuer_paths:65`；纯有限布局方法放到现有 `CompanyRawAdapter:35` 与 `DayuAdapter:108`。caller 继续拥有 I/O/byte/deadline/entry/group budget、root containment、metadata reader；adapter 不写 DB、不下载、不调用模型。无 adapter 的 1x 旧配置只在 adapter dispatch 保留集中 kind→factory 兼容，reconcile 不知道 root 名称/布局。

新增真实反例与验收：两个不同 root_id、中文空格目录、同 company adapter 的 directory 根、非周期 IR TXT 未登记原件 → 有界发现/登记 → 一个 SourceRef、两根 locations → 公开 source-export read 返回原 bytes → 再发现无变化。超 aggregate entry budget 仍失败，原件不变。Dayu 方法仅在 **CWP adapter** 读取外部布局，Dayu 项目没有任何改动。`SourceAdapter.enumerate` 原签名不变；新 `discover_issuer_paths` 是可选仓内能力，无该能力的 adapter 不触发全根扫。

### AQ-CWP-05：共享有序存储路由，真正驱动 scanner（追加已完成，P1）

ROOT 明确选择列表 first-match，不再拒绝合理 overlap。先 22 个 route/hook 反例中 19 RED / 3 已有正确拒绝；真实 scanner 混合布局反例也 RED：只运行 root.default sidecar，原文变成 indexed_only，route 指定 adapter 未执行。

`RootSpec.first_matching_route:112` 统一 include/exclude 顺序，`route_matches:121` 委托该方法，`effective_root_for_path:125` 选择 route adapter/profile，缺值继承 root。删除 1x `_OVERLAP_SAMPLES/_glob_overlap/_check_route_overlap` 九个样例阻断，2x/3x 共用 `_route_spec:222` 真实字段/adapter/profile校验。原两条 overlap-reject 旧测试按已确认语义改为明示 first route 所有权；未知 ports、非法类型、root allowed kinds 不扩大、真实路径/bytes/budget约束保留。

实际入口是 `scanner._scan_catalog_impl:843` 的策略选择（包括只配置 route adapter 的根），经 `scan_root_strategy` 调 `adapter_dispatch.scan_root_via_adapter:120`，不是包装器假路由。每不同 adapter 最多枚举一次；原文选择其 group 和附件所有者，候选携带 effective RootSpec。显式 registration paths 先按同一 matcher 分区。三个既有 adapter 新可选 `primary_filter`（默认 None，老调用不变）拒绝非owner原件后再解其 metadata；否则实测 Dayu 错布局会把 `.source.json` 当新 original，或在有限登记时跑到根外读 metadata。这两个实际反例均修复，未通过扩大 allowlist/取消根归属掩盖。

调用方只传原有 metadata/walker/group/entry/byte/deadline ports，所有 adapter 共用同一个预算，不复制额度。真实两个布局 max_discovery_groups=1 在第二 group 报 local_source_group_limit；TXT IR 的完整 SourceCatalog scan/local-discovery → SourceRef query/open 绿，原件不变。route profile 作为 source processing 声明随 effective RootSpec 传递，不变成新的逐文档权限或投资 acceptance。

现行使用说明是仓内 `docs/source-catalog-routing.md`。这属于存储扫描 scope，与 DU 文档阅读策略 router 分开；DU 包和冻结接口没有变动。

### AQ-CWP-07：便携 pre-commit 实际启动（追加已完成，P2）

`.githooks/pre-commit` 原 wrapper 固定 C:/Miniconda、bash arrays 与 sh shebang 互相矛盾。现用 POSIX shell，按当前 PATH 的 python/python3（或 pre-commit）启动原 `pre_commit hook-impl`，保留已有快检查及参数，缺 runtime 明确失败。没有加 pytest、pre-push 或安装路径/新门。

三个真实 shell 执行反例先红后绿：隔离 PATH python shim 被正确选择、中文/空格参数保持、没有 runtime 的失败信息明确。最终正常 `git commit` 真实调用新的 hook；ruff/mypy-contract/config-doctor/host-assumption-guard 全 Passed，dependency hook无相关文件正常 skipped，整个 commit约10秒。

## 3. 验收与已遇到问题

- 第一次存储/atomic TDD：7 个，6 fail / 1 pass，2.54 秒。
- 配置 TDD：30 个，15 fail / 15 pass，1.23 秒；修复后三schema全绿。
- 布局 TDD：2 个新真链 + 1 个既有架构门，3 fail，1.00 秒；改造后全绿。
- 存储/reader/export/projection/既有 spawn parser liveness：131 pass，86.33 秒。慢的是既有进程生存/故障套件，不加入每 commit 的新 gate。
- 配置/布局/已有local-reconcile/adapter/架构集中：156 pass、1 skip，8.46 秒。
- **最终交付集中验收：267 个，266 pass、1 skip，23.08 秒**，见 `pytest-final.xml`。44 个新增行为回归（其中 2 integration）；没有修改旧测试断言。
- 全 `src/company_wiki tests/unit tests/contract` 加新 integration 的 ruff 绿；source_reader/policy_2x mypy 绿；`git diff --check` 绿。正常 commit hooks：ruff、mypy-contract、host-assumption-guard Passed，其余无受影响文件正常 Skipped。

最终 pytest 命令完整保存在 handoff.json 的 tests 条目。skip 是旧 Dropbox symlink 越根能力样本，理由为本机不支持 symlink 创建；最终 XML 带具体原因，不是跳过新增坏情况。

施工中两个测试命令错用了不存在的历史文件名（parser_isolation、zr401_root_policy_3x），两次零收集，均通过 `rg --files` 换为实际路径，不算成功测试。新增完整搬家测试第一次重建 staging parent 触发 FileExistsError，已修正其 fixture lifecycle；新 IR fixture 第一次 adapter_version="1" 不符合原有 semantic version 规则而被隔离，已改为合法 "1.0.0"，没有放宽生产校验。source_reader tracked HEAD 是 CRLF，最初换行规范化造成噪声，经 ROOT 提醒从 HEAD 原字节重建局部改动，最终只是 9增/30减。

## 4. 保留、关联与后续事项

1. **DU 接线负责**：当前页/句关键词、文档标题 kind、完整 QA/业务项目语义组合等不足归 document-understanding-2026-10-13。不得再建平行 parser/selector；本次未写 DU profiles/structure/benchmark 及其 tests/fixtures/PWF。
2. **配置 route overlap 启发式（历史 RED，现已关闭）**：`config.py:240` 用固定九个示例路径做 `_glob_overlap`、不计 exclude。实测假阴性（两个 `issuer-x/**` 同时匹配而 load 允许），也实测假阳性（`**/*.pdf` 排除 `financial_reports/**` 与第二 route 仅含该目录，却 load 拒绝），见 `config-route-observations.json`，2x 无此检查。该问题是存储扫描 scope 配置，不能与 DU 文档类型路由混称。ROOT 已明确选择有序 first-match；追加 commit 实施统一语义及真实扫描所有权，历史反例留存为 RED，不再作为当前缺陷或后续待办。
3. **legacy 与 canonical 仍有大函数**：结构普查最大的 CLI `main` 608 行、`narrative_batch._run_prepared` 434、scanner `_scan_catalog_impl`423/`_scan_root_v1`388、store read_pipeline_status376。行数说明维护成本，不证明错误。实际可继续沿现有 service/handler ports 收口应用调度，优先合并同职责重复，不按类/文件数量再引入抽象层；DU 集成时避免又加一套主流程。
4. **不同 source DTO / source_contract adapter 有兼容职责**：SourceRef、SourceRefValue、SourceHandle、manifest/export 和 NarrativeRef 不是同一个对象的几份随意备份；外部 v1 仍可引用。只有确认跨仓消费者切换后才删除旧 wire adapter，不把 canonical 原文/事实和研究结论合并。
5. **旧 canary/activation/snapshot 文件仍是显式兼容操作**：当前 steady reader 不自动发现它们作许可，prompt review 为诊断。旧类/迁移/显式命令仍有历史记录和对应测试，不以 `reviewer/hash` 字面就判定生产正常读取仍被门禁。未来继续做可达调用盘点和删兼容；不要求用户重新逐文件许可。
6. **广泛异常不是统一坏代码**：CLI 防密钥泄露、process/thread/transaction boundary、坏行不杀全批和unknown billing必须保留正确失败语义。`normalizer._manifest_from_column`/Worker handler boundary/NarrativeRunStore rollback 等仍有明确上层分类。可选诊断退化不能伪装成功；本次无错误状态放松。
7. **有意保留跨进程验 hash**：SourceRef来源层拥有原文读和验证；FF/RF 对自己实际收到的 transport bytes/evidence 应独立确认，不能当成多余重验全部删掉。没有给每条业务事实额外加身份门。
8. **安装/hook 部署（wrapper 已关闭）**：CWP `.githooks/pre-commit` 是早期生成 wrapper，含主机 C:/Miniconda Python 和 bash array（first shebang sh）；追加 commit 已用当前 PATH 的 POSIX wrapper 收口并真实正常提交成功，机器路径不再作为 hook 设置。runtime 模型应沿已配置 composition root；冻结 typed AppConfig 与 scripts/config 的默认表不应被当成新模型配置来源。
9. **Sidecar adapter 无 issuer-scoped discovery 能力**：它的既有显式 register/scan 仍可用；新可选 API 不默默做昂贵全根递归。当前新增测试覆盖 directory+company_raw adapter，不宣称任意布局已有自动发现。若新增此能力，需要明确目录查询策略和同一 I/O budgets，不能扔回 consumer 直接文件扫。
10. **真实模型/事实质量**：这次无 LLM/网络调用，费用 0。工程恢复性和路径证据不能替代真实文档精选摘要质量及 RF 合理性，仍需 ROOT 大节点 G2/G4/G5。

## 5. ROOT 接收建议

先前 `d71c8e4f...` 已接收；现在接它的直接子 commit `1f9f0673...`。公开 CLI/DTO 无变更，跨仓只需跑 existing FF→CWP SourceRef reader→RF 离线真链：已有文件不下载、缺源 provider 正确、根搬家仍复用、读取/入库失败诚实、预算/清理保持。`pytest-final.xml`（首轮）及 `pytest-routes-hook-final.xml`（追加）、report.md、handoff.json 由 ROOT 单独归档母计划即可；不需要重新运行 86 秒的旧进程故障套件。

追加保留同一边界：原始资料、生产配置、密钥、Dayu 项目、其他仓、DU worktrees 都未修改；所有 runtime tests 的文件来自独立 tmp 夹具。当前独立工作树干净，没有安装同步、push、生产迁移、许可材料或新工作库。
