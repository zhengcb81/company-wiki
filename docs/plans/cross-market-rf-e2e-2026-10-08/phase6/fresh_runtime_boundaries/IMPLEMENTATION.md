# 全新三市场研究发现的共用边界修复

MAIN 负责归总、代码整合、安装、母账和主 PWF。当前三个执行 agent 独占各自 audit run 和 TEMP 环境，不写实现。已有审批残留清理已完成；本包解决真实接口错误，不创建人签、许可文件或公司特判。保留每个旧 scope/capture/失败/费用，不重写成通过。

## 已确认与尚待验证的责任

| 问题 | 原生证据 | 根因 / 下一动作 |
|---|---|---|
| 已安装 FF 缺 `upstream_cause` | MSFT 首次 traceback；修前/修后属性及原生 install check | 已完成定点同步 canonical 两文件、两物理根；完整 15 owned 文件 MATCH。安装不是公司研究通过。见 `../fresh_executor_launch/launched/ff_runtime_closure_repair.json` |
| 管理沟通 `checked_date` 晚于 as-of 即拒绝 | CN validate-only 5e4c597e；HK 同类实际反例 | RF `research/targets.py` 仍把实际检查时间当信息截止。使用现有 source-clock 资格和事件顺序；保持真实 Oct9，材料资格按 Oct8。TDD 后与 rich MIME 一次责任验收 |
| PPTX 被要求 transcript lineage | MSFT 32e319ba；canonical/installed 合同同 SHA | RF 旧非电话会 MIME 白名单漏掉已支持的 PPTX。公开 rich-document 合同允许 PDF/HTML/XHTML/PPTX；TXT/JSON 仍要求原字节到文本的 lineage；未知 MIME 不能伪装成功 |
| CWP H1 `zh-CN` 无法进入 AUTO | CN 7e40cb5a，AUTO 创建前拒绝 | 既有来源 locale 与事件枚举不一致。需要统一 producer locale 投影责任、保留原 locale，不翻译；先确定整个入口范围再 TDD，不改单份原件 |
| 年报摘要输出截断 | CN 0c6f5a13，已花费用、有原生 terminal error | 选择/打包/输出长度需要有界设计；保持已配置模型与 token 上限，不改公司资料/摘短来假称整个节点通过。从原生请求与 ledger 验证后设计共因修复 |
| 公布已早于截止的 HTTP 官方来源被 RF 拒绝 | CN H1/Q1/IPO 真实 manifest URL | 存储允许 http/https，RF 仅允许 https。来源URL是provenance、RF不据此发HTTP：共用校验已支持原始public HTTP(S)，不猜HTTPS或重复GET。另1真实RED后责任GREEN；三真实原件已由CN新capture公开准备成功/0重下载 |
| ET companion request_schema | HK e343e43a，provider_calls=1 / provider_requests=0 | 真正请求/schema 兼容问题；先核完整调用 DTO 和工具版本，未发 HTTP 不写成 entitlement 拒绝，不盲重试 |
| MSFT FY26 真缺报表被 local_metadata_gap 阻断 | FF reuse-only 2e88917b，0 下载 | 本地未知候选与真正缺失期间的区分需要 storage 负责；查 producer matching/reconcile，不让 consumer 扫盘或绕 identity/期间 |
| 非财报 source_type 默认投影 regulatory_filing | CN SEMI 已公开准备成功 86b3 | RF 语义投影不可提升来源等级。原始 builder/capture 保留；有实证的 industry_association 可由研究输入如实分类，后续修通用公开投影 |
| 官方 import 长路径失败 | CN Lam 87ba，Windows FileNotFoundError | 长路径目前只是待验证假设。应核实际 staging/destination 长度，再考虑存储短稳定文件名、标题仅 metadata；不在消费者改目录/绕导入 |
| 祖先参数敏感性未遍历/重算 DAG | HK 8d52f917、US 7262b659 | sensitivity 使用direct refs，而公共calc已有expanded Base DAG。仅放行ID仍不重算derived descendants；ratio通用0..1可能错误夹住negative growth delta。须整体统一依赖、重算、量纲bounds；保留当前原失败及native替代测法经济区别 |
| 官方IR DOCX未支持 | CN2026-08-25已找到真实链接但未下载 | CWP官方导入未支持DOCX，不能假装text/PDF入库。待四审专家归并规范化格式责任，不机械下载闲置原件 |

## 当前执行顺序

1. RF 三个已确认共因在独立工作树施工。先写迟检查合法、未来材料拒绝、检查早于真实读取拒绝；再写 PPTX 公共 wire 合法、未知 MIME 拒绝、TXT/JSON 缺 lineage 拒绝；原始HTTP(S)出处保持、非public协议/占位URL拒绝。实际3+1个产品RED留存，初次夹具构造错误不计产品RED。
2. 使用现有 source-clock 与已有 rich-document 格式，禁止新增许可/研究状态库/供应商或更改生产模型配置。修改后一次责任集成节点跑这些测试及既有 source-clock/management/narrative tests，保存实际 GREEN 和 Ruff。
3. 正常 commit / merge main / 安装定点同步；旧安装 SHA 与原生安装 check 执行记录保留。向三个 executor 交接实际版本过渡，由它们在自己原 run 新 capture 重试；旧记录不删。今天检查的日期不能回填昨天。
4. 其他已发现问题记录到各自责任层。能独立推进的原文、研究、输入步骤继续；正式验收无法完成则真实封存 partial，再四独立审查。不得把本包两修称为全部研究问题闭环。
5. 费用以原生 ledger/receipt 实读入母账一次；已失败收费、未知 HTTP 用量均不忽略。原件留到四审完成，TEMP 只按所有权清理。

## 此责任节点交付

`f88ace5a`正常合RF main `79139534`并推，193PASS+2subtests/1.54秒，正常prepush126PASS，Ruff/mypy通过；精确远端CI37900018978成功。原生定点安装六文件到两物理root、真实execution路径byte-equal，.claude现有alias核对；配置/output不覆盖。第一次安装参数误把完整skill目录当parent，产生本次六文件嵌套副本，错误回执保留，纠正后按精确文件集/SHA证明仅清理自己的两个副本；新工程工作树干净并线后恢复不存在。详见 `acceptance.json`。

三原执行继续：CN旧HTTP三原件公开prepare均0重下载、Q1实际span消费与正式输入验真通过；US PPTX公共narrative读取成功，保留partial coverage。公司级完整报告和四审尚未完成，不以此称预测质量PASS。操作母账已实读四个原生收费run（含失败annual），最新236614tokens/151565microUSD估计；旧unknown7/FX2764保持，见 `../fresh_executor_launch/launched/budget_observation.json`，不是最终结算。

## 大节点验收与交接

工程责任节点只验接口与资格，不评价公司预测。真实公司节点必须由执行 agent 再实际调用正式 validator、CWP public NarrativeRef reader / RF consumption、compute/report/snapshot，并保留完整实际结果。之后四独立审查按原计划逐公司覆盖存储/采集/数字与流程/买方模型；编程专家根据报告归并共因。原两组六家公司与 NVDA loop 均未完成，不以离线绿色替代。

不得动 Dayu 代码、IQS owner WIP、RF assurance alerts/output、FF FMP 密钥。不得额外跑全套几十分钟 CI 来掩盖或重复定位同一故障。
