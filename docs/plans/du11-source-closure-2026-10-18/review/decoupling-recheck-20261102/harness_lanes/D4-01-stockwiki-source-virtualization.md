# D4-01 — StockWiki 默认公司来源虚拟化

状态：**已备妥，尚未派发。** 完成 D4-01（P1）。只处理真实公司资料来源入口；不扩到 investment framework、研究结论或独立仪表盘。

## 唯一目标

让 StockWiki 的日常公司流程从 CWP 的公开公司来源接口读取资料，完全通过逻辑来源 ID/SourceRef 和可替换 reader 工作。默认 `run-company`、`enrich-evidence`、`extract-document-signals` 不再扫描或解析公司 `doc_root`。

CWP 当前 query 是按已知公司、文种、期次查询，不够作为“列出该公司全部资料”的证明。本卡由**同一负责人同时修改 CWP 来源端和 StockWiki 消费端**，实现有界、按需分页的 company source index API + 默认消费接线。若证明已有公开端点完全满足可实际枚举所有目标来源，可复用，不为形式加一个新 API；必须以跨多个文种/期次的端到端证据说明。

## 写域

- `company-wiki`: 新的 company source index/query 专属实现模块、专属 CLI/console entry、该接口自己的 contract tests/fixtures。CWP 代码访问物理目录和数据库只在 CWP 层。
- `StockWiki`: 来源 provider/连接 adapter、`run-company`、`enrich-evidence`、`extract-document-signals` 接线、公司来源配置及这些入口自己的测试/说明。
- 另建 `company-wiki` 和 `StockWiki` 独立 worktree。只提交本卡列出的两仓文件；CWP 共用 integration runner/`integration/` 留给 ROOT。

## 接口冻结要求

公司级 query 接收公司逻辑身份和 as-of，返回分页 SourceRef 与阅读所需的最小 manifest 字段（文种、市场/证券身份、发布日期/期次、语言、字节 SHA/大小、MIME）及真实可用状态。响应不得有绝对路径、根目录 ID、SQLite 表形状或 consumer 私有信息。每个 SourceRef 可由现有的独立原文/叙述端口读取；consumer 不能拼 CWP 模块命令绕过已配置 adapter。

在本卡便携 fixture 中固定完整 wire 字段、排序/分页、时间语义、not-found/unavailable、重复文件对应多个副本的行为。扩展诊断不成为公司来源事实。不要把“每家公司最新一个文种”误当完整公司资料清单，也不要无上界一次性传全量内容。

## 先写行为测试

先让隔离真实入口测试 RED，再修改实现。测试最少覆盖：

1. 同一公司在两个临时物理根、多个文种和多个期次的资料都由逻辑 query 枚举；返回 SourceRef 不暴露任一物理路径；分页拼接与不分页集合一致。
2. 改根位置而保留同一来源版本时，逻辑身份/证据引用稳定；同路径替换内容时新版本 SHA/SourceRef 变化。只对测试 scratch 操作。
3. `run-company`、`enrich-evidence`、`extract-document-signals` 由默认 CLI 进入时都调用注入端口；禁止 `discover_sources` 访问 CWP `companies` 物理根。原文与叙述分别走公开 reader，保持证据和 claim 在 StockWiki 所有。
4. as-of、文种、身份歧义、原件撤下/不可读清楚映射到既有结果类型，不静默当“公司没有资料”。同一文件的多个物理副本按来源 owner 的版本语义处理。
5. 原有独立 raw/narrative reader 和 StockWiki 业务用例保留；配置中不能再把本地路径当成日常来源协议。

真实端到端使用专用临时 CWP catalog 与临时原件；不能从生产库复制完整资料，也不调用供应商或模型。清理测试目录并核对启动前后清单。

## 明确不做

不改 RF、FF、ET、IQS、Dayu 或 CWP PDF/阅读策略；不改 StockWiki investment 判断；不删 legacy 数据/旧 evidence，不把旧物理来源 ID 直接换掉而丢映射；不新增私有/公开授权、人工材料签收或第二套资料数据库。

## 通过标准与独审

- 以上真实入口全部通过隔离 CWP 端点，consumer 看不到/打不开生产上游物理路径，且同一结果可由替换端点提供。
- 身份、来源期间、hash、原话/locator 和 StockWiki 研究语义无回归；不是只有新增 service unit test 变绿。
- 本卡直接受影响的仓内快速测试通过；ROOT 最终跨仓组合由总控执行，不在本卡更改 runner。
- 交付前委派未参与实现的独立审查 agent，检查完整入口、路径泄漏、版本映射、迁移兼容与测试代表性。问题全部修好后才交 ROOT；不是每个 helper 单独签收。

交付 `handoff.md`：两个仓实际 HEAD/commit、精确修改清单、接口 fixture 版本、已运行命令和结果、独审、scratch 清理与仍待 ROOT 的组合步骤。不可把 D4 完成声明或迁移剩余工作交给 ROOT 猜。

