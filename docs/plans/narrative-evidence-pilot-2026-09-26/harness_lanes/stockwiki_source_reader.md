# StockWiki 独立并行线：SourceExport v2 来源 reader

<!-- CURRENT_PWF_NAV -->
> **历史施工/调查材料：**当前状态与唯一下一步见[总计划](../task_plan.md)。下方旧待办、暂停、人工签收和预算只是当时记录，不自动恢复；R3/R5的真实剩余范围以总计划为准。

> **当前 StockWiki 任务：**本卡仍已完成。CWP N3a `a640400` 已发布且 CI 绿，新叙述范围按[StockWiki narrative consumer 卡](stockwiki_narrative_consumer.md)实施；不重复本卡，不改 quick-scan owner 文件。

> **2026-10-03 状态：本卡已完成，不再派发。**reader 已并入 StockWiki 主线，基础 G-B 已通过真实跨仓 E2E；W01–W04 均已完成，[W04 卡](stockwiki_g2b_owner_context.md)保留交付记录。当前主线是 CWP [N3a 叙述传输实现](../narrative_transport_implementation.md)，RF/StockWiki selected 消费 G-C 仍 pending；它是新的接口范围，不应重复本卡 reader 实施。G-D/生产 Worker 仍 paused，IQS 活动项目归其既有 owner。

> 下方开工输入、命令、起点 SHA 和实施步骤是已交付 reader 的历史合同记录。总指挥负责新的跨仓接口与汇合；后续 StockWiki 工作仍只写该仓的独占工作树，其他仓只读，每仓维持单一产品代码写入者。不要依据本卡重新启动 W02/W03/W04 或接管 IQS。

## 0. 开工事实、目标与边界

- 2026-09-29 的 StockWiki `master@5bb68f6` 已包含 W01 `QuickScanStore` 修复；`tests/test_quick_scan_store.py` 为 18/18，通过全量回归。现存 `codex/source-export-v2-reader` 工作树/分支是**旧基线空壳**，不能把它当实现，也不能直接在旧 HEAD 上交付。该仓无已知 remote；本线交付本地提交即可，不宣称已推送。
- CWP 唯一产品代码线当前为 `C:\Users\郑曾波\.codex\worktrees\data-lake-reader\company-wiki`，分支 `codex/narrative-gates-integration@7760b09`。正式输入在其 `tests/golden/source_v2/`：`source_ref.json`（schema 2.0）、`source_export_bundle.json`（bundle schema 2.0.0）、`evidence_span.json`、`source_ref_bad_sha.json`、`verified_open_receipt_normalized.json`（read receipt schema 2.1）、`verified_open_bad_sha.json`。先核对该目录 README、producer HEAD 和各文件 SHA；金样本由 CWP 真实 serializer/CLI 生成，消费者不得自造一个替代的“生产者正例”。Windows 错误回执的换行已在 `7760b09` 归一化，LF 金样本 SHA 为 `daed1b192dab90daf50bc2c9a3dc92695009944f51457177374cc77e0d53a0b5`。
- StockWiki 本线目标是**只读、显式 opt-in** 的来源 reader/CLI：消费 CWP 的 pathless SourceExport v2，按 `document_id + source_id + content_sha256` 请求 CWP 的 verified-open，验证实际返回字节后给研究侧提供来源身份、可回放 locator 和原文片段。来源事实归 CWP，投资研究状态归 StockWiki。
- 本线不做 IQS identity 2.2 的 W02/W03、四态映射、CWP selected package、默认 full sync/weekly、批量迁移、旧物理目录清理或新增跨仓写入。这些分别在既有总计划 G2b/G-C/G-D 实施；基础 G-B reader 不等 IQS 的公开 CLI。
- **原始文档绝不删除或修改。** 所有真实样本先复制到本线独有临时根，只读生产原件。StockWiki 的旧 `doc_root`/路径 SHA1 路由保持兼容已有真实持久引用；只有证明某种旧引用确实存在，才加窄迁移适配，不把路径 ID 延续到 v2。

## 1. 冻结的跨仓接口与本线输出

