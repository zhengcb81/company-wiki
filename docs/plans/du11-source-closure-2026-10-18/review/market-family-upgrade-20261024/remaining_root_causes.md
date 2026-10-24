# 本轮真实样本带出的后续共因（未完成）

本文件不覆盖已有annual14六partial或R1公司循环；合入同一ROOT队列，禁止另建router、任务库、授权链或公司特例。

## M1 先让观察与金标准确（第一顺位）

2026-10-24最新：本节点已完成源侧独立验收，见m1-independent/report.md/json。保留旧47ID，最终51事实/139锚点，102P；保留全部旧版和修订理由、3项v1语义错误反控。仅源侧development gold通过，不代表选材或摘要通过。以下为当时问题发现记录。

证据：independent-baseline-review/report.md/json。4份本次选择均完整映射（19/30/96/7），不能再拿helper潜在不兼容解释真漏材。reading_context不发布route，读其真实reading_policies/版本，不把null判未路由；新的replay工具已记录producer源码+catalog SHA并核前后一致。旧baseline缺完整producer冻结，保留该局限，不补造历史SHA。

旧gold存在：ASR“会不会再”强定否定、编辑注释字符串当must_preserve、HKcapex以折旧作支持、百万元替代支持与千元精度要求冲突、非收入财务数强制入叙述分母。下一步先逐源冻结修订版，不改旧gold；required_business/disposition_context/correctness_if_emitted按本项目职责解释，原数据/支持组保留。新增语义/数字突变反例，不能仅降低重要性让分数变绿。

## M2 原语言电话会跨载体与匿名说话人（第二顺位）

2026-10-24最新：已进入TDD实现/集中独审，见M2_IMPLEMENTATION.md。匿名DOCX真实路由已恢复为earnings_call；仅路由不增加召回，定性经营意向补材后19→23，仍未整体内容通过。独审又发现同轮计划限定未进入真实模型卡片、新DOCX批处理pin未接线，正在共因修复；不把中间工程绿作为节点完成。

吉比特DOCX在实际0.9仍generic/unknown，且遗漏后段存量运营/企稳不确定性/未落地更新。当前native信号collector只消费已有carrier，不能向它添加重新扫描全文的正则。应调查现normalization DOCX原段落/原speaker时间戳与TXT turn owner的可共用端口；先冻结中性匿名speaker1/2+连续段、独立Q/A、未知映射、ASR噪声反例。匿名speaker编号本身不能证明谁是管理层/分析师，不以“说话人2一律公司”硬编码，不能自动把疑似ASR改为强否定/精确单位。

原文引用/段落定位不改，角色不明输出unknown/uncertain；同一问答的后段回答与限定需随target进入已有有界依赖，不新建第二转写器或跳过未知角色材料。中文、英文、TXT/DOCX/PDF的业务问题共用语义层，各adapter只产生原生观察。

## M3 经营指标定义与历史指引更新（与annual14共享）

真实EX99.1中bookings/RPO定义、分部重述、mechanical outlook、no change to outlook与Azure剔汇率/新定义相连，不能仅保留两分部名称。按现source purpose识别定义、基数变更、口径关系；条件/旧新期间由同一局部闭包负责。与annual14地域口径、父子业务、容量日期问题合并设计，不提高限额、不全表切片；实际SourceRef/API补精确数字后必须留读取和采用记录。

## M4 稀疏材料降噪与负例

珀莱雅唯一经营解释已选，但30片段仍混常规治理/金融表噪声；不是“只要有数字就重要”。保留现金回款/推广变动的原经营解释，其余financial-only可不切片/不调用模型；若输出数字则原单位/期间/方向仍检查。不能按公司名、PDF页数或标题统一skip。与原material_value单owner共因处理。

## M5 USIPO样本准备失败的精确诊断

正式FF→CWP调用返回budget_exceeded、provider_started=false、0HTTP/0下载、费用null，母预算耗尽没有证据；见us-ipo-acquisition-gap.json。CWP已有local_preparation blocks_download分支及LocalReadBudget.observation（phase/limit/counter）；需将真实诊断透传已有upstream_cause，而非再加审批。先只读重建该请求本地发现/准备的计量，定位究竟字节/候选/遍历限制；不重跑同一失败下载、不盲目升10MB或归咎供应商付费。若本地索引漏筛而扫全湖，按实体/期间/类型先筛候选、共享一次观察，在所属层TDD根修。Dayu代码保持纯外部、不改。

### 2026-10-24 owner observation 链修复结果

- 根因：`AcquisitionCoordinator.ensure` 在 local preparation 阻止下载时，只复制 status/reason/causes；`LocalReadBudget.observation()` 的 phase、限制、消耗和触发bound在CWP层丢失，故FF只见`budget_exceeded`而没有owner计量。修复将且仅将零/一个`local_read_budget/1`并入已有`local_preparation`；重复观察拒绝。CWP `operation_contract` 对schema、usage scope、key set、令牌、limits、counters、elapsed及bound作有界严格验证，无路径字段；FF把它映射进已有`filing-local-preparation-observation/1`，不创建新诊断账本或权限门。
- 离线跨仓E2E故意令source-group discovery超限，并安装网络拒绝器、marker provider；RF结果中可见唯一触发bound及精确`limit+1`，`provider_started=false`、0 downloads、provider marker absent、无`local_io_usage`，原error中不含lake路径。测试不伪称复现了真实Snowflake原件。
- 同轮canonical regression暴露另一共同条件：issuer layout二次发现调用`qualified_source_scope`时没有historical capture journal，也没读已有登记的`metadata_json`。known old-period S-1因而失去trusted vintage，并可被打开。修复在二次发现中复用同一个`HistoricalCaptureScopes`，从已登记metadata恢复document kind/period约束；原`test_real_historical_commit_request_excludes_old_period`由RED转GREEN，`test_canonical_acquisition_scope.py` 22/22通过。
- FF首轮pre-push的6个失败不属于production行为回归：请求超时用3秒涵盖识别和被测ensure；Windows process probe用1秒涵盖测试子进程自身启动，满套运行下测试在目标子进程启动前超时。只扩大合成请求/探针时间窗，保留端到端总deadline、timeout cleanup和“不杀无关进程”断言；相关8例8/8、两个完整FF受影响模块见FF记录。FF commit `324ced2` 加测试修复 `e0d9642` 已推送，远端CI `40115441655` success。
- 当前CWP验证：`test_source_operation_v2.py`、`test_canonical_acquisition_scope.py`、`test_local_budget_observation_rf_e2e.py` 共45/45通过；Ruff、acquisition/local_reconcile/operation_contract三文件mypy及diff-check通过。CWP发布及精确CI待本次正常提交/推送。当前`companies/`无Snowflake目录，故原Snowflake 2020 S-1的历史本地bound仍未被观测；保持OPEN。0 provider请求、0下载、0模型调用、原件不改，Dayu未改。

## 后续大节点

M1冻结准确的源侧语义检查点 → M2/M3/M4共享修复及集中独审 → 正式配置摘要/引用和缓存恢复 → RF实际采用/四审 → 未用于调规则的新公司/版式。当前五family匹配/请求组件通过不等于本页已完成，不能冒称25份文档或全部15市场文种格生产验收通过。
