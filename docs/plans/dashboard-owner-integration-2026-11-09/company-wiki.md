# Company Wiki 实施单

工作目录为 `C:/Users/郑曾波/Projects/company-wiki`。从最新远端 `master` 建独立工作树。写域为来源目录、公开读取和定向合同测试。PDF 端口单独由解析层维护。依赖、验收与交接见 [总计划](task_plan.md) 和 [事实基线](findings.md)。

## CWP-BROWSE · 对应 CWP-4 · 第一批发布

1. 核对 `7ef04c9c0`、`214c53796`、`c0189aeeb` 三提交。范围是 `public_document_browser{,_cli}.py`、`tests/contract/test_public_document_browser.py` 及两份 G-CWP-01 交接。采用逐提交移植，避免带入旧 `62602102a` 的 canonical 专用后续改动。
2. 重跑 `python -m pytest tests/contract/test_public_document_browser.py -q`。验证原有 /1 请求、响应、分页和指定版本重开。夹具含不同存储根、同名不同字节、同文档多版本、旧快照和零路径泄露。以当前主线 CI 复核后正常发布。
3. 给 D00 发布代码 SHA、两个实际公开 schema、公开命令和接口范围。只打开基础 browse/reopen 的隔离组合验证可以先跑。若当前 Dashboard 配置同根还要用 stream/canonical，等这两个能力一并到位再替换整套 pin。

## CWP-ID · 对应 CWP-1 · 先核定身份事实

1. 固定 E12 实际 FF→CWP 解释器、代码、connector、目录及 security-master 快照代次。以公开 `identity_cli` cache-only 重放 E12 公司全名+US，再跑 `US+BABA`、`HK+09988/9988`、精确请求的矛盾挂牌和另一个双上市对照。只记录候选原因、类型、market、exchange、代码和已验证状态。
2. 当前本地只读实测 BABA US、09988 HK 可明确解析。全名无 market 的 fuzzy 命中多个 US 候选。搜索 alias 和精确挂牌选择分别处理，例如 `BABA HK` 搜索词可能是合法 HK alias。以明确的挂牌 selector 验证显式 market/security_id/exchange，保持同发行人可有多个真实挂牌。
3. 若实际部署快照缺正确记录，依据可追溯的交易所或官方来源使用 owner 现有登记流程。若精确入口已经工作，交给 FF/D00 使用它。仅在能复现错误归属时修共用身份匹配。验收正例、真实多候选和错发行人反例。不新增名称特判、人工门或自动主挂牌。

## CWP-SCOPE · 对应 CWP-2 · 单一来源事实

1. 固定同一个 SourceRef，在实际 CWP `source_query_cli`、ensure 的公开响应、owner 读取回执及 FF 实际请求间逐字段比对。具体入口是 `SourceVersionReader.describe_candidate` 和 `operation_projection.py`。核实 null 是配置漂移、原始事实未知、登记冲突，还是已有事实丢失于投影。
2. 已验真的来源市场由 assertion/manifest 公用规则输出。事实缺失先走 exact accession、官方发布元数据和原文 SHA 等证明。真未知明确保留。请求市场只约束选择；挂牌市场由身份层决定。合同里对缺证据、已证匹配、明确冲突给稳定的可测试语义。跨仓兼容需要新增字段时走版本化的可选扩展。
3. HK 本地补登先用已知 HKEX accession、发行人、真实期次和发布时间。在临时库用现有 `company_wiki.source_catalog.cli source-facts --request` 验真原 SourceRef 和同 SHA append-only 更新。准备足够的 entity、market、security_id、document_kind、期次与发布证据，避免只补一个列。验 query、local_prepare 和 ensure 的同 scope 结果及二次幂等。当前新件 writer 已传 market，先用新件回归决定是否要改通用路径。证据确实不足时保留具名 incomplete。需要 cover 证据时通过解析端口，继续使用既有预算。
4. 验证 FY2025 查询不拿到 FY2026、latest-as-of 不使用未来/未知发布时间、真实错市场拒绝、已验源重复请求零下载。相同规则在另一个发行人和 MDB 控制例复验。
5. 交 FF 一个最小 contract fixture 或归档的公开 DTO，含市场匹配、未知和冲突。双方各自测试实际 CLI。US provider 的零 HTTP 失败单独查部署 SDK 和 provider capability，保留实际 named failure。