| 边界 | 输入/输出 | 本线验证与失败规则 |
|---|---|---|
| CWP export → StockWiki | `SourceExportBundleV2` schema `2.0.0`，`manifests[]`、`evidence_spans[]`、`bundle_sha256`、`export_id`；manifest 含逻辑 `document_id/source_id`、原文 SHA、字节数、MIME、身份/期间/时间。 | 严格 schema/字段/类型、bundle 内容哈希和 export ID；同一 bundle 内不能出现冲突的逻辑 ID 或来源版本；禁止把 path/root/location 字段当成业务身份。未知主版本、损坏/重复 JSON key、错关联、错 hash 均具名拒绝。 |
| StockWiki → CWP verified-open | 独立子进程调用 `python -m company_wiki.source_catalog.source_reader_cli --config <CWP config> --document-id ... --source-id ... --content-sha256 ... --purpose source_export`；配置路径仅属 transport adapter，不进入研究对象或持久 source ID。 | 要求退出码 0、stdout 为完整原文字节、stderr 恰一条 `schema_version=2.1, status=ok` receipt；StockWiki 自己复算 stdout SHA/长度，核对 request、bundle manifest、receipt 的 ID/SHA/长度/MIME，**还要全字段对照 receipt.manifest 与 bundle manifest**（显示的名称、类型、期次、实体、URL、collector 等都由当前 verified-open 复核）。`read_at` 为运行时 UTC，两个 policy SHA 为 64 位 hex，不硬编码。任何失败或半截 stdout 绝不产出可信证据。 |
| StockWiki 内部只读 DTO/CLI | 最小公开结果含 `document_id, source_id, content_sha256, byte_size, mime_type, export_id, title, document_kind, fiscal_year, fiscal_period, period_end, published_date, locator, exact_quote, verification_status`；对 span 还保留 `parser_name, parser_version, parse_status, quality_flags`，将字节验证与抽取质量分开。允许另带已核对的来源身份/collector 字段，但绝不带持久物理绝对路径。 | 对文本 `loc:v1/chars:start-end` 用**实际已验证的原文字节**按 UTF-8 解码并回放，核对 `raw_text`，不得凭 bundle 中的引文直接证明原文。原件为 PDF 且只有 manifest 时只报告 `verified_manifest/no_grounded_span`，不得伪造页/段落 locator。迁根前后通过真实 CLI 断言标题、类型和期间字段完全一致。输出作为资料事实，不写 accepted/rejected 投资结论。 |

**哈希与 span 的精确算法：**bundle 哈希并非 CLI stdout 的文件 SHA。删除 `bundle_sha256/export_id` 后，按 CWP `SourceExportBundleV2.from_dict` 的规范 JSON：`json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")`，求 SHA-256，再核对 `export_id`。StockWiki 独立实现 wire 校验，不能通过导入 CWP 内部类来“自证”跨仓兼容；输入上限 16 MiB，拒绝重复 JSON key/NaN。对每条 `EvidenceSpan` 另核 `coordinates → locator`、`raw_text/structured_value → output_sha256`、`source_id + locator + output_sha256 → span_id` 与 parse status/quality flags 的合同；完成 verified-open 后再次按 Unicode 字符坐标回放原文。bundle SHA 可被重算，不能替代这些语义和真实字节检查。

实际 producer CLI：`company_wiki.source_catalog.source_export_v2_cli` 从 stdin 读取 schema 2.0 的 `source_refs/evidence_spans`，参数 `--config`；它输出 bundle JSON。verified-open 的二进制 stdout 和 JSON stderr 是**两个通道**，调用者必须同时检查。可通过明确的 CWP 代码 checkout/PYTHONPATH 或安装的 CLI 调用，不在 StockWiki 代码中导入 CWP 的 SQLite、catalog、内部 Python 类型，也不直接扫描 company/dayu/Dropbox。历史 as-of 请求只在来源可用时间和 CWP 读取合同都能证明时返回历史可用；缺少可证的历史时间则明确 `availability_unverified`，不能凭当前可读倒推历史可见。

## 2. TDD 实施步骤（同一 StockWiki harness 顺序完成）

