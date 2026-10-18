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
