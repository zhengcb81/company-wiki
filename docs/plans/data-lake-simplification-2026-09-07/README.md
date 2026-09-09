# 把三仓收敛为一个虚拟数据湖：现状与减法建议

> **后续规划状态（2026-09-07）**：用户已批准将下述方向纳入规划，当前路线见[R4详细实施计划](../painpoint-outcome-audit-2026-09-05/simplified-execution-plan.md)。下方“不自动取代旧计划”是本诊断首次交付时的权限说明；如今仅执行编排已更新，仍未批准或实施产品变更，诊断观测也未因此变成当前运行验证。

日期：2026-09-07。本轮只读诊断，未修改产品/旧计划/权限/数据/worker/任务，也未运行真实业务或性能测试。源码观测：wiki `5c4fa301b83a244da55a63208874ee578343227a`、filing `89c8bdb2cfba4d88720d005d0558f422957e8ade`、revenue `81553f1312af8e8a8ae2a7e4700f909416ea0d95`；并发变化后需重核。本建议是供选择的架构方向，不自动取代旧计划或批准实施。

## 结论

用户的目标是合理而且更简单的：**多个获准目录是同一资料库的存储位置，不是多个业务权限等级；用户按公司、报告类型、期间和版本取资料，而不是选文件夹。** 不需要为了这个目标搬动全部文件、统一成一个大目录，或重写成分布式数据平台。

当前系统已有虚拟化基础，但尚未把物理位置完全封装起来。复杂度主要来自：迁移兼容长期留在主链；本地可读、正式来源完备、解析可复用、外部调用权限被绑成一个巨大成功条件；责任分散导致多仓重复判断/重复读取；原始问题未被正确抽象时又用更多验收流程防错。

上一轮160步/95个计划门是风险清单的详细展开，不是证明那就是最简架构。我也需要纠正前一轮方案的倾向：它加强了执行约束，却没有先建立“应当消除哪些概念和重复逻辑”的复杂度预算。应先做这次架构收敛，再压缩实施计划，不能继续机械地给现有结构补门。独立审查应保留在关键变更节点，而非每次取文件都重复审批。

## 一、现在实际上如何工作

### 1. 权限配置已经基本平权，代码合同尚未完全平权

当前`config/source_catalog.yaml`四根：

| root | 物理用途 | kind / priority | 当前配置的读取地位 |
|---|---|---|---|
| company_raw | companies | company_raw / 10 | public，kind可复用 |
| dayu_portfolio | dayu-agent portfolio | dayu_portfolio / 20 | public，kind可复用 |
| dropbox_stock | Dropbox/Stock | directory / 30 | public，kind可复用 |
| future_lake | 第四根 | directory / 40 | public，显式reusable及sidecar adapter |

`RootSpec.read_only`默认true，所以前三根没写read_only不表示可以任意写。priority本身是选副本偏好，**不等于OS权限或内容可信等级**。但它进一步影响canonical选择和元数据更新，形成不该有的业务差异。不能说当前Dropbox默认private或完全不能复用；当前owner已经配置全部public。

同等读取权限也不意味着允许删改所有来源目录。外部原始资料只读、下载只落指定收件区，是合理的操作差异；不妨碍它们作为财报具有同等使用地位。真实OS ACL、离线云文件、文件损坏仍是可访问性事实，虚拟层应处理或清晰报告，不能假装不存在。

### 2. 已经有一个统一目录索引，不是三套互不相干文件夹

`store.py:128–209`已有roots、sources、documents、locations、artifacts等表；sources以content_sha256唯一，逻辑文档与物理location分离。`SourceCatalog`也已经把只读reader与写store分开（service.py:39–58）。这些应该保留。

当前大致链路：

```text
多个root → 各adapter/旧scanner → 统一catalog + content hash
                                  ↓
                      按root priority标canonical
                                  ↓
              resolver再检查kind/身份/期间/来源完整性/迁移状态
                                  ↓
               filing验证policy+路径+文件hash → revenue再读路径/hash
```

