# Revenue Forecast 架构与代码质量审查

2026-10-13；负责人：独立 RF agent；基线 `b9208a2117b8423f4b355dfca885aaf0d56a05bb`。仅修改隔离 `Projects/_harness_worktrees/architecture-quality-20261013/revenue-forecast`，不写 canonical RF 的 150 个运行/output 文件。

当前交付：B 已完成，正常 commit `f0d694d69a05ef3f7a449e87cd91cdb44d1ff8ce`；工作树干净，未 push、未安装、未改 canonical。ROOT 的 C 接收/跨仓/推送仍待。最终证据见仓内 `docs/implementation/architecture-quality-2026-10-13/verification.json`；97个owned runtime 文件，退休队列和 tools 不发货，14个定点 runtime 文件见 handoff。

## A：调查范围与结构

对 `scripts/`、`tools/` 的 105 个非测试 Python 模块（30,585 行）执行 AST 解析、导入/函数结构清点和字面路径/宽异常扫描。CodeGraph 可用，但仅索引 32 个 scripts 文件，且部分代码位置对应旧内容；结构查询已执行，当前行为证据以隔离 checkout 读取为准。7 行以上函数未发现逐字完全相同的 AST，存在语义重复，需要按职责消除而非按函数名删除。

重点阅读：CLI `revenue_forecast` → `revenue_core` → contracts/document/evidence → forecast/calc/segments → model_registry/extensions → recognition/constraints；source_preparation → FF subprocess → SourceRef v2 verified reader → narrative reader/context；research/native_dependencies、驱动树/目标/证据输入的边界；publication/snapshot/backtest；sync_installations/运行包与快测 CI。其余模块完成静态扫描，未逐行人工证明。本文不是所有投资分析质量已达标的声明。

当前有效分层：CWP 负责存储定位和原文版本，FF 负责复用/采集，RF 消费来源并拥有纯数学模型、声明与计算依赖。模型公式/会计定义/低中高情景、schema 版本等是领域常量，不是应删除的公司硬编码。生产 RF 未发现具体公司名、供应商模型或个人绝对目录硬编码。`tools/ex05_chain_replay.py` 等旧工程重放仍含个人目录，见暂缓项。

## 优先根因与实施范围

| ID | 证据与影响 | 处理 |
|---|---|---|
| RF-AQ-01 | `revenue_forecast.main --version` 单独复制安装包清单，仅对文件名列表 hash；`sync_installations.installable_files/manifest` 使用另一份清单并对真实字节 hash。改运行脚本内容后 version 标识不会改变；两个入口的目录缺失语义也不同。 | 建立位于可安装 runtime 的共用运行包清单/内容 manifest。安装工具消费该接口，runtime 不依赖 tools。保留 version 文本字段，修正 manifest_sha256 的含义为清单+实际 owned 文件字节；不改旧快照。 |
| RF-AQ-02 | `source_narrative_context._formula_refs` 只遍历 model driver，漏实际收入确认 carry-in/progress、合并调整与约束；`research.native_dependencies.segment_roots` 以 len(ids)==len(years) 读取 carry-in，实际 lagged_activity 的 carry-in 数量是 lag_years，短于预测期时整条依赖丢失。calc 又维护第三份根列表/情景投影。 | TDD 固化真实 carry-in/进度/调整反例；抽共享原生参数用途 visitor 和 derived ancestry；calc/native research/narrative 消费同一职责。保留期间、情景、segment 与输出角色，不能把每个元数据引用算消费。数学公式与预测数值不变。 |
| RF-AQ-03 | `contracts.evidence.finite_number` 对任意大整数 float 转换抛裸 OverflowError；`forecast.calc.evaluate_derived_formula` 的幂/算术可抛 ZeroDivisionError/OverflowError 或产生 complex，绕过 ForecastInputError 的 CLI 诊断契约。 | 在共同数值/公式边界将真实非法实数算术转为既有 ForecastInputError；负值合法公式、正常幂和实际模型保留。 |

上表是 A 调查时的实施范围；以下 B 记录及首页当前交付覆盖当时的未实施状态。

### B 阶段追加事实（独立 peer 与真实三公司回放）

