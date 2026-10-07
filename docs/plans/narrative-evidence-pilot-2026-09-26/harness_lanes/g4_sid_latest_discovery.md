# G4-SID-LATEST：按as-of发现A股最新财报

**状态：complete / accepted / published（provider范围）。SID eb8495c已并/推正式v2-clean-rewrite；CWP df7d7ba路由已接1.3.0，127责任/真实离线CLI合同绿。完整ensure/FF/ET/CWP入库复用仍归MAIN G2-12，不是本卡已完成范围。**

正式收据：[G4 MAIN验收](../g4_main_acceptance_2026-10-07.md)。以下为已完成施工细则/历史基线，不再重新开工。

## 1. 已证实缺口与目标

当前CWP统一获取线正在MAIN施工；上层传公司/证券、document_kind、`mode=latest_as_of`与as_of_date，让provider按真实公告元数据给候选。当前SID `AdapterDiscoveryRequest.fiscal_year`及JSON CLI都强制整数；API查询按该年份建窗口，两层过滤也固定year。CWP若不猜年份，latest半年报/季报在provider直接报错；即使年报猜as-of减一，年初未出新年报时也可能漏掉实际已公开的上一份。这是实际能力缺口，与个人权限无关。

本包把CNINFO**元数据发现**做完整：exact保留精确年份行为，latest按明确as-of查真实年度/期间、返回完整有界候选或明确不完整结果；共享响应bytes/deadline继续生效。只补年报/半年报/季报，不扩招股/研报/新闻provider，不自动下载整库、翻译、摘要或调用模型。

SID供应候选与暂存下载；CWP独占目标选择、幂等、SHA入库、canonical路径与原文保存。不能在SID写company-wiki目录/数据库或自建公司资料湖。

## 2. 基线、工作树与owner保护

原执行仓：`C:/Users/郑曾波/Projects/StockInfoDLSimple/v2-clean-rewrite`，执行分支`v2-clean-rewrite`，基线`8ed5fdde5e88c13470c120665ff3074a7f44a052`。该Git remote仍为StockInfoDownloader仓库URL；这是现有Git命名，**不维护旧StockInfoDownloader main**。最后接回SID执行分支由MAIN负责。

原仓有11个tracked owner改动：README、config_template、main、browser/downloader/logger/mapping/models、official_e2e与两unit文件；另有公司名单和scripts。全部保持，不能reset/clean/stash当作本卡材料，也不复制未提交变更到新基线。

```powershell
git -C 'C:/Users/郑曾波/Projects/StockInfoDLSimple/v2-clean-rewrite' status --short
git -C 'C:/Users/郑曾波/Projects/StockInfoDLSimple/v2-clean-rewrite' worktree add -b codex/g4-sid-latest 'C:/Users/郑曾波/Projects/_g4/SID-LATEST/StockInfoDLSimple' 8ed5fdde5e88c13470c120665ff3074a7f44a052
```

新worktree仓根直接含src/tests/config等，不再追加v2-clean-rewrite子目录。路径/分支占用核归属后用新后缀，不能覆盖其他harness。自己的PWF在`docs/implementation/g4-sid-latest/`；使用planning-with-files并显式pin `PLAN_ID=g4-sid-latest/PWF_PLAN_ROOT=<自身worktree>/docs/implementation`（两个环境变量分别赋值，resolver传同一PlanRoot）。读实际适用AGENTS；原仓没有仓内AGENTS，不新建虚构规则。

## 3. 独占写集

- `src/company_wiki_adapter.py`：request解释、候选过滤、版本及typed发现失败传递。
- `src/company_wiki_adapter_cli.py`：兼容request解析、真实JSON输出/错误、资源usage与初始化次序。
- `src/cninfo_api.py`：latest日期窗口/分页/元数据过滤/真实不完整状态；现有bounded读取沿用。
- `tests/unit/test_company_wiki_adapter.py/test_company_wiki_adapter_cli.py/test_company_wiki_adapter_cli_budget.py/test_cninfo_api.py/test_cninfo_api_fixture_contract.py/test_cninfo_api_budget.py`相应责任同步。
- 新`tests/unit/test_g4_latest_discovery.py`、新`tests/e2e/test_g4_latest_cli_offline.py`，新测试小JSON夹具仅在`tests/fixtures/g4_latest/`。
- `docs/implementation/g4-sid-latest/**`自身PWF、接口说明、交接与小报告；必要独立测试driver在此目录，不改未跟踪owner scripts。

