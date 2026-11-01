# Q01 r3 — READY，源码冻结，待 ROOT 集中独审

2026-11-01；本记录接续 `independent-A-r2.md` 的 A-r2-01 / P2，保留原 `Q01-rework.md`、r2 审查及其收据为历史。**不是 A 节点验收通过，也不是 C 节点真实摘要/RF采用完成。** 当前文件身份见 `Q01-rework-r3-evidence.json`。

## 同根修复

此前虽然有独立 POS/matrix owner，`_EN_DECLARATION / _CN_DECLARATION` 和 `causal=True` 仍可直接返回 True。单词 `are / have / 拥有 / 正在` 出现在 relative/的 名词化片段中时，会绕过同一个 owner，造成 observer=fragment、passage=support 的自相矛盾。

现在已删除两套旧 declaration regex，删除 `_declarative` 的 causal 参数及直接 True 分支。没有新增公司、证券代码、行业、页码、样例词条或授权门。已有 source-owned typed relation/event/measurement 的独立 proof 仍由原责任层快速处理；**没有该 proof 的一般可读性全部经过 statement grammar**。问题、套话、财务目的、来源角色等既有负向责任边界继续独立保留。

- `source-passage/5`；`statement-grammar/2`。
- `narrative_source_passage.py` 统一消费 matrix observation，不再有第二套正向词法通行证。
- `narrative_business_policy.py` 仅追加将原 WorkBudget 传入 statement scope 的那一处调用；原 fact/event/number/issuer 投影算法不变。
- 原 `_CN_DECLARATION` aspect 兜底没有恢复；原真实 p12 三 unit 及跨行业同形例仍绿。

## 英文条件 / 疑问责任边界

ROOT 追加的真实责任层核查复现：旧 `_EN_QUESTION` 将 `When order volumes recover, we reopen the coastal terminals.` 和 `Where equipment fails, we dispatch a maintenance crew.` 整段抹掉。仅将规则改成 wh+aux 倒装也不够：`Which software processes customer billing records`、`What equipment manufactures medical tools` 无问号时会借 typed 描述外观进入 support。

最终由同一 `statement_grammar` owner 提供 `observe_english_statement_boundary`：

1. 问号、显式 Q/投资者角色、明确助动词倒装保持非陈述边界。
2. wh 前缀本身不被当成问题，也不被当成陈述；对该完整 sentence scope 调用同一有界 matrix observer。有后续 matrix 的完整条件句保留；仅 subordinate/relative/疑问片段不制造独立 proof。
3. leading wh 功能词不能被 POS 的偶发 proper-name 标签中性化成 `The entity`；专名中性观察只作用于真正的首部 proper NP，不能吞掉语法角色。
4. statement scope 保存 `(normalized assertion key, observation)`，后续 `_declarative` 复用同一个 scope 的结果，**零重复 POS / 零重复 32n 计量**。不同子句 scope 的实际观察分别计量，不伪装成零成本。
5. matrix 观察资源不可用/超界时，边界保持 unknown，诊断随 prepared scope 到 passage；不能借 typed 外观将未判的疑问/条件片段免费放行，也不伪称它是已确定问句。

完整条件、无 matrix 的单从句、带/不带问号的倒装及 What/Which/Who 主语疑问反控均通过真实 assessment。原话保留，conditional 可读并不产生 actual milestone/current_state。

## 中文“的”作用域与诚实歧义

撤掉词法旁路后，窄旧例暴露 `毛利率下降主要由于订单转向不同的产品组合。` 被误拒：初版 POS grammar 把谓词之后任意“的”都当作整句 VP 名词化，跨越了宾语内形容/方位修饰的作用域。

- `V+的` 明确相对名词化继续判 fragment；`正在运输液化天然气的船舶。`、`公司拥有的沿海码头。` 不准入。
- 词性明确的宾语内 `a/ad/an/f/s + 的` 修饰不吞掉 matrix predicate；`订单转向不同的产品组合。`、`公司拥有沿海的码头。` 及原毛利率业务原因例保留。
- 固定 jieba 词典把“新鲜”标为 `ns`。没有增加“新鲜”特例、强改词性或借助公司名单。在 subject+V 后、名词/地名+的 的作用域确实不能由小 POS owner 区分时，明确返回 `unknown / statement_grammar_ambiguous`。
- 按 ROOT 确认的双轴规则，该语言歧义的具体原话保留为 `use=unresolved, relevant=True, reason=source_grammar_ambiguous`；它可经实际 `_admitted` 保留，**不是 support，不升级 event/number/issuer proof**。完整但词义误标的 `农户购买新鲜的蔬菜。` 与潜在 NP `农户购买蔬菜的村庄。` 同形反控均证明 fact 不升级、原话不改、重复访问不补扫/补收费。
- 缺资源 `source_grammar_unavailable`、超界 `source_grammar_scope_limit` 仍是 `unresolved + relevant=False` 能力诊断。不能把能力失败混成语言歧义，从而免费放行所有材料。

