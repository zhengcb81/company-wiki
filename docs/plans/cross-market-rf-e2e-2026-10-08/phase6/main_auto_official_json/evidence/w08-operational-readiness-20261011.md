# W08 可执行入口与输入绑定（只读准备，2026-10-11）

状态：**OPERATIONAL_PREPARATION_ONLY**。承接同目录 `w08-readiness-20261011.md`（SHA050b43b6087bb49a6e624d4e2b6ccbae8ef0b450173f53996192380ac86f8f06）和既有 W08/MAJOR_NODE。未调用下面任何业务入口，没有新下载/模型、没有改源码/安装/配置/原件/数据库。只读刷新六个明确 AUTO 账本并新增独立 budget receipt。下一真实研究始终原三家公司、as-of2026-10-08；CN/HK2026–2028，US2027–2029。

## 1. 工程发布与真实研究分别记状态

当前父线程确认：canonical 本地已正常fast-forward至 `1415e314` 且clean；远端仍是 `accdeccc737ccaf27d1698238a31af022960a3fa`。normal pre-push实际3137 PASS/7 FAIL，测试197.27s（全程203.31s）阻止了push；其中纯0.7套话/邻接5项由内部owner修复，另2责任测试已强化并20 PASS。W03公共3项和独立审本身通过，但不足以签整发布。P7-RF本地/远端47f497ad、CI38096229764 success和下表安装绑定仍成立。**不能用 accdeccc 的旧CI证明1415e314或今天0.7接线已远端发布，也不能把工程节点签成三家研究结果通过。** 下一真实节点由ROOT完成正常发布后，重新冻结实际CWP源码、installed/config/version/generation；本文件不承诺未发布源码已可用。

本次只检查三个实际 installed 入口（CRLF归一后与各仓源码一致，不是整技能安装审计）：

| 已有文件 | 本次原字节 SHA256 |
|---|---|
| `.agents/skills/revenue-forecast/scripts/source_preparation.py` | e8db267971f5c967ab6cd8e358e23423afe42f7af8ce19847be7b266cc00742d |
| `.agents/skills/revenue-forecast/scripts/filing_fetch_client.py` | 7f730131f4bad0e22e3e43b0ffac48475dd1c373a4bc8dec40ad21a6b8a1341b |
| `.agents/skills/filing-fetch/scripts/fetch_filing.py` | 6b12ee17ab2a01f1292eacf3598177ca959d2f5ab306c44b772abec6a648d12c |

三个路径的共同绝对前缀 `C:/Users/郑曾波/`。RF原M3旧 `runtime_observation.json` 是2026-10-09证据，不能代替本轮实际entry snapshot。未改Git或安装。

## 2. 固定已有根、参数位置与配置职责

已存在的来源隔离环境（本轮仅只读确认）：

`C:/Users/郑曾波/AppData/Local/Temp/mFresh-me8cejn4/{CN-688012,HK-00700,US-MSFT}/`

每个公司目录的这些文件实际存在：`config/source_catalog.yaml`、`config/filing_fetch_company_wiki.json`、`config/source_acquisition.yaml`、`config/local_ocr.json`。FF config1.0 `company_wiki_root` 指向其公司隔离根；它控制 catalog/config/状态地址，**不是源码地址**。RF链真实调用：installed source_preparation → installed filing_fetch_client → 通过显式 `--filing-fetch-root` 的 installed FF `scripts/fetch_filing.py` → `python -m company_wiki.source_catalog.cli/source_query_cli`。继承的 PYTHONPATH 决定 CWP 模块实际源码；不能以空隔离根里不存在 scripts/source_catalog_cli.py 断言工具缺失。

原catalog roots已有company写根，以及既存CWP公司/Dayu portfolio/Dropbox只读来源根。acquisition已有CN StockInfoDLSimple/v2-clean-rewrite、HK/US外部Dayu + CWP的 `tools/dayu_sdk_bridge.py`；Dayu本身无代码变更。ET实际工具根 `C:/Users/郑曾波/Projects/earnings-transcripts/earnings-transcripts/transcript_tool.py`。这些 provider 只在有真实 missing intent 时执行；本次没有启动它们。

