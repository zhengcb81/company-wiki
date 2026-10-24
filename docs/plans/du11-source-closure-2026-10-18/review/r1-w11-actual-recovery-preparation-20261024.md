# W11 实际来源恢复：只读准备（2026-10-24）

下一步应先用现有 **official capture 做一次1MiB/20秒/零新增费用的有界GET并正式保存HTML**，再对同一SourceRef字节运行本地pages发现。**不要先重跑discover urls**：该分支仍只返回候选/响应hash，不持久保存正文，无法补上旧缺口。当前源码SHA已实核为`6869349b…`（ROOT已发布1be42a76）；本准备没有联网或执行生产脚本。

## 旧事实与不可重放边界

- 原始/最终URL：`https://www.wuxiapptec.cn/investors/announcement/ir-material`。CWP既有身份收据确认药明康德/CN/SSE/603259，org_id9900035584；不重新建身份库。
- 原请求窗口：2026-01-01至**2026-10-21 as-of**、30items、1048576B、20s。索引自身不是财报期间，发布日期/period/fiscal_year未知。取回时间不得冒充材料发布日期；新取回快照也不能充2026-10-21当时网页。
- 真实HTTP200发生于2026-10-22T19:39:09.041249至19:39:16.413958Z；receipt记录486789B、SHA`f1e822a8067c0b8eb7fc6376d8e1491acfa1ae3b60ce605db90c06326603396e`。旧结果为三个privacy/terms lead、partial，不是取得IR原件。
- 实存的是`C:\Users\郑曾波\Projects\revenue-forecast-audit\runs\r1-20261021-cn-wuxi-apptec\execution_replays\r1-remediation-01\roles\executor\commands\faa5bf2650964e9480566759c565ce11`下250B input/consume（SHA9c235138…）和2839B stdout（SHA1c33f18b…）；母INPUTS的W11十一项本次大小/SHA全部匹配。
- 486789B HTML正文仍据作者有界inventory为absent_body。本次没有重复深扫：既有检查仅覆盖该audit run与CWP隔离湖，分别2052/65文件；不能扩大为全盘不存在。旧body hash/response ID绝不等于已保存正文，也不能从三个候选复原网页。作者evidence_inventory与root_followup保持只读。

## 当前隔离位置

继续使用既有隔离store，不创建第二库：

- wiki：`C:\Users\郑曾波\Projects\company-wiki\.planning\shared-reading-production\r1-holdout-20261021\CN-603259\wiki`
- catalog：`C:\Users\郑曾波\Projects\company-wiki\.planning\shared-reading-production\r1-holdout-20261021\CN-603259\wiki\.source_catalog`，实际DB为`catalog.sqlite3`，当前WAL存在；本次只看文件元数据，未打开DB。
- raw公司目录：`C:\Users\郑曾波\Projects\company-wiki\.planning\shared-reading-production\r1-holdout-20261021\CN-603259\wiki\companies`（holdout_raw可写）。生产companies/Dayu/Dropbox/future_lake为只读复用根。
- 显式catalog config：`C:\Users\郑曾波\Projects\company-wiki\.planning\shared-reading-production\r1-holdout-20261021\CN-603259\wiki\config\source_catalog.yaml`，SHA482ee2f6…；FF/RF连接`C:\Users\郑曾波\Projects\company-wiki\.planning\shared-reading-production\r1-holdout-20261021\CN-603259\wiki\company_wiki.json`，SHAb32bc38b…。
- **本次待建的新收据目录**：`C:\Users\郑曾波\Projects\revenue-forecast-audit\runs\r1-20261021-cn-wuxi-apptec\execution_replays\r1-remediation-02\w11-actual-20261024`，本次核对不存在；只把新request/response/locator放这里，旧initial639、final3和原manifest不增补回写。原始字节由storage在上述既有隔离湖落位。

当前有效scope：`execution_replays/r1-remediation-02/coordinator-effective-scope-budget-20261023.json`（SHA77c6af8c…），不是旧scope中的2M。当前配置累计10M tokens/USD20，公司150k/USD1仅软目标，unknown不释放。外层 acquisition为50MiB/180s/0费；本次建议更小1MiB/20s/0费。capture自身上限128MiB/300s，discover上限6页/30items/8MiB/120s，均不应当作本次放大量。

## ROOT 最小执行

本MD配套JSON内有**可直接写出的完整capture请求**`recommended_capture_request`和argv。它只填已知entity/官方URL，period/date均null、language unknown、title仅为请求描述；不填旧expected_content_sha256（新页面可更新）。ROOT把它写入新attempt的requests/capture-index.json，沿现有execution_request/capture记录实际请求字节、stdout/stderr和exit，不另造批准/任务状态。

