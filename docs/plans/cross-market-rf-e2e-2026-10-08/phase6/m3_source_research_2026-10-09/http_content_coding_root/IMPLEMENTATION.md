# 有界HTTP压缩原件施工：接口冻结与TDD

状态：开始隔离施工，主运行时不改。复用clean且历史已入master的audit-provider-cause工作树，从18d635f2建codex/m3-http-source-20261009；不新复制数据湖。US-parser工作树由独立审查只读，本卡不触碰。

## 不等待小节点签收

六个transport反例和八个真实失败已证明工程缺口，可以在四审期间先TDD/隔离实现。四审/专家仍负责整合影响与遗漏；集中整合节点才验收、发布及真实采集重跑，不要求每页/每个commit先等另一份人工报告。旧冻结execution、scope、原件与失败不改。

## 字节语义（已阅读实际父子协议后补充）

现JsonCommandAdapter.fetch_bounded要求staged byte_size≤报告response_bytes，Official capture.receipt.response_bytes也绑定原件大小；所以不能把新压缩wire长度直接替代这些应用正文计量，否则合法压缩原件会在下一层再次被错拒。

- 既有acquisition_usage/1三字段及response_bytes继续表示已 materialize 的应用正文/原件响应字节；identity时与wire相同。source SHA/byte_size一律对应解压后的实际文档bytes，绝不hash网络压缩容器冒充PDF/HTML。
- 同一个AcquisitionBudget增加wire_response_bytes内部计量，上限与当前请求max_response_bytes一致；同操作所有redirect/error/retry共享两个计量。没有第二账本。实体和wire均先计实际再拒，真实超量不clamp；解压输出一次最多64KiB且不超过剩余实体限额+1，压缩炸弹不能先膨胀全文再判断。
- usage_receipt和FF/RF公开诊断DTO不扩字段。CWP自管SDK的progress/final/error envelope可以附有界http_wire_bytes观察，父桥以现有counter合并一次，不把多checkpoint相加；旧外部adapter没有这个字段则wire保持unknown，不虚构等于正文或零。原件正文/费用/时间上限仍由现有协议实控，不新增人工授权。
- 子请求为协议兼容继续使用现max_response_bytes字段；CWP父桥传两种剩余额度的保守较小值，子进程在该范围同时限制wire/实体。若wire历史未知保留诊断和原正文上限，不把缺观察字段变成全局许可阻断。当前原文正文cap没有放大。

## 责任写集

1. download_budget.py：共享wire计量、剩余量及合并；原response/cost/unknown会计接口兼容，新增可选信息不得导致已读正文/费用丢账。
2. 新小型bounded_content_encoding.py：仅codec状态机，支持identity、gzip（多member/CRC）、标准及raw deflate；chunk边界、EOF和错误由固定具名结果表示。br/zstd/链式编码若未实现则继续unsupported，不广告支持。
3. bounded_http.py：两种transport共用同一codec逻辑，wire在收到时计量，entity在交付前计量/截止检查；解码后的response清掉Content-Encoding和压缩Content-Length以阻止HTTPX再解码，原typed status/mime/encoding/wire length进extensions。HEAD/204/304不拿资源长度当已收body，失败关闭stream。
4. official_source_flow.py：CountedTransport在外层校验之前记录实际已观察typed header；connect/DNS没有header保持unknown。capture/失败/恢复只留有限字段及真实wire/entity计量，canonical import仍由现入口校验，不接受半份文件。
5. dayu_sdk_cli.py及adapter_process.py：只CWP-owned wrapper的wire观察向父预算一次传递/合并，SDK仍公开接口；分开正文与wire，修正父子累计和checkpoint恢复，不改Dayu任何文件。不修改旧外部receipt或伪造未知wire计量。

## 先测试再实现

