# P7-RF：经营校准绑定与支持范围诊断

**可以立即开工；较大 RF 工程包。**本卡修已复现的共用校准诊断，不将原 W09 研究执行改称已完成工程。

## 0. 独立上下文与启动

- 项目 revenue-forecast；工作目录：`C:/Users/郑曾波/.codex/worktrees/m3-acceptance-20261010/revenue-forecast`。
- 分支 `codex/p7-rf-calibration-binding`；base `6883bf00548abb9891eab6762aeaa89e3898b202`（4.2.0 / opt-in3.9）。
- 复用MAIN已干净的集成工作树，避免再复制870MB历史跟踪记录；原分支仍保留。
- 唯一 PWF `.planning/p7-rf-scoped-calibration/`，三文档/本卡已放好。
- 先读本仓约束、SKILL 的经营研究与校准references、本卡/自己PWF。冻结 R16/R18/W09 仅作工程起因，不关闭它们的真实研究缺口。

```powershell
Set-Location -LiteralPath 'C:/Users/郑曾波/.codex/worktrees/m3-acceptance-20261010/revenue-forecast'
$env:PWF_PLAN_ROOT = (Get-Location).Path
$env:PLAN_ID = 'p7-rf-scoped-calibration'
& 'C:/Users/郑曾波/.cache/codex-runtimes/codex-primary-runtime/dependencies/native/powershell/pwsh.exe' -NoProfile -File 'C:/Users/郑曾波/.agents/skills/planning-with-files/scripts/resolve-plan-dir.ps1'
```

启动解析使用本机已有 PowerShell 7；旧 Windows PowerShell 5.1 缺 IsPathFullyQualified，会返回空结果，不能据此切换到别的计划。

检查branch/base及本卡启动文件之外的diff。canonical仓 assurance3文件/output 是原owner WIP，不读作夹具、不改、不提交。

工作树已有仅含本卡启动文档的 bootstrap commit；base是源码基线（HEAD祖先），不要求HEAD与base相等，不reset丢掉启动PWF。工作树源码未施工；按自己的PWF执行M1。独立目录内的 `INTERFACES.md`、`HANDOFF_FORMAT.md`、`handoff.schema.json` 和合成example已配齐，相对路径从本卡PWF解释。

## 1. 已实测根因

`scripts/research/evidence_roles.py::_calibration` 不消费 observation.binding_status。用 calibrated_document fixture 经 validate_document→analyze_operating_research 的纯函数反例：

| 变化 | observation层 | 最终错误结果 |
|---|---|---|
| 三conversion换无关业务scope | unverified_scope | referenced_range，三个未来输出supported |
| 三conversion换FY2031 | unverified_period | 同样误绿 |
| range端点及calibration.scope同时换无关产品 | unverified_scope | 同样误绿 |

原有效 upper endpoint 未用于收入DAG，现有诊断也为unverified_scope，却是合法独立参考。**不能一刀切要求参考端点都bound/都参与DAG。**应区分独立范围真实性/口径和实际转换/收入输出的绑定；不重验原件身份，不新建研究许可。

## 2. 精确排他写集

允许：

- `scripts/research/evidence_roles.py`、`scripts/research/native_dependencies.py`。
- 必要时新增 `scripts/research/calibration_binding.py`。
- 新 `scripts/research_support_diagnostics.py`。
- `tests/test_research_evidence_roles.py`、新 `test_scoped_calibration_support.py`、`test_research_support_diagnostics.py`及 `tests/fixtures/scoped_calibration_support/**`。
- `references/evidence-role-calibration.md`、新诊断reference、SKILL中相关步骤定点文案。
- 如 native emitting 诊断语义变化需要补丁版，仅 `scripts/contracts/constants.py` 的版本常量和 CHANGELOG；不改其中算法/期间/schema规则，版本影响在交接明确。
- `.planning/p7-rf-scoped-calibration/**`。

禁止：CWP/FF/audit/其他仓、assurance/output/artifacts/用户config、旧 PWF/报告/157矩阵、源下载与source-preparation、period_flow/annual consumption/triangulation、model calculators/sensitivity DAG、CI/hooks、安装副本。不删除或改 golden/hash凑绿。MAIN不同时改此RF写集。