不改原/新仓生产config.json/config_template、README/main/browser/downloader/mapping/logger/models、其他owner测试、requirements、hook/CI；不写CWP/FF/ET/Dayu/IQS、总PWF、生产原件或安装副本。不重构浏览器抓取链，不增加新provider或第二任务库。发现共享依赖问题交具体重现给MAIN，不扩大写集。

## 4. 冻结输入输出与实现规则

### 4.1 请求兼容

继续现有stdin JSON与`discover/fetch` CLI、schema_version1.0。CWP现成SourceRequest包含`entity/market/security_id/document_kind/mode/fiscal_year/fiscal_period/form_type/as_of_date`；budget仍现有acquisition_budget，没有额外authorization/receipt/hash/TTL。

1. 旧请求缺mode时按exact；exact要求合法整数fiscal_year（bool不是整数），当前年度/期间过滤不放宽。
2. latest明确`mode=latest_as_of`且合法ISO日期as_of_date；允许fiscal_year=null/缺失。兼容旧CN annual caller携带的年份提示，但**latest不把提示当必须等于该年的过滤条件**，否则年初回退仍断。候选自己的年份只能来自真实公告标题/元数据，不能抄as-of年或请求提示。
3. 内部AdapterDiscoveryRequest在末尾增加兼容可选mode/as_of/period字段，保留原位置参数与exact调用；类型/date/kind错误在provider/浏览器/network初始化之前具名失败。未知mode非零，不silent转exact。
4. 先支持现有annual_report、semi_annual_report（H1）、quarterly_report（Q1/Q3及当前parser真实支持期间）。尊重显式period/form_type；未知年/期间不能假填。半年报不伪装Q2，年报不伪装Q4。不要为“通用”改CWP公开合同。

最小离线stdin样例（示例公司/响应均由自身夹具提供，不是live事实）：

```json
{"entity":"示例公司","market":"CN","security_id":"600000","document_kind":"quarterly_report","mode":"latest_as_of","fiscal_year":null,"fiscal_period":null,"form_type":null,"as_of_date":"2026-06-01","acquisition_budget":{"schema_version":"1.0","max_response_bytes":1048576,"timeout_seconds":20,"max_cost_usd":"0"}}
```

budget必须严格保留现有四字段及decimal字符串cost；父CWP传的是本次剩余额度，不能重新取默认整份预算。返回candidate格式照当前DisclosureCandidate.to_dict，usage照ProviderAcquisitionBudget.usage；payload请求样例不授予实际live下载。

| 可控夹具 | cutoff | 应有结果 |
|---|---|---|
| 2024年报已于2025-03-20公开，2025年报2026-03-25才公开 | 2026-02-01 | 保留2024/FY，排除未来2025；即使请求带2025提示也不能漏2024 |
| 2025/2026半年报各有真实模拟公告 | 2026-09-01 | 按各自公开日保留可见H1，2026实际期间供CWP选择 |
| 2025Q3、2026Q1已公开，2026Q3在2026-10-28公开 | 2026-06-01 | 保留可见Q3/2025与Q1/2026，排除未来Q3/2026，不伪造Q2 |
| 第一页摘要/非目标类型，后页才有全文 | 同上 | 继续分页并返回后页全文，不因已过滤列表为空停止 |
| 原始总量超过5页且未能完整覆盖 | 同上 | discovery_incomplete非零，保留实际usage，不正常返回partial/empty |

### 4.2 官方发现与有界完整性

日期窗口由as-of计算，截止不晚于as_of_date；初始latest窗口覆盖最近三个自然年（as_of.year-2的01-01至as_of），每次最多现有5页×30条，共用一份预算。不读取本机today决定历史请求，不逐年重新申请预算，不遍历全部历史。

