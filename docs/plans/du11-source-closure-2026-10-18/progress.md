## B2 复审 v2：2 个新 P1 已修（2026-10-18；优先于上一节）

复审仍判 **REJECT**（工程 7/10、合同 5/10）：v1 的 P1-1/2/3/5 关闭，P1-4 部分关闭（furniture 邻接错误），另发现 P1-A/P1-B 与 6 个 P2。已逐条修复：

- **P1-A 泛称伪声明**：拉丁名改为“大写专名 token 序列”，CJK 名排除公司/产品/这些/计量词；`We sell products…`、`Our products…`、`公司产品系列丰富`、`这些产品线` 不再成为声明。
- **P1-B furniture 邻接**：回溯改为与“最后保留的 unit”比较，并记录被跳过的 proven furniture 数；跨页 carry 仍按真实邻居 `(p1,p2)`，错误 carry `(p1,header)` 不再接受。
- **P2-A** deictic 先识别实际 head（含系统/平台/方案），不支持的 head 回退 legacy，不再把“这些平台”当产品。
- **P2-B** collective marker 必须出现在声明之后，同句客户列举不再挂到产品系列。
- **P2-C** 客户/供应商主导句判 `quoted_related_party`（不捐赠），公司主语判 `issuer`；新增正反例。
- **P2-D** 重跑三源并绑定最终代码：bindings 含 `product_reference a1300818`、`narrative_antecedent 41d42ef7`、`relations dce431d9`、`narrative_reading ddc36db5`；`deferral_reasons` 三源均可见（CN 5、HK 2、US 11 unresolved）。
- **P2-E** 新增 9 个负例/正例：泛称句、unsupported head、同句 collective、attribution 正反、furniture carry 正反、separate-window。
- **P2-F** 同页跨窗口由 ordinal 证明；跨页只认已证明窗口边，separate-window 不桥接（有反例）。`SourcePageFlow` 只暴露汇总、不暴露边，故不接线并如实记录。

测试 `tests/unit/du11_source_closure` **99 PASS**；selection 738 PASS；全量 unit 见 progress。真实三源：CN 10/10、HK 7/7、US 8/8，work 6,133,095 / 13,157,181 / 7,993,449，0 API、原件/gold 不变。收据：`b2-v2-20261018/`、`b2-real-sources-v2-20261018/`。

**Next Step：** 三修后复审 → 提交/推送核精确 CI → 正式 C。

---
## B2 独立审查 REJECT → P1 全修（2026-10-18；优先于上一节）

独立审查（非作者 agent，绑定 family-scope 快照 SHA）结论 **REJECT**：工程完整度 6/10、合同一致性 4/10，P1×5、P2×11。已逐条修复，报告见 `review/b2-antecedent-independent-review.md`。

**P1 修复：**

- P1-1 声明上下文端到端：`_candidates` 现在把声明的原始 unit id 同时写入 budget 包与原始 eligible 包；`_context`/citation view 的 target 组变成 support=target、context=declaration（新增 `select_reading_evidence` 端到端断言）。
- P1-2 envelope 命名空间：声明按原始 id 计数，carrier 通过 `expand` 展开为全部 originals；不再拿 carrier id 查 `original_units`。
- P1-3 offset：声明/成员 ref 直接在原文上匹配（不再用压缩空白的匹配视图），CJK 换行场景新增回放断言。
- P1-4 跨页：从 continuity window 导出 `page_carries` 并传入窗口构建；未证明物理顺序 → `complete=False`/`partial`；proven running furniture 可跳过；`project_for` 与真实 section key 接线。
- P1-5 内部声明：只接受 deictic **之前**的声明；forward declaration → `missing`；两个内部 family → `ambiguous`。

**P2 修复：** 单卡 reference deferral 不再让整篇 `status=partial`/`coverage_complete=False`；unread/unproved/cap → `partial`；envelope block key 改为 `(parent, page, pdf_block)` 且 carrier 展开；坐标缺失不再借为相邻；collective members 只取声明所在句；attribution 按 role 保守判定；产品 head 词表改为 `PRODUCT_SUFFIX` 子集＋import 断言（无第二套词典）；reference deferral 前置于 128 截断；probe `source_bindings` 绑定 3 个新模块；readiness 异常统一转 `partial`。

测试 `tests/unit/du11_source_closure` **90 PASS**（新增端到端 context、forward、内部 ambiguous、换行 offset、carrier envelope、跨页 carry、文档状态、collective 负例、客户声明不可捐赠）。

