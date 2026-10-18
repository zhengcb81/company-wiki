## 当前两卡接收与发布结果（2026-10-18；优先于历史）

RF/FF两张DU11卡功能工程已接收、全部交付提交进入各自主线。CWP producer先发布0ccdc689（6801PASS24SKIP346.26s＋142合同PASS48.31s，精确CI39094787278 success）；RF runtime f8002f5f（18独立行为接收、416PASS＋36子测、CI39092538354 success、6源码定点安装）；FF最终e8740748（873PASS7SKIP78subtests91.13s、精确CI39095654355 success、6物理源码依赖序原子安装，双根imports/help通过）。RF唯一兼容版本表两阶段正常更新：e7364639的wiki pin/CI39094965965 success，再9669c4d7收敛filing=e874、wiki=0cc、revenue=f800，最终416PASS＋36子测73.74s、远端一致，精确CI39095818018已completed/success，三仓本次发布CI全部绿。

正常FF发布共3次尝试=2RED+1GREEN：先修异构schema类型丢失及既有mypy hook漏掉transitive scripts依赖，再修旧“未知日期”夹具缺provider导致测试错位。保留原完整拒绝/0下载/日期资格断言，不删测试/提高阈值/跳hook。JSON stdout的GBK/UTF8根因和集中CI表漏DU11纯回归也已修并独审；最终类型delta独立公共mypy＋10有限控制通过。详细收据见review/du11-reception-closeout.md以及各publication报告。

未动生产原件/gold/配置/密钥/Dayu/IQS或作者树，没有新收费模型调用。RF旧3个assurance WIP保留，stage1曾观察weekly_manifest自然变化，不归因/不恢复旧值；stage2前后相同。一个RF外层审查Temp仍NOT_CLEAN，历史PermissionError后平台拒删，保留且不换通道重试；内部端到端原样恢复。未知发布日期的/3投影仍如实source_availability_unknown，不伪造日期或另加许可。

整体PWF仍OPEN：t32最新真实诊断不再selected；t34仍缺有界先行词。下一实现按review/antecedent-source-interface-final.md，在现source/operating唯一owner、同parent16M及8units/4原block/2048chars封闭依赖，再做正式三供应商摘要、收费/activation恢复、同跨run缓存及真实FF/RF消费C，之后holdout与RF循环。不要把工程/金标命中当内容C通过，不重做已接受DU11或新增小节点签收。

## 当前发布结果（优先于下方历史）

CWP已正常发布remote master=0ccdc6896ee58063ff827e9ceab16043c7550e0c：全量6801PASS24SKIP346.26s、独立合同142PASS48.31s，未删测/提时限/跳hook。精确CI39094787278已completed/success，匿名API核对相同HEAD。详见review/du11-cwp-publication.md/json及保留的原push日志。RF runtime已发布，集中compatibility/current.json须先更新CWP producer pin，随后正常发布FF，再同步安装源码/核精确CI。t32最新诊断不再selected；t34有界先行词及正式C仍OPEN，下一实现接口/TDD见review/antecedent-source-interface-final.md。

# DU11 ROOT 剩余来源闭合实施

PLAN_ID=du11-source-closure-2026-10-18; PWF_PLAN_ROOT=docs/plans。唯一实现owner ROOT。作者工区沿用当前ROOT隔离checkout；母仓主线正常推送期间不改母仓源码/HEAD。RF/FF两DU11外包工区、Dayu/IQS不写。

## 入口与完成定义

**当前工程位置（2026-10-18）：** B1已正常发布9c681ed2，精确CI39092308121 success；RF外包已独立18项验收、main与远端f8002f5f、精确CI39092538354 success、安装6文件定点同步，旧3个assurance WIP不变。FF初审102项主链绿但4反例暴露发布日期及代码解释漏洞，隔离修后28边界＋真实HK TXT1链独审通过；待ROOT先发布CWP producer的canonical_identity可选投影，再正常发布FF，不让新flag先上线断链。

ROOT本节点是物理跨页/真实parser MIME/共享语法/因果cache以及FF reader端口完整组件，**不代表唯一/集体先行词或正式C已完成**。32ab6e06已合母仓5ad4295f/6ee5ebf1但尚未发布：正常push的全量单测在600s到约96%超时，保留原失败日志，不称已推送。现有xdist依赖用于完整unit目录的两个隔离worker，窄测/contract保持原运行方式、集合和600s期限不变；完整运行与远端CI仍待正常push验证。

