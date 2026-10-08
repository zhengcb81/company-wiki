# P1 FF/ET 费用与能力的共用修复

## 已证实机制

FF两层在ET启动前按`max_cost_usd==0`拒绝；它既没有查询账户权限，也没有查询本次请求是否额外收费。ET原本可exact fetch FMP，不能discover/fetch-candidate FMP，两类能力不同。[官方订阅定价](https://site.financialmodelingprep.com/pricing-plans)按订阅/API速率/带宽列示；正常API请求不购买/升级订阅。订阅已付费与本次增量费用不能混为同一布尔值。实际账户403必须在真实请求后如实输出，不能用启用配置/存在key冒充权限。

## 实施接口及责任边界

1. ET提供一个本地、无网络的操作能力描述：provider、operation、configured/enabled、exact/discover支持、`incremental_cost_usd`及计费依据。FMP exact fetch是subscription-quota（本次增量0），discover仍明确不支持；Motley Fool配置禁用保持现状，无强行添加provider。配置能力不声称当前账户有权限。
2. ET原`request/1`允许可选`max_cost_usd`（严格有限非负decimal文本）；FF将原费用上限逐字转发。旧请求缺字段按0增量处理，旧结果/内容schema不改。ET共用provider操作判定在HTTP前核费用和能力；超额度/未知计费不得试付费探测。不购买订阅，不翻译、不新增缓存。
3. FF删除重复零预算猜测，先CWP精确查已有，再把明确期次请求与字节/时间/费用上限交ET；查询/正文/入库仍走原公共接口。缺tool/缺key/能力不支持/账户拒绝/真实请求/硬截止分别保留状态，不把工具进程数当真实HTTP调用数。
4. 既有unknown-publication不能冒充历史可用，不把call_date当publication_date。本节点只修费用/能力，来源发布日期另归P1资格组。

## TDD与一个集中验收

- ET: 本地能力不联网；FMP exact支持但discover不支持；0费用合法、非法费用字段拒绝；显式disabled/缺key保持0网络；账户403保持真实错误；实际Worker收到原费用字段。
- FF: 0费用的免费/订阅内合法请求能到替身ET；原限额未扩大/未删除；费用判定由ET返回，缺/不可用provider仍不冒充下载；local reuse保持0调用。
- 集成: 原FF→实际ET CLI/Worker→CWP离线套件切0费用运行，真实原始payload、SHA、语言、期间、入库后复用、硬截止与目录恢复。禁止只mock整ET成功结果。
- live: 当前FMP key仅内存传递，一个确切公司/期次请求，记录tool启动、真正HTTP次数、结果/账户权限；不购买任何新套餐。完整第一组三公司live/replay在下一共用格式节点集中跑，避免每小步重复下载。

## 隔离与发布

MAIN写本PWF；FF/ET分别在`company-wiki/tmp/ff-transcript-cost`与`tmp/et-transcript-cost`独立Git工作树施工。不动两主目录的未提交key/评估/harness文件。责任与离线联调绿后分别commit→快进main→push；只同步已改技能文件，保留安装配置/output。测试独立TEMP退出恢复，Git工作树合并后移除，保留小JSON工程结果。

## 集中验收记录（2026-10-08）

- ET费用13项由6RED/7PASS到13PASS；用量接口3RED后修共用supervisor，能力/原API/真实Worker硬截止等74PASS33.77秒。FF用量7RED后26PASS5.60秒；0上限逐字抵达ET，没有删除字节/时间限额。旧测试将0费用等同不能请求，按明确计费规则替换，付费/非法额度拒绝新增断言没有放松。
- 初次直接给CLI stderr增加回执导致5个旧静默合同失败；改为FF显式`--report-usage`，默认CLI stdout/stderr保持。内容result/2及CWP原件合同不加入遥测字段。FF的`provider_requests`/`provider_response_bytes`才是实测用量；`provider_calls`保留旧attempt兼容含义。hard-kill未知用量不自动重试。
- 实际FF→ET CLI/supervisor/Worker/API→CWP import/query/open离线验收成功：费用0.00、原语言raw及SHA/期间、一次HTTP、复用0HTTP、unknown-publication仍拒绝历史可用、timeout不入库且scratch清空。没有用整ET成功mock冒充联调。
- 真实现有FMP账户MSFT Q4 FY2026，20秒/2MiB/0.00请求2.117秒：ET真实启动、精确HTTP请求1次、账户`provider_entitlement_required`，无模型/新付费，无原件测试副本留存。详见et_fmp_live_probe.json。费用路由机制已修，当前账户电话会获取仍客观BLOCKED；不购买套餐、不切未授权provider伪造成功。
- 调试错误：首次probe用了错误共用运行器keyword，TypeError发生HTTP前（0请求），查实际签名后更正；tests助手导入需相对路径；本轮几个文档/测试入口猜测不存在，后续以rg --files清单选路径。未把这些操作错误当产品故障。

发布完毕：ET main=282e8908e98196447e3ac72d95a4c7425a3aa322；FF main=697af966475a4aa7bb0687c78bfb81a7edb54f21，49相关测试绿，精确SHA远端CI37833957140成功。首次FF CI只因新顶层用量解析的复杂度15>10失败（418行为测试通过），拆分回执身份/计数类型责任后原门绿，不放宽阈值。ET无Actions工作流，不虚报CI。两仓owner未提交项目保持；已同步3份FF安装副本的4选定文件，后续同一文件再定点修正。2施工工作树和9测试根已回收，资料原件删除0。