下一执行者的基础变量示例（**仅命令说明，本次未运行**）：

```powershell
$w08Python = 'C:/Miniconda/python.exe'
$w08CwpCode = 'C:/Users/郑曾波/Projects/company-wiki'
$w08Sources = 'C:/Users/郑曾波/AppData/Local/Temp/mFresh-me8cejn4'
$w08Rf = 'C:/Users/郑曾波/.agents/skills/revenue-forecast'
$w08Ff = 'C:/Users/郑曾波/.agents/skills/filing-fetch'
$w08Runs = 'C:/Users/郑曾波/Projects/revenue-forecast-audit/runs'
$env:PYTHONUTF8 = '1'
$env:PYTHONDONTWRITEBYTECODE = '1'
$env:PYTHONPATH = "$w08CwpCode/src"
```

`$w08CwpCode` 只有 ROOT 发布后再固定；不得悄悄指仍过渡的隔离源码。新AUTO/work/request/log必须使用本次新 owned attempt 子目录，保留旧 M3 `m3/20261009T184946/auto/narrative.sqlite3`。若 ROOT 另建全新来源catalog，应通过公开接口导入已存原件并将以下 company config 变量替换成新scope真实路径；不得直接复制全湖、生产DB或默认重下。

## 3. RF 正式 source_preparation：确切CLI与已有请求

真实 CLI 来自 installed 源码 `main`：

- `--request-file`：请求 JSON（没有该参数则stdin）；公司/market/kind/期次/as-of在该JSON，**不存在 --company/--as-of/--fiscal-year 这些source_preparation CLI参数**。
- `--result-envelope`：保留FF结果和narrative sidecar；`--company-wiki-catalog-config`、`--company-wiki-config`、`--filing-fetch-root`；`--timeout-seconds`。
- `--source-reader-receipt-version` 可2.1/2.2，默认2.1；本轮沿既有默认，不用2.2替代缺失出版事实。
- `--allow-download` 是兼容参数；FF2.0的请求意图是实际下载授权。下面 reuse_only 不传它。
- `--source-reader-v2` 是已失效的compatibility no-op，不重复加；`--narrative-request-file` 仅读取已存在的显式narrative请求，不自动启动模型。

**下面三份请求文件都已经存在，且无 companion/provider新取动作：**

| 公司 | 现成路径（以下路径相对 `$w08Runs`） | 实际请求 |
|---|---|---|
| CN | `m3-20261009T184946-cn-688012/roles/executor/commands/4aa57e402fb14d5e99de71a0ebbcd127/input-0001-044fec139857.json` | 2.0 /688012/CN/semi_annual_report/exact/2026/H1/asof10-08/reuse_only |
| HK | `m3-20261009T184946-hk-00700/roles/executor/commands/92667a62c4b4440ba43ff1b1b354c981/input-0001-decbab8aed1f.json` | 2.0 /00700/HK/semi_annual_report/exact/2026/H1/asof10-08/reuse_only |
| US | `m3-20261009T184946-us-msft/roles/executor/commands/31b3707473954d698b37eae2f4f4b88a/input-0001-dea372322f9a.json` | 2.0 /MSFT/US/regulatory_filing/exact/2026/Q3/form10-Q/asof10-08/reuse_only |

以下命令已按真实参数和现存路径拼好，可作为第一组复用链（业务结果必须真实记录，不能预称success）：

