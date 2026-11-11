# 模块边界施工图独立方案审查

- 日期：2026-11-11。
- 审查者：`/root/plan_research_boundaries`；本次审查对象是 ROOT 新施工图，不是对本 agent 原架构调查的自我复核。
- 结论：**PASS；当前没有未关闭的本范围问题。** 原两项阻断及后三项文档精确性建议均已修复并复核，五卡具备独立开始 A→B→C 的条件。不增设启动许可或新实现卡。
- 本轮只读计划、指定源码与路径；只写本报告。没有运行测试、安装、网络、付费调用、创建工区或修改生产代码。通过表示计划可执行，不表示待实施的产品边界已经验收。

## 审查范围与依据

已读当前 `README.md`、`task_plan.md`、`architecture.md`、`interfaces.md`、`acceptance.md`、`dispatch.md`、`handoff_contract.md`、`boundary_matrix.json`、新增 `runtime_verification.md`，以及 `harness_lanes/MB-CWP.md`、`MB-FF.md`、`MB-RF.md`、`MB-ET.md`、`MB-SID.md`。用三路现状调查、ROOT 基线和真实安装脚本核对施工要求；未把旧收据当作本轮已通过。

父计划对齐由 ROOT 另行处理，本审查不将先前尚未更新的父文件判为失败。外仓 Git 的普通沙箱权限错误仍是核验限制，不能冒称仓库无测试、基线不存在或工区干净；WIP 基线采用 ROOT 已完成的宿主只读核验。

## 原阻断的修复与复核

| 项 | 原问题 | 当前修复 | 复核结论 |
|---|---|---|---|
| B1：M0 启动依赖 | 接口文档曾要求 ROOT 先完成新 fixture / 冻结，和五卡直接 A→B→C 矛盾；真实样本前置也可能让全部 lane 停等 | `interfaces.md:3,19,27` 明确现有接口和写集合已固定，各 lane 用本仓合同/fixture，缺失由本 lane 建立；`acceptance.md:35` 把真实组合样本冻结放在 M2 运行前 | **关闭**。ROOT 汇总是组合职责，不再是模块开工门槛 |
| B2：RF 历史兼容被扩大为迁移 | 旧 B34 admission 保留绝对执行路径和特定探针形状，不能同时要求所有旧执行包搬迁且不改身份/重签 | `MB-RF.md:41` 保留旧 retained-path 合同，只测兼容正反例和当前默认隔离；移动测试限已声明可移动 artifact / 新 fixture；矩阵 RF-03 同步修改 | **关闭**。无需新 Audit 协议、旧 run 重签或历史全量迁移 |

第二项的源码依据仍是 RF `scripts/report_catalog_research_identity.py:182` 对保留命令路径与执行目录的检查；这属于既有历史 profile 的兼容定义。它不证明普通来源读取依赖 CWP 私有实现。新卡已准确区分。

## 七项审查结果

| 检查项 | 判断与具体依据 |
|---|---|
| 实际缺口的 owner 和 TDD 出口 | 矩阵的 14 项要求各归一个 lane。CWP 的隐藏 OCR / budget / 类型依赖 / 实际包验收，RF 的旧分发工具 / core-report / 历史默认隔离，ET 的协议反向依赖和表示限额风险，SID 的 typed 错误与 metadata 反向依赖都有针对性正反例。FF 将证明缺口与业务故障区分，允许 `NO_CHANGE_PROVEN`。没有观察到本范围已确认缺口落成无人负责 |
| 写集合、现有 WIP 与并线 | 五仓五个新工区互斥，CWP 内部七责任由一作者处理。ROOT 的 integration / source-system runner 在 CWP 交付后才写。RF 四项 assurance 输出、SID 十一项 WIP 与 Dashboard 四项 WIP 有保护；Dashboard 原 owner 接续，不存在竞争实现卡。作者只交分支，ROOT 核主线增量并线，不能 restore 未提交工作 |
| 较弱模型能否独立接卡 | 每卡给真实仓根、基线、目标分支、唯一工区、PWF、读取集合、写集合、明确排除、A/B/C、现有测试及拟新增测试、独审和交接。ET 内层 Git 根、SID 非 main 正式分支、CWP master 均明确。安装文档补齐了最易误猜的 runtime 形态；无须自行发明 wheel 或新发布系统 |
| M0/M1 是否产生小门禁 | 已消除全体等待 ROOT fixture。现有 wire 不变时可独立实施并交付；真正不兼容的接口问题只协调相关 owner，其余工作继续。独审只在模块交付与组合大节点，没有逐函数/逐测试许可 |
| 范围是否过宽 | 卡内要求清点活动 runtime，是有限交付闭包核验；没有要求所有模块都重写。StockWiki / Audit 只做 ROOT 黑盒，Dashboard 走原 owner，IQS / Dayu 不改。RF 数字算法与公司预测、摘要召回、OCR 精度、未来业务和历史 run 清理不混入架构出口。ET 固定表示帽先复现，真实资源额度仍保留 |
| 权限与重复全量 | 没有新增授权 JSON、人工签收、canary 放行或 Python 调用栈鉴权。普通修改跑相关测试，模块最终 CI 与 ROOT 组合各一大节点，失败只重跑受影响面。默认无网络/付费、不部署全局 skill、不修改生产配置 |
| 验收及版本真实性 | E01–E09 覆盖复用、模拟供应、解析/阅读、真实有限样本、恢复、研究消费者接口、三表、实际 Dashboard 版本组合与交付闭包。E08 不把 main 缺少 release 命令直接判生产缺陷，也不允许用 unsupported 跳过必需场景。handoff 将代码版本、文档版本、独审、未跑、环境失败与合并状态分开 |

## 安装入口与参数的只读核实