1. **固定起点和 owner。** 只读 `git status`、W01 HANDOFF、当前 `sources.py` 及调用链。确认 W01 已进当前 master，保存任何有归属的活动文件。既有 reader worktree 若干净，可以由该仓 owner 安全更新到 `master@5bb68f6`；否则新建独立工作树/`codex/` 分支，先保留旧工作。记录 base 与最终 HEAD。不要清理 `.claude/` 等不属于本线的文件。
2. **先写 RED 合同测试。** 用 CWP 真金样本验证 bundle/manifest/span 的精确 wire 结构和成功文本回放；负例覆盖未知版本、重复 key、路径字段、bundle/export 错 hash、manifest/source/span 不一致、重复 ID 冲突、错 SHA/长度、乱码或越界 locator、错误 MIME。测试明确期待本线自己的错误码；不让测试随实现而放宽。只在 StockWiki 测试目录复制必要的小 JSON fixture，记录其 producer SHA 与来源 commit；CWP producer 更新时由总指挥协调版本及样本刷新。
3. **实现薄 adapter。** 分离纯函数 wire validator、CWP 读取 transport 和 StockWiki 资料投影。纯函数只懂版本化 JSON 和字节，不知道物理根；transport 只知道配置句柄、子进程参数、超时/最大输出字节；投影仅保存逻辑来源键与可回放引文。处理子进程非零、超时、stderr 多行、success receipt 缺失、失败却带 stdout、输出超限和跨通道不一致，均不返回 `verified`。
4. **接一个显式 opt-in CLI/入口。** CLI 参数能指定 export bundle、CWP transport 配置、精确 source/version 和可选 locator，输出稳定的 JSON/错误码；不改当前用户默认 sync/weekly、不隐式启用网络或 Tavily。若要改 `analysis.py`/`enrichment.py`，只加窄入口调用 adapter，使 v2 数据不走旧 `stable_source_id(path)`；既有命令与研究状态保持可用。
5. **跑真实但隔离的 E2E。** 从 CWP producer 的文本 fixture 创建真实 catalog/export，在 StockWiki CLI 调 CWP verified-open 子进程，独立重算字节 SHA，回放含中文和 emoji 的字符 locator；再将 P06 增发 PDF **及其同名 `.PDF.source.json` sidecar** 一起复制到本线隔离根，两份都记原 SHA。P06 必须保留 CWP 原生相对布局 `三角防务/raw/research/<原文件>.PDF`，配置 `RootSpec(kind="company_raw", adapter_id="company_raw_v1", ...)` 指向其隔离父根，才能由真正的 catalog adapter 扫出相同 manifest；可参考 CWP `tests/e2e/test_source_version_reader_real_bytes.py::test_real_p06_four_root_export_is_independent_of_root_names_and_priority`。用 CWP 真 catalog/reader 验 manifest/字节但不虚构 PDF span。测试从与 CWP/StockWiki 仓不同的 cwd 运行，生产原件只读。另测多根同 SHA 迁移（逻辑 ID 稳定、标题/类型/期间不变）、篡改、撤回/不可用、错版本和缺失来源，预期拒绝可重复。
6. **只在大节点检查。** 开发时跑受影响单测；代码准备交接时运行 `python -m pytest -q tests/test_source_export_v2_reader.py tests/test_source_export_v2_cli.py tests/e2e/test_cwp_source_export_v2.py tests/test_quick_scan_store.py`（若实际文件名调整则等价替换），然后按 StockWiki 当前 `AGENTS.md` 的提交前要求跑一次 `bash scripts/check_all.sh`（ruff、全量 pytest、coverage、validate-framework）和 `git diff --check`。不要每个小提交都重复全量；如该仓 owner另行按用户要求正式简化 AGENTS/脚本，需先记录变更与等效大节点测试。CWP 生产者复现命令为 `python -m pytest -q tests/contract/test_source_export_v2_cli.py`。总指挥独立执行 G-B：从固定 CWP producer checkout 真 export → StockWiki 真 CLI → CWP verified-open → exact locator/manifest 回放与负例。单仓绿灯只表示可交接，不代替 G-B。

