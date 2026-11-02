# 先解耦、后分模块：独立验收设计

2026-11-02；独立审查 `/root/decoupling_acceptance`。本轮只读代码与既有计划，没有产品修改、付费调用或全量测试。用户最新要求取代本目录此前“可先并行”的建议：外部RF/AUDIT施工暂不派发，由ROOT先集中关闭已知跨层依赖。

本报告的D0–D3是验收矩阵视角，**执行顺序和唯一阶段编号以[DECOUPLING_FIRST.md](DECOUPLING_FIRST.md)为准**。本报告D1映射主计划D1测试及D2.1/D2.3实现，本报告D2映射主计划D2.2资源实现，本报告D3映射主计划D3集中验收；不创建第二套阶段状态。

## 本轮“解耦完成”的有限定义

核心来源链CWP、FF、ET、RF、StockWiki及AUDIT只依赖所属公开接口与本仓适配。一个模块内部数据库布局、文件目录或解析实现改变，在公开合同不变时，其他模块无需改源码/本仓单元测试；可通过配置连接另一个符合合同的实现。跨仓集成测试继续存在并由ROOT执行，不能将其删除或skip换“独立”。

这不等于模块没有业务依赖，也不要求先解决所有公司研究问题。T4父链、SEM-QUAL-01、RF ghost/期间计算和新真实摘要/研究采用是后续业务质量责任，不能一并塞进架构验收，令本节点永远收不了口。若某改动直接触及现有数据语义，必须保原有反控；不能以“只看架构”为由放行已知破坏。

## D0：接口与责任清点

交付一份公开入口/调用者/字段责任/连接适配/实际资源账户表，复用已有协议，不另建SDK仓、微服务、第二数据库或新调度器。

| 接口 | 所属事实 | 消费者应做 | 消费者不得做 |
|---|---|---|---|
| SourceRef、verified-open、SourceExport v2 | CWP原件、版本、manifest、locator | 实收字节与自己用途的期间/as-of匹配；转本仓不可变值 | 拼物理公司路径、读CWP表或内部artifact DAG |
| Narrative reference/bundle | CWP来源卡、support/context、质量观察 | 保完整来源与不确定性，独立研究解释 | 重建PDF结构、将可选诊断缺失当禁读，或把无诊断当世界事实已证 |
| Acquisition与ET结果 | FF编排、ET provider原件/真实usage、CWP canonical入库 | 传递任务资源意图、实际usage和命名状态 | 每层私造更小原件帽、用provider自报verified替代CWP实读 |
| Native execution与audit观察 | native owner结果；AUDIT记录/评价 | 分别保存native状态、观察完整性、独立质量结论 | optional日志故障翻转已保存成功、重POST或伪造PASS |

核心字段/版本/身份与可选诊断扩展要明确。可选字段兼容不等于盲目忽略未知核心语义；未知核心版本/无法解释的必需能力应命名unsupported。字段合同由producer维护，portable fixture归合同，不用consumer从producer内部对象反向推schema。

**D0可执行判据**：列出的实际生产入口全部有owner和适配点；现有样例可被producer输出、consumer读入；没有仅靠会议式“同意”或allow JSON的通过条件。

## D1：端口与测试独立

1. 连接配置在组合/适配层收敛为公开command/connection描述。旧`python -m company_wiki...`可以作为默认适配；默认本身不是违规。应用与研究逻辑不能要求CWP checkout名、固定`config/source_catalog.yaml`位置或直接导入实现。
2. Consumer本仓测试使用便携公开wire fixtures/fake ports，可在没有CWP源码/DB、任意工作目录、不同安装位置下运行。public接收端对实收字节复核保留；同进程已经验证的不可变值不反复重算同buffer。
3. AST依赖检查覆盖实际active调用面，检测直接和常量动态import、跨仓SQLite/物理根扫描；同时以可运行fake port替换试验证明，不只查字符串。不能一刀切禁止本仓自己的数据库或正常文件I/O。
4. 现有跨仓E2E的CWP内部fixture生成迁回CWP owner的test-support/公开初始化入口，ROOT组合测试调用它。RF不维护CWP表结构。**原测试场景/断言→新位置/入口的映射必须完整，ROOT仍执行；没有执行责任的“移出默认测试”不算解耦。**

实际证据与可复用起点：