元数据查找层负责官方证券/公告ID、公开日期、kind和标题的真实year/period；晚于cutoff、不匹配证券、全文摘要companion/纯标题空记录不成为有效候选。沿用当前公告毫秒时间戳→UTC filing_date定义，并覆盖UTC跨日边界；官方页面日期与既有UTC定义的差异作诊断，不悄改旧来源日期/ID或从文件名补日期。返回distinct announcement ID的完整候选集合，排序确定，version/amended保留；同一ID冲突内容须诊断失败，不能以dict覆盖掩盖冲突。provider不挑“第一条”或自行替CWP解决两个同期间全文版本歧义。

分页必须依据原始API total/page记录推进，不能因本页过滤后0条就认为后页没有全文。确证最后页/总量收齐才可认为窗口内发现完整；5页耗尽仍有未覆盖记录、关键字段缺失/上游顺序不可靠时，给机器可识别的非retryable `discovery_incomplete`，不能返回正常空/partial列表让CWP把旧本地件当最新。窗口内完全无有效候选时明确`bounded_discovery_empty`与窗口诊断，不宣称查遍全部历史；MAIN将其作为诚实GAP，不扩大窗口无限重试。

单一对象共享response bytes与剩余deadline，metadata分页和后续fetch不能恢复已用额度。已有ProviderAcquisitionBudget与bounded response reader继续执行读取中硬限额；超限/超时不能在except里转confirmed_empty。支持未知Content-Length、truncated body、超额response与局部失败usage，使用现有budget类，不建立另一账本。

### 4.3 JSON与版本

成功仍输出一个JSON value，candidates/receipt shape不变；诊断进stderr或兼容小字段，不混入stdout。失败仍现有schema1.0/error.code/retryable/acquisition_usage；保留typed上游错误与预算事实，不把discovery_incomplete当可重试网络故障。若AdapterError包装CninfoApiError，用属性传递稳定code/retryable，CLI优先读取这些属性，不靠消息字符串猜。

行为版本用`ADAPTER_VERSION=1.3.0`，wire schema仍1.0。交接准确列旧1.2.0→新1.3.0；CWP `JsonCommandAdapter`真实校验name/version，MAIN必须同步目标路由版本再发布，harness不修改生产source_acquisition.yaml或安装配置。离线消费联调在自己的tmp配置显式用新版本，不能拿旧路由失败称功能不支持，也不能删真实version校验。

fetch接口保持当前selected candidate→调用方staging；SHA/PDF magic/原始byte size仍真实验证，existing exact与预算回归保留。不自动启动fetch，不在metadata discover保存PDF或全文转换。

## 5. TDD与实施顺序

1. 建自身PWF，记录Git/owner保护和既有接口。读真实三源文件、预算类和六测试；结构用CodeGraph，已打开文件再读字符串。不要使用原仓owner脚本作入口。
2. **先RED：**latest季度/半年报fiscal_year=null在现行CLI失败；年初annual最新实际为旧年而不是猜年；as-of之后公告排除；摘要占第一页而全文在后页；页数预算耗尽不能报完整；请求坏输入不构造provider。RED用真实代码与可控官方HTTP响应，不能直接伪造完整CLI结果。
3. 分别实现request解释、日期窗口、kind/period/证券/cutoff过滤、有限分页完整性、typed错误；复用一份budget。返回候选让CWP选，不能在SID复制resolver/gap_plan/canonical writer。
4. 补exact兼容、JSON/usage与fetch回归，代码Ruff/现有类型只核修改；完工做一次下节集中责任和真实公共CLI离线E2E。
5. 交commit/HANDOFF/机器接口/main_wiring，正常推自己的分支（有权限时），不合执行分支、不安装、不改原仓owner配置。MAIN验证实际统一ensure后并线。

## 6. 测试包与恢复

**Unit/集成必测：**exact旧年份语义；年初/年中/季度/H1切换；最新年份提示不强行过滤；合法cutoff与未来公开拒绝；跨年/缺年/坏日期/错误证券；全文与摘要分离；同period不同公告ID均保留；重复ID冲突；分页过滤0但尚有后页；5页耗尽、schema drift与预算拒绝是明确失败；读取中的共享bytes/deadline、失败usage和既有PDF/SHA/fetch保持。

