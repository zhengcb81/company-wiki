# 主线工程完成后的真实研究大节点

状态：原三家全新执行已于2026-10-09 06:50 UTC实际启动，四审待执行封存。工程前置已合并发布；本轮新增RF日期/MIME/URL共因经TDD并main79139534/安装/精确CI成功，执行者新增真实版本过渡capture，旧scope/失败不重写。见 `fresh_executor_launch/launched/cohort.json` 和 `fresh_runtime_boundaries/acceptance.json`。先原三家，再固定新三家，最后恢复公司池loop；不以旧预测或CI绿色替代本节点。

## 样本与环境

- 原三家保持中微688012、腾讯00700、微软MSFT，as-of=2026-10-08及旧71检查点不变。旧输入/审查/快照仅用于前后对照，执行者须建立新的真实研究，不能复制旧模型冒充重新执行。
- 新三家依 `second_cohort_generalization.md` 固定后才启动。当前仅调查宁德时代300750、吉利00175、Costco COST；官方有资料且业务驱动不同。它们尚未正式选定，不计抽样、执行或clean。
- 每个公司一个审计运行包，置于 `revenue-forecast-audit/runs/`；每个attempt一个隔离CWP catalog/公司原件根、AUTO/work、RF registry/output。各公司代码只读；执行者无共享代码/安装/生产配置写权。正式研究成果只在RF/audit输出，CWP主线只收工程证据。
- 旧生产原件通过CWP来源接口读取。储存层先处理必要既有原件的登记；上层不拼底层目录。当前生产catalog只有47个annual候选，不能把query not_found等同全机不存在。
- 已有宁德2024原件的独立public register→query实测1.49秒found、0下载，证明现有显式登记机制可用；测试根已恢复。准备环境时复用这个机制，按请求登记必要来源组，不开启全库转换、不故意藏原件凑新下载、不改原始字节。

## 角色与交接

1. MAIN冻结版本/配置来源、有效累计预算和每轮额度、初始清单、来源登记及scope。读当前audit skill/workflow/artifact-contract/executor，不照搬旧请求schema或已退休allow-download双门。
2. 三个独立executor分别负责CN/HK/US，真实调用当前安装RF技能。所有CLI用已有audit capture，原生web/tool用actual ID/events；二进制原件只记录ID/locator/SHA。保留失败输出、退出码和费用未知，禁输出key。
3. 封存每家execution manifest后做四路独立审查：storage/fetch/process/analyst。总四槽保留MAIN，最多三位reviewer并发；第四位在槽释放后跑。每位只读同一封存执行包和自己职责卡，不读其他初稿、不改代码/执行包。
4. 四份JSON/Markdown齐后MAIN做一次结构check并阅读结论；专家归并共因、建立issue→原因→责任包→测试映射。研究错误修事实、方法和参数；工程错误先通用RED再实现；供应商限制如实标记。修复后新attempt复验原样本，旧报告保留。

## 必做检查点

