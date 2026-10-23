# W11 ROOT 独立整合终审：有限工程验收通过

同一份、字节未改的独立 37 项断言在 ROOT 修复版本上 **37P / 0F / 0E / 0skip，pytest 6.73 秒**。初轮 30P/7F 的三类发现均在本次复审消除。没有新增反例范围、没有重跑作者 120 项或 ROOT 132 项关联套件；它们不能计入本次独立通过数。

母 HEAD 在复审时为 `6c5f6f04312c38aea7125a47ce0ea8c9409c4f7a`。本报告以以下六个实际文件版本为准：

| 文件 | 字节 | raw SHA-256 | CRLF→LF SHA-256 |
|---|---:|---|---|
| `src/company_wiki/source_catalog/official_discovery.py` | 29358 | `06794d6826c1dc05bd505871cb32c17cd13ed7a9c7e12afb7be0b5d6f3c2d6d0` | `bc2a3955d550435893bc6752d40bc7b37f53c35a0de2044a42b1b9e0721d3710` |
| `src/company_wiki/source_catalog/official_source_cli.py` | 13362 | `bdd06d5728dc25ef9a7433e5d7c1c89534f3fa52b9dd6e15ce7867e40d9c6162` | `7fb9a8031e6d98fd9788518b9fb41904179f326fba57c2bbb08fb48d1dee1adf` |
| `tests/integration/test_official_source_flow.py` | 56854 | `f374c7d7ff39677c9b30c9f4ac9c8429740c7e8df1655fb95efc3bb453564b66` | `ff255559a09fbb00dfe6e2f233f2eebb779d2f0daf43fcb6d6de6c1aaaa7b142` |
| `tests/integration/test_official_discovery_offline.py` | 31358 | `b1a0da0228b3b077c076ea1a4665728dd022fc33358248d16c53bc4d9dd16069` | `b1a0da0228b3b077c076ea1a4665728dd022fc33358248d16c53bc4d9dd16069` |
| `tests/unit/test_official_discovery_scope.py` | 8632 | `5611b2ea250a789bbd6c834b418d86c36386808b8b39a8564e4e1899d6e81f0c` | `b3670e1f60d74e4fa654bc83424b0ba99d87bcf122cb9a1f80f99310a1b515a5` |
| `tests/integration/test_official_discovery_root_scope.py` | 2019 | `a84df73d21b46708bd6aa2035408a7f8603cf3e870e6d1524b99e49ca5c3b4a0` | `a80669f0c0c690b765079eb986467374d95a8b239bf735729482251a90093f3c` |

## 修复与边界

- **IF-01 通过**：无 @type 的 contentUrl、CreativeWork+encoding 等明确文档关系现在保持未知；现有可见锚仍正常处理。没有增加 URL 提取、原件获取或 JS 执行。
- **IF-02 通过**：静态有日期材料旁的 analytics script、普通 inline UI script 和 Downloading 文案保持 checked_index_only；空 app+外链 script 仍 partial。静态阅读确认动态观察器只用明确 loading 占位或不可读的外链脚本壳，按页观察，未增加公司/域名白名单。
- **IF-03 通过**：根/graph 非节点成员、重复 JSON 键保留 embedded_data_unresolved，文档声明不再被 last-wins 遮掉。观察器对普通属性的 literal arrays 保留正常语义，ROOT 已加入 sameAs/keywords 正控；该新增正控属于静态核阅，本次未另跑它。

原有最近 article/li/tr 标题和日期、祖先/多链接隔离、窗口与非法日期、普通 Event/Organization、声明文档未知、字节/节点/深度/脚本数边界、合法规模负控、两 issuer/顺序交换、法律导航、earnings 身份、URL 去重及四个公共 CLI 案例均继续通过。

本轮只确认有界来源发现的覆盖诊断。checked_index_only 仅表示当前索引检查范围；metadata lead 不成为 business original、已验 issuer 身份或已读问答正文。没有恢复历史 486789 B 原网页，没有签署真实 IR 原件、公司研究或全站穷尽 PASS。未实现完整 JSON-LD 规范，也未作全结构枚举承诺。

## 架构与持久回归

复核了两个共享观察器及其调用点：维持纯解析、薄 CLI、既有 transport；无第二 provider/任务/缓存/授权系统。CLI 的产品变化仍局限 discover 输入校验与限制去重。ROOT 正式回归已位于 tests/unit/test_official_discovery_scope.py，普通 CI 明确执行 tests/unit，因此纯解析回归有持久入口；两个 CLI integration 案例属于显式集中验收，当前普通 CI 不自动运行该 integration 文件。本轮独立执行了四个真实公共本地 pages CLI 子进程，未 mock 产品返回值。

## 证据与恢复

- `final-junit.xml`、`final-stdout.txt`、`final-stderr.txt` 和 `final-receipt.json` 为本轮真实产物；pytest 及四个 CLI 子进程的实际模块路径均来自母仓 src。
- 全六个最终源码/测试在运行前后逐字节相同。六个保护文件与初轮逐字节相同，含生产 source_catalog 配置、resource_budget 配置/实现及 narrative/decision 文件；另外四个未修改产品/测试仍匹配初轮冻结。
- 原37项文件及全部初轮报告、失败 stdout/JUnit/收据的 artifact SHA 再核一致。`initial-review.md/json` 继续保留 FAIL 状态，未重写历史证据。
- 本轮独占 scratch 初始不存在；只在该目录写临时夹具、导入日志和 pytest 文件，核对绝对父路径后删除本轮文件，结束不存在。CLI 输入、请求和 sentinel 在每次运行前后 SHA 相同。未碰作者工区、生产资料或历史临时物。
- 所有运行进程禁 dotenv、清除 API/访问密钥变量并阻断 socket connect/connect_ex/create_connection/getaddrinfo（含 loopback）；禁网自检验证阻断。外部 HTTP/模型/下载与真实原件读取均为 0。

raw SHA 绑定本轮实际字节；LF SHA 仅支持这六份 Python 文件在 CRLF→LF 规范化后与 Git blob 的确切文本对应。只有换行变化且归一后 SHA 匹配时，本次有限结论可沿用；其他源码/测试变化需按实际影响判断，不能自动继承该通过。

ROOT 可据此完成已授权的普通 Git 整合、ancestry、PWF 和发布工作；本独审不新设人工许可或小节点签收。