## CWP-STREAM · 第二批发布

1. 以 `d0c55e974` 的 byte lock/stream 作为参考。三方合并时保留当前主线 `SourceVersionReader` 的严格准入、正确复用和位置绑定。先写公开读合同的正反例，再由 Reader 提供类型化流式打开能力，统一候选、当前根、字节预算、精确 SHA 和实际打开位置。CLI 负责参数、块传输、收据和退出状态。
2. 保持整缓冲收据 2.1、流式收据 2.2 及现有调用方式。策略指纹沿用追溯语义；当前主线两种读取实测一致。流完成前以现有协议区分 locked 和终态 ok，取消、超时、错 SHA 或不完整传输不能产出成功收据。正式传输无需落额外整份副本。
3. 用 Windows/Linux 真文件验路径改绑、等长篡改、根迁移、不同合法副本、锁竞争截止时间、取消、慢消费者、资源上限、尾收据及句柄释放。旧 POSIX `flock(LOCK_EX)` 需特别验证不能无限等待。大件验有界内存和实际配置有效上限，保留相邻小预览行为。跨不同层使用同一有意义的资源约束。

## CWP-CANONICAL · 第三批发布

2026-11-10 已提供 parser_adapters 公开的 NativePdfError、validate_native_pdf 和 read_native_pdf_prefix。入库校验、CN封面scope、语言采样三个现行入口均已迁移并通过边界测试。下一步 canonical 候选的 CN issuer 读取也应消费该 owner 能力，并同步收口浏览器私有扫描。流式候选仍需处理私有 Reader 访问、预算重置、固定字节帽及 POSIX 阻塞锁后接收。

1. 将 `cn_primary_issuer.py` 的直接 PyMuPDF 调用替换为有界原生页文本端口。先查现有解析 API 能否满足需要。需要新端口时仅由 parser/normalization owner 实现，DTO 含页序与明确的缺口，接受调用的工作预算。保留原生证据定位、加密/坏文档诊断和无 OCR/模型的读取语义。相同受影响的 CN cover 路径按同一端口收口。
2. 来源目录以验证原件建立 CN USCC、登记主体、证券代码和出处的匹配，调用自己 owner 的有界公共查询。将 canonical 浏览对基础浏览私有扫描方法的依赖改成同 owner 的稳定读取端口。保留既有 SEC 发行人验证，不通过代码或语言猜市场。
3. StockWiki 自己签发当前版本的发行人证明。canonical 浏览消费受信配置的版本化证明端口，端口调用由组合适配层提供。保持同 issuer/listing/as-of 的请求绑定和证据完整性，拒绝任意调用者给出的未验证证明。避免来源领域对象绑定具体 StockWiki subprocess 客户端。
4. 用原有证据回放和新合成 CN、SEC、别名冲突、未来日、字节变动、证明端口替换案例验收。隔离的 Dashboard 组合验证采用现存原件和实际公开入口，保护现有证据定位。

## CWP-3 · Range 后置

保留 E13 的现行语义，当前完整原文流不声明 Range。验证完整 GET 和 Range 的明确不可用行为，Dashboard 展示按实际能力。未来需要 Range 时独立设计并验收 206、416、If-Range、范围摘要和取消。未发布能力不影响前三批。

## CWP P2 · 跨市场匹配验收（2026-11-10 更新）

