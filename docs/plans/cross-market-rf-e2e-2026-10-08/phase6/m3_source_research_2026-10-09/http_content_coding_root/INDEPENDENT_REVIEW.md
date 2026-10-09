# 有界 HTTP 压缩责任链独立工程审查

结论：**FAIL — c8c4dac1 当前不宜合入主线**。原责任短测 91 PASS；独立接口探针 41 PASS / 6 FAIL，六个失败归并为三项 P2 和一项 P3。无需扩大生产上限、增加许可门禁或改变来源身份/期间/hash规则；先在隔离树补 RED 与根修，再验收本节点。

审查源码：`c8c4dac11898c54d2124bb5ddb66f79b12485e3d`，父提交 `18d635f2857f3189241d3518b5325097c9b21e26`，分支 `codex/m3-http-source-20261009`。只读审查该版本完整 11 文件 diff（7 runtime + 4 tests），未修改隔离源码、Dayu、生产配置、raw、原执行/history或其他 agent 报告。源工作树初始/最终 status 均为空；12项源码/测试/生产配置 SHA 前后一致。精确 SHA、命令、逐用例结果、写集与证据索引见 JSON 和 `independent_review/`。

## 具体缺陷与最小反例

| ID | 严重性 | 位置（此提交） | 实证与影响 |
|---|---|---|---|
| HTTP-IR-01 | P2 | `bounded_content_encoding.py:50–51` | 首两字节像 zlib 不足以排除合法 raw DEFLATE。独立 zlib raw oracle 解出156B；CWP在1B、2B、完整166B切分均报 incomplete_response，错拒合法文件。 |
| HTTP-IR-02 | P2 | `official_source_flow.py:858–864`；`official_source_cli.py:159–163` | 完整 gzip HTML 下载后按请求 PDF 做 MIME 校验而拒绝：内部 capture_receipt有HTTP观察/wire，异常没有对应顶层属性，CLI丢失三个HTTP字段。头部拒绝路径能投影，正文后校验路径不能，真实失败难定位。 |
| HTTP-IR-03 | P2 | `bounded_http.py:185–210` | gzip180000B读首个最多65536B输出后退出AsyncClient.stream，再显式关闭外层aiter_bytes和client；底层stream.closed=True，active iterator的finally仍未执行。依赖event-loop shutdown/GC延后回收；预算异常关闭已PASS，提前终止关闭仍遗漏。 |
| HTTP-IR-04 | P3 | `adapter_process.py:374–380,258–272` | handled失败final明确`http_wire_usage_complete=false`，公开正文/费用receipt完整；父桥未携带wire completeness，最后误标True。正文9、wire7、费用0.25均保留；缺陷是未知wire观察被标为完整。自管SDK当前不产生该组合，影响有限，但已支持的可选观察协议失败分支不一致。 |

**HTTP-IR-01 最小原始字节**：`bytes.fromhex('789c0063ff') + b'A' * 156 + bytes.fromhex('010000ffff')`。它是非final stored块（LEN156、NLEN65379）和final空块，padding bits合法；`zlib.decompress(raw, -15) == b'A' * 156`。首`78 9c`满足当前zlib头启发式，却不是zlib容器。源码不再尝试raw，抛`invalid stored block lengths`，再转`incomplete_response`。修复须保持增量和输出上限，并保留坏标准deflate校验/EOF/尾垃圾拒绝；不能用忽略checksum或无界全文回放满足正例。

**HTTP-IR-02 公共复现**：真实`official_source_cli.main` → 真实`capture_official_source` → MockTransport返回HTTP200/text-html/gzip，正文是`<html><body>This is not the requested PDF.</body></html>`，请求mime为application/pdf。原文验真正确拒绝，公司canonical目录无文件，CLI返回2。独立断言得到`KeyError: 'http_observation'`。观察应仅投影有限status/mime/coding/wire length、实际wire bytes及completeness；未收到头的网络失败仍unknown。mock的authorization/x-secret头和路径没有进入失败输出。完整后SHA/持久化/来源校验失败与recover复用同样应消费真实receipt，保持原始具名拒绝和原费用语义。

**HTTP-IR-03 公共复现**：`async with client.stream(...): outer=response.aiter_bytes(); await outer.__anext__()`；退出上下文后`await outer.aclose()`并退出client，底层独立stream迭代器finally标记仍False。本次没有宣称真实socket已泄漏：stream自己的aclose已执行；证实的是装饰层未立即关闭它已持有的迭代器，无法保证其独立资源清理。本轮既有timeout/预算异常负控已关闭stream和iterator。根修应让显式aclose拥有活跃迭代器生命周期、幂等收口且不重入关闭正在执行的generator。