```powershell
& $w08Python -B "$w08Rf/scripts/source_preparation.py" --request-file "$w08Runs/m3-20261009T184946-cn-688012/roles/executor/commands/4aa57e402fb14d5e99de71a0ebbcd127/input-0001-044fec139857.json" --result-envelope --company-wiki-catalog-config "$w08Sources/CN-688012/config/source_catalog.yaml" --company-wiki-config "$w08Sources/CN-688012/config/filing_fetch_company_wiki.json" --filing-fetch-root $w08Ff --timeout-seconds 180
& $w08Python -B "$w08Rf/scripts/source_preparation.py" --request-file "$w08Runs/m3-20261009T184946-hk-00700/roles/executor/commands/92667a62c4b4440ba43ff1b1b354c981/input-0001-decbab8aed1f.json" --result-envelope --company-wiki-catalog-config "$w08Sources/HK-00700/config/source_catalog.yaml" --company-wiki-config "$w08Sources/HK-00700/config/filing_fetch_company_wiki.json" --filing-fetch-root $w08Ff --timeout-seconds 180
& $w08Python -B "$w08Rf/scripts/source_preparation.py" --request-file "$w08Runs/m3-20261009T184946-us-msft/roles/executor/commands/31b3707473954d698b37eae2f4f4b88a/input-0001-dea372322f9a.json" --result-envelope --company-wiki-catalog-config "$w08Sources/US-MSFT/config/source_catalog.yaml" --company-wiki-config "$w08Sources/US-MSFT/config/filing_fetch_company_wiki.json" --filing-fetch-root $w08Ff --timeout-seconds 180
```

它们只是每公司一份示范，不代替完整资料集。现成CN最终IPO请求：`...cn.../roles/executor/commands/32daaa62177e4c11b38e6d44668a4f7a/input-0001-9b8a9cf8a08f.json`（2019/prospectus/reuse_only）；现成HK supplement精确请求：`...hk.../roles/executor/commands/0b7e63c267ca45249e400151d1b8cca8/input-0001-9c34c43ea790.json`（prospectus/2026/provider_document_id=980c2b43…/reuse_only）。后者分类是实际旧请求，不据“债券补充”改写成另一个不存在的参数。

**MSFT FY26年报已有原件，旧first-fetch输入不可原样复跑：** `...us.../roles/executor/commands/3b1bbb24f02b4cbcac143a016869df71/input-0001-1c8765f6f009.json` 包含fetch_if_missing和FMP companion；新的owned请求应只复用年报，不重试已知entitlement。可直接写入新owned请求的精确JSON如下（本次未创建这个文件）：

```json
{"schema_version":"2.0","company_query":"MSFT","market":"US","document_kind":"annual_report","mode":"exact","fiscal_year":2026,"form_type":"10-K","as_of_date":"2026-10-08","filing_intent":"reuse_only"}
```

同理CN/HK年报与IR按 `execution/source_ledger.json` 的真实Ref/kind/date选择，不因为production未indexed或retired猜缺原件。已存官方HTML call独立复用；不把它标成FMP/ET取得。

## 4. SSE86页：existing inputs与可执行 public CLI

**真正已存在的输入**：

- manifest/reconciliation：`$w08Runs/m3-20261009T184946-cn-688012/execution/research/qa-reconciliation.json`；streams latest65/questions11/precollect10，共86页668,749B。
- 原字节：同run `execution/sources/qa-*-form-*.raw`，按reconciliation的每一行确切path/SHA/bytes，不靠glob把失败JSON也吞入。
- 原捕获receipt：`execution/sources/qa-first-form-receipts.json`（3条）、`qa-remaining-receipts.json`（83条）、`qa-missing-one-receipts.json`（1条重复补抓观察）；按path+SHA+实际响应匹配。不要把旧 `qa-first-receipts.json` 三个错误页当form成功页。
- layout ID：当前真实注册值 **official-paged-qa**，collection `/datas/0/records`；不是SSE公司特判。
- issuer匹配来源：activityId40766；中微provider_activity_company_id57790、precollect provider_company_id145565、security_id688012。ID/字段类型和不同stream语义来自 DATA_CONTRACT/真实record；不要猜其它公司的identity。

**尚未存在的执行输入**：86份official-source-import-request/2、3份project请求、project返回的SourceRef/projectionID和新request2。下一ownedscope需要生成；当前不能声称“路径已准备/SourceRef已取得”。构造规则及真实 CLI：

