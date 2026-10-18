# DU11 摘录优先执行方案独立设计审查

## 结论

**方向可行，按以下边界批准设计；不代表实现或真实 C 已通过。** 引用 ID 合法不证明自由改写真实。把模型职责压到“选择程序事先闭合的原文卡 ID”，再由程序从冻结来源组装原语言摘录，可以系统性消除本次 HiT3/UniMax 串产品、跨任务借否定、改数字/单位等自由生成通道。单纯提高20上限、加提示词、接收合法ID或精确子串都不够。

## 1. 原文闭合必须归程序

模型不得生成 canonical text、任意offset/子串、产品数字或 actual/planned。优先选择完整原文 part 或已有 source-owner 闭合 scope。一个精确子串也可能把“尚未量产”裁成“量产”；不允许靠关键词匹配把它判为真实。程序必须保留主语、否定、条件、期间及跨 fragment 限定，不以省字为由删 closure。

原片段本身只有“该新产品”、半句或缺限定时，仍是 unresolved/deferred，不让模型从全局记忆补全。source roles 和 support/context 分工沿用原 owner；问题不可改管理层陈述，context-only 不可当事实。混合实际/未来状态用 uncertain/needs_review 或拆已有明确 owner scope，不能整个卡写 actual。歧义表格的原数字不是可靠列归属证据；这类内容保留 evidence，但不能因“精确摘录”而升级为带归属的数值业务事实。

模型稀疏选择本身不会修复遗漏：若还允许无理由选19/64，t17等缺失会重现。程序先以现有 strategy/section/quality 与公平范围分配制定有限 admitted 集合；每项有已输出、精确重复、上下文不明、容量延期或未处理等 disposition。容量足时保留安全闭合业务卡，模型排序不应静默删掉既定覆盖。缺项不能冒称完整；不强求64全选，也不允许金标或公司专名进入生产规则。

## 2. 实际容量与兼容性

| 层 | 现有真实限制 |
|---|---|
| canonical summary | `SUMMARY_RESULT_MAX_BYTES=65536`，包含身份、全部canonical ID、support/context与原文 |
| selected result | 1MiB |
| bundle/RF body | 1280KiB / 1,310,720B |
| model final content | 128KiB，并受配置8192 output tokens |
| HTTP envelope | 配置值，默认262,144B |
| BudgetedCaller 2MiB | 最终artifact输出预留，不是模型正文上限 |

canonical claims 没有20/280固定上限；限制来自旧model/scoped decoder。新mode可以接受完整原文长卡，旧v4语义20/280不变。实际序列化后逐卡规划，不从2MiB或“64task”推想容量，不裁closure、不扩canonical、不藏metadata第二summary。

纯JSON读取冻结CN selection作容量测量：96spans、64tasks、7739原字符。每task全部support原文＋完整support/context IDs＋实际summary身份结构的**size-only候选为43,913B**，共8223摘录字符；最长892字符，仅1项超过280。64task ID-only示意响应395B。收据 `extractive-design-capacity-probe.json`。这是可容纳性证据，**不是这些任务全部安全闭合或可输出的证明**，没有实际新协议、摘要或bundle验收。无需先预定4次付费调用；只有真实输入/输出/bytes不容纳时才明确defer，或使用现有AUTO有限jobs。

RF现有 `scripts/company_wiki_narrative_contracts.py:365–431` 接受非空claims/text、原有枚举/role/ID，不限制20/280。SourceExport与claims字段可不变。FF仍只承担来源复用/获取。实现和测试限定CWP，不修改正在施工的RF/FF文件。精确选中材料和完整closure绑定在有限内部plan与原响应中；canonical text须可从绑定来源确定性重建，不向claim乱加未知字段。

## 3. 新协议、缓存和耐久恢复

增加独立 internal projection/prompt/request/decoder 身份，完整execution-plan/task/source/selection/hash进入既有generation。旧v4失败22条响应仍失败，保留原版本、费用和字节，不裁成20或伪装新ID协议成功。实现源码SHA改变可能使旧generation缓存失效，这是因果边界；历史冻结identity不等于今日decoder相同。

当前caller只settle responseSHA然后返回，summary随后decode；failed_final是不足16KiB的可裁诊断。`finish_attempt` 才写outbox，所以只改最终outbox无法保护provider已返回、decode前崩溃。原 `NarrativeArtifactDraft` 又强制role=narrative_bundle，不能把响应伪装成可见bundle。

最窄接线：复用现有内容寻址对象存储保存完整已观测final bytes；在已有attempt/reservation添加小的不可变response pin/receipt（必要时做additive migration），记录准确bytes/SHA、request/body/task/source/selection、model/prompt等，不存key/header。对象耐久后，fenced AUTO事务一次写pin并settle已知usage，再交decoder。原verify/outbox仍只发布最终bundle。不建立新Store、ledger、响应cache或人审许可。