真实三源（修复后，0 API、原件/gold 不变、同 16M）：CN 10/10、HK 7/7、US 8/8；work 6,133,095 / 13,157,180 / 7,987,497。CN 收据首次可见 `REFERENCE_UNRESOLVED=3`、`REFERENCE_ENVELOPE=1`；t32/t34 精确 SHA 仍 `selected_matches=0`。收据：`b2-reviewed-final-20261018/`、`b2-real-sources-reviewed-20261018/`。

仍未关闭（如实记录）：单数产品指代按计划保留 legacy admission；第三方归属只做句内启发式（`THIRD_PARTY` 出现在声明前且无 `ISSUER_WORD` 即不捐赠），不做完整引述解析；运行期 selection cache 是否因语法模块字节变化而失效未验证。

**Next Step：** 复审 → 正常提交/推送/核精确 CI → 进入正式 C。

---
## B2 有界先行词工程节点完成（2026-10-18；优先于历史）

B2 已按 `review/antecedent-source-interface-final.md` 实现，并跑通真实三源回放。状态：**ENGINEERING_GREEN（独立审查/发布进行中）**；正式内容 C 仍 OPEN。

本轮改动（只扩展现有责任层，没有第二套 detector/Store/预算/产品词典）：

- 新增 `document_understanding/operating_states/product_reference.py`：产品 deictic 与具名声明/集体枚举的纯语法；单数指代与族指代分开标记。
- `OperatingRelationSession.reference_closure()`：按 target + 有序 predecessor + window_complete 缓存，返回 `not_applicable/unique/collective/ambiguous/missing/partial`；声明 ref 保持原始 namespace。
- 新增 `source_catalog/narrative_antecedent.py`：按真实 source ordinal 的有界前驱窗口（同 source/section/project/role/kind，连续性不足即停，cap 截断标记 incomplete）＋ 联合 envelope（8 原 unit、4 个 `(source,page,pdf_block)`、2048 原文字符）。
- `SourceOperatingSession` 增加 originals 只读回退、antecedents、`reference()`；声明 ref 按自身原文校验，不经过 target offsets 重映。
- `_candidates` 把 readiness 前移到 graph 与任何 fact/cache 之前；`ambiguous/missing/partial` 只 defer 该卡（`REFERENCE_UNRESOLVED`），envelope 超限只 defer（`REFERENCE_ENVELOPE`），`unique/collective` 把声明原 unit 计入 required context。

范围收敛（详见 findings）：只有**族/系列指代**（系列、产品线、上述、前述、这些、该等、these/those/such）进入门禁；单数「该设备/该产品」保留 legacy admission，避免把没有跨窗身份主张的句子误 defer。该收敛由 4 个既有 selection 测试暴露后决定，不是放宽断言。

真实三源回放（0 API、0 原件副本、原件/gold 前后 SHA 不变、同 16M 账户）：CN 10/10、HK 7/7、US 8/8；selected 96；CN 6,141,589、HK 13,171,440、US 7,993,452 work units。t32/t34 精确 SHA `selected_matches=0`；p17「该系列设备已付运」以 `REFERENCE_UNRESOLVED/missing` 显式 defer；CN withheld 137（`REFERENCE_UNRESOLVED` 2、`REFERENCE_ENVELOPE` 1、其余为既有非可选/预算）。收据：`b2-family-scope-20261018/`、`b2-real-sources-20261018/`。

测试：`tests/unit/du11_source_closure` 78 PASS；全量 unit 结果见 `progress.md`（4 项宿主环境失败不计本节点，逐项列出原因）。

**Next Step：** 独立审查 → 修复确认项 → 正常提交/推送并核精确 CI；之后才进入正式 C（三供应商原语言摘要、付费恢复、同/跨 run 缓存、FF/RF 真实消费），不得用本节点工程绿或金标命中代替内容 C。

---
## 当前两卡接收与发布结果（2026-10-18；优先于历史）

接手下一主线时先读[DU11 当前主线接手指南](review/harness-handoff.md)；本文件后续各节定义 B2 的详细行为和测试合同。

RF/FF两张DU11卡功能工程已接收、全部交付提交进入各自主线。CWP producer先发布0ccdc689（6801PASS24SKIP346.26s＋142合同PASS48.31s，精确CI39094787278 success）；RF runtime f8002f5f（18独立行为接收、416PASS＋36子测、CI39092538354 success、6源码定点安装）；FF最终e8740748（873PASS7SKIP78subtests91.13s、精确CI39095654355 success、6物理源码依赖序原子安装，双根imports/help通过）。RF唯一兼容版本表两阶段正常更新：e7364639的wiki pin/CI39094965965 success，再9669c4d7收敛filing=e874、wiki=0cc、revenue=f800，最终416PASS＋36子测73.74s、远端一致，精确CI39095818018已completed/success，三仓本次发布CI全部绿。