```json
{
  "schema_version":"official-source-import-request/2",
  "request_id":"<本次真实local import操作ID>",
  "max_bytes":<reconciliation该页真实bytes>,
  "content_sha256":"<该页真实sealed SHA>",
  "expected_content_sha256":"<同一SHA>",
  "mime_type":"application/json",
  "document_kind":"investor_relations",
  "source_subject":{"kind":"multi_issuer_event","event_namespace":"roadshow.sseinfo.com","event_id":"40766","issuer_refs":[],"attribution_status":"partial"},
  "capture_receipt":{
    "capture_method":"local_document",
    "tool_name":"company-wiki-official-source-import",
    "tool_call_id":"<本次真实local import操作ID>",
    "captured_at":"<实际本次读入UTC时间>",
    "response_bytes":<该页真实bytes>,
    "content_sha256":"<同一SHA>",
    "http_requests":0,
    "original_capture_observation":<原receipt对应条目的完整非秘密观察>
  }
}
```

这是本次local import事件，不假造新HTTP成功/网络call ID；旧POST/表单/URL/HTTP200/content_type/started_at/finished_at留 `original_capture_observation`，只取得旧response观察，并不把请求DTO冒充socket wire bytes。receipt要求UTC-aware时刻、最大16,384B；该shape是当前validator允许的扩展，真正public import验 bytes和layout；不新增schema/许可。若直接沿用原capture事件则必须能提供其真实tool identity/时刻，不补造。

操作命令参数（请求和输出名由ROOT新owned目录生成后方可执行）：

```powershell
$w08CnRoot = "$w08Sources/CN-688012"
$w08CnCatalog = "$w08CnRoot/config/source_catalog.yaml"
& $w08Python -B -m company_wiki.source_catalog.cli official --config $w08CnCatalog --project-root $w08CnRoot --operation import --request '<本次owned/import/<页名>.json>' --input-file '<reconciliation该页已存在绝对raw路径>'
```

三流各一次project，分别含真实成功import返回的65/11/10个Ref（不是旧raw路径/虚构Ref）。精确project payload：

```json
{"schema_version":"official-json-projection-request/1","parent_source_refs":["<实际Ref2 objects，非字符串占位>"],"layout_id":"official-paged-qa","issuer":{"market":"CN","security_id":"688012","provider_activity_company_id":57790,"provider_company_id":145565},"as_of_date":"2026-10-08","projection_version":"1.0.2","persist":true}
```

上面的parent array只是说明实际object位置，不能把占位文本交给CLI。正式65/11/10 Ref JSON来自import stdout的`source_ref`字段；3份请求分别命名 `project-latest.json/project-questions.json/project-precollect.json`。明确使用1.0.2，不能将默认1.0.1历史顺序语义重标。

```powershell
& $w08Python -B -m company_wiki.source_catalog.cli official --config $w08CnCatalog --project-root $w08CnRoot --operation project --request '<本次owned/project-latest.json>'
& $w08Python -B -m company_wiki.source_catalog.cli official --config $w08CnCatalog --project-root $w08CnRoot --operation project --request '<本次owned/project-questions.json>'
& $w08Python -B -m company_wiki.source_catalog.cli official --config $w08CnCatalog --project-root $w08CnRoot --operation project --request '<本次owned/project-precollect.json>'
```

接着 replay 请求 `{"schema_version":"official-json-replay-request/1","projection_id":"<实际返回>"}` / export请求 `{"schema_version":"source-projection-export-request/1","projection_id":"<同一个实际ID>"}`，参数 `--operation replay/export --request <owned JSON>`。原件二进制公开read是 `--operation read` + `official-source-read-request/1`/真实source_ref；stdout是bytes，不用文本capture存正文。