**真正CLI离线E2E：**在自己短tmp启动`python -m src.company_wiki_adapter_cli discover --config <自己生成的tmp配置>`，stdin为CWP形状与真实acquisition_budget。仅替换最底层HTTP transport/loopback响应；使用真实CninfoAnnouncementClient、StockInfoCompanyWikiAdapter、CLI序列化，不用FakeAdapter直接吐候选。若启动器需bootstrap注入可控HTTP，交具体driver与mock边界，保持实际runpy/-m入口与真实发现/序列化代码。

覆盖年报旧年回退、H1、Q1/Q3、future排除、分页耗尽/bytes超限/截止非零；成功stdout只能解析为一个JSON，失败usage真实。另从已提交CWP `5930a644...`只读导出最小adapter模块闭包到自身scratch，用真实`JsonCommandAdapter.discover_bounded`消费新1.3.0响应，source candidate身份/年份/period/日期与预算计费一致。不读MAIN未提交ensure代码；完整FF→ET→CWP/latest下载接线留MAIN。

可控fetch回归只下载loopback合成PDF到本卡staging，保留SHA/size/magic，超限失败清局部文件；test下载原先不存在则结束删除。无需付费API/FMP/LLM、无需live下载。若另做可选匿名官方元数据探针：显式3MiB response/60秒/$0、最多2次请求，无PDF、无凭证，不把网络不可用作为本包离线完成阻断；如未运行写NOT RUN，不冒称live成功。

集中责任命令（新文件由本卡创建）：

```powershell
python -B -m pytest -q -p no:cacheprovider tests/unit/test_g4_latest_discovery.py tests/unit/test_company_wiki_adapter.py tests/unit/test_company_wiki_adapter_cli.py tests/unit/test_company_wiki_adapter_cli_budget.py tests/unit/test_cninfo_api.py tests/unit/test_cninfo_api_fixture_contract.py tests/unit/test_cninfo_api_budget.py tests/e2e/test_g4_latest_cli_offline.py
```

自己的短测试根用系统TEMP唯一`si4l-<随机>`目录，实际cwd/config/logs/output/browser scratch全在本卡root，网络替换/子进程结束后finally清理，前后恢复absent/原清单。原仓owner files不读秘密、不改；复制测试资料与临时CWP闭包结束删除，不保留PDF/正文大包。删除前核绝对路径包含和无reparse，关闭client/process/DB再删。验证原仓status与已知owner文件SHA不变；缓存若落自身worktree只清本次新建且可证明owned的路径，不广域clean。

集中验收只看责任/真实命令/退出码/资源与恢复，不按固定pass或coverage。本包不证明生产CN下载、跨仓latest整链或外部Dayu已支持。

## 7. 交接接口

自己`docs/implementation/g4-sid-latest/`交`task_plan.md/findings.md/progress.md/HANDOFF.md/handoff.json/main_wiring.md`，另`latest_request_contract.md`和小JSON请求/响应golden（无正文/凭证）。HANDOFF列RED→GREEN、确切mock层、页面完整性判断、bounded-empty/incomplete错误、旧exact兼容、新adapter版本、尚未执行live与MAIN接线。

```json
{"schema_version":"g4-handoff/1","lane":"G4-SID-LATEST","base_commit":"8ed5fdde5e88c13470c120665ff3074a7f44a052","implementation_head":"实际实现提交SHA","delivery_branch":"codex/g4-sid-latest","worktree":"实际绝对路径","commits":[],"changed_paths":[],"tests":[{"command":"实际命令","exit_code":0,"seconds":0,"passed":0,"failed":0,"skipped":0,"evidence":"本卡小收据相对路径"}],"behavior_changes":[],"compatibility":{"wire_schema":"1.0","adapter_name":"stockinfo-cninfo","old_adapter_version":"1.2.0","new_adapter_version":"1.3.0","exact_preserved":true},"protected_state":{},"cleanup":{"roots":[],"restored":true},"external_effects":{"network_requests":0,"model_posts":0,"raw_deleted":0,"production_writes":0},"remaining":[],"main_integration":{"target_branch":"v2-clean-rewrite","route_version_update_required":true,"wiring":"main_wiring.md"}}
```

示例计数必须替换为实际值；localhost HTTP和真实外网请求分别报告。implementation_head是实现commit，随后交接commit列commits；不要求机器报告预知自身commit SHA。正常提交/自己的分支推送，不跳hook；MAIN负责冲突、执行分支合入和真实CWP/FF接线。
