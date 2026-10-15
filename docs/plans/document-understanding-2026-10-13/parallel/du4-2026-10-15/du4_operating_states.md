# DU4-STATE：经营状态、否定、主体和合作阶段

状态 READY，2026-10-15。这是共享经营语义组件实施，不能只给万润股份增加关键词。

## 开工入口与独占范围

- 工作目录：`C:/Users/郑曾波/Projects/company-wiki-du4-state`。
- 分支：`codex/du4-state-20261015`；基线 `8206e78d4087531b1d7ed57c45a73c942cc702e3`。
- PWF：`docs/plans/du4-state-2026-10-15/`；阅读本卡、INTERFACES.md、references/operating_state_admission_implementation.md。
- **只写** `src/company_wiki/document_understanding/operating_states/**`、`tests/unit/du4_operating_states/**`、本 PWF。
- 不改现有 `narrative_business_policy.py`、catalog、selector、QA、parser、rank/cap、model、总 PWF。参考旧设计里的直接改谓词方案由 ROOT 接线，**本卡分工优先**。不建另一套 IR-only selector。

## 已证实问题

真实 IR 文档中一个完整 QA 已解析并形成完整三成员闭包，但共享谓词漏掉：

> 公司现无生产 VC（碳酸亚乙烯酯）的情况，根据公司控股股东中国节能信息，中国节能与宁德时代已经建立了联系，并希望建立业务协同与合作。

应分别保留：发行人当前不生产 VC；管理层转述控股股东已建立联系；希望合作。不能变成发行人已供应/签约/产生收入。问题中采购设想不能升级成公司承诺，另一个回答股东增持也不应单独变成经营事实。

`fixtures/cn-ir-observation.json` 是以前一次真实 parse/select 的保存观察，含来源 SHA、完整目标文字、角色/locator/旧谓词结果；没有重新下载/解析。`fixtures/manifest.json` 标记来源和 SHA。real omission 与合成泛化预期分开，旧 predicate 的对照值是 baseline，不是新输出期望。

## 实施目标

按公共 `detect_operating_relations` 接口提取**具体经营断言关系**：

1. 面向中英及繁体中文；复用现有只读匹配工具。归一化用于匹配，返回原文精确偏移，不能将简繁转换后的偏移当原文位置。
2. 对象与经营谓词必须在有界关系中绑定，不因相隔很远的 OBJECT 与 ACTIVITY 同时出现就成立。任意产品名可作 production/shipment 等操作的对象，不维护公司/产品白名单。
3. 肯定/否定、尚未、暂停/终止、认证/受限、计划/条件/愿望分别保留；关系主体可为 issuer、被转述关联方、其他或 unknown。不要求外部实体库查询或额外身份签收。
4. 行政否定、定义、枚举、无对象的合作愿望、纯财务总额不靠关键词成为经营断言；同一单元有独立有效经营断言时仍保留它。
5. 保持事实范围：not cancelled 不等于投产，only pilot 不等于生产许可，contact 不等于合同或客户，hope 不等于订单。

输出只提供 source-oriented 关系与诊断；不打投资分、不判可信公司、不直接决定选择。不修改问题/回答原角色，不缩减完整 QA 闭包。ROOT 会让唯一现有谓词消费本组件，并移除绕过新语义的旧 reading-only OR 分支，保留显式 0.8 历史行为。

## A：反例与真正 RED

对真实第一答案写三条独立断言，主体/阶段/模态/引用分别断言，不能只测 eligible=True。覆盖参考设计 32 原始例及 12 扩展反例，另加未见公司/产品/英文 holdout，至少包含：

- 不生产 X / 尚未商业化 / 生产已暂停 / 认证失败或附条件 / 截至当前未参与某业务。
- 已建立联系 / 计划合作 / 希望协同 / 已签约 / 已发货的阶段区别。
- “未收到有关产品商业化的问题/通知”不能当作未商业化；“并非没有生产”不能简单倒置；复杂无法确定则 uncertain。
- “项目未取消”不证明启用；“非批量生产仅试用”不证明认证成功。
- 股东与发行人、子公司、对手方不能交换；跨 parent 上下文不能串联。
- 问题中的客户/采购设想仍为 question context；正文经营关系与来源可采纳角色分开测试，不改角色作假。
- 纯财务组成、名词串、定义和愿景负控；感谢语加真实否定仍有效。
- 因停产影响营收保留原因，不能一刀切过滤含财务词的句子。
- 原文换行/简繁/英文、不变性、精确 refs、零预算/部分预算、长句有界和稳定结果。

模块导入错误不算语义 RED，至少保存一次真实三关系失败的可执行断言。

## B：集中组件验收

本包单测/契约测试、Ruff、mypy。真实保存段落与普通 synthetic holdout 分开报告，不能用人为用例通过率宣称全市场召回率。检查否定作用域/归属，避免用 blanket negative whitelist 或整段黑名单逃避误报。

## C：交接

输出公共 handoff + 分支 commit + 原始语义 RED/最终结果。给 ROOT 精确的现有 `OperatingFact` 适配建议（topics/reasons/普通 score），不自行编辑共享谓词。声明未做原件重放/选择/真实摘要/下游 RF 验收，STOP。

ROOT 接收后只在一个 reading 业务谓词接入；做 selector/完整 QA/预算与历史 0.8 回归、真实 IR 重放与另一公司 holdout，再做摘要主体/阶段独审。不增加人工门禁。
