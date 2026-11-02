# RF / StockWiki 消费边界独立复核

检查时间：2026-11-02（目录名沿 ROOT 指派）。范围仅当前 RF、StockWiki 消费生产入口及对应测试边界，不替代全系统审计。没有改产品、生产配置、原件或他人 WIP；0 外网/收费调用。探针与结果：本仓 `.planning/decoupling-recheck-20261103/consumers/probe.py`、`probe-result.json`，独立 scratch 已恢复不存在。

版本：RF `ad178dbcc4c407c1006659c537b09d88728b5af9`；StockWiki `d8d3303cb4b91fb6bfc8db6202ea3919276f833e`。

## 结论

**不能把已完成的 reader 能力称为所有当前消费者业务路径解耦完成。** 两个可达遗漏已复现。RF raw/preparation 两端口本身的改造有效；StockWiki 的 opt-in 只读 reader 也有效。问题在于上层业务入口未全部接入这些端口，前次测试把组件能力覆盖推成了全流程完成。

### C-R1（P1，架构完成声明的主要缺口）：StockWiki 正常公司研究仍直接发现、读取并解析上游物理原件

当前可达链：

- `StockWiki/stockwiki/cli_parsers/company.py:50` 注册正常 `run-company`，`:57` 必须 `--doc-root`，`:69` 绑定 handler；没有提供 source provider / reader 端口选项。
- `StockWiki/stockwiki/services/company.py:76` 的 `cmd_run_company`，`:95` 将物理根写入公司配置，`:99` 调用 `run_company_pipeline`。
- `StockWiki/stockwiki/analysis.py:334` 的 pipeline，`:346–349` 从参数或 `company.doc_root` 直接 `discover_sources`，`:126` 对每个 `source.original_path` 调用 `read_text_excerpt`，`:378–381` 持久化物理根/源路径。
- 并非只有用户主动导入目录这个入口：正常 `enrich-evidence --ticker ...` (`services/company.py:134–161`) 在无 `--doc-root` 时由 `enrichment.py:200–203` 读取公司配置根，`:145–147` 直接调用 StockWiki 自己的 PDF/Word/Excel parser；`extract-document-signals` (`document_signals.py:336–339`, `:216`) 同样扫描、解析。
- `StockWiki/config/companies.yaml:9` 起当前 12 公司全部 `doc_root` 指向 CWP `companies` 物理目录。README 当前日常工作流 `README.md:60–72` 仍推荐这一用法；不是死代码或只读归档说明。
- `sources.py:48–49` 用绝对物理路径的 SHA1 生成来源 ID；`:139` 递归扫描；`:175` 直接读文本；`:181–183` 进入本仓文档解析。迁移原件目录影响来源身份；虚拟湖的其他物理根不在该单目录内则无此来源。

与新端口的关系：`services/source_reader_v2.py:1–8` 和 `services/narrative_source.py:1` 明确 opt-in read/preview。它们没有进入以上正常业务路径。`docs/narrative_source_consumer.md:7` 明确当时 default/full/weekly paths unchanged，结尾把默认转换留作后续 G-D。原能力卡本身没有虚假验收；后续全局完成声明遗漏了这一剩余责任。

最小复现：本轮在新建合成 workspace 运行真实 `stockwiki.cli run-company` 成功，产出带 `original_path` 的 `external_sources.yaml`；再以 `enrich-evidence --ticker TEST.N --no-refresh-reviews`（没有传 doc-root）运行，实际 `discover_sources` 收到配置中的同一物理目录，两个公开 reader 调用均为 0。同一 TXT 字节复制到另一物理根后 source ID 改变；原路径内容修改后 source ID 不变。只修改了 scratch 合成文件，未移动或读取任何生产原件。

为何此前 110 项隔离通过：`.planning/decoupling-implementation-20261102/run_other_consumers.py:15–16` 只选了四个 raw/narrative reader/process/CLI 套件，不含 `test_company_pipeline.py`、enrich、document signals 的业务接线验收。现有 `tests/test_company_pipeline.py:8` 反而正向断言原件物理路径应进入 source manifest。无 CWP import 的测试不足以发现磁盘耦合。

建议：将目录发现/原文解析的责任归 CWP。在 StockWiki 公司业务入口注入版本化 `list/query + read-source + read-narrative` 接口，业务只消费逻辑来源 ID、版本、locator、派生文字/质量。当前 read-only reader 已有能力可复用，但单份精确 read 不能代替公司级来源列表/摘要发现；需要定义/接通现有公开 query/export/ref discovery。保留研究 evidence/claims/accepted 的 StockWiki 归属。旧 `doc_root` 如需兼容，明确限定为导入适配入口，由上游登记后返回逻辑来源，不再让研究代码自主遍历解析；迁移保留旧 evidence ID 引用映射。

