# 官方分页JSON原件与公司业务证据：共因调查及施工细则

状态：调查和方案，尚未实现；须纳入M3四审/专家归因后的同一整合节点。不能把业务JSON扮成电话会TXT绕过格式检查。

## 现场证据与现有机制

本次CN execution/research/qa-reconciliation.json记录SSE activity40766的三流：latest195条/65页、questions33条/11页、precollect29条/10页，共86页/257记录；逐流ID与页数完整，不等于同一公司的257条问答。公司投影24记录（latest8、questions15、precollect1），另231其它公司/2未归属。latest中7条回答之外的一条是另类发言，不能计作第8个回答；7回答+15未答+1预征集也不能笼统说全部记录有管理层答复。原逐页bytes/SHA、公司归属字段、JSONPointer都保留在隔离run。

例如qa-latest-form-01.raw为5119B，SHA416542b0c8f72400800edf69832df1bd3b48e50cf19c0019c647af445b97760b；/datas/0/records/1实际ID2508406，字段activityCompanyId/aactivityCompanyId57790；/datas/0/records/2实际ID2508385另有questionId/questionContent/questionDate/qactivityCompanyId。不能用观察时间替代crtTime/updTime或questionDate，更不能仅按activityId给跨公司记录都标688012。

当前official_source_flow._validate_bytes把text/plain与application/json统一调用extract_transcript_material；transcript_json_extract._record_content要求单个根content字符串，或长度恰1的单个record数组。因此合法官方datas/records分页JSON无法正常登记。此策略最初证明电话会单条JSON可回放，没有覆盖其它官方业务JSON。CodeGraph本次context只返legacy ingest，近期官方入口未被索引；依据已打开明确源文件调查，不把legacy结果当现机制。

## 分层职责和必要决策

1. 原件验证负责有界、合法UTF-8/JSON、真实响应及SHA；电话会结构资格属于对应文档parser，不应成为所有JSON的入库前提。职责分开不意味着任何错误响应都作业务原件：HTML伪JSON、空/error envelope、重复key、非标准NaN、截断、超字节/深度/节点限制须具名诊断。
2. 先检查实际SSE公开接口/UI是否提供按activityCompanyId筛选并实测有效。只有真实响应证明按公司限制才可使用，不能凭参数名猜成功、不能把本地过滤后的重序列化JSON宣称服务器原件。分页完整和公司过滤完整必须分开记。
3. 若服务只给跨公司页面，则保留一次不可变page原件；公司记录是绑定page SHA与JSONPointer/实际encoded字节范围的来源投影。不得给整页虚构单公司身份。现SourceRef单实体合同能否承载共享page及多公司投影，交专家明确设计；优先复用现source/normalized locator，不另造可变research库或重复copy原件。合同能力不足须具名说明，不能先塞入某公司raw假装解决。
4. 问题、已回答管理层发言、未回答、预征集、其它发言分别保留来源角色与关联ID；跨主体问答不能以answer公司偷改question公司。缺身份/时间或晚于as-of不自动推断；资料型内容与投资研究结论继续分层。

## TDD与实施顺序（一个大的集成节点）

1. 冻结实际上述单页反例及小型未见fixture；先RED公共import/正常read/normalize证明合法非电话会JSON被错拒，另固定原FMP单content JSON与TXT成功、原parser locator语义不变。测试资料在独立TEMP，不触生产配置/库。
2. 在CWP唯一原文入口把MIME字节合法性与document-kind parser资格拆开；如新增通用JSON读/normalize能力，显式版本化并保留旧transcript_json extractor。不关闭SourceRef字节/hash/真实身份/期间/as-of规则，也不让消费者直接读仓库目录补洞。
3. 通用JSON定位以原bytes回放：UTF-8多字节、escaped中文、换行、重复同文、斜线/波浪号JSONPointer、数组序号及字符串中的content键都要测试。不得正则扫所有content后误拼正文；display/筛选结果不是原文，保存必要小型locator/manifest而非整份第二全文。
4. SSE记录投影由有界已声明schema adapter负责：不同stream/record ID关联、明确company字段、不答问题不转成管理层承诺。实测错误主体/缺字段/重复ID/同ID不同版本/缺页/total波动/未来日期均有negative control；稳定页序与selected QA逐项可回放。不是针对688012或57790硬编码。
5. 既有AUTO选择/摘要以正确SourceRef+locator消费高价值业务发言；财务口径/未答限制不抹去，旧半份结果不发布成功。有限scope/profile按当前配置，重复同页/同策略新AUTO证明零下载/零模型/零新reservation；配置策略改变仅影响应重算派生，原bytes复用。
6. 集中验证公共capture/import→source projection→normalize/select→summary→RF真实消费→同规格复用与失败恢复。首先离线loopback小样本，随后真实SSE当前原页，以及未见另一公司/另一官方JSON布局；不凭合成绿声称全部provider可用。
7. 恢复自己TEMP，原真实页/SHA与旧失败/费用留存；selected责任短测进既有共享push/CI，整批分页/付费/长矩阵只在本节点。一次独立完整审查及正常commit/push/安装交接，不增加每页审批、身份签收或第二账本。

## 验收与非验收

公共消费者可读取合法原页，并获得正确公司业务投影；每精选文本都能回放到实际SHA/locator，跨公司/未答/未来信息不污染预测事实，原件只保存一次。原ET/FMP电话会JSON和旧版本回放不退步，字节/时间/空间上限与费用未知仍如实留账。仅修好JSON入口不等于本次全部问答已被RF正确采用，也不等于买方预测模型已成熟；四路原finding继续逐项核验。