**具体provenance注意点**：当前 `official_json_import._commit_shared` canonical source_url固定 `https://official.invalid/shared-json`。真实原HTTP URL只在保留capture observation；placeholder不等于 primary URL，更不能直接放进RF研究事实。public export必须保真实parent+capture关联；若RF具体输入需要primary URL，取真实capture observation的原URL并绑定同页/receipt，或明确该接口待接，不捏造URL。本准备不改writer或签该研究集成完成。

完整中微24record覆盖、86父页coverage和partial/角色语义仍在真实大节点核；不能为覆盖QA编号全送模型。17命中页只是已有最小调试子集，不称全stream coverage。问题/回答原locator分别保留，2508385确在latest18不是latest01。

## 5. 配置模型/预算与request2入口

真正入口 `C:/Users/郑曾波/Projects/company-wiki/scripts/narrative_batch_configured.py`，CLI额外参数只有 `--llm-config`、`--llm-provider`（minimax/mimo/deepseek/openai）、工程loopback专用`--allow-local-model-http`；余下传public narrative_batch_cli：**必须** `--project-root/--catalog-config/--automation-db/--work-dir/--request`。

当前生产YAML的非秘密声明只按白名单读取，未调用Config.load、未取环境密钥：primary minimax/MiniMax-M3/https://api.minimaxi.com/v1/8192/temperature1/reasoning_split=true；fallback mimo/mimo-v2.6-flash/https://token-plan-cn.xiaomimimo.com/v1/enabled/general。Config已有第三profile defaults为deepseek-flash/https://api.deepseek.com，显式 `--llm-provider deepseek` 沿该loader选择并继承generation settings；不是把request里临时捏造的endpoint盖上去。原M3三家实际用该DeepSeek profile，建议修后对照仍显式它；MiMo/其它profile如由ROOT选择，用其真实既有pricing/generation，不复制DeepSeek代理价格到其它供应商。

wrapper从 `Config.load(...).llm` 构造options，覆盖request中的model选型，只保留request自己的timeout/max_request_bytes/max_response_bytes。因此request2只填这些transport caps即可；不要放另一个竞争的model/endpoint。真正Config.load在将来执行时加载credentials；本次没有访问dotenv/环境凭证，也未探测key是否存在。

新 finite request2 必填：`schema_version/run_id/items/profile/max_seconds/max_tokens/max_cost_usd/model/pricing`，可选`refresh/max_final_bytes/max_persistent_bytes/max_scratch_bytes`。items精确只允许：

```json
{"kind":"raw","source_ref":<真实SourceRef2 object>}
{"kind":"official_json","projection_id":"<真实返回ID>","projection_sha256":"<真实返回SHA>"}
```

item_key由生产DTO自动导出，**请求item不加item_key、subject_binding或source_ref假anchor**。最多100items；投影ID必须 `urn:company-wiki:source-projection:sha256:<SHA>`，不可猜。旧request1仍可用，但SSE必须新2；v2输出items/ref2，raw输出完整ref1。

request2的有限设置模板（profile沿原P1；ROOT为本次fresh单轮在现有母账真实剩余中分配每公司不超过120,000 tokens/$2，再与实际配置/运行限额取更小值；历史公司scope残额不是新的永久公司限额）：

```json
{
  "schema_version":"narrative-batch-request/2",
  "run_id":"<新真实attempt，非旧M3 ID>",
  "items":[<上述真实raw/projection items>],
  "profile":"P1",
  "max_seconds":900,
  "max_tokens":<本次单轮分配与当前母账及配置的更小上限>,
  "max_cost_usd":"<本次单轮分配与当前母账及配置的更小USD上限>",
  "model":{"timeout_seconds":60,"max_request_bytes":262144,"max_response_bytes":262144},
  "pricing":{"version":"deepseek-cn-full-peak-fx-floor6-proxy-2026-10-06","input_micro_usd_per_million_tokens":333334,"output_micro_usd_per_million_tokens":1333334},
  "refresh":false,
  "max_final_bytes":2097152,
  "max_persistent_bytes":33554432,
  "max_scratch_bytes":67108864
}
```