1. 新unit模块先RED：sync/async合法gzip/两种deflate（单字节split）、gzip多member；同source正文SHA与元数据准确；identity保留原行为。模拟chunk stream，无外部网络/费用。
2. 响应非法/截断/CRC/尾垃圾、未知/多编码、压缩炸弹、wire超量、两次响应共享实体cap、redirect/429重试、迟到chunk与总deadline、HEAD/204/304、异常关闭全部negative controls。错误payload不进入SDK重试通用RuntimeError/HTTPError处理。
3. 父桥正常公开discover/fetch的compressed正文长度大于wire时不被错拒；跨调用预算、最后progress与handled error/kill不重复计量，旧三字段usage及unknown保持。检查费用已可能发生时不被后续metric错误抹掉。
4. 现旧“compressed”测试提供的是无效字节，先保持其不能绕预算目标；实现后改为验证真实坏编码拒绝/实际已读计量，而非继续断言所有gzip都unsupported。旧合法identity/时间/费用/进程组/原件SHA/错主体边界不可放松。
5. 公共capture/import→原文SourceRef/locator→0重复GET的一次离线整合节点，用有效小PDF/HTML压缩fixture；失败原始类型及typed实际headers可查，自己TEMP恢复。再用真实SSE一件重要原件证明实际codec/bytes，不把mock当真实服务支持或放宽来源资格。
6. official_source_cli.py额外投影有限HTTP观察，不透传任意头、凭证或正文，FF/RF原三字段usage DTO不变。责任短测/静态与既有预算/桥/官方source集中通过后正常commit/push，独立大节点审查再并主线/精确CI。真实收费摘要只在配置/选择根修完成后重跑相关失败来源，不在本HTTP节点调用LLM。

## 完成标准

合法官方压缩文件能在当前上限内下载并保持原文SHA/复用；任何wire或entity超限、坏编码、时间超限都在上游读期间停止并保留真实计量/已观察headers，partial不入库。父子累计与失败恢复一致、Dayu零修改、FF/RF旧usage DTO兼容、旧原件/配置/冻结scope不漂移。最终真实SSE证明与四审影响处理之前不宣布此能力已完成。

## 本轮实际结果（2026-10-09 20:50 UTC）

- 新codec先21FAIL；父桥/capture另先13FAIL/34PASS，async实际迭代器关闭另1FAIL/警告，都保留原日志。实现后集中91PASS/30.51秒，无resource warning，自有TEMP恢复、外部模型0、Dayu零改动。新codec/transport额外mypy2模块PASS；扩大的7文件检查28条既有动态异常/外部SDK/Decimal联合类型诊断，与未改主线6文件基线28条相同，未伪称全范围类型绿或加新日常门禁。
- 源commit c8c4dac11898c54d2124bb5ddb66f79b12485e3d，正常pre-commit18.06秒、ruff/host guard PASS。11文件：7运行时（含official_source_cli）+4测试。已正常push隔离codex/m3-http-source-20261009，2512PASS/148.18秒、完整push156.674秒；主运行时尚未合此修复，验收/准确推送状态以source-push.json为准。
- 真实SSE同一重要并购公告有限GET已观察gzip/HTTP200/text-html。网络3872B，正文7373B，费用0且usage complete；不是PDF，OfficialSourceError正确拒绝入库。测试TEMP仅10000B并恢复。错误具名str本次记录未保存，因此不补造error_code、HTML原因或PDF SHA；不能声称八份公告已成功或绕mime验真。见real_sse_after_codec.json。压缩层实读已证，原件采集缺口待配置官方可用路线/具体响应诊断新attempt，不盲重抓8份。
- 仍待集中接口独立审查、父桥错误/硬停计量及公共类型失败投影边界核对、正常主线整合/精确CI；不能用91工程PASS核销公告缺口、模型截断或研究FAIL。

独立HTTP整合审查已启动 /root/m3_http_integration_review，限固定11文件接口/TEMP，无公司研究角色替签。首次支线push没有既有远端range而按现有规则跑全Unit；commit仍18.06秒静态，不是每commit跑全套。该分支不在master-only Actions触发范围，不能把无branch CI记录说成绿色。