新真实诊断查明paragraph_index每页重置，而ordinal为source全局位置；未知下一页底部计数块也不能抢先清掉上一页半句。修在同一native owner，未知前缀只defer而不伪造家具/正向拼接。77项相关行为通过、独立10个不同控制跨两轮通过；本次实源诊断旧t32“求的同时…”selected_matches=0，t34“该系列产品…”仍1，原件/gold不变、0API。该诊断明确不是冻结内容验收/性能收据；不得把10/10 gold命中当语义闭合通过。剩余有界先行词设计参见review/antecedent-owner-design.md。继续不读作者密钥、不写原件/gold/生产配置。

母计划 document-understanding-2026-10-13 为总控。前置代码9eff4ee7随e33d40ed已正常发布：6741PASS/24SKIP/580.05s和142独立合同PASS/37.31s；精确CI39090720114 success。母仓后续文档0099dd5d已正常推送，未触发新的行为CI。剩余真实CN断句/指代见 ../du11-source-quality-2026-10-18/closure-investigation/findings.md；具体20源码接口调查见 ../du11-source-tail-geometry-2026-10-18/review/remaining-closure-design.md/json。

完成要求：所有可证明的跨页原support和有限明确先行词context可复现；缺证/多义/超过原上限仅该卡defer，不创造事实；正式三供应商摘要、真实收费/activation恢复、同/跨run缓存和FF/RF消费均通过且有独立内容审查。金标命中/元数据/局部测试不替代完整内容质量。

## 阶段A — 先写端到端依赖行为与纯反例（IN PROGRESS）

1. 用现unit IR/观察/结构/SourceOperatingSession，不新增parser/store/第二预算。先写新公司名通用fixtures：两物理页原句切断、明确同列/同scope和真正running furniture，输出一个多原span support，禁止伪造跨页native_page_view。
2. 缺上一页/列未知/真实页眉证据缺失/TOC/表格/QA/新project或section/source/font/frame/页序不匹配/下一页独立新断言为反控。只知道block_char_start=0不能宣称语义闭合；也不能把所有singleton判残缺重演HK0/7。
3. 唯一/集体产品先行词(简繁/EN)跨窗口；明确列举的A/B/C仍集体，不把每个成员各宣称验证成功。两个竞争series、普通章标题、另一公司或问题、前文缺失及预算不容纳均defer。
4. typed summary/public-context链检查target与context refs同数值offset也不混映、原文SHA/locator/parser/否定/计划/日期/单位原样、所有支持与上下文事先计入同budget。重复page pdf_block号码必须按(source,page,block)计，不得低估。
5. 真实问题与新组合先RED留证。无需每小步人审/签收。

## 阶段B — 现source owner生产接线

### B1 完整组件：共享预算与线性metadata索引（已正常发布、精确CI绿）

不与B2混签：B1只包含已完成的test_source_metadata_budget.py九项及两owner改动，当时跨页RED仍隔离。包external-context只索引一次、exclusions只union一次；每个实际member/context fanout、section heads×body和排序在扩展前扣现WorkBudget。几何局部200K只是同parent嵌套上限，不克隆余额；预算不足在source owner返回有限partial，不能释放半句。

独审两个预遍历遗漏先写反例，RED7PASS/2FAIL，修后集中739PASS/50.52s。之前733PASS/4FAIL是新测试未定义fixture及deepcopy不兼容不可变MappingProxy，已改为正确source_case及递归全字段快照；保留失败日志，不修改生产IR迁就pickle。两预遍历修复为headings在prose成功后单独预扣；native sections先按len预扣再chain，预算0时真实ID访问0。

### B2 剩余物理与指代闭合（OPEN）

物理组件现30行为反控/8依赖与性能控制/既有states及cache集中219PASS10.11s；最终不同agent27有限PASS8.51s（含5个逐owner CRLF等价反控）已签精确5源码/2测试SHA的PASS_PHYSICAL_BUDGET_CACHE_COMPONENT，自有Temp删除。不能忽略实源接线：真实PDF IR此前mime_type=None，已先RED后在唯一PDF parser声明实际格式；全source coverage_complete含细表deferred，不能因此全局关闭物理处理再让半句退回singleton。现按完整coarse正文和pair实际opaque/deferred状态判断，pair未知只defer该pending依赖；页9缺细表不能禁页7→8已观察的延续。复用同account，当前未知column不伪造证明。