正常FF发布共3次尝试=2RED+1GREEN：先修异构schema类型丢失及既有mypy hook漏掉transitive scripts依赖，再修旧“未知日期”夹具缺provider导致测试错位。保留原完整拒绝/0下载/日期资格断言，不删测试/提高阈值/跳hook。JSON stdout的GBK/UTF8根因和集中CI表漏DU11纯回归也已修并独审；最终类型delta独立公共mypy＋10有限控制通过。详细收据见review/du11-reception-closeout.md以及各publication报告。

未动生产原件/gold/配置/密钥/Dayu/IQS或作者树，没有新收费模型调用。RF旧3个assurance WIP保留，stage1曾观察weekly_manifest自然变化，不归因/不恢复旧值；stage2前后相同。一个RF外层审查Temp仍NOT_CLEAN，历史PermissionError后平台拒删，保留且不换通道重试；内部端到端原样恢复。未知发布日期的/3投影仍如实source_availability_unknown，不伪造日期或另加许可。

整体PWF仍OPEN：t32最新真实诊断不再selected；t34仍缺有界先行词。下一实现按review/antecedent-source-interface-final.md，在现source/operating唯一owner、同parent16M及8units/4原block/2048chars封闭依赖，再做正式三供应商摘要、收费/activation恢复、同跨run缓存及真实FF/RF消费C，之后holdout与RF循环。不要把工程/金标命中当内容C通过，不重做已接受DU11或新增小节点签收。

## 当前发布结果（优先于下方历史）

CWP已正常发布remote master=0ccdc6896ee58063ff827e9ceab16043c7550e0c：全量6801PASS24SKIP346.26s、独立合同142PASS48.31s，未删测/提时限/跳hook。精确CI39094787278已completed/success，匿名API核对相同HEAD。详见review/du11-cwp-publication.md/json及保留的原push日志。RF runtime已发布，集中compatibility/current.json须先更新CWP producer pin，随后正常发布FF，再同步安装源码/核精确CI。t32最新诊断不再selected；t34有界先行词及正式C仍OPEN，下一实现接口/TDD见review/antecedent-source-interface-final.md。

# Progress

## 最新：正常push超时与两个独审delta（2026-10-18）

母仓6ee5ebf1正常push未成功：完整unit约96%时达到600s，日志在母仓`.planning/shared-reading-production/du11/push-source-flow-reader-port.log`；远端仍9c681ed2。原日志保留，非断言失败证明，也不能因PowerShell尾部命令exit0误报发布。现用已声明xdist对完整unit目录启两个file-scheduled worker，不删测试/改期限，窄测和contract不增加启动开销。实现先3FAIL/1PASS，修后4新及80既有gate控制共84PASS6.44s。独立4新控制PASS4.69s，另3窄测/非零退出控制通过；真实2-worker/SQLite超时反控5s期限后20.064s返回124（既有execnet约15s关停），返回时worker均退出、gate/outer Temp均删除。完整7000组运行提速未签收，留待正常push；不增加第二进程管理框架。

源编号修复先3RED、补未知counter反控1FAIL/3PASS，再77PASS3.95s。独立新4＋自选6跨两轮10个不同控制通过，首轮9PASS/1FAIL是审查控制误要求局部拒扣后parent.exhausted=True；按既有B1语义应保留父余额，仅修外部审查控制且单跑通过，生产源码未迁就错误断言。报告精确SHA绑定见review/page-local-readiness-independent.md/json。实源诊断page-scope-after-counter-fix明确非冻结验收/计时证据：CN10/10、parent6142162、旧t32不再选中，t34仍选中，0API/原件gold不改。该剩余先行词问题不混签绿。

## 当前发布与接收（2026-10-18）

物理/cache最终独审已完成：PASS_PHYSICAL_BUDGET_CACHE_COMPONENT，27有限PASS8.51s、5源码/2测试精确SHA前后相同、两自有Temp均删除；未重跑219/763，不代签一般语义/先行词C。FF隔离根修已正常commit a9c2dcf7，等待先producer发布；新CWP test唯一静态F811以同既有pytest fixture参数noqa说明，runtime与各独审冻结一致。

B1远端9c681ed2已精确CI39092308121 success，正常push5221PASS/11SKIP517.05s，未跳hook/改deadline。RF外包已18项独立行为接收，正常main发布f8002f5f（416PASS＋36子测65.46s），精确CI39092538354 success，2物理技能目录6源码同步、原3WIP SHA不变；验收一次外层Temp被平台拒绝删除仍NOT_CLEAN，其内部E2E恢复真，未再换方式删除。

FF初审102PASS＋4实际反例发现日期/股票码根因，ROOT隔离修34PASS后不同agent28控制＋真实HK TXT1链最终复审PASS；29unique跨次通过、0ET/network/原件修改，作者树未写。仅待CWP先发布reader canonical端口，再正常FF commit/merge/push/定点同步。

