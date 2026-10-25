# W18-CWP-HOLDOUT：三市场真实新材料的源侧金标与可复现回放

可以立即开工，不等待ROOT正在修的选择器/摘要或W16/W17。独占目录`C:/Users/郑曾波/Projects/company-wiki-w18-holdout`；分支`codex/w18-cwp-holdout-20261025`；代码基线以本工区START_HERE/dispatch.json记录的`ba8f8543`完整Git提交为准。`PLAN_ID=w18-cwp-holdout-2026-10-25`，`PWF_PLAN_ROOT=docs/plans`。先读本仓AGENTS、本地START_HERE、本卡和COMMON。

## 目标与边界

ROOT已在药明康德annual14和微软10-K定位多项共同问题；需要不同公司/版式的独立参照，避免修复只适用于已见样本。本卡交付源侧语义金标、真实材料的冻结基线与可对任意显式候选commit重跑的工具。**不改生产解析/选择/摘要代码，不调用模型，不执行真实RF，不宣称最终摘要质量通过。**

先读并复用已有`tools/document_understanding_benchmark`的gold/records/recovery/native及`holdout_acceptance_contracts.configured_preview`等现有能力。新`tools/holdout_replay`只做冻结提交、来源输入与分维度观察的薄编排，不另起金标、评分、恢复或清理框架。确实不适用时在A记录具体接口缺口和最小适配；生产模块仍不在本卡写范围。

只写新`tools/holdout_replay/**`、`tests/holdout/w18/**`、本地`docs/plans/w18-cwp-holdout-2026-10-25/**`、`delivery/w18/**`。ROOT不写这些新目录。禁止其他tests/fixtures、`src/**`、生产config、共享budget/store、母PWF、companies/等原始库、FF/RF/Audit/Dayu/IQS及安装副本。若发现产品问题交可复现finding，不在自己工区修生产源码。

## 样本与源侧独立性

| ID | 要求 |
|---|---|
| H01 | 通过配置内现有来源目录/SourceRef只读盘点，选至少3家公司、至少6份已有原件覆盖CN/HK/US；类型包含年报、半年报或季报、电话会原语言TXT/HTML/DOCX之一、投资者关系、招股/再融资，另有一份治理/程序套话负例。重叠市场/文种允许，一份材料不能冒充两个独立原件 |
| H02 | 排除ROOT已调规则的药明康德、中微、万润、吉比特、珀莱雅、金山云、微软，以及本轮25样本/m1 development gold的原件SHA。优先不同公司；不能只换同一文件名。其他历史金标未证明盲测则标local-unseen或development，不能伪称全历史fresh。先查现有PWF/样本清单/test gold，给每份prior-use证据和分类 |
| H03 | 在跑候选选择结果之前冻结manifest和源侧gold commit。逐源直接阅读关键业务章节/问答及前提，不先看候选产物决定考题。每份8–15个业务目标（治理负例可少于此），包含核心业务边界、新业务/海外进展、指标定义、指引条件/否定、计划与完成、日期与产能分离、期间/单位；按实际原文适用，不能虚构不存在的事实凑数量 |
| H04 | gold区分required_business、disposition_context、correctness_if_emitted等已有等价义务；完整财务表不强制进叙述摘要。每目标给source_id/SHA、准确locator、最小原文引句、主体/业务对象、期间、单位、modality、上下文/前提、必保留和禁止推断项。数值只在完整来源绑定可证时记录；ASR疑词保持疑词，二手纪要不能冒充官方管理层发言 |
| H05 | manifest保存版本化来源引用、原件SHA/字节/格式/市场/文种/身份信息来源和只读解析说明；不从物理目录猜公司身份。源目录定位是CWP测试所有者一次处理的细节，不让下游脚本拼production目录；缺SourceRef可在自有隔离湖登记原件，不写生产库 |
| H06 | 若确实找不到某市场/文种现有原件，先完成可做部分并写明缺哪个cell和查询证据；不下载、不拿研报冒充招股书、不把未执行写PASS。H01核心广度未满足时按INCOMPLETE_EXTERNAL_BLOCKER交接，不能缩窄定义声明全完成 |

