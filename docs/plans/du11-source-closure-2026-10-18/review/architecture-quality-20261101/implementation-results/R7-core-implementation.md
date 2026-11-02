# R7 核心门禁整改 — G1/G2阶段交付

状态：**CORE_G1_G5_FROZEN_FOR_ROOT_INDEPENDENT_REVIEW**（最终37文件：25源码＋12测试）。原21文件阶段SHA仍完整一致，见JSON manifest；新增16文件见delivery_files_sha256。下方阶段交付保留为历史，当前结果见文末。基线`fa8ef38e`。本线G1–G5工程已完成并冻结；独审/当前完整CI/真实C仍待，不能宣称全部PWF完成。下方原阶段说明属历史，最终结论看文末及JSON status/delivery_files_sha256。未自行commit/push/安装，不改主PWF、tools、配置、原件或其它仓。

## 共同根修

取消正常select/summary/bundle/context/dependencies、artifact reference/read、receipt/evidence view/CLI和official capture收据的固定字节/条数/深度许可。核心字段、来源ID/hash/locator、非finite/循环/错误类型/未知核心字段仍拒；可序列化内容完整保留，不为凑字节数删必需材料。旧容量常量仅兼容存储估算，没有再给结果授权。

JSON验证/路径检查/copy/freeze共用迭代树owner，避免删12层后又被自己递归walk卡住。没有自制JSON parser/serializer，没有新12/32或别的阈值；标准库真正不能编码时如实报encoding error，不叫用户材料超额。100层合法树及普通canonical JSON字节不变。

execution报告/summary assessment不再因32/64KB失败。extractive缺省56KB来自旧summary64KB，属于附加默认门，已去掉；调用方显式max_draft_bytes仍按真实UTF-8完整卡预算逐卡遵守，不切原话，去掉显式预算不能超过56KB的天花板。137任务完整execution可正常进入假模型handler；400个大scope在显式quota下仍不render被拒卡。

HTTP适配器固定128KB final content门在body已读、usage已知之后才触发，并在Response/FailedFinal DTO重复执行，非资源防护。它还遮住真正finish_reason=length。该后置门及计数上限已删；真正HTTP Content-Length/逐块读取max_response_bytes、timeout、配置max_output_tokens、usage和账仍由原owner保留。本轮未真实HTTP/供应商POST。

自动缓存候选坏metadata/bundle只log固定CACHE_CANDIDATE_INVALID及异常类型，继续好候选；没有好候选就正常cache miss。明确指定pin/同run冻结、原文变化、source/as-of不符、未知费用与真实I/O异常仍抛。解析器reading_candidate_manifest本身仍严格，只有自动发现调用点把坏派生产物降为诊断。未重建第二账或另造许可文件。

## 真实TDD与一次集成的范围

- 新G1/G2组5F3P→14P。初次bytes样本错用forbidden observation字段，已透明改为合法diagnostic_text；不把这个fixture错误当size RED，其余array/policy/depth/cache均真实RED。
- 新HTTP后置内容门2F→2P（含stop/length和已知usage）。
- 一次13文件325项受影响集成在sandbox跑到85%，含旧门禁expectation F和5个cache fixture E；local HTTP contract末组停滞，约290s主动收停。保partial log，无XML，**不算PASS**，不再重跑325/全仓。
- 正常host仅精确cache fixture3P，无代码变化，区分此前sandbox E；18P1F精确复验中F为旧32KB execution拒绝期待。
- 迁移后55项54P1F/28.50s，唯一F为测试假定1500层必触宿主递归；宿主实际可编码，因此改注入owned JSON encoder真实异常。一次全局json.dumps注入层过宽误影响subject构造，失败保留，再精确owned canonical_json入口1P/2.01s。没有为此改产品或新加深度门。
- 55项中的新真实handler已保存>1MiB合法diagnostic并对合成PDF真实原文replay成功，不只是私有helper；错误引用/path/nonfinite/cycle仍拒，fake oversized原话仍因不匹配原件而PARSER_INCOMPLETE。
- Ruff21文件通过，mypy15源码通过。最终上述状态不能拼成“325全绿”；后续只对新增G4/G5/G3与新失败定点，最后ROOT集中独审与既有CI。

证据均`.planning/architecture-quality-20261101/r7-*.log/xml`，JSON列精确运行/边界和当前SHA。真实source/摘要/缓存恢复/RF采用未由本纯工程节点代签。所有旧F/E及停止记录保留。

## 原阶段后续（现已完成，见最终冻结段）

G4复用一次VerifiedContent/metadata观察；G5共享WorkBudget去32/4096/64任意导航天花板且保有效前缀；G3先真实同unit RED，不确认不改。source-text恰好以技术路径开头的全局path-walker静态风险已获ROOT提醒，暂不扩无证施工，真实metadata路径跨层拒绝仍保。

