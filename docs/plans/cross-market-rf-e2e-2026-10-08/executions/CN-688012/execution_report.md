# 中微公司 CN-688012：真实RF全流程执行交接

状态：**执行完成，等待全新独立审查；执行者没有自验收。**

## 可复核产物

正式研究文件只在独立 TEMP：`input.json`、`forecast.json`、`forecast.md`、`snapshot_v2.json`；精确绝对路径和全部SHA在manifest。CWP内仅工程日志、来源/事实核对、施工脚本和交接材料。

最新版为`2026-10-08-cn688012-v2`，信息日2026-10-08；CNY百万元；FY2025基年及2026–28三情景。正式预测数字仅以已验证JSON及其引擎渲染Markdown为准，此工程文档不形成第二套正式研究状态。

## 实际数据链

1. 实读RF/FF技能及必需引用，先真实`source_preparation`，由它调用FF和CWP。早期schema2封装、原retrieved_at未知和HTTPURL导致失败，完整stderr保留，MAIN修复runtime并定点安装后年度链跑通。
2. 2025年报原件本地复用。原HTTP地址通过同一官方HTTPS实际GET、SHA和长度相同，随后标准CWPsource-facts只更正source_url。原retrieval未知仍null，没有补造原始采集时间。
3. 初始2026H1不在本地。真实官方category对比发现SID半年度错误使用年度分类；Q1/Q3错误分类也得到实证。MAIN按职责修复后重跑RF→FF→CWP，SID真正downloaded_new，原件进入CWP。
4. 新H1官方epoch转CST是8/20，原UTC处理错误提前至8/19。MAIN修复provider；标准producer事实更正只登记published_date，旧下载receipt/acqsidecar保留。相同RF请求0下载复用、SHA相同，当前verifiedrawmanifest8/20正确。
5. SourceRefv2携带ID/SHA/bytes、不携带底层路径；CWP实读验真原件。确定性PyMuPDF页级提取仅在TEMP，259年报页和210半年页。**没有调用生产CWPWorker或假装已完成模型摘要；reuse_receipt中的parser/LLMcounts为null，不冒称0。**
6. 完整核对年报收入、产销量、折扣、集中度和收入确认；H1实际收入、产品验证、收购购买日/并表贡献、年度卖方承诺。FY2024完整年报查找not_found；历史比较数确实在2025年报，未假装读2024独立报告。
7. 上证官方9/10路演真实页面打开，公共API返回全部195互动回复；公司名+companyId+688012logo核得8条本公司内容；另按10页补齐29预征集，其中1条本公司答复。主持人/其他公司不归为中微。官方容量/海外交付/供应链答复纳入v2，只支持机制；厂房面积不是腔数，累计交付不是当年收入。原问句中的传闻不作为管理层事实。
8. 官方CNINFO在8/20至10/8返回全部19公告标题。标题只作发现：募投延期/基金公告正文未完整取得，保留gap。八月IR-DOCX仅有二手线索，没有当成官方已核事实。
9. SEMI7/14官方原文由web.run实际打开，保存的是完整返回解析文本而非声称完整HTML。行业WFE三年基准及中国增速放缓为独立外部参考，不能机械替换本公司增长。

## 模型与经济限制

- 三曲线互斥：原有设备与原有备件/服务残差均排除新CMP；CMP为购买日后100%并表收入，不乘所购股权比例。
- 设备用unit_sales，但2025加权收入/销售腔数只是代理，未证明等于每一台验收设备收入；缺少逐SKU价格及确认率，未来量价均为analyst_assumption。
- 残差使用已确认混合收入direct_revenue；拆成设备/备件PIT与服务成本进度完整policyclaims，明确aggregation_boundary，不虚构服务金额和进度再扣一次。
- CMPFY2025增量0是analyst_assumption的并表边界判断，不是CMP自身历史收入披露为0。2026卖方全年承诺与部分年度并表不同，显著mismatch；2027/28独立基准不强迫Base达标。
- 管理经营计划不冒充收入承诺。九维/完整证据表能验证工作链，不能证明经济预测正确；没有SKU、产能硬上限、客户未来资本开支和长周期历史，模型经济校准仍有限。
- 三情景不赋概率；置信度是引擎流程/证据分数，不能解释成Base实现概率。无未来实际业绩，回测evaluate不适用。

## 大节点实际验收

v2 template→fill→lint→hash check→validate-only verbose→formalengine→strong original-input validator→字节完全相同render→三情景逐年独立量价/残差/CMP加总、增长、CAGR→write-once snapshot全部绿。`formal_verification_receipt.json`绑定实际产物SHA。

Publication registry仅本公司TEMP/publications.jsonl，未写安装目录或共享研究状态；attestation真实unattested，不造签名。v1正式输入/结果/快照保存于TEMP/v1，原snapshot.json未改；新IRfacts只绑定v2，未挂到旧快照。

## 审查与清理

独立审查必须逐条检查facts/parameter_inventory、声明/原文/目标单位、request→process→response→raw→claim→parameter→result，以及模型范围和漏项。先按runtime_and_configuration.json恢复隔离环境再复跑verify_formal.py；不能将执行者PASS当独立通过。

日志时间与部分早期web精确时间不齐：其原工具IDs/返回快照均保留，events补记明确retrospective和原精确时间未知，不捏造时刻。早期trace尚未启用时由run_logged完整命令stdout/stderr覆盖；后续processes是真正嵌套子进程。

没有付费provider或外部LLMAPI调用。所有真实网络请求有界；原件大小远低40MiB。独立审查前保留TEMP证据和工程日志；MAIN验收后按manifest.owned_cleanup删除本批临时原文副本/解析文本/公共脚本，原CWP原件保留。此执行者创建的临时路演标签已关闭。
