# 官方HTTP压缩响应：能力与预算责任调查

## 实测

中微executor对8个不同重要官方SSE原件的capture都得到unsupported_content_encoding，返回provider_started=true/acquisition_usage_complete=false/response_bytes=0。它们是不同材料请求；相同确定性能力缺口后停止进一步重复尝试，全部失败及unknown留存。公共错误receipt未保留实际Content-Encoding，不能猜gzip/br。材料来源与调用见本次CN execution/requests/material-*-v2.json及原生commands。

MAIN用完全不改headers/policy的public capture、独立空catalog、一件64KiB/30秒/零费上限的响应头观察得到ConnectTimeout而未看到任何HTTP header；不是已证明某压缩格式，原实测记录real_sse_headers_probe.json保留。仅自己TEMP2300B已恢复，生产原件/config/库无写入；根记录失败仍usage未知，不把0已观察body说成确定无provider尝试。没有为了诊断重复完整下载财报。

20:14:28 UTC公共sync/async transport加MockTransport有限样本实证：identity2成功，合法gzip/deflate4拒绝；entity84B，wire94/82B均远小于1KiB cap，反例不是压缩炸弹，0外部请求/模型，runtime SHA不变，见RED-valid-encoded-transport.json。这不确定真实SSE编码。先前sandbox诊断无持久结果而由协调员中断；改以正常宿主允许本机asyncio唤醒的进程和直接transport观察完成，未将中断说成通过，也不能仅凭前后改变断言卡住原因已唯一定位。

## 已定位的代码策略

bounded_http强制Accept-Encoding: identity，任何non-identity编码均在body前拒绝。既有单元测试只证明无效gzip/br/deflate不会解压绕过预算；没测合法压缩官方文档能否在实际有界预算下成功。因此现测试绿可以和真实SSE采集全部失败同时存在。官方capture在transport header验证之后才记录response status/mime，故encoding拒绝时关键信息丢失。不能直接删除这段检查让httpx自动无界膨胀，也不能针对688012绕过。

## 共用修复接口与TDD顺序

1. 拟在唯一CWP HTTP transport责任层支持明确、有界的常见编码，不修改外部Dayu/StockInfoDLSimple SDK。响应头记录只留有限typed status/mime/encoding/content-length，URL仍现有来源数据；未知/非法编码给具名有限诊断，不存任意headers/credential。先测错误发生在header之前也能保留真实已观察status/encoding，DNS/连接无header仍unknown。
2. 解码必须流式且在输出chunk进入SDK/caller之前限额。网络wire_bytes与解压entity_bytes分别说明；既有acquisition usage网络字节不冒称canonical byte_size，SourceRef/原文SHA永远针对实际文档原始entity字节。使用同一预算对象约束redirect/retry/失败累计，另保留有限decoded-size guard，不另起第二任务账本。
3. 测合法gzip、标准/raw deflate等最终选定支持格式的chunk分割、空头、多成员/截断/坏压缩流；未知编码按实际能力记录而非猜。压缩炸弹应在≤chunk有界内失败，wire和已解码实数照计，不把实际超量clamp；不接受半份原件入库。HEAD/204/304不误用响应资源长度；失败/重定向body累计、总deadline/慢滴流、transport close/子进程deadline保留。
4. 明确SDK与official capture的同一策略；如果最终只支持gzip/deflate，不能广告已支持br/zstd，也不能新加大型依赖却未入运行依赖/CI校验。模型JSON transport不在此范围。
5. 一次共用传输→official capture→入库/复用的大节点用标准合成压缩PDF/HTML证明SHA/0重复GET及失败恢复；真实SSE核心业务原件随后用正确公共入口实际取得、校验内容，不以合成红绿替代现场能力。费用/unknown与既有budget累计，恢复仅owned测试新文件。

当前调查/方案，不把代码修改或真实下载成功提前记为完成；四路fetch/storage报告将决定影响和共因处置。