```powershell
$w11Python = 'C:/Users/郑曾波/Projects/company-wiki/.venv/Scripts/python.exe'
$w11Wiki = 'C:/Users/郑曾波/Projects/company-wiki/.planning/shared-reading-production/r1-holdout-20261021/CN-603259/wiki'
$w11Attempt = 'C:/Users/郑曾波/Projects/revenue-forecast-audit/runs/r1-20261021-cn-wuxi-apptec/execution_replays/r1-remediation-02/w11-actual-20261024'
$env:PYTHONPATH = 'C:/Users/郑曾波/Projects/company-wiki/src'
& $w11Python -X utf8 -B -m company_wiki.source_catalog.official_source_cli --config "$w11Wiki/config/source_catalog.yaml" --project-root $w11Wiki --operation capture --request "$w11Attempt/requests/capture-index.json"
```

一次capture会由既有AcquisitionBudget+BudgetedAsyncHTTPTransport计时/计字节（最多5重定向、0自动重试）、persist原始响应与capture observation，再经CanonicalSourceWriter入库、返回SourceRef2.0和manifest。**capture成功即已正式入库，不要再重复import同一body**。记录新的实际SHA/size/effectiveURL、HTTP/wire usage及source_id，允许新SHA与旧hash不同；旧版本缺失仍不补写成重放成功。若HTTP/编码/MIME/登记失败，保留实际失败/capture_id，按现有recover查询；不盲重GET。当前HTML入库校验是UTF8，若非UTF8拒绝，保留原字节诊断，不能转码原件强行入库。

随后生成`official-source-read-request/1`（`source_ref`完全取capture返回值），使用同一CLI `--operation read`。**stdout必须用Python subprocess.run(stdout=以wb打开的文件)**保存至`work/ir-index.html`，避免PowerShell文本重编码。重计工作副本SHA/size，须等于返回SourceRef；原件仍留storage。

生成本地discover请求：schema official-discovery-request/1，entity药明康德，start_date2026-01-01，as_of_date2026-10-21，max_items30，max_bytes1048576；pages只含该工作副本绝对路径、原官方URL、text/html与真实capture_id。再执行：

```powershell
& $w11Python -X utf8 -B -m company_wiki.source_catalog.official_source_cli --operation discover --request "$w11Attempt/requests/discover-pages.json"
```

该步骤0网络，结果放receipts/index-discovery.json。未知/坏内嵌文档和动态内容继续partial。若只看到静态导航，没有可得业务lead，就交付明确external_limit与触发条件；不猜PDF地址，不执行JS，不进入无限重试。H1deck/JPM/专门IR活动线索见旧web_discovery.json的8条查询和nativeIDs，尚不是可离线读取正文或确定原件URL。

## 原件 → FF/RF正式消费

1. 只对实际业务lead逐一capture/import，先核真正发行人、材料自身日期/期间、标题/正文及as-of；date_unknown不得用抓取日补。Deck/event notice不充Q&A正文。已有本地真实原件才走import，附实际SHA与capture receipt；新GET走capture，均由CWP统一保存。
2. **定期财报**：RF当前`scripts/source_preparation.py --request-file … --company-wiki-config <隔离wiki>/company_wiki.json --company-wiki-catalog-config <隔离wiki>/config/source_catalog.yaml --filing-fetch-root C:/Users/郑曾波/Projects/filing-fetch --result-envelope`，请求schema2.0、company_query药明康德、确切document_kind/FY/as-of、filing_intent=reuse_only。其真实链是FF source_candidate→同库verified raw open→RevenueSourceRecord/reuse receipt；只复用，不再下载。
3. **已登记的非财务IR/deck/Q&A原件**：用RF正式owner `source_preparation.prepare_registered_source_result(candidate, as_of_date=…, company_wiki_catalog_config=…, source_reader_receipt_version='2.2')`。candidate来自实际CWP SourceRef及同manifest事实；该入口明确不要求FF把非财务资料伪装成财报、也不发明FY。当前普通source_preparation CLI没有registered模式旗标，不能编造CLI参数；由ROOT现有执行器调用该公开API并封存真实结果。
4. 正式摘要/原语言问答沿当前CWP AUTO与public narrative-read引用，由RF source_preparation实际读取；本恢复准备不启动模型。保留prepared/read/use各真实收据、source_id+locator+parser/version/quality，再重建逐材料矩阵。取得索引或SourceRef metadata不等于材料已读，更不等于W12公司四审通过。

## 本次操作范围

只读了已知元数据/代码、W11输入/交付与现有配置；0网络、0下载、0provider/LLM、0原件正文/PDF/密钥读取、0DB打开/写入、0Git操作、0作者/生产脚本执行、0新scratch。仅写本MD/JSON。未重扫全盘、未改initial639/final3、原件/库/配置/作者工区；没有新增许可、签收、身份库或任务库。