**HTTP-IR-04 最小final**：版本/identity匹配的`status=failed` envelope，外层`http_wire_bytes=7,http_wire_usage_complete=false`，error内usage为原三字段`1.0 / response_bytes=9 / cost_usd=0.25`。调用真实`_decode_response`后`_charge_failure_usage`，两counter/费用正确，却`wire_usage_complete=True`。缺字段/坏字段仍unknown且不产生新门禁；正文/费用完整和wire观察完整必须各自保留。

## 已通过的责任链与验证

- 原5个责任文件集中执行一次：`test_bounded_content_encoding`、`test_bounded_http`、`test_adapter_process_budget`、`test_dayu_sdk_fetch`、`test_official_source_flow`，**91 PASS / 32.13秒**（进程总34.788秒）。没有全仓检查。
- 独立47用例 **41 PASS / 6 FAIL / 2.57秒**（进程总5.107秒）：gzip/多member含空member、标准与通常raw deflate，1/2/7/整块切分；CRC/EOF/尾垃圾/非法block负控；wire/entity实际超量与此前0.25费用；压缩redirect/429/retry累计；HEAD/204/304；迟到压缩chunk、总deadline、异常关闭；可选wire缺/坏unknown、不新门禁；原usage三字段；真实子进程final覆盖progress一次、真实hard-stop最后checkpoint作为下界；prelaunch证明零用量。
- 为补足实际父子调用，执行真实`JsonCommandAdapter.fetch_bounded → CWP dayu_sdk_cli.main → _sec_operation → bounded transport → _stage`，仅在子进程注入fake Dayu SDK与MockTransport，**5 PASS**。gzip/标准deflate/raw deflate均还原314B，wire分别159/147/141B，同源SHA `70de41eb0ae4468e6c1ea6014dff0db8fcad8ffc4c4238d356e45a22cb740ddb`。截断gzip具名incomplete_response；错财政年度具名fiscal_period_unresolved；两失败无staged，已读正文/wire及0费用保留。CWP真实协议已执行，真实Dayu和网络服务支持未由此证明。
- HTTPX收到已解码entity前移除Content-Encoding/压缩Content-Length，不二次膨胀；现有公开capture→SourceRef→原文精确读取→0重复GET复用的PDF/HTML压缩fixture均PASS。原件SHA/byte_size仍对应文档bytes，身份、期间和MIME验真保持。
- 供方TDD日志完整读取并做SHA索引：codec先21FAIL；桥/capture先13FAIL/34PASS；async active-iterator异常关闭另1FAIL；责任初轮1FAIL/89PASS/1warning，最终91PASS。未把旧RED、warning或假“compressed”字节直接解释成合法新能力。
- 供方扩大7文件mypy为28错误；旧6文件基线同28。去行号后的错误Counter完全相等、无新增/移除；新codec/transport两模块供方日志PASS。本审查未重复mypy或把这28条既有动态属性/外SDK缺stub/Decimal联合类型错误另作合入阻断。

## 真实来源与限制

只读取已有`real_sse_after_codec.json`，本审查**外部请求0、模型调用0、收费0**。真实记录是HTTP200/text-html/gzip，wire3872B、entity7373B、费用0、公开usage complete。PDF请求被OfficialSourceError拒绝，未新增真实PDF；记录中error_code/具名str未保存，仍unknown，未推断WAF或伪造PDF SHA。该证据仅证明真实gzip正文在当前上限内读/解码/计量，不能核销8份原件缺口、旧未知费用或下游研究失败。

工作树CodeGraph未初始化，工具返回明确错误；保持只读，不运行init。按已锁定文件、完整diff、现有协议源码和离线执行审查。没有修改Dayu、任何许可/预算上限或FF/RF公开DTO，不跨仓写StockWiki；也不对公司投资分析作任何结论。

## 写集、临时恢复与复验范围

永久写集仅本报告、JSON和`independent_review/`下源码diff、探针源文档、日志、命令及哈希索引。自有临时区为主仓`.tmp/http-independent-c8c4-20261009`，含fake SDK脚本、staging、provider-state、子进程scratch、pytest分配；完成后只删除已验证位于该命名目录内的自有路径，恢复结果见JSON。初次sandbox临时目录跨call重定向且无文件可延续，随后async sandbox探针挂起由我中断；有审批的离线运行成功，未发生平台拒绝或绕过。父子probe初次夹具version=1被既有semantic-version规则正确拒绝，改夹具为1.0.0后完成5项验证，未改源码或验真断言。

狭义合入条件：根修HTTP-IR-01/02/03，并保留HTTP-IR-04的unknown语义；复验此责任范围和独立反例即可。真实PDF成功仍是后续明确来源路由与新attempt的未完成事项，不应通过放宽MIME/身份/hash或盲重抓旧8份解决。