必要测试：同一逻辑资料分散两个临时物理根、根迁移、同路径新版本、已撤销来源，正常 `run-company/enrich/extract` 只走注入端口且不访问原件目录；当前 helper raw/narrative 单测保留，无需增加每小步门禁。

### C-R2（P2）：RF 的实际摘要采用入口没继承可替换 reader

当前可达链：

- `revenue-forecast/tools/build_auditable_case.py:59–72` 支持真实 narrative request/bindings，调用 `consume_narrative_input`；工具没有 reader command 配置。
- `revenue-forecast/tools/run_narrative_consumption_e2e.py:19–32` 同样走该生产采用函数，只有 catalog config。
- `revenue-forecast/scripts/source_narrative_context.py:154–173` 的 `consume_narrative_input` 不接 reader/port，也不接已验证 `NarrativeContext`；直接调用 `read_narrative_context` 未传 `reader_command`。
- 因此落到 `company_wiki_narrative_reader.py:20–21` 的默认同 Python 环境 `-m company_wiki.source_catalog.narrative_transport_cli`。在独立安装、不同 Python 或替代服务部署里，准备阶段可成功，实际引用参数/公式采用阶段仍不能使用同一配置端点。它依赖的是默认 module 安装而非 CWP DB，但违反 D1/D2 的端点可替换要求。

最小复现：同一合法生产者公开 golden，由自建独立脚本 endpoint 返回给 `read_narrative_context(reader_command=...)`，真实 subprocess/协议验证成功且 quality=verified；向 `consume_narrative_input` 传该 command 得 `TypeError: unexpected keyword argument 'reader_command'`。不传时在 transport 开始前截获实际组装命令，确为上述默认 CWP module。没有运行任何生产 CWP、调用 provider 或读取公司原件。

为何此前通过：`tests/test_decoupled_source_port.py:69` 只测 `prepare_source_result` 转发双端口。多数采用测试（如 `test_du11_narrative_citation_consumption.py:70`）patch 整个 `source_narrative_context.read_narrative_context`，消除了端点配置问题；`test_du11_narrative_citation_e2e.py:184–192` 为子进程构造同名 `company_wiki/source_catalog/narrative_transport_cli.py` 并设置 PYTHONPATH，验证默认部署模式而未验证替换部署。

建议：把“实读一次”和“已验证 NarrativeContext → RF claim/parameter/formula”分为 transport/orchestration 和纯消费两个职责，采用端点使用与准备相同的部署配置；兼容函数可转发 command，不能每一业务层自己硬拼默认命令。两公开工具同步参数，避免只修函数不修用户入口。

必要测试：从源准备到实际采用/报告的一次完整小离线用例，不允许 CWP package/PYTHONPATH，仅用临时不同名 producer 脚本；同一 source/summary 的哈希和身份反控保留。若传入已验证 immutable context，记录不能二次偷偷启动 reader。

## 已确认正常、未作为缺陷的部分

- RF raw `open_source_version_v2` 与 registered/full preparation 支持显式 command，配置对显式端点是 opaque handle；临时 non-existent handle 可工作。真实接收字节 SHA、身份和时间核验属于接收边界，不是跨仓 private 依赖。
- RF 生产 `prepare_source` 没有自动降级 v1。`_prepare_legacy_source` 的旧 path/derived DAG 属明确冻结 helper，不因为 literal grep 命中就算当前主链。
- StockWiki 的 SourceExport/narrative transport 本身不导入 CWP 私有代码，argv_prefix 可替换，顶层 diagnostics extensions 可接收。当前缺口是默认研究服务未采用它们。
- StockWiki 自有 identity/quick-scan SQLite 是本仓状态，不把 `sqlite3` 字面出现全当跨仓存储耦合。未改 IQS/Dayu/Dashboard。
- RF 与 FF 的显式安装目录/public CLI discovery 是 adapter 部署兼容，不机械要求改成网络服务。本次没有实证其调用内部 DB。

## 审计限制

CodeGraph 开始用于结构定位，但 RF 索引仍返回已迁移测试位置且当前 `consume_narrative_input` 查无符号，StockWiki `discover_sources` callers 为空；对实际打开的现行文件与明确 CLI dispatch 使用只读文本核查。未重建索引、未因空结果推断不存在调用。没有重复整仓、收费公司分析或源修改。探针只证明所列可达链，不宣称复验全市场业务语义。未发现当前 RF/Stock 源消费者写 CWP 原件/DB 的新证据。
