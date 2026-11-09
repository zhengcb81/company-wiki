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

1. 将 `cn_primary_issuer.py` 的直接 PyMuPDF 调用替换为有界原生页文本端口。先查现有解析 API 能否满足需要。需要新端口时仅由 parser/normalization owner 实现，DTO 含页序与明确的缺口，接受调用的工作预算。保留原生证据定位、加密/坏文档诊断和无 OCR/模型的读取语义。相同受影响的 CN cover 路径按同一端口收口。
2. 来源目录以验证原件建立 CN USCC、登记主体、证券代码和出处的匹配，调用自己 owner 的有界公共查询。将 canonical 浏览对基础浏览私有扫描方法的依赖改成同 owner 的稳定读取端口。保留既有 SEC 发行人验证，不通过代码或语言猜市场。
3. StockWiki 自己签发当前版本的发行人证明。canonical 浏览消费受信配置的版本化证明端口，端口调用由组合适配层提供。保持同 issuer/listing/as-of 的请求绑定和证据完整性，拒绝任意调用者给出的未验证证明。避免来源领域对象绑定具体 StockWiki subprocess 客户端。
4. 用原有证据回放和新合成 CN、SEC、别名冲突、未来日、字节变动、证明端口替换案例验收。隔离的 Dashboard 组合验证采用现存原件和实际公开入口，保护现有证据定位。

## CWP-3 · Range 后置

保留 E13 的现行语义，当前完整原文流不声明 Range。验证完整 GET 和 Range 的明确不可用行为，Dashboard 展示按实际能力。未来需要 Range 时独立设计并验收 206、416、If-Range、范围摘要和取消。未发布能力不影响前三批。

## CWP P2 · 跨市场匹配验收（2026-11-09）

- 通用 issuer-link 判定及来源市场/挂牌市场/期间隔离已实现并通过 70 项定向测试、Ruff 和独立审查。离线真实原件组合使用阿里 FY2025、B 站 FY2022 HKEX 年报，GLEIF LEI/ISIN 与存托凭证发行人公开证据；US BABA/BILI 挂牌可复用同 issuer 的 HK 原件，匹配结果保留 HK 来源市场和原 security ID。
- 反例拒绝错误财年、文种、财政期间、来源证券、来源市场以及 `as-of` 晚于已知发布日期的来源。Query/local_prepare/ensure 使用同一候选语义，E2E 对原件 SHA 复核且零下载。
- **生产数据闭环仍未完成**：部署 CWP 身份快照当前没有 LEI/ISIN，现有 refreshers 只提供 CN org ID、HKEX 证券 ID、US CIK。故测试证明通用匹配逻辑，不证明线上能自动建立跨市场 issuer link。后续须接入带来源、发布时间与刷新规则的通用权威标识 feed，再在实际部署对 BABA/BILI 做只读复验；禁止把 fixture 中两个公司的 ID 写入生产或加入公司特判。
- 当前候选尚未提交；提交后在此记录确切 release SHA、远端分支及 CI 状态。
