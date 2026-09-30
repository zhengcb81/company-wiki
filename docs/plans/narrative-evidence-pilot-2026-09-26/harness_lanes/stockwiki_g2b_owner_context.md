# StockWiki 独占施工卡 W04：G2b owner identity context 与公开导出

> **状态：可独立派发。**StockWiki reader、W02/W03 identity snapshot/mapping 已进入本地 master；基础 CWP→StockWiki G-B 已通过。G2b 仍缺 owner-controlled identity receipt 与 market registry。此卡补齐 StockWiki 生产者公开读取/导出，不修改 IQS 消费者，也不碰 company-wiki 当前 E7。

## 任务目标

让 StockWiki 通过自己的公开读接口和 serializer，针对一项精确 Entity/as-of 请求输出 IQS identity package 2.2.0 所需的完整 request envelope：

- `schema_version=2.2.0`、`object_type=entity`、Entity 2.1.0 `payload`；
- `trusted_context.market_registry`：由 owner 持有、带数据版本的 ISO 市场辖区→MIC 投影；
- `trusted_context.identity_receipts`：payload 所引用的真实 scope attestation 或 verified issuer receipt；
- `trusted_context.source_bindings`：按 binding_ref 索引的完整 owner source-binding 投影。

目标是以最小的一条正向样例通过已提交的 IQS 公开 CLI，并能拒绝缺失/错配的 owner 记录。先以单上市地、单证券、provisional Entity 做正例；不为了过门把 provisional 升为 verified。只有存在真实、可核对的 owner 证据时才额外覆盖 verified、多证券 issuer。

## 派发边界

- **唯一产品写入仓：**`C:\Users\郑曾波\Projects\StockWiki`，从当前 `master` 建新 `codex/stockwiki-g2b-owner-context` 分支/隔离 worktree。开工重查 master、worktree、tracked/untracked；保留根 `.claude/`、现存 reader/identity worktree 和所有活动文件。
- **只读依赖：**IQS 的 identity schema、contract validator、CLI 和本卡引用的 handoff；company-wiki 的 SourceExport v2；其它所有仓库。IQS 正由既有 owner 推进，本线绝不改 IQS。
- **不修改：**CWP/RF/FF/ET/IQS 文件、测试或数据库；StockWiki 正式身份数据库；任何实际上市公司身份/回执；SourceExport reader、full sync/weekly、selected evidence、研究结论、公司原文。
- 使用 StockWiki 已有 WorkspacePaths/QuickScanStore 等边界管理数据。只在新隔离 worktree 的测试临时根创建数据库、下载和 golden；不把临时数据库、个人数据或密钥提交。
- 若 IQS 的 schema/validator 在开工时已改变，先比对其当前提交、版本与本卡固定合同；只有可兼容字段变化时更新本仓 producer，否则停止并把精确不兼容字段回报总指挥，不能顺手修改 IQS。

## 已调查的基线事实

