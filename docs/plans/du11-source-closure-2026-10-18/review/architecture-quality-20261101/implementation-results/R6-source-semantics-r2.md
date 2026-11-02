# R6 source semantics R2 — 并列目标/补语责任返修

**FROZEN_READY_ROOT_INDEPENDENT_REVIEW**。冻结基线 `718fced8` 后，仅在 `tmp/architecture-r2` 解冻本线6个owner源文件与新测试。旧 `R6-source-semantics.md/json`、旧7/5 SHA观察、独审P2历史全部保留，不覆盖旧结论；本报告不自行签A通过。

## 本轮真实根因

旧 `_english_statement` 从整个后串挑最后一个VB，其后的名词被当成整个句子的补语。于是“重开病房并创造价值”只剩value，倒序却保留病房，具体经营内容被最后的套话吞掉；只并入所有后串名词又会把`for clinicians`或受益者relative的动作捐给目标。旧 `_VAGUE_OBJECTIVE` 全句search也会直接否决strive/aspire的混合真业务，绕过语法owner。

另有whole-clause typed witness：`customers whose products process orders`中的产品功能能把整个generic goal标成independent_payload=True，并进入fact快通道。其整句witness没有精确谓语/补语位置，不能直接当目标的独立证据。本轮在目标purpose处完成绑定，不在末尾按reason清fact，不扩全typed-witness span系统。

## 单owner修复

- 新增 `statement_grammar/predicate_arguments.py`：一个前向O(n)观察器，以EN/CN POS语法标签识别并列NP/VP、嵌套补语、direct-object relative与beneficiary/background relative。and/or/but由CC类别处理，中文连接词由c类别处理，无reopen/treat或行业/公司词。
- 每个PredicateArgumentScope保留自己的谓语、直接名词、NP修饰语、量词原词与attachment。具体直接修饰语（如option-pricing、surgical）不能像rhetorical adjectives一起丢掉；受益者PP中的名词、量词和relative动作不参与直接补语判定。没有把全文所有名词混成一次相关性投票。
- 目标及未取得independent_payload的功能性原话，其单次grammar/complement观察在原 `prepare_source_statement_scope` 完成，再给fact与passage复用。明确abstract/context在fact投影前屏蔽；具体原话保留，不提升issuer/event/数值proof。非goal typed内容仍零POS快通道（定点反控通过）。
- 删除重复整句 `_VAGUE_OBJECTIVE` 目标否决。其原有goal/vision、rhetorical descriptor和程度构式归回既有abstract argument owner；不增加公司名、业务谓词、产品或行业许可名单。未知技术NP修饰语保留。
- CN官方词典把“努力创造”整块标为nr。本轮用已经观察到的通用objective operator终点作为**瞬态lexer边界**，不改词典/POS，不改原文或locators；努力/争取/坚持和相同名词化反控均验证。边界有序、不重叠、长度有界，仍一次32n工作。
- 部分base-verb量目标尚无原metric owner的typed proof。新scope仅保存direct量词原词，并用原 `source_has_operating_measure` observer辨认名词角色（prepared scope内memo）；如“服务1200客户”保留`unresolved + relevant=True`原话，**不产生当前量/增长率/期间/单位事实**。不能把one vision或PP里的300 clinicians当经营量。此类源在fact准入上仍待定，不能借旧弱数字匹配形成已实现quantity；混合独立业务句照常保留。

## 真实TDD与验收

- 并列/嵌套/受益者/CN29新例：**18F/11P，20.49s → 29P，10.43s**。
- typed受益者relative反控：**1F/2P，18.42s**，同根修入目标前置绑定；直接产品relative与mix独立句正对照保留。
- direct quantity：**2F/3P，14.36s**，只保留原话而未扩展数字facts。
- 相关旧例回归曾有四个descriptor/uncertainty失败，之后一个中文程度构式失败；没有改旧expect，已在原抽象参数owner闭环。
- 最新冻结组：**322P/0F/0E，15.65s**。涵盖新93例、旧未知业务/relative/问句/抽象/财务/cause反控、R4资源缺失/超长公开selector、R5实际handler正常及缺资源、非goal typed零POS与scope复用。没有重跑746，也没有以这322项代替全候选CI。
- callback单source观察、一次POS复用、重复访问零新增收费、纯scope遍历32/64/128的2n访问，均有检查。Ruff（6源+测试）、mypy（6源）、diff check绿。源和测试版本与测试历史见JSON。

## 实际成本与剩余边界

原16M、112槽、4096字符/1024 tokens不变。SourcePassage仍36n的保守预留，POS仍32n+1；单次准备的结果在fact/passsage间缓存，非goal typed无额外POS。过去可直接走unresolved的功能性原话、以及需要区分direct/background的目标，会有一次真实POS/补语工作，不能称零成本；资源缺失时公开deferred/partial，独立健康typed scope仍处理（新公开selector反控）。原H1在16M/112的召回、耗时与完整候选CI仍待ROOT；15.65s仅本组，不能证明真实大文档无退化。

Whole-clause witness缺精确位置是仍存在的泛化技术债；本轮以目标purpose绑定收住，若非goal再次出现同根再扩大原owner，不增加第二身份/许可/证明系统。量目标数字的完整形态覆盖仍归原metric owner，本轮保留unknown原话，不用它制造数值事实。POS观察器有界且可移植，未声称覆盖所有依存语义或经济真值。

新纯模块已进入实际PDF/非PDF `business_algorithm_hashes` AST闭包，hash均为 `44733068065e4489f3d20e2b586fadc8840dce498613beae5c58f3260399c154`；未手补算法清单。grammar=`statement-grammar/4`，passage=`source-passage/8`，资源identity=`123fbe7c75f816991ad5112a748e59e7339a054cd40483a905ddf4c30e8c93f7`（包含算法schema；模型资产字节未改）。

## 冻结身份与交接

| 路径（相对隔离工区） | SHA-256 |
|---|---|
| `src/company_wiki/document_understanding/statement_grammar/__init__.py` | `dace7c6b31227c934238e325e3cababf93c4f9445d6b01a208910731f46089e9` |
| `src/company_wiki/document_understanding/statement_grammar/predicate_arguments.py` | `44733068065e4489f3d20e2b586fadc8840dce498613beae5c58f3260399c154` |
| `src/company_wiki/document_understanding/operating_states/assertion_roles.py` | `a14877efff01cdb62e4091a2e89e98d2b93bcae27146042594c967afad188ff3` |
| `src/company_wiki/source_catalog/narrative_source_passage.py` | `dccf866b6cac91edcbde52b2cb253f53957b2cc63fd8e9adceee1226b20a92a0` |
| `src/company_wiki/source_catalog/narrative_source_context.py` | `d9578083a07ae26d43a847e7e814dc3242304d1cf1b88408f10caae4468b5e64` |
| `src/company_wiki/source_catalog/narrative_business_policy.py` | `6c1bc1ab07d77b95e9f5a94be1e8471a0831a456f9d75422c4319571f0b0f465` |
| `tests/unit/du11_production/test_source_semantic_axes.py` | `e4aaea98b9e50560cd6f454a09a63b9868dce75eed37dc42c809f2c64106438a` |

`predicate_arguments.py`为新增文件，ROOT发布须显式stage。完整命令/输出在工区 `tmp/r6-r2-final-scope.log`，JUnit为同名xml；各次RED/中间回归/最终artifact SHA在同名JSON。未操作Git、主工区src、PWF主文件、原件、生产库、配置、凭证、模型资产或收费服务。当前STOP，交ROOT独审，仍不得称整个整改或真实摘要/RF闭环已完成。