`runtime_verification.md` 已解决“全部仓库都应造 wheel”或直接复制整仓验收的问题。下列是源码支持的实际入口；命令仅供实施阶段临时目标使用，本轮没有执行。

| Owner | 已核实入口 | 参数与边界证据 |
|---|---|---|
| CWP | `python -m pip wheel` 构建现有 setuptools 项目，再把本次 wheel 装到新 venv | `pyproject.toml:1` 定义 setuptools backend；`:19` 定义 11 个 console scripts；`:32` 定义 extras；`:84` 声明 schema/profile/grammar 资源。必须验证候选 wheel、空 cwd、无源码 PYTHONPATH，不能仅检查 TOML |
| FF | `python tools/sync_installs_b3.py --install --dest "$scratch/skills" --json`；检查用 `--check` 替代 `--install` | `tools/sync_installs_b3.py:336` 的 mode 是 check / plan / install，`:350` 接收 skill 父目录 `--dest`。没有 `--canonical`；canonical 来自执行脚本所在仓。因此必须从 FF lane 调用，实际根为 `skills/filing-fetch` |
| RF | `python tools/sync_installations.py --canonical "$laneRoot" --destination "$scratch/skills" --apply --json` | `tools/sync_installations.py:643` 定义 apply / print-manifest / import-from / plan；`:664` 和 `:667` 定义 canonical / destination。实际根为 `skills/revenue-forecast`。省略 destination 会落到默认全局目标，测试必须显式传入 |
| ET | 由 owner 列活动脚本的完整传递依赖 manifest，从当前候选逐项复制成临时 runtime artifact | 本轮未见 wheel/setup/安装器。`transcript_tool.py` 的链包括 runtime / API / extraction / worker / budget / comparison 与本卡新纯模块；不能只复制一个 CLI，也不复制 .env / 原件 / 输出。空 cwd 用 artifact 内 CLI 绝对路径启动 |
| SID | manifest 复制为保留 `src` 包结构的临时 artifact，在临时环境运行 `python -m src.company_wiki_adapter_cli` | 本轮未见 wheel/setup/安装器。runtime 应包括 CLI / API / adapter / 纯 metadata / budget / identity 及实际依赖；只允许 artifact 根参与 import，不允许 checkout 或邻仓根。保护文件可以从干净候选读入 artifact，不等于授权修改原 WIP |

RF **没有 `--check` 参数**。其精确只读命令是：

```powershell
python tools/sync_installations.py --canonical "$laneRoot" --destination "$scratch/skills" --json
```

源码 `tools/sync_installations.py:743` 在未选 apply / plan 等模式且带 `--json` 时调用 `check_target` 并输出 `check` 结果。FF 的 `--check` 则真实存在。第二次安装零写是后续需要实际证明的行为，不能由参数存在推导通过。

## 路径与命令核验的实际限度

- 五卡“现有测试”命令中的 37 个测试文件路径，在对应当前仓库文件系统均存在；拟新增测试清楚标成新增，未把它们当已有入口。检查是 `Test-Path` / 文本读取，没有 pytest 执行。
- CWP 的基线对象读取可用；外仓部分 `git cat-file` 遭沙箱权限拒绝，因此只证明当前路径存在，不声称逐个测试文件在每个指定 commit 已获同样对象核对。各卡已经要求开工记录真实基线，并将缺文件/权限/fixture 错误归环境或计划核验，不能冒产品 RED。
- `pyproject.toml`、RF 与 FF 安装器参数已直接读取；ET/SID 的 runtime 传递依赖需作者随最终实现生成完整 manifest。当前文档的最小列举不是完成 manifest，不是测试通过证据。
- 未执行 E01–E09，也未验证实际运行中的 Dashboard 进程选择了哪个配置；可见 release 配置与主仓不同只说明必须核对部署组合。计划已把这个工作交给 ROOT 和既有 owner。

## 非阻断精确性建议的最终复核

| 项 | 原文字风险 | 当前修复与结论 |
|---|---|---|
| N1：候选 wheel 与离线命令 | CWP install 曾按包名从共享 wheelhouse 和新 wheel 目录选择，同名同版本不能唯一指向本次候选 | `runtime_verification.md:8` 构建显式 `--no-index`，`:10` 至 `:12` 从本次目录选择唯一 wheel 并按绝对路径安装；`:15` 保留依赖缺失归环境、不自动联网。**关闭** |
| N2：身份和视图职责的表述 | “身份在 CWP”过宽，与 StockWiki 身份 owner 混淆；Dashboard 视图可能被误读为权威研究公司池 | `architecture.md:20,53` 区分 CWP 来源/发行人/挂牌 metadata、StockWiki canonical 研究主体/公司池与 Dashboard 自有视图/交互状态。job/run 仍各自拥有。**关闭** |
| N3：P 层验收文字 | “正式构建/安装器”可能迫使尚无安装器的 ET/SID 额外造发布系统 | `acceptance.md:18` 直接引用 runtime 文档，并明确 ET/SID 使用 runtime manifest 复制。**关闭** |

RF 的只读检查命令也已准确写入 `runtime_verification.md:31,32,35`，明确没有 `--check` 开关。这些修复全部位于文档，不扩大矩阵、不重审原研究质量，不给 StockWiki/Audit 新开实现卡。没有证据表明原共享 wheelhouse 实际存在候选冲突；N1 是验收候选选择的精确化，不是产品故障报告。

## 交付判断

本轮方案中已知的实质依赖冲突已解除，审查意见全部关闭。ROOT 可将文档状态更新为方案独审通过、五卡可派发但尚未开始；本轮仍不启动生产代码实施。后续每卡按自身测试闭环和交付独审工作，ROOT 按冻结组合与既有 owner 证据关闭本阶段，不以研究质量或新的无证据重构继续延长架构阶段。