崩溃后只有pin和完整字节均验真且请求/protocol一致才0POST重放；损坏、裁断、缺失或错身份为not_replayable，原unknown/保守费用不减，不能盲目重发。provider返回到首次耐久记录前的不可观测窗口仍可unknown，不能承诺恢复从未落盘的字节。完整final正文和provider envelope要区分；本次结构错误重放只需完整final，若要恢复HTTP envelope解析故障必须在原HTTP owner观测全响应，不可用截断diagnostic推造。响应按SHA仅存一份、计物理空间，后续retention依既有终态/引用规则，避免重回多份大记录。

## 4. 最小TDD与大节点验收

### A：离线协议与计划

- 旧22条/v4保持原失败；新协议拒绝自由text、错ID、上下文ID、错task及旧响应冒用。合法ID串产品无自由改写通道。
- 否定前缀、跨fragment条件、残主语、问题/回答、混合current/target和歧义表格正反控。不能只检查输出是否原文子串。
- 64task、乱序噪声、精确重复、稀疏回包都有有限disposition；不先20、不固定四批付费、无金标。
- 新mode892字符完整卡；旧v4仍280。实际UTF8/长ID/closure/身份65535/65536/65537边界及单scope超限诚实defer，不截卡。

### B：工程和恢复集中验收

- owned临时lake内真正 select→新mode→canonical→verify→bundle/transport；固定RF消费夹具验证>20/>280及错角色/ID否控，无消费者改动。
- response pin后/decode前崩溃：同请求0POST、usage一次；无效响应也耐久保留但不伪成功。decode后/activation前走原outbox，same/crossrun恢复。
- byte/hash/source/task/input/protocol错配、missing/clipped、对象写/SQLite/lease失败均0POST且保留费用。
- 物理response记录计数、临时目录/哨兵恢复、原件/config/productionDB未变，不复制原文、不新库。

### C：一次集中真实验收

A/B通过后冻结accepted源；配置MiMo/DeepSeek/MiniMax与母账2Mtokens/$20不变、旧unknown保留。分别量输入selected recall和最终交付source-extract支持，CN10/HK7/US8与每条实际输出的产品/数值/货币/单位/否定/stage/role一起审。不是输入有10/10就摘要通过。随后实际activation中断、same/crossrun0POST、source tamper和独立测试目录恢复。保留partial/unknown/deferred，不谎称整篇完整。

## 审查执行边界

本次仅源码/诊断/冻结JSON读取与纯序列化容量测量；**0测试启动、0PDF读取、0网络、0模型、0生产源改动**。详细源SHA、边界和检查点见同名JSON。ROOT尚需冻结具体新wire及response pin schema；本报告批准设计方向，不替代实现独审与C。

## 最终收敛与施工文件建议

ROOT已确认：program优先保留所有admitted、closed、质量合法且64KiB内的source cards；LLM只提供这些任务的有限disposition和重要性排序，不能改正文或删除安全卡。缺项unprocessed；新mode明确 `source-extractive / reading-model-input/5`，没有额外compact/digest或第二store。

无模型时可以先生成确定性**内部**source-card计划，但现canonical completed强制draft与真实model观察，不能伪造model_id或responseSHA发布completed。配置/调用缺失仍诚实不可用；实际模型已返回但排序无效时，可以使错误只影响排序诊断，正文仍是程序原文摘录、保持真实response身份及needs_review，不冒称生成式语义通过。无模型直接发布若将来需要，应单独演进契约，不混进本轮。

| 施工面 | 建议文件 |
|---|---|
| 原文卡和实际bytes计划 | 既有 `document_understanding/summary_tasks.py`＋新 `document_understanding/source_cards.py`，只处理原owner任务/support/context，不新解析器/库 |
| 新internal协议 | 新 `automation/narrative_model_extractive.py`＋既有 `narrative_model_runtime.py` 分派；独立v5身份，旧v4不放宽 |
| 正式接线 | 既有 `narrative_summarize.py`、`narrative_generation.py`；同caller、同母账、同verify/outbox，不发明第二执行器 |
| 完整响应恢复 | 既有 `narrative_model_caller.py`、`narrative_run_store.py`、AUTO migration和LocalNarrativeObjectStore；小pin＋内容寻址对象，不新Store、不响应伪bundle |
| 验收 | 新有限source-cards/protocol单测，既有caller/store恢复集测，以及原phase-C runner集中真实验收 |

外包RF/FF文件保持只读不改；兼容验证使用冻结wire夹具。具体schema及源码实现仍须TDD后独审，此设计结论不是跳过工程验收。