## 3. 保持与新增接口

保持 analyze_operating_research(data, validated)、operating-research/1 输入结构、收入Low/Base/High算术、stable-fsum/1 confidence、来源API及period合同、无optional research的旧行为。不新增必填事实或默猜reference口径。

修正共同 calibration relation：

- 独立范围端点证明其真实parameter/单位/观测期间/声明参考scope；它可不在收入DAG。
- 实际conversion和预测output必须指向目标业务、情景、期间与真实native DAG；无关scope/period不能由文本calibration标签晋升supported。
- 跨scope合法benchmark需显式可复查转换关系；不同公司/总市场不是自动同口径。
- 单driver被支持不等于所有segment、情景、全部三年被支持。unknown不填0，stress不改称校准。

新增只读CLI输出 `economic-support-diagnostics/1`：input SHA、请求年、逐segment×year×scenario的supported/unsupported/conditional及原因、相关calibration/parameter/claim ID，economic_truth_inferred=false。输出JSON到明确新路径或stdout，不写输入/来源/生产registry，不调用模型/下载。

现有 revenue_report 通用展示 adequacy_status/reasons，尽量直接复用，不改它。诊断新细节放独立输出；如更改native研究诊断，明确新emitting补丁版本，旧4.2.0输入/报告原字节保留并用pinned emitter验证，不冒用旧版本。不得改3.9 schema或增加一套严格发布门。诊断不等于买方经济质量认证。

## 4. 三个大节点与TDD

### M1：关系合同与RED

读既有测试/函数，保存上述三个反例真实失败日志，冻结新CLI样例。额外正控：upper未入DAG仍合法独立参考；正确conversion/output仍referenced_range。不要把缺证据改成许可问题。

### M2：共用修复和集中GREEN

覆盖同驱动与其他驱动、FY26与FY27/28、业务/情景/期间交叉借用、显式benchmark转换、stress、unknown/null、空optionalresearch。证明合法收入算术/confidence不变。input与诊断同步篡改也不得绕过既有strong recompute。每个不支持项给具体关系/ID原因，不能只一条“insufficient”。

运行新责任tests和既有research_evidence_roles；沿既有静态标准。更新方法文案讲清范围、转换、支持期和真实研究的区别，不堆审批。

### M3：隔离公共E2E及交接

自己的TEMP中生成native fixture，真实CLI正负控；准确参考 `tests/test_research_evidence_roles.py::test_actual_case_assembly_cli_then_native_validate_compute_snapshot`：它用 build_revenue_source_record_from_verified_read 创建合成source preparation，并示范 tools/build_auditable_case.py 全部实参与 run_target_measurement_e2e.py 的 validate→compute→render→strong→snapshot。先读此例和实际 --help，不得猜argv、伪造preparation receipt或把手写JSON当native结果。

**每个会run_forecast/snapshot的子进程都将 REVENUE_PUBLICATION_REGISTRY 指向该 owned TEMP。**调查误用run_forecast曾尝试生产registry写入、被沙箱拒绝且未写；不能重复此错误。测试context设置并finally恢复环境，调用前检查输出/registry路径均在owned根。

比较native output/Markdown/独立诊断一致及正确算术不变；保护旧fixtures/config/ownerWIP SHA，结束恢复TEMP初始状态，无全湖备份。外部provider/LLM费用0。独立agent只在此大节点复核无关scope/period和合法独立endpoint，不逐函数签收。

## 5. 交接

normal hooks commit/push自己的branch，禁止main merge/push/no-verify；exact CI未触发如实记录。HANDOFF.md/JSON用共同格式，列RED/GREEN/E2E、实际diff、兼容与版本、保护/恢复证据、源输入输出SHA、诊断CLI样例、定点安装候选文件清单。安装及三仓集成由MAIN做。

research_remaining必须保留：原R16/R17/R18真实公司幅度、管理目标/并购控制、三年路径、时序与jointstress尚需原件研究/四独立审查。本卡工程通过不能关闭这些研究项，也不能把unsupported自动凑成三年成功。
