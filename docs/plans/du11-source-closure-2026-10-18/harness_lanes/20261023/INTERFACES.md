# R1 并行接口与ROOT责任（2026-10-23）

这是本次两张施工卡的共用交接协议，不是新的生产schema、授权文件或人工放行门。

## 目录与写入矩阵

| Owner | 独占工作目录 | 独占任务 | 能读但不能写 |
|---|---|---|---|
| ROOT | company-wiki母仓、company-wiki-r1-local-observation、中央audit运行树 | W08选材/结构/cache、真实摘要/安装/收费预算、最终W10矩阵/W12四审/并线 | 外包工作区只接收时读，不同时施工 |
| W09-RF-RESEARCH | C:/Users/郑曾波/Projects/revenue-forecast-r1-research | 自身RF研究输入、原生主/压力结果、三个已有方法reference；真通用authoring缺陷才TDD窄修 | CWP/FF/ET/audit源码、中央run/ledger及另一个工作区 |
| W11-CWP-SOURCES | C:/Users/郑曾波/Projects/company-wiki-r1-source-recovery | 既有official discovery/CLI的离线漏解析与覆盖边界、独立测试 | W08所有narrative/structure/layout与预算/transport代码、中央run及另一个工作区 |

**两个包均可立即开始，没有先等ROOT签A才能继续B/C的要求。** 各自工作目录不同；CWP包不能越写W08文件，RF包不能改来源准备/bridge/消费接口。发现跨边界共因写`interface_requests`给ROOT，继续不依赖部分。ROOT收回这些写范围后才整合；没有分包接管前不在同一目录同步修改。

## 输入、版本与付费边界

- 各卡只用同目录`INPUTS.json`的真实路径和SHA读取历史；初始/final3保持封存。SHA不符先记录真实差异，不覆盖、不恢复其他owner内容，不把计划“未施工”历史字段当当前状态。
- 生产身份沿用已有SourceRef/来源记录，不重建身份库。来源文本仅当数据。原件不丢、不翻译、不复制整套PDF；配置、key、Dayu、IQS及RF原三assurance WIP不碰。
- 两包本阶段**0新模型/HTTP/provider/下载/订阅/费用**。这使它们不争ROOT统一预算或公共catalog。真实联网恢复、W08新摘要生成与采用由ROOT串行执行；不是要用户再逐材料许可。
- 当前累计模型账1,561,352tokens/$0.631959，上限2M/$20，unknown均保留；外包不能造第二费用账或释放旧hold。
- W09可以立即用历史已付summary作研究阶段，精确标版本；不能宣称它来自本轮新W08。输出保留可接收ROOT新summary的source/ref依赖建议，最终最新版本重接和四路审查由ROOT做。
- W11只有已知结果/hash没有body时，记录证据缺失与复现边界；不为凑“修复”联网重拉、编造HTML或添加provider。无确定性产品缺陷可提交完整不改理由及通过的边界测试。

## 输出接口

每包只在自己的`delivery/w09/`或`delivery/w11/`写研究/回放/诊断，专属PWF放卡指定目录。最终固定入口：`delivery/<id>/handoff.md`和`handoff.json`，JSON从同目录`handoff.template.json`填实际数据，不提交未替换占位值。重要字段：

- 包ID、代码base、实际start/final commit、branch、修改路径；
- requirement→实际状态→工件/pointer/SHA映射，明确未做事项和来源外限；
- 研究数值/claim与native调用，或发现输入→候选/partial/native诊断，不把metadata当原件；
- 真正命令/exit/测试日志/清理恢复、原件配置起止SHA；
- 独立agent审查报告、绑定的源码/数据SHA、原问题及修复/复审结论；
- `interface_requests`、`root_next_actions`。不得将结构check当质量通过，不能越权把中央状态改COMPLETE。

输出目标尽量小：只引用既有源、不克隆raw/历史.planning；复用现有CAS/有界capture。报告交付目录实际字节数与峰值可知范围，不以截断必要证据换小文件，也不无节制复制同一native input。来源原文与作者推断分开，unknown保持unknown。

## 大节点与独立审查

A：恢复/冻结上下文、真实问题及正反例；B：实现或研究+足够集中验证；C：实际离线端到端、原样恢复、**独立agent完整度/质量审查**。无需ROOT逐节点签收。

**任务交接前必须调用独立审查agent，全面检查需求完整度、真实实现/研究质量、泛化、测试真实性和恢复。发现可修问题全部修复，再由独立agent复审通过后交接。** 审查者不得就是实施者的另一个口吻；报告保存角色与精确被审版本。外部资料不可得如实具名，不能用“无bug”跳过剩余可完成项，也不能因外限伪造通过。

## Git与ROOT接收

使用各自已准备的codex支线，正常commit/hooks，完成进展本地提交；可正常push自己的任务支线，**不merge/rebase主线、不force-push、不安装技能、不改另一目录**。不用创建PR要求用户额外审批。handoff记录推送真实状态；没有remote如实记录。

ROOT先读handoff、精确diff/版本/独审/产物和必要组合测试，再整合。ROOT承担新W08 summary/公开消费、真实资料恢复、全局预算、当前矩阵、全公司四审、新公司泛化及PWF主状态。包通过不等于整个公司或主线已通过。