物理早期763PASS45.71s后独审新发现繁体新issuer、English显式新产品主语被接到旧半句；修共享grammar后225PASS4.70s，又补source grammar缓存漏口/N²/真实parser MIME/per-pair coverage，先6FAIL及8FAIL30PASS后修，最终219PASS10.11s。最终实源零收费CN/HK/US10/7/8及canonical一致，parent work6106955/12820408/7975948，原件/gold不改、0copy/ownedTemp删除。但实际CN t32/t34仍selected，整个语义闭合/先行词及正式C仍OPEN。最后delta独审进行中，未拿旧收据重签当前源。

CWP reader新端口及同次manifest读取先3RED，第一次相关54P3F（2fixture config目录错、1暴露global pin兼容），改后4针对PASS；新filing_reuse单观察反控2FAIL3PASS指出None未观察混淆，复用scope sentinel修，最终59PASS37.37s。FF跨仓最终review绑定两reader真实源SHA，原manifest/原文不变、不新增人工门禁。

## 最新 B1 节点（2026-10-18）

最终独审PASS_B1_ENGINEERING，精确3文件SHA前后相同；独立9PASS/3.27s＋3有限控制（两入口预扣失败0访问、外部context正控不丢），自有及pytest重定位Temp均删除。真实三源budget-source-replay/receipt.json：CN10/10、HK7/7、US8/8，canonical同分；分别12.665/27.042/11.721s，同一16M账户各用5758585/12269996/7975948，无耗尽。原件/gold不变、0POST/0原文复制、ownedTemp删除。内容/C仍OPEN，不能用此工程节点代签。

现production source metadata与native continuity已复用同parent账户，移除逐member重建容器集合的N²行为。独审指出两预扣前遍历并新增CountedIds反控；RED为7PASS/2FAIL，修复后739集中PASS/50.52s。首次大组733PASS/4FAIL是四个新fixture错误，完整失败保留budget-index-full-green.log（文件名非结论）；改正后目标行为才真正执行。最终独审及真实三源回放进行中，B2物理跨页与先行词未实现，正式付费C仍OPEN。

母e33d40ed正常push6741PASS/24SKIP/580.05s+142合同PASS/37.31s，精确GitHub CI39090720114 success；文档0099dd5d已推。B1未发布前的后续记录与母结果分开。下方是历史顺序证据，不作为当前Next Step。

2026-10-18：建立ROOT后续独立包；无新生产源码改动、无API/原件写入。前置工程9eff4ee7已独审正常提交并合母e33d40ed，母正常push进行中。阶段A RED尚未实施，阶段B/C均OPEN。

## Stage A physical behavior RED

Existing production _prose_reading_packages/_candidates/finalize_selection, not a missing-module placeholder: tests/unit/du11_source_closure/test_cross_page_reference_plan.py collected15,8FAIL/7PASS4.45s. Six CN/EN × background/event/risk positive multi-original carries currently split; five distinct (source,page,block) sentence can expose right suffix; one-span budget currently exports only half a cross-page sentence. Seven unknown/changed-column/page-gap/scope/font/heading/table controls pass. No production changes yet; draft tests remain only ROOT isolated branch and are not in mother pending push. Next write furniture/independent-statement/parent-budget and antecedent cases, then shared owner implementation.

StageA expanded19cases:10FAIL/9PASS5.61s, including explicit running furniture and exhausted parent geometry scan. Root began systematic budget connection: _Analysis uses existing WorkBudget.scoped, source candidate metadata reserves before indexes, same parent flows into geometry and operating session. First zero-parent controlGREEN1PASS/102deselected4.83s: -k applied to all requested paths, so this is explicitly not103PASS. Correct explicit-node compatibility command is separately running. Full physical crosspage/antecedent implementation and independent review remainOPEN; mothere33 normalpush succeeded6741PASS24SKIP580.05s +142contracts37.31s and remote master exactlye33d40ed7688cfdcead1e02d55542f7026d0b8e5. RemoteCI352/runs39090720114 currentlyIn progress.

Metadata performance root cause reproduced on actual _prose:16/32members visited288/1088times (quadratic),2FAIL5.05s; no timing-only claim. One owner external-context index and one combined exclusion set now avoid rebuilding whole member/context sets for each paragraph. Reservations account actual membership/section/header-context edges and sort work on the same parent; _candidates returns finite partial if preprocessing cannot reserve. Concentrated88PASS5.59s covers2linear controls/2parent-budget+previous native/prose readiness controls. Source crosspage/antecedent RED remains intentionallyOPEN and unmerged. New design review approved overall owner direction but is not final implementation acceptance.