- StockWiki `_source_reader_v2_transport.py:57–85`已有`argv_prefix`等注入接口，可参考，不必统一成一个共享实现包。
- FF `scripts/ff_configuration.py:79–95`仍要求root下固定config；RF `scripts/company_wiki_source_reader_v2.py`直接组装CLI，相关测试`test_company_wiki_source_reader_v2.py`已包含有效bytes/错误SHA/期间/单调用反控。
- RF `tests/e2e_support/isolated_lake.py:245,352–355,382–387`导入CWP配置/flags/policy/prompt guard并直接SQLite写表。实际调用测试包括`test_fc1001_isolated_lake.py`、`test_fc1002_three_process_e2e.py`、`test_fc1003_uj.py`、`test_fc1004_platform.py`、`test_fc1102_t2_runner.py`、`test_fc1105_fault_injection.py`、`test_fc1302_scan_health.py`、`test_preparation_e2e_success.py`及ZR709/802–805旅程；实施时确认哪些当前仍执行，逐项保覆盖归属，不凭历史名称删掉。
- FF `tests/financial_statements/test_layer_boundary.py`已有AST动态import反控，当前只覆盖两个statements入口，可按明确active端口扩展；不能误报公开module字符串为跨层import。
- CWP `tests/contract/test_architecture_gate.py`偏历史flag/activation，RF `test_ca303_arch_quality.py`偏复杂度/旧图快照/mypy；二者通过不足以证明本轮跨仓独立，不能拿旧大套件代D1。

**D1通过**：相关消费者离线本仓包在无上游源码条件下通过；同公开接口换fake command/安装位置无需改业务代码；active边界违规为0；迁移的原集成场景已映射并保ROOT执行入口。历史不再可达兼容路径明确标识，不假装仍是生产依赖，也不借“legacy”掩盖真实caller。

## D2：同一任务资源与输入责任贯通

清理已确认本地OCR/CLI表示帽及CWP import重复16MiB/25MiB帽，沿实际请求预算闭合。显式真实资源限制仍负责读取、进程清理、费用和恢复；可选诊断字节/空白不决定业务成功。

关键区分：**原件允许大小**、**已消耗网络字节/费用**、**剩余deadline**不是同一个数。17MiB下载后22MiB网络额度可能剩5MiB，但同原件入库仍应按本次允许原件大小检验，不能拿网络余额5MiB二次拒绝；本地入库也不能重复扣provider网络或费用。deadline可传剩余时长；JSON/base64 pipe空间由原件额度推导，不另设任意小顶帽。

**D2必要正反例**：

- 语义相同compact/padded合法本地JSON走到同owner；坏JSON/重复key/类型错误仍命名失败；不靠裁内容。
- 小原件显式大预算可接受；本次17MiB合法FMP原始JSON在22MiB允许额度内，到CWP writer/verified-open保持原始字节与SHA。TXT是提取结果，不冒原始FMP响应。
- 真正超过请求原件/网络额度、剩余deadline耗尽、错误身份/期次/hash/type仍按实际owner失败；只扣真实usage；未知付费状态不盲目重做。
- 再次请求已保存原件复用，provider调用0；中途观察文件I/O失败不变成重下载/重复付费理由。

## D3：一组组合验收与集中独审

不重复全量；选择覆盖改变边界的现有测试＋缺口测试，执行以下完整端点：

| 场景 | 最终端点/判据 |
|---|---|
| 存储可替换 | 移动配置根/修改CWP内部存储布置后，同SourceRef经公开reader得到同内容，RF/Stock无需改代码；错字节仍被发现 |
| 采集闭合 | FF→真实ET CLI/supervisor+fake HTTP→CWP import/canonical writer→verified-open；17MiB FMP JSON/22MiB额度、再次0下载及真实错误反控 |
| 消费者合同 | 同一便携current/兼容fixture经RF/Stock/FF adapter语义一致；允许的诊断扩展不影响核心值；未知必需语义不伪成功 |
| 观察隔离 | fake native实际成功、optional observer失败，native结果和unknown观察分别保留；真实输入变化/错误SHA仍可见，不重复调用 |
| 测试迁移不丢覆盖 | D1映射的原三根/旅程/故障恢复场景在ROOT组合入口仍执行，结果可追溯；不能skip/move-out换绿 |

可复用小包：CWP `test_architecture_quality_storage.py`根迁移/公开读反控；RF `test_company_wiki_source_reader_v2.py`、narrative reader/process相关；FF `test_transcript_owner_budget.py`、`test_transcript_response_budget.py`、`test_transcript_companion_transport.py`和statements边界；StockWiki `test_narrative_source.py`、`tests/e2e/test_cwp_narrative_source.py`；AUDIT `test_scope_request_binding.py`、`test_w04_capture_runtime.py`和checkpoint observation。选精确受影响节点，不把这些文件列表变全量固定门。

最终由未实施本次改动的独立agent审D0–D3证据和实际接口，修好所有影响本节点的主要问题；正常提交/推送/必要定点部署。只需一个集中架构验收结论：公开端口、接口兼容、测试独立、预算、观察状态及完整链都满足；不增逐函数人工许可或运行时“架构已批准”flag。

通过后ROOT更新各仓PWF为可启动，才派RF/AUDIT等后续业务任务。架构验收不签T4/SEM或公司研究通过；它确保后面的修复可以归本仓、独立测试、稳定集成。

## 审查操作说明

CodeGraph先用于结构/文件检索；其部分结果指向旧镜像，随后读取已定位当前源文件。一次询问RF旧测试名不存在，已根据实际调用检索找到FC1001/FC1002等；没有据缺失文件认定功能缺失。未运行作者脚本、完整测试、付费调用或写原件/配置，只新增本报告。