至少保留两种版式或载体，例如中英文长PDF与HTML/TXT；原件不翻译、不复制入Git。源侧gold应只保存必要引句和结构，不做新的完整PDF→MD/切片数据库。

已有本地线索（只供发现，不是已冻结gold或新颖性证明）：`companies/紫金矿业/raw/financial_reports/annual/`有2025年报，`companies/比亚迪/raw/financial_reports/annual/`有2024年报，`companies/百济神州/raw/prospectus/`有招股书及raw/research下投资者关系原件。HK/US通过已有来源清单和配置根寻找并核官方身份/原件；不假定按公司目录名即可证明市场或文种。需要按H02排除已见来源并选择样本，不能把本段线索直接当完成H01。

## 回放与结果接口

| ID | 要求 |
|---|---|
| H07 | 新工具有单一入口，显式接受`--producer-repo`、`--producer-commit`、`--manifest`、`--source-root`或当前可用的SourceRef解析配置、`--out-dir`。冻结部署并运行真实CWP parser/selector/summary task compiler，记录实际import根和源码commit；不能导入ROOT正在变化的工作树/已安装旧副本，不能复制第二套选材算法 |
| H08 | 不发模型POST；允许实际编译scoped model view，分别报告source scan、candidate selection、layout、每目标source支持/进入模型输入的机械可见性；没有模型响应/独立语义审查就not_reviewed。词匹配/locator可解析不自动等于业务事实PASS，不能用模型输入覆盖率代签摘要覆盖率 |
| H09 | 每样本分别记录原件前后SHA、生产参数/预算来源、候选与选中/延期计数及原因、逐目标原始span/context/support成员、任务可见性和质量标记。只读继承现配置，不上调cap；timeout/结构不完整/预算用完保留原始原因，不算成功内容 |
| H10 | 金标与候选输出分开保存；baseline原样保留。后续候选commit的结果写新attempt，逐目标对照并保留旧失败；变更gold必须新版本、逐项源侧理由并重新独审，不覆盖旧oracle。无网络、原始库/预算账零写入 |
| H11 | 用小型中性PDF/TXT/HTML夹具测试runner边界，完整真实样本跑一次冻结baseline。两个不同绝对测试根实际跑同一小型链，一个含中文/空格，从外部cwd启动并污染PYTHONPATH验证执行来源；成功/失败/timeout/结果已存在均不覆盖sentinel和旧evidence，清理只限自己目录 |

不能为完成此卡重新跑收费的formal-v4或重写旧收据。若真实baseline有缺口，**失败记录本身可以是完整交付的正确结果**：本卡验收的是源侧oracle/真实回放/观察诚实完整，而不是强迫现有选择器每项都PASS。产品缺口逐目标交ROOT。

## A/B/C与独立审查

A清点prior-use并冻结manifest＋source gold，先commit，再跑任何候选；B编写隔离runner/中性边界测试；C集中真实baseline与可移位/恢复测试。建议入口：

```powershell
python -m pytest -q tests/holdout/w18
python -m tools.holdout_replay --help
```

最终调用独立agent：逐份核原文和gold，检查是否先冻结/是否把财务表或二手资料误归类，审完整工具diff与所有H项。独立在新scratch重放至少一份真实样本和一条失败清理链，新增一个否定/条件或期间单位错配反例。所有本范围问题必须修复、复测及独立复审最终文件SHA才交接；真实产品缺陷保留开放，不能修改生产代码使分数好看。

## 交接

`delivery/w18/handoff.md/json`、`review.md/json`、固定manifest/gold路径及先冻结的commit、真实baseline结果/逐目标finding、可重跑命令和两个根的恢复收据、原件前后SHA、文件新增字节。实际大原件路径只作本机只读配置，不硬编码进可移位runner；Git只交最小引句、manifest、收据和代码。ROOT随后对修复后的候选commit重跑，并负责真实摘要和RF四审。
