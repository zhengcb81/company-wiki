# W11 ROOT 独立整合验收：初轮未通过

独立执行 **37 项：30 通过、7 失败、0 errors、0 skipped，pytest 9.09 秒**。产品未改；已将三类根因交给 ROOT 修复，等待新 SHA 后有限复审。未复述或重跑作者的 120 项收据。

本轮绑定母 HEAD `6c5f6f04312c38aea7125a47ce0ea8c9409c4f7a`，`official_discovery.py` raw SHA `d79baa0d289bd918d80bc6335c202c2489d24c240061f91e2a3eae3c4a8d0a0f`。全部六个源码/测试以及六个保护文件的实际大小、raw/LF SHA 与前后比较，见 `initial-receipt.json`。该文件保留真实 Python 进程 import 路径，均来自母仓 `src`。

## 发现

| ID | 严重度 | 独立输入与实际行为 | 最小责任修复 |
|---|---|---|---|
| IF-01 | P2 | JSON-LD 无 `@type`，但有 `name: Annual Report 2025`、`contentUrl: /annual.pdf`；或 `CreativeWork` 带 `encoding.contentUrl` 和 PDF 格式。两例均在可见、已日期材料旁返回 `checked_index_only`，未保留嵌入材料未知 | 在现有有界观察器识别明确的未处理内容/encoding 声明并标 unresolved；无须抽取 URL、抓取材料或解析任意字符串 |
| IF-02 | P2 | 正常静态、已日期材料索引，附 analytics 外部脚本，或纯文字 “Downloading the Annual Report requires a PDF reader.”。两例均返回 `partial` | 动态未解析诊断需要未解析内容的证据；不能由任意 `script[src]` 或 `loading` 子串推断。空 app+外部 script 的动态壳正控仍须 partial |
| IF-03 | P2 | 顶层 `[Organization,42]`、`@graph:[42]`、重复 `@type:DigitalDocument` 后跟 `@type:Organization`，三例均静默 `checked_index_only`。重复键的 last-wins 行为遮掉明确文档类型 | 在同一声明观察层拒绝歧义键并保留非法节点结构 unknown；可明确 unsupported，无须实现完整 JSON-LD |

所有样本是中性合成输入。未证明历史 486789 B 真实网页含上述结构；该原 body 缺失限制不变。

## 已通过的独立正负控

30 项通过包括：最近 article/li/tr 的标题与日期、宽祖先和多链接隔离、窗口两端及未来/旧/非法日期、普通 Event/Organization/有效 graph、无 src 的普通 UI script、动态空壳、已知文档类型未知、大小/节点/深度/脚本数上限、正常大小负控、两个中性 issuer 与顺序交换、非业务法律链接、earnings 非 transcript、fragment/query 去重、真实本地 pages CLI 四例与输入 sentinel 保持。两个产品模块在 pytest 内核实为母仓源码；四个 CLI 子进程的 `__main__` 同样绑定母仓公共 CLI。

## 架构与持久回归

母 CodeGraph 健康，结构入口已先查。产品维持纯解析、薄 CLI 和既有 transport 分层；CLI diff 仅 discover 分支。新增 `tests/unit/test_official_discovery_scope.py` 位于普通 CI 的 `python -m pytest tests/unit` 路径，20 项纯解析回归具有持久入口；两个实际 CLI 回归在 integration，当前普通 CI 不自动运行该 integration 文件。本轮四个独立 CLI 子进程确实执行公共模块，未 mock discover 返回值。

本报告没有签署整套关联测试或全仓门；初始 RED 13 项及既有 ROOT 120 项仅属交接历史，本轮没有覆盖它们的失败证据。

## 操作与清理

`initial-junit.xml`、`initial-stdout.txt`、`initial-stderr.txt` 是真实本轮产物。六个产品/测试和六个保护文件运行前后字节相同。所有进程禁 dotenv，去除 API/访问密钥变量，阻断 socket connect/connect_ex/create_connection/getaddrinfo，包含 loopback；只有独立禁网自检曾主动验证阻断。没有外部 HTTP、模型、下载、原件读取或作者工区操作。

独占 `.planning/r1-w11-independent-20261023` 初始不存在，核对其绝对父路径后删除本轮 18 个文件，结束仍不存在；临时输入未写入生产目录。未清理历史 scratch。报告绑定 raw 字节；LF SHA 只允许后续 CRLF→LF 换行规范化的文本等价检查，不对其他文本或行为变更自动放行。

ROOT 已接手产品修复。本复核按要求暂停测试与产品读取，等待最终 SHA 后复审相同 37 项，保留本轮失败产物。