记录实际UTC：2026-10-09T21:07:55.292346+00:00

## 独立审查后第二轮根修（待TDD，基线c8c4dac1不接受）

独立41PASS/6FAIL归并HTTP-IR-01..04；原91PASS不变。先把四机制反例写进现责任测试，RED原生日志保留，再实现；所有公司执行仍冻结，不改旧失败。该集中节点保持原文/主体/期次/费用/时间上限与三字段usage不变。

1. **DEFLATE格式歧义**：不使用首两字节/固定前瞻宣称某个framing。两候选增量校验标准zlib与raw，在尚不可判定时保留各自解出的有界前缀；候选错误后只交仍合法候选，EOF双合法时按HTTP标准优先zlib。每个候选前缀最多当前剩余实体cap+1，每次zlib输出≤64KiB；自有spool内存阈值64KiB，临时磁盘最坏两份有界前缀，只在这一HTTP响应歧义期间存在，关闭/异常必恢复。候选试解字节不当作两次网络/两份文档；选定实体在SDK交付前按原预算逐块记一次，超限候选至多产生cap+1，不能先膨胀全文。wire每收到chunk先记并拒超量，总deadline也覆盖两个候选内部循环。一般gzip保持原流式路径。
2. **显式关闭所有者**：sync/async stream持有active底层iterator；正常EOF、预算异常、调用方只读首块便退出、取消/timeout均用同一个幂等关闭路径。关闭候选spool和底层iterator/stream，不依赖GC/event-loop结束；清理失败不得覆盖下载主要异常，不重入正在执行的generator。
3. **完成下载后的失败观察**：从现capture_receipt统一附有限HTTP观察/计量到原始异常，用于类型/SHA/持久化/import以及recover失败，公共CLI只投影现白名单。没有真实头保持unknown；不能凭请求MIME或本地文件猜网络头。正文已完整与canonical拒绝分开，不丢费用或改变具名拒绝。
4. **父桥wire completeness**：成功/handled失败/cleanup-after-final/lastcheckpoint均传同一个可选wire完整性字段；body receipt完整不推定wire完整。保持原unknown sticky、last cumulative计一次、已知费用不丢，不增加wire unknown许可门。

测试：raw前缀歧义不同stored长度/1B、2B、全块与异步；标准/原raw既有正例；CRC/EOF/尾垃圾、deflate实体炸弹/共享重试cap/64KiB输出；sync/async首块退出、异常/取消幂等关闭与自有TEMP恢复；实际public CLI完整HTML冒PDF和expectedSHA失败/存储失败/recover失败诊断，secret header不得外露；handled final body完整/wire仅下界及旧无字段负控。集中91既有责任加新反例+独立探针复验后正常commit/push，再大节点整合主线/精确CI。无需逐小节点人签，真实SSE当前HTML限制仍另列。

## 整改后实际节点 2026-10-09 21:27 UTC

四反例16FAIL/1PASS及cleanup主因2产品FAIL已保留；一次模块名错误exit4/0收集和Windows本机socket夹具setup错误分列。110集中PASS/31.21秒/无警告，最后有限观察投影3CLI PASS，ownTEMP全部恢复。source6cc9959f正常commit17.621秒、push2528PASS/141.33秒；整改大节点独立复验正在运行，原c8c失败报告不改、未并主线，不是研究或真实SSE PDF验收。

## 2026-10-09 21:34 UTC：整改复验封存与主线整合

独立报告 INDEPENDENT_REVIEW_REMEDIATED.json SHA965e6ada…、MD2a53308f…已核对。原47原样PASS、新11控制PASS、真实父子5场景PASS；审查未改源码/配置/旧FAIL证据，自有TEMP恢复。仅工程接受，尚无新真实PDF。源码6cc9959f正常并master806818cf，配置SHA及MAIN未提交记录保持，见main-merge.json。正常主线push/精确CI由本发布节点完成，不假称已远端全绿。