有统一索引，不等于位置透明：下游仍依赖`canonical_path`、`canonical_location_id`、root policy、epoch/cohort和上游role依赖，抽象边界还没完成。

### 3. 具体复杂度泄漏点

| 当前实现证据（项目相对路径，行号为本次观测） | 为什么复杂 / 如何收敛 |
|---|---|
| wiki `service.py:621–662`先按root_priority等选canonical；`resolver.py:912–940,1153–1167`只用canonical候选/检查该文件存在 | 某首选副本失效时，此处没有逐个尝试健康同内容副本。应先筛可读副本，再选I/O最合适的一份；优先级不应决定逻辑文件有无 |
| wiki `scanner.py:1038–1080`以root.priority控制metadata更新，再补URL/身份字段例外 | 存储偏好和元数据可信度混合。来源事实按provenance/质量合并，冲突明确，不按“放在哪儿”决策 |
| wiki `resolver.py:782–785`按kind判断reusable；`policy.py:72–77`优先per-root字段再kind | 同一权限意图有两种计算方式。统一注册后的读取能力，规则只计算一次；消费者校验结果，不重新解释另一套策略 |
| filing `fetch_filing.py:103–107`已移除独立allowed_handle_roots；`:881–888`及`filing_contracts.py:449–488`无policy仍退回companies | 已有改进，不应误称仍维护两份生产白名单。真正待去除的是运行时静默兼容回退，改为明确版本协商和一次性适配 |
| wiki `resolver.py:1179–1200`capture_ready要求https_url/date/capture_trace；`:961–969`不完整则不提供复用 | “本地真实原文可读取”被下载来源合同绑住。缺URL可显示provenance incomplete，不得伪造URL，也不必因此触发重下或禁原文预览；正式证据/特定分析按实际要求另验身份/日期 |
| filing `filing_contracts.py:503–517`整文件验hash；revenue `company_wiki_source.py:297–306`再读路径/hash，`:311–319,348–352`路径与location进入trace | 存储细节传到消费端，重复I/O。由存储边界提供稳定只读流/快照并验真；路径留诊断，不作业务身份。不能只去掉hash制造速度 |
| revenue `source_preparation.py:99–108`→client`:185`→filing`:685–704`层层subprocess；latest_as_of走ensure/provider（filing:716–720） | 合并一次identify+query请求，区分“湖中最新”和“在线查最新”。薄wrapper不必各起Python进程；跨仓CLI可保留一个边界 |
| filing `fetch_filing.py:736–757`资料获取管理PausedWorkerScope | 文件获取耦合长期worker运维。目标是单写者队列/短事务，而非每个读者pause/resume。并发安全替代测试过前不能直接删保护 |
| revenue `source_preparation.py:121–156`缺envelope/call counts可阻止准备；`company_wiki_source.py:108–228`了解上游ROLE_DEPENDENCIES/重建闭包 | 可读资料与“证明零重算”混合；消费者承担生产编排。只读预览可报告usage_evidence unknown，不声称零调用；付费动作仍必须有预算账本。消费者声明所需产物，producer自己安排重建 |

runtime snapshot目前还保留epoch/cohort，resolve active与shadow同时开启、scan shadow开启、bundle active关闭，legacy bridge关闭；而resolver缺snapshot默认v1/bridge（resolver.py:734–759）。这是长期混合迁移模式，不是虚拟数据湖的必要构成。不同格式的adapter有必要，但它们应只把目录/sidecar差异翻译成同一输入，不向业务层传播权限差异。

## 二、哪些门要留，哪些应该拿掉或移走

不能把所有门都叫“门禁”然后一删了之，也不能用安全名义永久保留每一个条件。