- `RF-AQ-04`：ROOT 真实腾讯冻结回放发现 shared excerpt 守卫将物理引文 SHA 当成命题身份。原表同时有 H1 下滑和 Q2 改善，两个节点结论不同；误拒并非输入数字幻觉。按 ROOT 确认，仍拒绝同 claim 或同来源+引文+规范化同命题的正反重标，不同结论共享引文披露 `NOT_EVALUATED`，不升级为语义/买方质量认证。原负测 `Supports./Contradicts.` 没有具体命题，已强化为同一明确命题换 ID；另有混合期间表格和同 claim 重用反例。RED 1 failed/2 passed，随后相关集中回归已通过。
- `RF-AQ-05`：RF 生产 source preparation 每次成功时提交第二个进程内 DemandQueue；实际只由两测试读取，没有 scheduler/worker 消费，且 `now=0.0`。CodeGraph 未收录新模块，当前源码/导入查询证明 CWP/FF 没有该全局队列读者。已移除生产 enqueue/global/API；旧契约实现移到 `tools/legacy/processing_demand.py`，只用于历史回放，停止安装发货。旧两个测试改为真实公开复用/零下载与禁止第二任务提交断言；独立 tripwire RED 1 failed。旧安装残留明确排除运行包 manifest，不进行目录替换或额外自动删除。
- `RF-AQ-06`：提交 hook 固定 `C:/Miniconda/python.exe` 和个人 PortableGit 目录，`#!/bin/sh` 下使用 Bash 数组。已改为当前 PATH 的工具发现和 POSIX 参数传递，保留 PATHEXT 兼容及正常检查；本机现有 sh 的 `-n` 与真实正常 commit 通过（ruff/mypy/host-assumption 均 passed，4.22s）。
- `RF-AQ-02` 的独立 peer 进一步证明：A 参数影响 linked_ratio/proportional sum_cap 下 B 的有效收入，但旧归属图拒绝该真实跨分部作用。共享 visitor 现区分直接输入 clock 与 recognized/effective 输出 clock；有效依赖按原约束声明顺序只传播 ID，不计算金额。fixed_weights 的金额与激活条件依赖分开；elimination 不混入其他分部。growth 归属和 native scope 使用有效值依赖；Narrative 回执可指出跨分部作用、lag 输入期与确认期。direct_growth 累积关系由 ModelSpec 元数据声明。新增 4 个 peer 反例先 RED；模型 tail 不得当作期内增长驱动，旧通用夹具独立按显式 lag 算法排除尾部，没有从生产 visitor 复制答案。
- `RF-AQ-07`：合法三情景共同 A+10% 后，proportional cap 下 A 三情景理论均 103.125，但 native 原公式得到 low=103.12500000000001、base=high=103.125，严格排序拒绝 1 ULP 舍入误差。已用共同 `scenario_ordered` 的最多4 binary64 ULP判定修复，runtime/output 都消费此边界；原金额不变，不排序/夹平，不用收入对账容差，5 ULP 与真实金额倒序反例仍拒绝。

初次三个根因 RED 11 failed/7 passed（4.40s）→18 passed（6.65s）；首轮受影响集合213 passed（30.05s）。追加 peer/退休/ULP后的最终集中 core **151 passed、2 subtests（13.37s）**，边界/模型/安装/W07-W08工具 **217 passed、62 subtests、8 skipped（24.58s）**。8 skip 是既有 scalar mutation helper 不适用于特殊/拒绝案例；最终真实31向量全跑，旧主线/候选均20 PASS/11 REJECT_OK，31个 actual observed+status逐项精确一致。各3 public CLI返回预期，readonly/tmp恢复。ruff/mypy11模块/host-assumption/sh syntax均绿。

真实中微、腾讯、微软冻结输入在最终代码重算：货币、单位、基础年/财年、历史收入、每个分部完整输出、合并路径、敏感性和管理目标与原正式输出逐项精确相同；输入与原 forecast.json 均 SHA 未变。腾讯新增语义限制而非“全技能审查通过”。机器证据已提交在 RF 隔离仓 `docs/implementation/architecture-quality-2026-10-13/verification.json`。

## 兼容性与不做的改动

- 不改变 SourceRef/SourceExport、FF wire、原文 SHA/as-of 与货币/单位契约；不重复上游身份解析、不增许可或人工签收。
- 不把 pure RF 反向耦合 CWP/FF Python 包；保持进程公开接口。
- 版本标识文本形状保持，content digest 语义修正已报 ROOT；不是 attestation/release 放行许可。
- 原生模型算法、schema 3.7–3.10、W08 dated-flow/C05 真 snapshot 回测原样验收。
- DU 三包只处理文档理解，本线不写 DU worktrees/接口或替代文档解析引擎。

## 暂缓与理由

- 历史 `company_wiki_source`/`_prepare_legacy_source`、`processed_artifact_canary` 有真实历史 replay 测试调用，不能以“旧名字”为由直接删。RF DemandQueue 的生产热路径已按实际无消费者证据退休；纯历史回放留在不安装的 tools/legacy，当前不新建任务库。
- `revenue_report`（1,819 行）、contracts/document（1,295 行）有多个责任片段，但单按体积拆分无法证明质量改善；先收敛已复现的共享依赖与部署根因，避免一轮改写数值/渲染/验证整个体系。
- legacy attestation 仍有 build/validate/publication/registry 调用和兼容测试；既有人工授权已简化，保留的是来源/输出一致性，不增加新的签收。
- `ex05_chain_replay` 的个人路径是旧工程入口，不进入默认 skill/CI；未来统一接受明确 fixture/config 参数再迁移，当前不运行或改写生产目录。
- 真实模型供应商/下载、经济假设质量四独审由母计划 G2/G4/G5 承担，本工程质量线离线验证不能替代它们。

## 测试与交接

大节点 A 调查；B 先失败反例再实现，集中受影响单元/集成和 W08 原生组合已完成；C 由 ROOT 统一跨仓接收、安装、推送。所有真实 subprocess 测试使用 tmp 目录并恢复；本线没有 push、安装或生产写入。`handoff.json` 保存最终 commit/精确安装范围/计数/清理；本文件不替 ROOT 的跨仓验收签收。