## 3. 测试资产、隔离与验收

- 建议 StockWiki 新增 `tests/test_source_export_v2_reader.py`（纯合同）、`tests/test_source_export_v2_cli.py`（CLI/transport）、`tests/e2e/test_cwp_source_export_v2.py`（真实两个仓代码和隔离 catalog）。命名可随本仓结构调整，但三类测试必须可单独运行。每项用可写短根 `stockwiki-source-reader-<nonce>`，**创建前确认原本不存在**；只复制金样本和 P06 原件与 sidecar，记录两份 SHA/字节数/测试前树；结束关闭 SQLite/子进程，再按已核对的目标路径移除本次副本，复核测试根恢复为空或原状。生产 CWP catalog/source config、StockWiki DB、原件均不写。
- 文本正例同时检查金样本所指**62 字节原文** SHA `d9b0df81476e5c29dedd8acc8438f0dcfd8f45585a4f246e1cbc243ed4dd4de3`、`loc:v1/chars:4-22` 和精确引文 `Revenue increased.`；`source_ref.json` 文件自身 SHA 是 `aca22689b9369151932d8402614c48d0122a8049fee3015b420264bcfd335cf1`。切忌把含 emoji 的字符坐标错当 UTF-8 字节坐标。成功 verified-open receipt 的 policy hash/read_at 是动态值，只校验格式后与 normalized golden 对照。
- P06 原件来自 CWP 既有只读样本清单，SHA `cd803fe9528f4646f8f29b518a450ae4bd5b5968c482eb49789f9786b523595b`，5,595,592 字节；同名 `.PDF.source.json` sidecar 为 208 字节、SHA `b34ace23f1651c606ab6d646202445d407c6a50db932ad65995312cd5e1a40bb`。两件须一起复制并独立复核。若现行 CWP 导出尚不能给它提供受证的 PDF locator，本线只验 manifest 与真实字节，不声称完成 PDF 引文定位；E5 后由总指挥安排新合同。
- **通过标准：**每个被标作 `verified` 的输出，都有 producer bundle 关联、CWP 成功 receipt、消费者自己算出的实际字节 SHA/长度和可回放的文本 locator；失配/撤回/未知版本失败关闭；v2 输出无物理绝对路径、无路径来源 ID；W01 与旧入口回归绿；测试根和原件前后相同。负例必须断言具名错误和非零 CLI 退出码，不能仅断言“不抛异常”。
- 交接给总指挥：StockWiki base/branch/commit、改动文件、公开 CLI 用法与 JSON/错误码、消费的 CWP producer HEAD/各 golden SHA、测试命令/计数、P06 与文本 E2E 收据、测试根恢复、尚未支持的 PDF locator/历史 as-of/selected 范围。不要新造人工签收文件；自动化测试和差异审查足够。

## 4. 与其它并行线的握手

| 并行 owner | 本线只读依赖 | 何时通知总指挥 |
|---|---|---|
| CWP | SourceExport v2、verified-open CLI/golden、P06 原件与 G-0 结果 | producer 版本/字段/错误码变更；P06 无法在隔离 catalog 重现；真实字节与 receipt 不符。 |
| IQS（已有 harness） | 无基础 reader 前置；将来只读 identity 2.2 正式包 | IQS 完成后仅记录可交给 W02/W03，**本线不接手**。 |
| FF、RF、ET（各自 owner） | 无写入或运行前置 | 仅当同一 CWP wire 合同变化影响本线；不改其项目。 |
| 总指挥 | 本线固定 StockWiki 提交和 CLI | G-B 真实跨仓测试可启动；缺陷定位为 producer/consumer 哪一侧；随后 G2b/G-C/G-D 继续按总计划。 |

**给新 harness 的第一条任务指令：**阅读本文件、StockWiki W01 `HANDOFF.md`、CWP `tests/golden/source_v2/README.md` 与当前 producer CLI；只在 StockWiki 独占工作树按第 2 节 TDD 实施，提交代码和自动测试收据，把对外接口/待办汇报给总指挥。不要启动 IQS W02/W03 或默认批量同步。