冻结清单见同名JSON。当前15源在G1/G2阶段不再变化，等待ROOT审查；新缺陷例外才解冻。


## G3/G4/G5及漏consumer最终冻结

全部改动现在工程冻结，JSON的`delivery_files_sha256`共37项是最终精确清单；原`manifest`21项保持不变，供正在进行的G1/G2独审继续使用。没有自行commit/push/安装或生产/模型操作。

### G4 — 单source owner

新真实handler combined source observation＋上层hash spy两RED，错returned ID/hash/size四反控原绿。改select/verify共用`open_verified_source`：生产reader已有`open_described_version`一次返回实际已验buffer与metadata；旧两method reader兼容。上层只比较返回ref/长度和metadata，不重SHA。不创建跨请求信任缓存，真实打开仍由原SourceVersionReader完整SHA。7P/2.27s含真实reader原件腐坏/同SHA备用路径反控。

### G3 — 已实际确认并修局部失效连带

同一html unit的已交付/尚未认证中文原文＋缺本地POS的英文goal，两顺序公有selector均0span，2RED/6.21s。现仅当已有prepared独立source support且有已验证assertion scope时，保support/relevance；语法不可用仍assessment_complete=False和原reason，原整句不改。admission不再以complete一票否决已存在support。原withheld/processing_complete链照常给partial、deferred与未知，不给unknown子句添事件/issuer/数字。

修后新2＋旧13控制15P/14.95s；其中先显式import nltk花5.415s另记，只为定位最初pytest20s临时timer停在nltk/sklearn冷import，不能代签真实90s。后加source owner原始conditional/negative/foreign actor/quoted表述四对照，新6项全6P/7.73s：known关系的activity/attribution/modality/polarity/stage与baseline完全一致，quote若保留就包含全部原限定，不切出正向短语。没有改原engine binding/语义词表。第一版replace误写dimension字段导致两个case异常的历史被后续group timeout遮蔽，已改真实role字段并留日志；未归咎于资料或放宽事实测试。

### G5 — 实际资源预算，不叠hint许可

合法native4100项、40级、长title和显式1000/900请求限额原5RED；>64已在plan内key另1RED。现去4096/32/4096、64 clamp、64 key deny与生产keys[:64]。文种/页码/父子跳级/反序/冲突仍按真实结构验证。每条真实path按实际stack长度计工，policy/windows/admission材料在同WorkBudget预扣；runtime传同一账户，不复制/重置额度。明确页/request state计数/去重/恢复不改。

完成窗口通过prepared list保留，预算停止不会清空已完成prefix；merge在独立copy上完成，途中停止不会把原window endpoint改了却留下旧key。新6P/2.00s；唯一一次geometry94项91P3F/6.64s，2F为旧‘大即坏’oracle，1F为纯组件依赖导入应沿既有layout_hints WorkBudget别名，修后仅3项3P/3.02s。另budget合并中断key仍绑定、实际SourceGeometrySession同账户、零账户在plan拷贝/验证前拒工3P/4.01s。没有再94重跑。

旧‘megabyte scope必须invalid’改为有实际预算就保完整scope，短预算则partial无伪造allocation；旧‘坏caller回执必须<16KB’改为核心错误仍rejected、原key完整而非大小许可；层级34若跳过父级仍因LEVEL_JUMP拒，连续40级则可处理。所有真正预算/未到页/同page去重/跨source/未知证据负控保留。

### G1漏consumer — 真正保存链收口

最后字面复扫发现`narrative_summary_execution._report`仍32KB，400任务假模型handler在wrap_summary里就异常，实际2RED/4.32s，不能用137任务旧局部绿代签。只改这一新增consumer，不动原21冻结文件；首次新test错误地把冻结MappingProxy直接送strict canonical_json，仍保2F/5.72s，改走公开HandlerResult.to_dict而非改产品兼容门。最终400任务真实handler→公开persisted reader完整通过，改plan SHA仍拒，2P/8.61s。

### 最终静态与边界

Ruff37文件通过，mypy25源码通过。工程没有宣称最后325/94完整重跑；所有大组仅一次、剩余失败定点复验，日志/精确XML hash见JSON。ROOT后续独审新增16项、正常commit/push/当前CI，真实H1仍原90s/16M/112。实际冷启动未做系统性能修复，也没有用预热单测冒性能结论。

原SourceGeometrySession未知导航的一份同父work allocation（1/8、原250k上限）仍是实际资源分配，不是新增许可/账；本轮未改额度。源quote恰以技术物理路径开头是否被全局path-walker误拒是静态风险，未无证扩大施工。正常metadata路径跨层、错误source/period/as-of、核心数字/币种/事件归属、未知付费恢复、真实I/O失败仍由其责任层执行。

本线源码最终STOP待ROOT独审/发布。接下来仅按ROOT要求独立只读审RF，不审自身core、不改RF代码。
