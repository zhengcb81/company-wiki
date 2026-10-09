# 有界 HTTP 压缩整改后独立集中复验

结论：**PASS — 固定 6cc9959f 在本 HTTP 责任范围内可正常整合主线**。原四项工程缺陷均已解决；旧47项独立探针文件逐字节不变、全部PASS。针对新双候选方案的11项有限相邻控制和实际CWP父子5场景也全部PASS。未发现新的具体合入阻断，无需增加人工小节点签收或放宽原有预算/身份/期间/hash验真。

源提交：`6cc9959fdb7a74fcb16e92471e9584893747d1a4`；基线为`c8c4dac11898c54d2124bb5ddb66f79b12485e3d`。读完整7文件增量：4 runtime（codec、HTTP transport、adapter bridge、official flow）+3 tests。隔离工作树始终只读且最终status为空，12项源码/测试/生产配置SHA前后一致；原FAIL两报告及`independent_review/`原证据全部SHA不变。新报告不改写原提交的FAIL结论。

## 四项问题的闭环

| 原问题 | 新机制 | 独立复验 |
|---|---|---|
| HTTP-IR-01 / P2：合法raw DEFLATE首头像zlib被错拒 | 标准/raw两候选增量校验；不猜首头；确定前各自有界spool；选定后交付，EOF两合法优先标准 | 原1/2/整166B反例3项PASS；标准/raw/CRC/EOF/尾垃圾旧负控全部保持PASS；新增长歧义3种切分及spool控制PASS |
| HTTP-IR-02 / P2：完整下载后校验失败公共HTTP投影丢失 | 持久化/import/capture后失败都调用同一有限投影；recover import失败也使用此路径 | 原真实公共CLI mock MIME拒绝PASS；新增公共recover同receipt、无重复GET、有限字段PASS；任意receipt字段过滤PASS；供方MIME/SHA/storage三个实际CLI路径日志PASS |
| HTTP-IR-03 / P2：提前close仅关stream、iterator延后 | sync/async持有active iterator；close/aclose幂等收口，关闭decoder/spool；主要异常保留 | 原async early-close立即关闭PASS；原timeout/异常关闭PASS；新增歧义落盘后的任务取消，iterator/stream/两个spool立即关闭，CancelledError和既有费用保留PASS |
| HTTP-IR-04 / P3：failed final把wire unknown/false变True | typed异常携带独立wire complete；失败充账保留false/unknown，checkpoint仍下界 | 原false反例PASS；旧缺/坏wire未知不变新门禁、最终/硬停/费用/公开三字段控制PASS；供方False/None/True新参数化断言已审 |

## 新双候选方案的概念验证

独立构造了实际合法raw DEFLATE stored块，而非mock两个decoder状态。wire131091B、raw oracle解压后131071B。输入到最后10B之前时，标准和raw两候选均仍active，已分别产生131069/131066B、均超过64KiB并真实rollover落盘；**向调用方交付为0B**。最后的实际字节使标准解释遇到非法BTYPE，raw解释完成，最终正文与独立`zlib.decompress(raw,-15)`逐字节相同，输出块最大65536B。

该样本通过513B、65536B、整131091B输入切分的公共HTTP调用；最终entity只计131071B一次，wire计131091B，此前fixture费用0.25仍保留；两个候选spool、底层stream与iterator全部关闭。探针源保存在`independent_review_remediated/test_remediated_adjacent.py.txt`，公式和断言可复查。

另外验证两候选暂存各不超过allowance257B（cap+1）；内部候选循环第4次deadline回调可中断；长歧义EOF截断/尾垃圾拒绝并清理；在两个spool已落盘、第二wire读取等待时取消任务，未选定entity仍计0，已读wire131081B及费用保留，所有资源立即关闭。EOF双合法优先标准由候选顺序和finish分支源码核对，本轮未另外构造不同正文的双合法polyglot；没有把单候选错头回退或先向SDK发候选正文当成验证。

## 精确执行与证据

- 原独立47项：**47 PASS / pytest1.77秒**，进程总4.668秒；原探针source SHA与前次封存完全一致，未修改测试使其变绿。
- 新相邻11项：**11 PASS / pytest0.74秒**，进程总3.839秒。覆盖长歧义、spool、cap/deadline、EOF/垃圾、取消、有限投影与公共recover。
- 实际CWP `JsonCommandAdapter → dayu_sdk_cli → _sec_operation → bounded HTTP → _stage`：**5 PASS**，进程总5.951秒；Dayu是进程内注入fake SDK，HTTP是MockTransport。gzip/标准deflate/raw均314B，同SHA `70de41eb0ae4468e6c1ea6014dff0db8fcad8ffc4c4238d356e45a22cb740ddb`，wire159/147/141B；截断和错期间仍具名拒绝、无staged，0实际费用。
- 供方日志完整读取：本责任110PASS/31.21秒、无警告；另外MIME/SHA/storage实际公共CLI三项PASS；2模块mypy、7文件ruff、diff检查PASS。按请求未重复110范围或扩大全unit/全仓，未重新把旧28类型诊断设为门禁。
- 完整命令、原始输出、JUnit逐用例状态、7文件增量diff、探针源文档、源和基线报告SHA、临时恢复均见新JSON与`independent_review_remediated/`。

## 写集与适用限制

本轮外部请求0、真实GET0、模型0、实际收费0。永久写集仅`INDEPENDENT_REVIEW_REMEDIATED.md/.json`和自有`independent_review_remediated/`证据；未修改隔离源码、Dayu、生产配置/raw、冻结execution/history、原FAIL报告或其他agent报告；没有跨仓写StockWiki。仅更改自有runner哈希索引的Windows路径分隔符，首次在测试开跑前退出，随后完整执行；原47探针及断言未变。

自有临时区`.tmp/http-independent-remediated-6cc9959-20261009`只在校验其解析路径为本仓确切命名目录、无链接后删除；结果见JSON。源工作树的CodeGraph仍按原只读限制未初始化，本轮使用已锁定7文件diff和协议源码。

真实SSE旧证据仍是HTTP200、gzip HTML：wire3872B、entity7373B、费用0，被PDF验真正确拒绝；本轮没有重抓，也没有新增真实PDF。原具名error_code未保存，继续unknown。工程PASS不核销8份原件缺口、旧未知费用、模型截断或投资研究FAIL；真实服务/Dayu支持仍需后续准确来源attempt证据。本结论仅支持正常工程整合此固定源码，并保留后续精确CI和真实PDF取得的原责任边界。