共享statement边界复用operating_states脚本/issuer/NP/aux grammar，修繁体新issuer及English新产品主语；首个真实predicate只扫描subject一次，不能遍历每个后续predicate形成N²或借object当subject。Inventory1.8补实际5个共享grammar/matching/兼容owner源字节hash，不仅依赖import方偶然变化。

真实最新0收费三源仍10/10、7/7、8/8 source及canonical；实际parent work6106955/12820408/7975948未超16M，原件/gold不变、0copy/0POST、自有Temp删除。历史第一次physical回放的PDF MIME和全局coverage使新flow未生效，保留该收据，不把它代签当前实际路径，也不称全部语义质量绿。

### FF/CWP 最终读取端口（已按producer→consumer顺序发布、精确CI绿、安装完成）

CWP source_reader_cli可选--include-canonical-identity，由现security_code唯一owner投影market/security_id（schema source-canonical-identity/1），manifest保持观察值。现CLI复用open_described_version一次metadata观察与字节验证，原global/source lineage指纹兼容，旧hash不作权限阻断；显式None的not-applicable scope与未观察由sentinel区分，避免重复读取。5新及既有reader/identity/CLI共59PASS37.37s；两reader最终SHA与FF跨仓独审相同。

FF当前manifest的future/invalid/None不再继承旧query资格，使用已有date primitive；provider未知不能满足显式fmp；FF严格消费CWP canonical projection、legacy严格值比对，不再抄市场normalizer。原作者工区不改，根修在ROOT独立FF工区，独审29unique跨次通过非伪造单轮全绿。

- native_continuity只负责可观察物理proof，原同页edge/native_range保持严格；跨页原多span的closure planner返回reference-only包与不足诊断，不生成新原文。
- 入口在narrative_reading._prose_reading_packages -> _candidates carrier替换之前。旧body windows由新完整group消费/替换；同unit不得多个analysis owner静默最后覆盖。独立context可共享但不能暗变第二body owner。
- 只有structure诊断REPEATED_RUNNING_HEADER等已证明的ID可跳家具；excluded_furniture union包含TOC，不能全跳。列None相等、matching margins alone、no_column_gap不是现成单列证明。
- SourceOperatingSession.groups已能暂态CJK连接并返回5类原unit refs。新增referent proof由现operating_states owner复用prepared views/NP/对象规则，不能PDF adapter再造产品词典。明确unique/collective/ambiguous/missing与真实上下文refs；context refs原始namespace不得送_original_refs当target坐标重映。
- citation_support_views/required_context_unit_ids原端口保持；project原子上下文/公共最多2视图、typed execution原上限不放宽。缺proof在现deferred/withheld通道说明，不加人工许可。

## 阶段C — 大节点验收与发布

一次集中相关unit/integration/typed-public-context + 不同agent最终源码独审，全修真实发现后正常提交并线推送并核精确CI。真实CN/HK/US0收费源检查，再按母现配置/同累计ledger依次真实供应商摘要与缓存/FF-RF C。源码变动与收据按版本绑定，不把历史成功重签新SHA；测试owned目录原样恢复，生产raw/config/gold不写。

## 资源与范围

仍同WorkBudget16M、96spans/48kchars、物理8原unit/4个(source,page,block)/2048chars、draft56KiB/summary64KiB/execution32KiB。必要先行词也计原block/unit/char，不能作为freecontext绕限。实际CN p17/9–14全纳为5blocks，若无法证明更小真实充分context则诚实defer，不升上限/猜单个产品。

先建立一次metadata索引和有界邻窗，最多常数邻居/每scope有限已读上下文；每次新观察预扣原account，耗尽不能重启balance或释放半句。原paid run/未知费用不改，当前累计742228tokens/$0.421556proxy、历史unknown7+401新hold保留；限2Mtokens/$20，供应商按真实现配置，不读/打印密钥。

## Next Step

RF最终pin9669c4d7精确CI已success；本次PWF汇总正常提交/推送后，不重复接收/发布这两卡。下一工程节点：按最终接口先TDD写有界先行词（非event描述同样检查）与original/analysis namespace、原始联合限额及不重复扫描反例，再在现唯一owner接线。保留原文fallback只读视图，先readiness/context后单一graph与fact；未知/多义/超过原4blocks/8units/2048chars仅该卡defer，不编公司特例/raise上限/克隆16M余额。真实三源仅在完整节点完成后回放一次并独立内容检查，随后正式三供应商摘要及收费/activation/同跨run缓存/FF-RF C；holdout/RF循环仍OPEN。
