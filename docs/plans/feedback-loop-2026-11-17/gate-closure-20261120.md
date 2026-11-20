# 长溯源与已付确认恢复验收

2026-11-20。两个验收都使用隔离目录中的合成业务资料，运行实际公开入口。价格、公司和发票样本只用于验证软件路径。

## Dashboard 与 RF

- RF 从同一已注册报告生成固定图，连续分页绑定报告、节点、规范 UTF-8 内容 SHA-256 及总长度。遗留完整读取接口继续可用。Dashboard 经公开能力字段选择分页，报告预读和所有页面共享截止时间，单页接收仍为 2,000,000 字节。拼回字节并验证摘要后，现有公开 HTTP 接口发回完整图。
- 真注册目录的完整响应为 2,952,760 字节。实际 Dashboard HTTP 与 RF 完整结构相等，111 个参数、111 条证据、1 个来源全部保留。Chromium 逐页遍历参数后从首页链接跳至尾页并读到相应证据正文。单元回归覆盖跨计算节点翻页、跨 UTF-8 字节、缺页、错位置、错摘要和切页期间目录的无关版本变化。
- 独审复现了组装后 10 万 JSON 条目上限、RF 同节点诊断重复拼接以及 Dashboard 128 条缺口上限。完整图按业务合同验证，传输页继续按原限额读取。RF 去重摘要并保留全部逐输入缺口，Dashboard 的 OpenAPI、运行及离线 schema 接受合法的完整缺口列表。真实 RF 129 个具名调整回归逐条保留原绑定和缺口。
- RF 在宿主执行定向检查 139 通过、1 项宿主链接夹具跳过，提交检查通过，推送快测 12 通过。Dashboard 后端 151 项、前端预测功能 58 项、浏览器组合 1 项通过，类型检查、构建和合同生成验证通过。独立复审确认三个修复和原件绑定。

复验从 RF 仓内 `tests/test_report_catalog_deployment.py` 的 `build_long_lineage_fixture()` 生成隔离已注册报告。把 RF 代码根和隔离数据根分别传给 `DASHBOARD_TEST_RF_CODE` 与 `DASHBOARD_TEST_RF_DATA`。构建 Dashboard 后运行 `tests/e2e/m5-forecast/test_registered_trace_pages.py`。可用 `DASHBOARD_TEST_BROWSER` 指定已安装的 Chromium 浏览器频道。

## StockQA、StockWiki 与 IQS

StockWiki 的原生确认入口读取已有原记录和当前主体权限，IQS 的公开 `frozen-record` 操作按原请求解释原冻结三件套，StockQA 负责执行登记、原尝试及账本绑定。当前执行准入失效时，普通入口可复用已经收到的原响应。公开运行投影直接使用所属会话的派发决策，已付与待发混合时仍只报告原结果和待办。

复验在隔离 StockWiki、IQS 和 StockQA 代码根运行 `tests/integration/test_c06_refresh_execution.py`。使用现有 `IQS_C06_RUN_INTEGRATION=1` 与 `IQS_C06_OWN`，实际本机和原生确认生效。第一次模型传输由测试 fixture 模拟，并用隔离账本结算一张合成发票。实际验证以本页发布记录为准。

- 默认账本和显式账本两种布局各通过一次。最终受审源码再次跑通显式布局。原 1.1 确认升级到 1.6 配置后，普通权限入口拒绝新执行。删除现行预算文件后，付后公开接口和普通入口连续两次读回原交付。原确认、冻结三件记录、登记、尝试和交付 SHA 一致。账本始终为 1 笔原请求、1 次原尝试、250,000 微美元的模拟已结金额，恢复新增请求、尝试、保留额度和费用均为零。
- 缺预算且尚无持久响应的真实普通入口、撤销原消费者的真实公开权限入口均拒绝。混合批次的回归验证已有响应的条目与待发项分开记录，报告不新写交付包。历史记录被修改或混版重新封存时也会拒绝。
- IQS 定向 75 项、StockQA 定向 126 项通过。StockQA Black、isort、mypy 通过。独立复审复跑旧行为和混合批次 4 项，绑定到同一最终源码。

## 发布版本

| 仓库 | 已远端核对的分支 | 完整提交 |
|---|---|---|
| revenue-forecast | `main` | `70165f99acef4a0529ebfd487af5f8fdf7151ec9` |
| investment-dashboard | `main` | `104e07b2bcea7ac329950a5145796aa8721e4e43` |
| invest-quick-scan | `codex/iqs-manifest-delivery-01` | `c1dd6a479f527cb913ae422a559020f94dcb585f` |
| StockQAbyLLM | `codex/qa-content-filter-resolution-01` | `ee92bc9c640dc8afc3013c5be2f589b8199b5f6f` |

StockWiki 的原生入口采自本地 `master@47a2cf33ece140d97acc6efaebf388736bf88c95`。RF 和 Dashboard 经各自的隔离工作树发布，RF 本地分叉和 Dashboard 在途 FF 文档仍由原工作线持有。

已删除本轮隔离工作树、临时分支、浏览器验收数据、测试账本和本轮安装在隔离树中的依赖。