- **通用 owner 路径：**SEC 20-F 经 CWP acquisition/canonical import 验真后，从原文精确挂牌表提取证券/交易所，并通过公开 `SourceCatalog.register_sec_20f_listing_link` 登记原件 SHA 绑定关系；关系数据与原件在 CWP owner 内持久化。代码不按公司名或 ticker 猜关系。Dayu SEC submissions 没有 `fiscalYearEnd` 时，只生成候选 FY；下载后还要以 SEC 原文 DEI 核对 CIK、财年、期别和期末日，失败不写入。子进程 scratch 改到配置的 CWP staging 根，避免 Windows 低完整性 Dayu 进程因系统 Temp ACL 无法创建目录。
- **真实 CWP/FF→HK 原件端到端：**Alibaba `US:BABA → HK:09988` 的 SEC FY2025 20-F SHA 为 `36daec0ce8b9f646d67b692a7ae7923589a6204bd58fddc02fff37f53a46bb17`；Bilibili `US:BILI → HK:09626` 的 SEC FY2025 20-F SHA 为 `d5004d200eceaed8288d6c28916b5eac7c664cc003671f11c94418203128ffd4`。由这两份正式来源生成的 issuer-link ID、HK 年报 URL/元数据及原件字节数在总计划的 P2 E2E JSON 收据。
- FF 分别以 US 挂牌为公司身份、`source_market=HK` 请求 FY2025 `annual_report`，并使用来源市场的原生表单 `FY`。Alibaba HK 年报 SHA `8ab1234844b56a2be8b90d92301d0a46123c8770610e87f9462bb27b0e2b7182`（4,630,060 bytes），Bilibili HK 年报 SHA `88623041b7af0e423eb65a984ba34ca7bcba826b737210b062091bf51485bf4d`（2,473,744 bytes）。CWP public Reader 实读两份原件，长度与 SHA 均完全一致，receipt `ok`，manifest 均显示 HK 来源市场及正确挂牌代码。每项重放均为 `reused_existing`、0 downloads、0 provider HTTP exchanges、provider 未启动。
- **生产来源目录 cache-only 验证：**US/HK 两组精确挂牌查询分别返回同一 issuer-link；HK `Alibaba` 模糊名称保留 `ambiguous`，把 `09626` 以 CN 市场查询则返回 `conflict`。测试环境的错财年、错表单、错期次、错 source security/market、晚于 `as-of` 用例均拒绝候选。请求/关系证据、零下载重放与 SHA 见 [`validation/p2_cross_market_e2e_receipt.json`](validation/p2_cross_market_e2e_receipt.json)。
- **验证与交付状态：**CWP 本轮定向集成/合同/单元测试 **127 passed**；Ruff、`git diff --check` 和独立代码审查通过。代码变更、最终验收和远端分支信息以本文件末尾的 P2 收尾记录为准。P2 完成范围是已支持的 SEC 20-F 证明路径和真实 US→HK 复用；没有来源证明的发行人关系继续标记未知，不承诺对所有历史挂牌自动覆盖。FF owner 代码不在本工作树改动范围内。

### P2 CWP 最终交付

- 代码与测试提交：`174b422077f761422f9d826c12ee68eeef478ecb`，分支 `codex/dashboard-p2-cwp-market-20261109`。
- 精确复跑：8 个 P2 合同/单元测试文件 **127 passed**；`python -m mypy src` 470 个源文件通过；Ruff、`git diff --check` 通过。提交钩子的 Ruff、mypy、config doctor 也通过。
- 独立审查：代码审查无阻断项；最终 PWF/真实收据复核结果和远端同步状态记在总计划 `progress.md`。
- **当前结果（2026-11-10）：**上述 CWP P2 候选与 PWF 收尾已普通快进并入、推送至 `master`。本地和 `origin/master` 都在 `0fc56b25b89da9f3da5921ba64122d9745e1752d`；发布 hook 的快速 smoke 为 18/18。FF/RF 的对应 P2 也已分别并入其 owner 主线，精确版本和测试状态见[总计划](task_plan.md)及[工作区对账报告](review/local_workspace_reconciliation_2026-11-10.md)。此前的分叉与 4 个同写域未提交文件是合并前快照，已先核对其实际 blob 与远端基线，再对齐根工作区；没有覆盖独立 P3 提交。
- 当前本地针对架构边界、文档层隔离和 DU 核心隔离的定向回归为 68 passed。尚未确认本次 `master` 更新触发的完整 GitHub Actions 结果；本地定向测试不等同于全量远端 CI 通过。
- 此提交只改 CWP owner 和本计划；未改 FF、Dayu、Dashboard 或 RF 代码。