这段用于configured wrapper，不能绕它直接调用缺model选型的bareCLI。价格是原M3实际版本化保守估算，非现金发票；本文件未联网重查、不改价。existing generation_policy照读，0.7策略真实升级后新generation可需要模型，旧0.6不得当新缓存或伪resume。范例命令：

```powershell
& $w08Python -B "$w08CwpCode/scripts/narrative_batch_configured.py" --llm-config "$w08CwpCode/config.yaml" --llm-provider deepseek --project-root "$w08Sources/CN-688012" --catalog-config "$w08Sources/CN-688012/config/source_catalog.yaml" --automation-db '<本次owned/CN/auto/narrative.sqlite3>' --work-dir '<本次owned/CN/work>' --request '<本次owned/CN/narrative-request2.json>'
```

HK/US逐项换成相应真实root/catalog及独占AUTO/work/request路径，不能三个进程复用同一work目录。实际每missingitem一次POST，同run恢复零新费用；同generation另run精确reuse再读verify/ref。failure-final/partial/unknown照实保留，8192截断不提高caps或当success。source_preparation不会启动这个模型入口，真正调用记录必须分别保存。

## 6. 母预算：具体原生路径、去重与剩余值来源

本次只读刷新：[w08-budget-refresh-20261011.json](w08-budget-refresh-20261011.json)，SHA `8f55e362b681df1358bcf16c060fef10e8e2b725f38eb6ab7936094d23bf7186`。实际 `sqlite3.connect(path.as_uri()+'?mode=ro',uri=True)` + `PRAGMA query_only=ON`，不调用会初始化/migrate的NarrativeRunStore构造，不SQL变更、settle或复制DB。仅下表六库 `narrative_model_reservations` 的9个非秘密scalar字段；17unique attempt均known，新unknown/reserved0。

所有DB的绝对前缀 `$w08Sources`：

| 精确路径 | known tokens / microUSD |
|---|---:|
| CN-688012/auto/narrative.sqlite3 | 17,333 /18,817 |
| HK-00700/auto/narrative.sqlite3 | 7,134 /7,347 |
| US-MSFT/auto/narrative.sqlite3 | 5,105 /5,730 |
| CN-688012/m3/20261009T184946/auto/narrative.sqlite3 | 35,713 /35,802 |
| HK-00700/m3/20261009T184946/auto/narrative.sqlite3 | 24,249 /25,308 |
| US-MSFT/m3/20261009T184946/auto/narrative.sqlite3 | 35,439 /38,015 |

去重用actual attempt_id；同attempt不同字段拒绝算术。known按input_tokens+output_tokens/estimated_micro_usd；unknown/reserved按input_tokens_bound+max_output_tokens/reserved_micro_usd保守hold，不取0。不会按responsehash/sourceSHA去重不同付费attempt。cache-new-auto的零jobs/reservations不能当又一负收费或重复扣除。

**母链已有路径**（共同前缀 `C:/Users/郑曾波/Projects/company-wiki/docs/plans/cross-market-rf-e2e-2026-10-08/phase6/`）：

1. `main_budget_preparation.json`：baseline207,042 tokens/119,671microUSD；包含旧unknownhold，OCR known7,508/8,934已在该数，不能再加。
2. `fresh_executor_launch/launched/budget_observation.json`：加fresh六库中第一代29,572/31,894后的236,614/151,565。
3. `m3_source_research_2026-10-09/budget_observation.json`：18:40启动前snapshot，与2同数。
4. MAJOR_NODE后M3第二代已实际95,401/99,125（本次native刷新吻合）；相加 conservative charged332,015/250,690。**这些charged数含保守unknown预留，不应称全部known实测usage。**

