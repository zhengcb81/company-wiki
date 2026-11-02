# R6 来源语义 R4 — 最终集中独审

结论：**PASS_ENGINEERING_SOURCE_AXES_CURRENT_CANDIDATE_PENDING_CI**。当前限定工程范围未发现需返修的 P1/P2。ROOT 仍须以同一候选的完整 CI 绿为并线前提；本报告不代签真实 H1、摘要、缓存恢复、RF 采用或整个 PWF 完成。

审查人 `/root/rectification_review_a`，日期 2026-11-02。源码提交 `39f3a6049d5bf3b473d37f7c1ae33d27a04b5b03`；实测及结束候选 **`2b0787dc1c5352cd8566fc71fc585afe735ec75c`**，工区 `C:/Users/郑曾波/Projects/company-wiki/tmp/architecture-r2`。8 源码＋3 测试的 11 项 raw SHA 与作者冻结清单一致，已独审 gate 7 项也未变，合计 18 项均核 Git LF blob 一致。精确 SHA、历史 JUnit、复现源码与观测值见同名 JSON。

## 共因修复结论

上一轮的错链是“未知 NP 默认 specific → 泛 operating 角色当 payload → 业务相关/事实升级”。当前删除了 default-specific 和营销修饰词补丁。句法矩阵、NP、从句绑定只回答原话结构；原 argument owner 才提供正向语义证明。无证明的泛 function/goal 保持原文与 None，不能靠没落入抽象词表证明有价值。

`_ReadingRelationObservation` 现在显式区分 payload、scope、unknown，并由准备回调和后续 fact 投影复用同一规范 clause 缓存。原 `bool(relations)` 旁路已移除，`operating_mechanism` 不能仅靠 `roles.operating` 出现。资料中的产品范围/工序/用途/计划或统计口径可以是 source description，单独不代表事件、当前状态、数量证明或财务豁免。兼容 relevance 收到已有 roles 时也不能用旧 eligible 标签推翻 None/False。

新增 scope 类别是通用流程、作业、市场、地区、客户等语法角色及局部 argument 绑定，没有公司名、行业白名单或针对首轮反例的营销词列表。真正已有 argument proof 的语义继续有效，不被 scope 轴擦除。

## 独立实际执行

正常宿主 Python 3.13.9 / pytest 9.1.1，显式候选 config/rootdir/confcutdir 和模块真实路径断言；仅使用合成文本、内存材料及自有 tmp，不读原件、不加载 LLM/OCR 模型、不联网。没有重跑作者 290/280/37 或整仓 Unit。

首轮 **31 项：30 passed /1 failed，8.39 秒**；唯一失败是独审新断言本身的过强假设，详见下节。只复验修正后的那一项，加一个直接数量/受益者数量对照，**2 passed，3.83 秒**。因此是 30 个未变通过＋1 个纠正的独审断言通过＋1 个新增数量对照，共 **32 个唯一测试场景**，不声称最终另跑过一整组 32 例。

- 原 R3 独立 5 个反例全部闭合；另加 3 个未见的正面修饰 NP、两种顺序的陌生双成员列表，均保持 raw/prepared None、unresolved、不相关、无 fact/财务豁免。
- 已知 False 原样保留；产品目录及中文客户作业范围可作为 description/support，但在 raw None 时不变成事实、当前阶段或财务豁免。两条陌生真实动作保持可读原话，23 个市场覆盖保留原数值关系证明而不造 milestone/current-state。
- 普通财务句加未知功能、财务因果句、无问号 WH、relative 片段、受益者 relative 均不借业务范围放行。1700 个客户的直接目标仅保留原语言未决数量，不变当前数量；受益者 PP 中的 1700 不能转为目标 proof。
- 真实 public selector 的 mixed 缺资源仍为 deferral/partial inventory；真实超长 scope 不影响独立健康 scope，几何覆盖和 source-processing 完整度保持分轴。真实 `NativeSelectHandler` 正常/缺资源两种路径都能经过严格 wire，输出当前完整或 partial 状态。
- scope observer 工作前预扣、False memo、目标 callback memo、budget stop 后半份 assertions 不缓存为完成、显式 compat WorkBudget 透传均通过。
- 独立在内存模拟 `source_context` 算法字节变化，**实际 generation-cache** 的 text/PDF 两条入口都由先前 complete/match 变为不匹配；未修改真实源码字节。

## 独审断言自身的透明纠正

初始新例 `Our production services cover downstream assembly workflows.` 被我误写成 raw payload 必为 None。实际原 argument owner 已对 `assembly workflows` 给 True，当前是保留原有正向证明，非范围轴升级未知词。独立 AST 比较确认 `_argument_payload` 与 R3 基线完全一致。

只修改 self-owned probe：raw/prepared 轴必须一致；raw None 才要求 description、无 fact、无财务豁免；原 True 不应被 scope 擦除，且不允许制造 milestone/current-state。该项定点通过，产品代码和作者 oracle 均未改。原失败 JUnit、原始 raw/prepared 观测和纠正理由完整保留在 JSON，不把它记成产品 RED 或静默换绿。

## 测试修订、版本及预算

逐 case 身份核对，而非看总数：**R3 最终 `r6-r3-np-final.xml` 的 semantic_axes 本来就是 93，R4 最终也是 93**；此前 95 属非实际清单计数。原宽泛 positive 参数中的两条 goal 和一条未知目录，恰好移为两条明确 unknown goal 参数＋一个 unknown catalogue 测试，3 出 3 入、文本各保留。其余仅 POS 的目标正例期待修订有明确 ROOT 授权与 before/after 记录，不回写旧 PASS。原 CI20、真实 native60 所属的 5 个整文件，以及 R4 public deferral/R5 handler 两文件，均与原候选 Git blob 字节完全一致。

独立核对作者两轮合计 **30 份历史 JUnit SHA**，均找到且匹配；保留 RED、中间失败、最终绿。作者 290/280 运行早于最后一行 compat account 透传，最后 37 和本轮独立 compat/public 检查覆盖当前版本，不冒称前两大组此后重跑。

同一个 WorkBudget 进入 Session、直接 assessment 和显式 compat owner；新增扫描按实际 scope/目标长度预扣并 memo，保留原 16M/112、4096 chars/1024 tokens。未发现全源无界重复扫描或提高全局额度；这些逻辑工作系数仍不是机器指令计数，本报告不据单元秒数保证真实 H1 成本/召回/时延。

## 清理与剩余范围

唯一独审 tmp `C:/Users/郑曾波/Projects/company-wiki/tmp/j4` 初态 absent，最终核对绝对路径、精确末级、无任何 reparse 后 native PowerShell 清理，结束 **absent**。源码/索引/真实 Git/主 PWF/配置/模型/原件未改；原 hook mode WIP 保留。T3 `tests/unit/document_understanding_note_scope/` 仍 untracked/RED，未收集、未审、未签通过。

能力边界依然真实存在：某些陌生但实际有价值的目标，原 owner 没有正向证明时仍 unknown；原文可检索，不能用 default-specific 或行业词补丁掩盖能力不足。后续由原真实 H1、正式摘要、缓存恢复和 RF 采用节点衡量召回与效用。

本节点独审完成 **STOP**。ROOT 负责候选完整 CI、并线、正常提交推送和后续 C 验收。