| 责任 | 实际动作及证据 | 不能冒充完成的情况 |
|---|---|---|
| RF入口/FF | 当前source_preparation公开入口真实启动FF，完整result envelope保留财报/电话会分项和usage | 手动拼producer结果；绕FF下载 |
| 本地复用 | 原件字节验真、期间/as-of；已有文件先登记/查询；重复同请求零新下载 | catalog未建就称全机缺失 |
| 按需采集 | CN SIDSimple，HK/US Dayu外部，电话会ET；记录具体期间/文档类型/预算、真实download→import→ref→reuse | mock/网页手工取代路由；无限重试entitlement |
| 多类来源 | 年报、半年/季报、IR、原语言电话会、SEC HTML；适用的招股/增发/可转债经营描述 | 对无此材料公司硬凑；一般格式文件全量切片 |
| 官方补充 | 正确public official发现/原件登记统一writer；保留公开日、期间与采集日期差别 | 编造年份/公开日或HTTPreceipt |
| 处理/虚拟读取 | 有限真实batch精选/原语言摘要；source/span/claim/ref可回放；图片资料有实际正文识读与质量缺口 | 只有文件存在；confidence高就称全文完整 |
| 效率/空间 | 同generation跨run直接复用、0新POST/账；显式refresh才重算；多span一次回放；无全文MD/持久页图 | 调用之后的物理去重称计算复用 |
| RF证据消费 | NarrativeRef→已读span→claim→实际使用的parameter/driver→公式→输出可追溯；非财报null合法 | 仅把ref列附件，未进入模型 |
| RF全流程 | 0–11真实step matrix、两年度历史对账、全部业务、管理沟通及目标、独立基准、约束、三情景、敏感性、置信度、正式validate/compute/render/snapshot/registry | 引擎算术绿称研究完整；未经实读称checked |
| 数字/研究 | 逐事实出处；currency/scale/billion/亿/百分数/pp；季度原生桥、YoY分母；历史与未来机制区分；可观察量级校准、反证、确认时点/产能/资金约束 | 季度×4作官方年指引；凭空ASP/量级；同一历史段正反两用 |
| 信息日 | 真实可用资料截至scope；未知future actual只冻结，不虚构回测 | 引入as-of之后文件；生成情景当actual |

## 配置、预算与恢复

只使用 `scripts/narrative_batch_configured.py` 读取实际Config，明确支持的provider选择；读当前配置的模型/endpoint/生成参数和价格，不从记忆改MiMo/DeepSeek/MiniMax。工程本机OCR不计supplier POST。沿用本活动既有永久资料外发/配置供应商授权，不逐材料/供应商/小步骤再要人签。付费前使用当前AUTO及`main_budget_preparation.json`：2026-10-09真实OCR节点后累计207042tokens/119671microUSD，历史unknown7、FX guard2764保留；原生产r3和新OCR均各计一次。实际变化后以真实账更新，不能清零/重复加减。累计上限仍USD20/2M，不新建费用数据库或授权许可证。

三公司并发时MAIN先分配加总不超过剩余额度的单轮上限；单公司默认最多120000tokens/USD2且遵守更低配置界限，未知收费不自动重试。原三家和新三家共六轮的上限可容纳于当前已知余量，但实际旧账/unknown有变化时以实读为准。只有原工具的known receipt能结算，失联保留unknown并恢复原run，不能重开run绕账。

2026-10-09已实读四个native收费run，最新预算观测 `fresh_executor_launch/launched/budget_observation.json` 为累计236614tokens/151565microUSD估计，含失败年报费用、旧unknown7和FX2764保持；这不是最终settlement。相同AUTO可以承载多个finite批次，但每个不同input_hash必须在scope既有work父目录下分配独占子目录，自己的storage-baseline只由自己的run恢复使用。不跨批次覆盖baseline、不复制整套AUTO、不改模型配置来隐藏错误。

下载每请求采用当前能力支持的实际字节/时间/费用上限；不得沿用已弃用body/operation混淆。根据资料大小设有界值，超限保留读到的真实字节，失败不入库、不夹带无限历史下载。

## 大节点与收尾

- 工程合并后先固定71项full replay/live及前后compare，旧经济语义FAIL保留，等新研究实读解决；该回放不伪装六家公司研究。
- 原三家完整执行及四路审查完成后，再固定新三家执行；新增共因不得对公司特判或换样本避失败。
- reviewer期间来源必须可打开；最后核初始清单/原件SHA，关闭DB/进程，恢复本次owned测试根。保留小型日志/报告/最终必要预测交付与清理证据，不长期留六套原文/全文转录。
- 只有主要问题复验解决且关键检查实做才能通过。外部工具客观限制单列；适用替代官方资料覆盖内容不等于原ET provider成功。完成主线后引用既有company-pool-cycle活动，从冻结NVDA复验及其24发现恢复loop，不丢历史责任、不重抽绕失败、不新增scheduler/许可链。