- 当前主线基准为 StockWiki `master@c8cfb2e7dc09`；W02/W03 公开 snapshot/mapping 已合入。
- QuickScanStore v1 的 Entity 记录只保存 scope/issuer receipt **ID**，没有可读 receipt 实体表；`build_identity_snapshot` 输出 entities、analysis subjects、source bindings 和 snapshot hash，不生成 IQS `trusted_context`。
- 现有 `quick_scan_source_binding` 有来源键的唯一约束；当前 serializer 可推导 listing_id，但落库字段和 IQS SourceBindingV21 的有效区间/MIC/status 仍需逐项核对，不能把“字段能构造出来”当成真实 owner binding。
- IQS `identity-cli-request.schema.json` 将 trusted context 固定为三个 exact keys；公开 validator 还会校验 active receipt 的 Entity/revision、provisional qualification 或 verified issuer/security/listing 覆盖，以及 owner source binding 与市场 MIC 一致性。
- ISO 10383 的官方 MIC 发布页由 SWIFT 作为 Registration Authority 维护，提供 CSV；该页说明 MIC 每月第二个星期一发布、修改于第四个星期一生效。当前官方入口为 [ISO 20022 MIC list](https://www.iso20022.org/market-identifier-codes)，CSV 链接为 `https://www.iso20022.org/sites/default/files/ISO10383_MIC/ISO10383_MIC.csv`。导入时保存原文件 SHA、release/implementation dates、parser version 和投影 SHA。MIC 文件只用来验证市场/MIC 归属，不用来推导发行人同一性。
- StockWiki W02/W03 的测试证明了 serializer 对隔离 QuickScanStore 的可复现性；它不证明生产库里已经有可用于 G2b 的 owner receipts/registry。没有证据的记录不得补造。

## 冻结的 producer 输出

使用 IQS 已交付的 CLI request schema 1.0.0 / identity package 2.2.0；不修改该合同，不给 request 加额外字段。外层必须 exact-key：

    {
      "schema_version": "2.2.0",
      "object_type": "entity",
      "payload": { "...": "StockWiki Entity 2.1.0 serializer output" },
      "trusted_context": {
        "market_registry": { "US": ["..."] },
        "identity_receipts": { "<receipt id>": { "...": "owner record" } },
        "source_bindings": { "<binding ref>": { "...": "owner record" } }
      }
    }

实际字段须逐项服从 IQS 当前已提交 schema 和 validator，不以此示意 JSON 代替 schema。正文的 Entity、receipt、listing、binding、registry 都由 StockWiki store/API + serializer 读取并组装；测试不得从 StockWiki SQLite 私表复制行后手工拼正例。

保留 W02 原 snapshot API 的现有输出语义；新增独立的 G2b request builder/public read command，避免悄悄改变已合入 consumer 的 wire output。命令应支持精确 `entity_id` 和显式 UTC `as_of`，stdout 仅输出一行规范 JSON，schema/owner 数据失败有稳定错误码和非零退出码；诊断写 stderr，不回显凭证或不必要的原始正文。精确命令名以 StockWiki 现有 CLI registry 为准。

## TDD 实施步骤

### 1. 固定消费者合同与现有 owner store

1. 只读读取本卡、`harness_lanes/stockwiki_identity_snapshot.md`、IQS 的 `identity.schema.json`、`identity-cli-request.schema.json`、`scripts/contract_validation.py`、G2b handoff。记录这些文件的 git commit 与 SHA。
2. 从 StockWiki 当前 master 检查 QuickScanStore schema/migrations、identity snapshot serializer、CLI registry 和现有测试；确认哪些字段是持久 owner 数据，哪些只是 W02 的确定性派生。
3. 写一页简短字段映射到本仓测试/实现注释：receipt ID → owner receipt row；listing/source binding → 当前 Entity/Security/Listing revision；market/MIC → 注册表 release；as-of → 明确请求值。开工前不得通过 StockWiki 私有 DB 绕过 API。
4. 若有现成数据 owner/API 可提供 receipt 或 registry，先复用并补 public read projection；不复制出第二份可变状态。

### 2. Market registry：官方输入、受控投影、原子替换

1. 先写单元 RED：解析官方 ISO 10383 CSV 的实际列名/版本；MIC、country code、Operating/Segment MIC 关系；重复 MIC、空国家码、非法 MIC、坏编码、截断输入和未知格式均有具名拒绝。不要假设 CSV schema 固定不变。
2. 增加 owner-controlled registry import/read 组件，复用 StockWiki 存储路径抽象。记录原文件 SHA、获取/出版/生效时间、导入器版本、记录数和映射投影 SHA。MIC 按 ISO market/country code 归组，排序并去重；保留有效/失效记录语义，避免历史有效上市因只保存“当前有效”而误拒。
3. 更新必须事务化：先完整解析和校验新版本，再原子发布；任何下载、格式或字段异常保留 last-known-good，不清空当前 registry。重复导入相同 SHA 幂等；同 release 却不同内容须具名冲突。
4. 提供显式更新/导入入口，不在每次查询时隐式联网。正式查询不回退到代码中的 MIC 白名单；registry 缺失、过期策略无法判断或 market/MIC 不匹配时，不生成可验证 request。
5. 在测试隔离根对官方 CSV 做一次真实数据 canary：确认响应受限、计算 SHA、解析出非空完整 projection，并校验本地已有 sample MIC。失败时保留完整错误证据和 temp-root 清理，不把 mock 结果写成真实数据成功。离线单测使用小 CSV fixture。

### 3. Identity receipt：真实记录绑定精确 revision

1. 先写 store/service RED：引用不存在、status 非 active、Entity/revision 错、receipt 与 listing/security/source binding 集合不一致、receipt 证据字段缺失、过期/撤销、scope/issuer 类型混用均拒绝。
2. 若确认当前没有实体模型，新增最小 append-only owner receipt 记录及版本化读 API；Entity 写入不得仅凭传入 ID 自动制造 receipt。revision 更新必须新建或明确 supersede receipt，旧 receipt 不得静默绑定新 revision。
3. 让 G2b 正例使用 provisional scope attestation，记录其依据、UTC recorded_at、准确 Entity/revision、Security/Listing、source binding 和来源字段；只用 deterministic test fixture 中的 `https://example.invalid/...`，明示为 fixture，不能输出为现实公司证据。
4. Verified issuer 正例只有在真实 owner workflow 已有可查 evidence 时才加。测试夹具不得把多证券/ADR/H 股/ADR issuer bridge 的事实伪装成真实生产身份。

### 4. Public request serializer 与 CLI RED → 实现

1. 先加 StockWiki public service/CLI 测试，期望从临时 QuickScanStore、receipt owner API 和 registry public API 生成 exact request envelope；当前代码应在 receipt/registry lookup 缺失时失败，形成 RED。
2. 实现 W04 独立 request builder，取单个明确 Entity 和 as-of；根据现有 serializer 得到 Entity 2.1.0 payload；将 market registry 投影成 `market_code -> sorted MIC list`；将被引用 receipts 与 bindings 按 ID 建 map；在导出前逐字段验证 ID、revision、有效期、market/MIC、source namespace/record、raw/normalized venue/ticker、listing/status。
3. 做正反例：稳定 JSON/hash；输入顺序变化不改结果；同 SHA registry 重导入幂等；missing/stale/retired receipt、错 revision、错 source row、跨 Entity binding、未知市场/未注册 MIC、重复键、未知版本全部拒绝，不降级成 `unknown`/`mapped`。
4. 正向 integrated test 通过 StockWiki public writer/service 创建临时 DB 数据并通过 public exporter/CLI 导出；不得读取 private SQLite，也不得用手工 JSON 成功 fixture冒充 producer 输出。

### 5. IQS public CLI cross-repo E2E 与大节点验收

1. 将 StockWiki 实际 serializer 的原始输出保存为可复核 golden，并记录 canonical SHA、StockWiki commit、request schema/package、public command、registry release/hash。payload/receipt/context 任一核心字段不得由测试硬编码拼接成“成功 golden”。
2. 直接调用只读 IQS CLI：`python -B -X utf8 scripts/identity_contract_cli.py --input <request.json> --schema-version 2.2.0`。预期成功为 exit 0、`status=valid`、`errors=[]`。测试不得 import IQS 私有 Python 函数替代 public CLI。
3. 负例从 producer request 的副本逐次改一个字段：错 Entity/Security/Listing、receipt revision/coverage、source record、venue/MIC、ticker、期间、registry 删除/MIC 跨辖区、receipt 或 binding 移除；预期 IQS exit 2 和具名稳定拒绝。不要改测试期望来迎合实现。
4. 所有临时 registry file、SQLite/WAL、request/golden副本、CLI 输出只置于新隔离根；执行前记录根不存在，`finally` 删除本任务创建的精确根并断言恢复。记录 StockWiki 生产 store 的只读 hash/size/schema 状态前后相同；绝不运行生产 migration。
5. 迭代期间跑受影响测试；所有 RED 转绿后，StockWiki 完整质量门只跑一次 `bash scripts/check_all.sh`。另运行跨仓 G2b CLI E2E 一次及 `git diff --check`。若大门因本线变更失败，修复后仅重跑受影响用例和必要的大门。

## 自动验收与交付

- ISO MIC 官方 CSV 可在隔离环境获取并完整解析；registry projection 带来源 release、源 SHA、parser 版本、投影 SHA、有效/失效覆盖；故障导入不破坏 last-known-good。
- 正向输出由 StockWiki 公开 store/service/serializer/API 生成，request exact-key，稳定且通过 IQS public CLI；正向先用 provisional 单证券/单 listing，不冒充 verified。
- receipt 必须是 owner store 中有状态、有 UTC 时间、绑定确切 Entity revision/security/listing/source records 的记录；source binding 和 registry 都由 owner store/正式官方输入读取。
- 主要缺失和错配负例通过，CLI 退出码/错误码稳定；StockWiki 聚焦测试、本仓 `check_all.sh` 和 G2b E2E 绿，新增用例无 skip。
- 生产数据库、实际身份、其它仓库不变；所有隔离根恢复到原状态；无凭证、原文或生产 DB 被提交。

交接内容：StockWiki base/final HEAD、变更路径、迁移版本、registry 官方发布/生效日期与源 SHA、receipt/export schema 版本、golden 路径/SHA、命令/退出结果、临时根清理结果、IQS CLI 成功/负例结果及剩余未覆盖状态。单仓实现通过不代表 G2b 完成；总指挥按 IQS handoff 核对跨仓字段、原件/状态不变并记录最终 G2b gate。