这不是完整依存解析器，不能宣称任意复杂省略/嵌套/词义消歧都已解决；可读性、语言歧义和事实证明是不同轴。

## 预算、资源、缓存边界

- grammar 实际观察继续在同一 WorkBudget 预扣 `32*len(scope)+1`。wh 边界的实际 matrix 观察也计费，预算先于模型；scope/明确倒装等廉价边界不加载模型。
- 4096 chars / 1024 tokens 的原 scope 上限不变；不静默截句，不提升 **16M / 112**。新 typed 外观 wh 用尽预算时真实 session 转 partial；重复访问不重扫或补收费。
- 同 scope 复用测试同时禁用第二次 `observe_statement` 并验证实际费用严格不变；不同子句范围不冒充同 scope。
- 模型四文件、manifest、许可证、包版本未变：资源 **10,775,669 B**，宿主 NLTK **3.10.3**、jieba **0.42.1**。R3 没有再安装/下载/解压资源，没有新增常驻资源体积。
- `resource_identity()` 仍计算实际资源字节、推理包版本和 grammar schema。ROOT 已在 r2 将其接入实际 reading recipe；r3 schema/算法变化会进入该依赖。ROOT 应对最终冻结版本集中复核 actual cache，不把 r2 的旧 receipt 冒充 r3 已复查。
- r2 的 wheel 收据证明当时资源打包/异路径加载，**R3 没有重建 wheel，不能宣称旧 wheel 已含 R3 源码**。R3 fresh offline runtime 测试仍从当前包内资产推理且无下载/临时字典 cache。

## TDD 和最终定点结果

1. 首先加入独审精确六反例和同词完整 matrix 正例。修改前 **6F / 27.06s**，六例全部是 grammar fragment 却 passage support，确认同根旁路。
2. 删除旁路后最初 **67P / 15.39s**。窄旧17项与新14项组合发现中文宾语修饰回归 **30P/1F /11.60s**，没有恢复旁路掩盖回归。
3. 中文局部修饰和英文条件新增检查先 **5F/4P /5.68s**；后续版本出现词典“新鲜”歧义及错误的测试 fact 基线 **76P/2F /89.27s**。这次未超时，不能拿该受环境影响的整组耗时当新稳态时延；随后采用定点复验，没有反复整仓运行。
4. 测试基线修正有原因：`project_reading_business_fact(text, relations)` 未传 source_roles 时允许旧 financial_exempt；生产 assessment 有 source_roles。条件句现在以**同一 prepared source_roles 的原 project owner**对照，而不是将旧未绑定 financial_exempt 或 `eligible=False` 当所有业务风险描述的硬标准。测试额外禁止 readable 条件句升级 milestone/current_state。
5. 第一轮最终新组 **87P/1F /30.08s**：`Which` 被偶发 proper-name 标签吞掉。修复通用 wh 角色优先级后，**当前冻结新组 88P /26.73s**：readability/generalization 74项＋runtime/预算/资源14项。
6. 当前旧金融混合/因果/typed 与 numeric uncertainty 窄回归 **17P /11.21s**（81项中64 deselected）。没有重跑原100/118旧全组，没有跑真实 selector/摘要/RF C。
7. 当前 Ruff（3源＋2测试）通过；mypy（3个源模块）通过。两条既有 jieba/pkg_resources 弃用 warning 保留，没有新增依赖门或压警告。

最终两个测试命令（CWP cwd，`PYTHONPATH=src;tests`，`PYTEST_DISABLE_PLUGIN_AUTOLOAD=1`，宿主 Python）：

```text
python -B -X utf8 -m pytest -p pytest_asyncio.plugin tests/unit/du11_production/test_source_readability_generalization.py tests/unit/du11_production/test_statement_grammar_runtime.py -q -p no:cacheprovider
python -B -X utf8 -m pytest -p pytest_asyncio.plugin tests/unit/du11_production/test_source_passage_admission.py -k "mixed_narrative or financial_cause or established_support or true_financial or account_cause" -q -p no:cacheprovider
```

没有生产配置/原件/数据库/LLM POST/费用账/Git index/commit/push/主 PWF 改动；测试未复制原件或运行下载。离线运行测试显式核对字典 cache 临时目录仍为空；本轮没新建下载/构建临时树，没有下载 ZIP 或模型副本。pytest 基础设施的 fixture 清理由其现有策略负责，本线未另行删除全局临时目录。

## ROOT 下一步

对 evidence 绑定的 R3 冻结实现集中独审，检查六片段/完整句、中文歧义双轴、wh typed 外观先验和同 scope 预算复用。通过后由 ROOT 继续既定 C 节点：原资源上限下的实际选入/遗漏、真实摘要、缓存恢复及 RF 采用。本线 STOP，不以单元绿声称上述生产链路已完成。