| 类型 | 处理建议 | 具体边界 |
|---|---|---|
| 文件路径越界、symlink逃逸、读时字节完整性、真实公司/报告期间识别 | 保留并集中 | storage管文件访问/字节；catalog管身份/版本；无需每仓再解释root |
| 未授权写原始文件、回收误删、下载/LLM费用与外发、无限重试 | 保留，按动作触发 | 普通本地读取不审批；真实写/删除/外发才查对应合同。已批准的稳定数据域可复用批准，不每个文档重复人工审批 |
| 已解析产物版本/source hash与实际使用字段的有效性 | 保留，按所需能力检查 | 只要原文就不强求summary/sections/完整矿业链；解析失败不让整个文档凭空消失 |
| kind和per-root两种reusable解释、companies fallback、同路径反复验真 | 合并/淘汰重复规则 | 单一注册与唯一读取合同；content/address可验证；保留实际最小信任边界的必要复验 |
| epoch/cohort/双reader/双bundle/迁移影子模式 | 作为有终点的迁移设施退出 | 一套正式读取链，旧格式仅版本化兼容入口。不能在未知调用者情况下立即删除 |
| CA/ZR/receipt/reviewer/自然观察/几十个开发门 | 留在变更与发布流程，不进普通查询 | 本轮没发现消费者每次直接查CA/ZR accepted；95门是上一轮计划门，不是95个每文件运行门。按风险把独立审查集中在设计、变更验收、真实放量关键节点 |
| 缺调用次数就拒绝原文预览 | 分离资格 | usage unknown不伪称zero-call；安全/预算敏感执行依然拒绝未知。不能由预览放宽推导LLM可运行 |

不建议为简化把所有内容无条件给LLM、让所有root可写，或取消原文hash。这样的“简化”会改变用户授权与数据风险，不是减掉架构重复。

## 三、目标架构：一个小而清楚的读取门面

建议先在现有本地代码/CLI上收敛，不新增常驻HTTP服务、不引入对象存储/消息中间件、不强制FUSE挂载。

```text
用户 / revenue-forecast
         │ 公司、报告类型、期间、截至日、所需能力
         ▼
      DataLake门面（可由现有company-wiki API/CLI演进）
       ├─ query：只查已索引资料
       ├─ open：按文档版本打开健康副本/指定产物
       └─ request：显式申请缺失下载或加工，返回持久任务状态
         │
   catalog（身份/版本） ─ storage adapters（位置/字节）
         │
     单一producer（下载、解析、有限重试、产物缓存）
```

关键合同是建议接口，不是假称当前API已经存在：

- 对外引用：`document_id + source_version/content_sha256 + locator`。同一逻辑报告可有不同修订；同字节多副本不等于不同报告；来源引用保留原source identity，不因搬目录改变。
- storage内部保存`root_id/path/health`。副本消失时换同hash健康副本，所有副本失效返回unavailable，不偷偷换另一修订或默认下载。处理云盘占位文件/不可读状态，不以目录存在当文件可用。
- root只配置路径、格式adapter和必要读写能力；**所有已批准财报root默认同等可读**。新目录只加一次注册，消费者代码、白名单、provider逻辑不变。
- 内容是否足以做某项工作是能力问题：原文可读、身份待补、文本待处理、证据定位可用分别返回，避免一个capture_ready/accepted替所有问题。无需立即引入新几十态状态机，可用已有状态加清晰分项原因。
- `query_local`绝不联网、建库、暂停worker；`refresh_metadata`和`fetch_missing/process`是另两个显式动作。用户说“湖中有的最新版”不应自动产生在线抓取和费用。
- 跨仓只读数据交换不变；revenue不直写wiki DB，wiki不保存revenue的consumer_analysis研究状态。filing保留provider适配职责，但不再成为第二个catalog/权限中心。部署上可仍三仓，不必同时做仓库合并。

## 四、把实施路径压成四个增量，不再机械执行160步

这些是待批准的方向；旧风险和测试用例不会删除，只重新安排。保留每个关键阶段独立agent审查，减少重复手续而不是放弃审查。

