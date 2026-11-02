# R6 来源语义 CI 共因返修 R3

**FROZEN_READY_ROOT_INDEPENDENT_REVIEW**。隔离基线 `9f575810`；源文件与测试已冻结，未操作 Git/index。完整 CI `41364303788` 的22失败中本线负责20项，另外2项由ROOT处理。本报告不自行签A，也不替代完整候选CI或真实C验收。此前R6/R2独审和失败历史保留。

## 真实根因

1. 前版把“fact不能使用”的瞬态屏蔽当作“原文角色从未被观察”：明确generic的False被空clauses改成None，未知函数目标的operating角色也丢失。完整语法、业务相关性、事实proof混在一个DTO/控制流。
2. 通用POS弱关系判断在既有typed coverage/quantity/billing等owner之前运行，先否决了已经绑定的业务覆盖事实。反过来把所有reading reason当强proof又会让qualitative plan label绕过未知目标语义，不能以该粗方案修复。
3. 前版为了否决模糊目标把promotional/goal词加入closed abstract proof，未知None被误改False。相关性不足不能伪装为“已证明全为套话”。
4. POS可以将中文 compound分成verb+noun，也可能将并列的create标为JJ。整段尾部/摊平的nominal+modifier会丢失NP归属：portable goals被未知形容词升级，surgical services又可能被并列value吞掉。
5. WH无问号已被同一grammar owner判为fragment，却仅移除了fact视图，原文角色保留并通过旧unresolved/relevant捷径重新进入准入。

## 共同owner修复

- `SourceStatementScope.roles`只表达有效的源断言观察；新增内部`fact_roles`表达可进入fact投影的子集。已知套话、未知目标的原role/False/None保留；question/fragment从两个视图一致剔除。不存在持久schema/身份/许可新状态。
- 新callback复用原`_reading_relations`已绑定的relation种类与canonical clause memo。true和false都缓存，先于弱POS，后续fact投影复用同一结果；generic plan/description reason不能充当positive payload。扫描在现有phase WorkBudget预扣之后，预算不足则partial/unassessed，不偷偷预扫。
- 原closed abstract proof恢复窄责任。goal/promotional/degree仅是NP级relevance观察，不能更改independent payload。原function/composition owner保留已匹配的normalized argument_targets，供相同source scope复用，不再次匹配全源，也不产生locators或proof。
- NP head、名词修饰、形容词分轴：goal/vision等tentative head不因陌生形容词升级；纯benefit不靠陌生modifier变具体；现有source offering head可保留未知技术修饰的可读原话，仍不产生新typed proof。未知compressors正控与portable goals负控同时成立，没有加入公司、行业、产品或新业务谓词名单。
- 同一前向predicate/argument owner在CC/逗号协调处闭合已有NP，保留各NP自己的head/modifiers及共同predicate，不根据and/reopen/create/treat等字词补丁，也不改POS模型。并列concrete+abstract的顺序不再决定内容是否丢失。
- prepared matrix结果被WH边界与passage复用，不能凭词法辅助词另开通道。资源缺失、超界仍显式deferred/partial；语言歧义仍可保留unresolved原文；纯财务/明确fragment保持负控。

## TDD与验证

- 真实原失败域完整415项：**20F/395P，22.95s**。marker原3条独立观察是True/True/False，不是平台异常。
- 新分层9反控：**7F/2P，28.93s**；中间版原20已绿，但新增CN模糊目标未闭（423P/1F），随后R2回归又发现WH四例等6F。保留这些失败，不以小组绿代全通过。
- 普通新形容词+goal的最小证伪为**4F/12P，24.27s**；并列NP归属独立RED为**1F，4.86s**。
- 冻结原相关完整5目标 + 新18：**433P/0F/0E，32.93s**。
- 冻结R2剩余完整相关文件（未知业务/relative/问句/抽象/财务/cause、runtime、R4公开selector、R5真实handler wire）：**262P/0F/0E，46.85s**。
- 当前semantic_axes完整95 + 新18 + 原财务修饰/单调正控：**121P，21.80s**。与262组有少量5项单调测试重叠，不能把这些计数相加冒称独立新覆盖。
- Ruff、6源mypy、diff check均绿。只改旧semantic_axes中一次调用计数spy，使其透传新增可选budget kwargs；旧预期/负例/断言标准未改。
- marker现在三条均True。typed coverage零POS，canonical true/false只观察一次、重复访问零新增预算、phase不足不执行typed scan、target扫描预扣不足不执行观察，均有新反控。

## 预算、身份和边界

原16M/112、4096 chars/1024 tokens不变。原SourcePassage36n预留与POS32n+1不提高。新增prepared targets可能重叠，因此不虚称一次全文遍历：按实际Σtarget字符数×8在相同WorkBudget上额外预扣；scope缓存供fact/passsage消费，重复读取不补收费。强typed及明确context尽早返回；这不是实际CPU计时等价，真实H1召回/耗时仍待既有16M/112节点验证，不能由本组秒数推定没有退化。

实际PDF/非PDF reading_recipe AST闭包均含6个owner及predicate_arguments，见JSON，未手补全仓hash。grammar仍`statement-grammar/4`，passage为`source-passage/9`，模型资源/包固定版本未改；实际模块字节与resource identity共同进入recipe。SourceAssertionRoles/SourceStatementScope新增字段仅内部准备DTO，不新增wire schema或授权。

尚未解决/未声称解决：通用POS不是完整依存/语义理解；未知技术原话可以保留但不能由此制造event/issuer/number事实；whole-clause typed witness位置精度技术债仍按前R2边界保留。T3编号备注/终结符结构设计仍暂停，未混入此次源语义修复。未执行真实文档、模型、下载、生产DB或原件操作，未扩大权限/门禁。

## 冻结身份

| 隔离工区相对路径 | SHA-256 |
|---|---|
| `src/company_wiki/document_understanding/statement_grammar/__init__.py` | `cf66d1b19a82e20691ea00a75b6403e5c958c4eb1f699a191048ea2a181348ee` |
| `src/company_wiki/document_understanding/statement_grammar/predicate_arguments.py` | `207e0250cbe2aa7269dc2f021444577e38264791008b2ae8a15d0f76fcea2251` |
| `src/company_wiki/document_understanding/operating_states/assertion_roles.py` | `9195e38d5c54f125bf8e0f0af2e8b455c123b47a4d490d3944347e429fa43737` |
| `src/company_wiki/source_catalog/narrative_source_passage.py` | `74f96c7b0fd612b8771ee9ee090148842720e94c55cb74f06eb09022b17db7c6` |
| `src/company_wiki/source_catalog/narrative_source_context.py` | `fcdc4a9223895a59e1da2ab8d2d71599c5ec74d19547cf2cfa53524ce9b7eb31` |
| `src/company_wiki/source_catalog/narrative_business_policy.py` | `1e6c181ca389e95380e001d2c34e029024eb4f0238d5e7e7d375dffebe700f50` |
| `tests/unit/du11_production/test_source_semantic_axes.py` | `340ce52f3b82e47e39b604ce88fe6edf2ae16684fdffc89ee89bcb1dae7fd363` |
| `tests/unit/du11_production/test_source_preparation_axes.py` | `a60694672b40b034b76c9313d066931d7e182229e35de0d6f8dcb2f0dc89fde9` |

所有命令、真实RED/中间/最终JUnit字节SHA、recipe闭包及marker前后见同名JSON；日志在隔离工区`tmp/r6-r3-*.log/xml`。STOP交ROOT独审/完整候选CI，不自行提交推送，不标主线或整个PWF完成。