在只包含这些已链接记录的算术范围，20USD/2M tokens减上述charged、再扣FX2,764microUSD，余 **1,667,985 tokens /19,746,546microUSD（$19.746546）**。不普遍断言整个机器所有付费run当前余额，也不是最终发票。JSON中的 `company_original_cap_remaining` 只表示旧120k/$2执行scope的历史残额：CN66,954tokens/$1.945381；HK88,617/$1.967345；US79,456/$1.956255。继续该旧scope才沿其残额；它不是下一fresh轮的永久公司许可或公司累计终身限额。按MAJOR_NODE，下一三家公司可由ROOT分别冻结新的单轮不超过120,000 tokens/$2，仍在真实母账剩余及当前配置内分配；过去消费、旧unknown hold和FX继续累计，不能被新run清零或重复扣除。

7旧unknown的来源在 `C:/Users/郑曾波/Projects/company-wiki/docs/plans/narrative-evidence-pilot-2026-09-26/harness_lanes/results/`：

- `n4c_live_2026-10-05_run02.json`两attempt、run04一、run05两、run07一，6个冻结native-row snapshot，上界121,687tokens/44,972microUSD。
- `n4c_live_2026-10-05.json`的 prior_budget与 `n4c_latency_version_closeout_2026-10-05.md` 明确保留 wave1 unknown1的10,325tokens/5,258microUSD。**该第7个只有native run aggregate与明确closeout，没有当前可重开DB路径/逐attempt_id；本报告保持null，不补造。**
- 合旧hold **132,012tokens/50,230microUSD**；已含在上述 baselinecharged，不能再扣一遍，也不能清零/猜settled。FX2,764另保留。现金实际用量未知。
- 另旧US FF capture `1fc320db8942401694de2c53d2e5cc23` 无nativeHTTP usage，是独立acquisition观察缺口，不是第8个modelreservation。其 `roles/executor/events.jsonl` command_started/finished明确链接现存 `execution/requests/fy26-fetch.json`；511B请求SHA `b07ccc4156b989e409ac471e2fb6c3b405783a05662793112e41817979c554df` 与 `roles/storage/sealed-integrity-observation.json` 冻结记录一致。该请求 `acquisition_limits` 实际声明max_bytes=41,943,040、timeout_seconds=180、max_cost_usd="0.00"，companion FMP是reuse_only。保留这个原请求0费用硬上限事实，不能由“API免费”推导0；但该次exit3、stdout0/stderr165B没有原生成功provider usage，实际网络请求/响应bytes与费用结算仍unknown，不能把request上限当socket实测或发票。该已有capture不另加入第8个model unknown预留，也不宣称有正文。

若执行前有新真实收费run，应在这个same母链按attempt去重加上，而不是另建母budget DB。上述旧unknown有保守hold，但当前不可重开其DB不能虚称全native已验；采集费用未知的route若本次不能形成已知界，明确该route受限，其他0cost复用仍可继续。当前readiness与W03/W04工程0供应商调用，不抵销此前外部费用。

## 7. 下一执行者需要完成的最小准备，而非额外门禁

1. ROOT完成已定shared/default集中节点、normal发布/精确CI，更新实际code/installed非秘密binding；不要反复149/168整包。
2. 新owned attempt声明三个来源catalog/registry/AUTO/work/requests/log路径，沿本页已有reuse请求先查/读实际原件；无qualifying SourceRef保真实gap。
3. 生成真实86local-import请求、3project与新finite request2；保存原HTTPcapture引用，不给未import页/lead伪Ref。receipt placeholderURL对研究用途明确不能冒充primary。
4. 执行时再次读上述native母账（包括执行期间的新run），继承旧hold/FX/limits；按配置模型只对actualmissing generations运行。没有授权JSON、canary或逐材料确认。
5. 各真实输出的source/ref/span/replay/usage进入新三年RF研究与四独立审查，材料used/notused/covered_by逐项记。原M3预测/审查答案不作新研究输入；未得正文/截断/缺qualifying日期保持partial。原件保持，最后只清理本次owned临时副本并恢复baseline，不完整备份恢复演练。

本文件给出的是确切已有CLI/路径和尚需生成的输入shape，不伪称尚未创建的请求已就绪。既有W08继续，未签三家研究完成、未启动新公司或loop。