1. **先固定一个读取合同与“位置无关”测试。** 选已有真实财报，四root等价查询；明确“本地最新/联网更新”“只读原文/解析/外发”的区别。独立审查只看这份小合同与反例。暂不做模型升级、复杂回测或legacy大删除。
2. **收敛resolver/storage。** 一个地方筛可读副本/选版本/open验真；kind只负责解析输入。去除company特殊回退和元数据priority耦合，保留透明诊断。实际原文试验通过后再把旧分支切为兼容适配，不两套长期并行。
3. **瘦身两个消费者与producer入口。** revenue/filing只用来源ID和所需能力；合并多层薄subprocess、删除上游DAG推导重复、将下载/加工提交唯一队列。使用现有只读reader/持久任务设计，避免再建第三套系统。并发保护的替代测试通过才退出pause/resume scope。
4. **安全与运维做独立小收尾。** 先修真实自动回收风险并保持原文不可改；按现有版本/worker保护要求完成一次真实有限放量，再结束影子/legacy迁移。只保留需要的健康检查与运行记录。普通读取无需等待7/2/1/1；这些周期只约束对应持续上线资格，不抹去历史未达标要求。

收入模型的单位、发布事务、回测错误是真问题，但不应成为“打开一份财报”必须先修完的前置。把它们留在revenue业务轨道，而不是继续耦合进数据湖读取。

建议复杂度预算（验收时看结果，而不是文件数量）：读取权限规则一个来源；消费者代码零特定root名/路径分支；一次资料查询最多一个跨仓CLI边界（非对复杂provider网络流程的限制）；无写读取零worker控制；迁移兼容分支有明确退出条件；新增一个root不改消费者；每个运行状态有明确拥有者。不得为达预算隐藏同一逻辑到巨大函数或删必要验证。

## 五、最少但决定性的真实验收

以下未来在获批隔离目录与真实原文副本进行，不修改用户源目录；本轮未运行：

1. 同一真实PDF分别置于四个获批root：相同查询得到相同source版本和业务字段；只允许诊断中的物理位置不同。改变priority不改变公司/期间/内容可信度。
2. 四副本同时存在：删除/离线首选副本（仅隔离夹具），正常换同hash副本；不下载、不重解析、不改变来源引用。全部不可用则明确unavailable。
3. 报告移动目录/改文件名：重新索引后原source引用和EvidenceSpan locator仍能打开；不要把旧路径hash当业务身份。真实修订则必须成为另一版本，不被去重吞掉。
4. 增加第五个已有支持格式的root：只改注册配置，filing/revenue零代码改动。若是全新格式可新增adapter，但不能新增业务权限分支。
5. 正确本地财报缺历史下载URL：可只读预览并显式标provenance不足；若正式分析要求的公司/期间/来源身份未验证，阻断该分析而非自动再下载或伪造元数据。
6. 本地查询全程零写/零网络/零worker控制；exact二次读取不重复解析/LLM。独立OS观察和产物账本证明，不信自身calls=0。
7. 跨root路径逃逸、文件被替换、未知外发、批量超scope必须拒绝；安全拒绝不通过移动到另一个public root绕过。原文纯预览与LLM处理分别测试。

每个阶段只需一份输入版本清单、一份独立验证结果和一次明确决策；真实删除/外发/后台恢复另保留其必要批准。实际加速幅度需前后测wall/CPU/I/O/进程启动次数，本轮没有新profile，不能承诺倍数。

## 六、本轮取证范围

主agent读当前config、runtime snapshot指定字段、store/models/service/resolver/scanner/policy/adapter_dispatch/reader和LLM出口相关代码；独立有界agent核filing/revenue消费路径，返回7类证据。CodeGraph部分行号滞后，定位后按当前文件正文核实。未全文重审全部三仓、不读取真实报告正文、不运行生产库/网络/worker，不把源码推理写成现场性能或全部安全验收。

建议下一步是确认上述“小读取合同与四阶段收敛”方向，然后再修订旧实施清单。不是现在就删除95个门或执行旧160步，也不再新增一套庞大的批准平台。
