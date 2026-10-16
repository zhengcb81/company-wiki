# DU6-RF-TARGET-MEASURES：管理层目标的单位、带符号增长与比较语义

## 0．接单状态与工作目录

- **状态：PREPARING；等待 ROOT 真正创建工作树并在总表标为 READY。** 预定目录不等于已经存在；此卡不授权自行改主目录。
- 项目：`C:/Users/郑曾波/Projects/revenue-forecast`。
- 已只读确认基线：`5122107bbc86c3d1e79886b372700c05d19bb349`，2026-10-16；DU5 单位卡已发布，不能从作者旧分支继续。
- 预定独占工作目录：`C:/Users/郑曾波/Projects/revenue-forecast-du6-targets`。
- 预定分支：`codex/du6-rf-targets-20261016`，由 ROOT 建立并登记真实基线。
- 本线 PWF：工作树内 `docs/plans/du6-targets-2026-10-16/`，含 task_plan.md、findings.md、progress.md、handoff.md/json、receipts/。只写自己的计划，不回写 CWP 总计划。
- ROOT 负责与其他线接通、主线验收/提交/推送和安装同步。作者正常提交自己的分支后 STOP；不合主线、不改安装副本。

## 1．为什么做：当前代码证据与要验证的假设

先读工作树中的本卡、DU5 `docs/plans/du5-units-2026-10-15/{task_plan,root-acceptance}.md`、W05 `tests/test_target_measurement_comparison.py`、`references/management-targets.md`，再用 CodeGraph 查看结构。新工作树未初始化索引时不能擅自修改索引；可读取卡已点名的源文件，并如实记录结构工具不可用。

当前主线的静态事实：

1. `scripts/research/target_measurement.py` 又有一份 `_SCALES`，包括 trillion/万元/亿元，却未复用 DU5 Currency×Scale，缺 10k/100m 等同义表达；`normalize_target_bounds` 直接比较 raw_currency 和模型 currency 字符串，CNY/RMB 别名不能贯通。
2. `scripts/research/targets.py` 在进入 typed validator 前一律要求 raw 单值及区间下界非负；`input_targets.py::build_management_target` 也如此。负增长指引不能按原百分比进入相同流程，但普通收入金额的非负要求仍合理。
3. typed `level_multiple=0.9` 可规范化为 -10% 增长。`target_measurement.py::_meets` 的 `at_least` 使用 `low*(1-tolerance)`，当 low 为负时容差方向反转；对负目标直接计算 observed/low 作为 attainment_ratio，容易反转“较好/较坏”的含义。
4. `_meets` 在 low!=high 时直接区间成员判断，没有分辨原比较词。不能擅自猜所有比较词和区间的经济含义，需要先写清合同，无法定义的组合给具名诊断。

上述不是本卡已执行的 RED。A 节点必须用实际构建器/原生引擎证实：错误来自哪一层、合理输入是否真被拒、比较是否真算错。不得为凑缺陷把旧的有意拒绝称为代码错误。

W05 已完成季度桥、正同比、缺基期及真实 scenario 祖先关系；W07/W08 已完成正金额/累计/净额目标组合；DU5 已完成转换记录与真实 sensitivity 参数单位绑定。本卡不重做这些项目，也不重写预测引擎。

## 2．独占写入白名单

仅下列路径可写：

- `scripts/research/target_measurement.py`
- `scripts/research/input_targets.py`
- `scripts/research/targets.py`
- `scripts/research/input_quantities.py`：只增加目标消费者必需的共享金额接口/有限别名，保持 DU5 sensitivity 责任和所有既有转换字典；不得重新发明第二单位表。
- 新 `tests/test_du6_target_measurement_boundaries.py`
- 新 `tests/fixtures/du6_targets/**`，只保留小型合成输入/独立手算期望，不复制原文湖或旧大输出。
- `references/management-targets.md`
- 自己的 `docs/plans/du6-targets-2026-10-16/**`

其余均只读，包括旧测试和 golden、revenue_report.py、contracts/constants.py、顶层 input/output schema、schema_compatibility.py、SourceRef/reader/来源准备、证据 hash、CWP/ET/FF/Audit、模型公式、sensitivity.py、publication registry、配置/凭证、CI/hooks、安装副本、assurance/runs 与 output。若必要实现碰到白名单外的真实接口缺口，写最小复现/精确所需接口交给 ROOT，继续白名单内可做部分；不要自行扩权修改其他仓库。

## 3．冻结输入输出与唯一责任

### 3.1 现有端口

- `research.target_measurement.normalize_target_bounds(target, data) -> tuple[float, float]`
- `research.target_measurement.compare_target_measurement(target, result, parameters=None) -> dict`，每 scenario 保留现有 metric_kind/period/unit/modeled_value/target_value/target_low/target_high/comparison/comparison_status/reason/meets_target/attainment_ratio，以及同比已有 base_value/base_period/numerator_value/difference_percentage_points/derived_revenue_benchmark。
- `research.input_targets.build_management_target(...) -> {target, claims, notes}`：缺省调用形状与旧语义保持；statement、raw 值/单位/币种、claim/source/locator 不因规范化而重写。
- `rf-input-quantity/1` 与 DU5 convert_input_quantity、build_sensitivity_test、validate_input_quantity_for_parameter 合同保持。不是所有目标都必须产生 sensitivity record。

### 3.2 设计要求

1. 同币金额缩放复用 DU5 唯一描述，CNY/RMB 属同币；HKD/USD/RMB 互换无 FX 证据仍拒绝。保留 typed target 原先合法的 trillion、units、万元/亿元等词汇，不能统一后反而丢能力。模糊货币符号、无币种原始量仍不能猜。
2. typed 构建可采用一个显式可选 comparison spec 入参，或清晰的新 typed builder；A 节点先把签名/例子写在自己的 INTERFACES.md。旧缺省调用保持，不要求消费者手工 patch target 字典。
3. 金额、增长比率、level_multiple 分开。允许有证据的带符号增长，不可由此允许负收入金额；不要把“下降10%”变成正增长10%，也不能把比例与百分点混淆。
4. 定义正/负/零 target 的 at_least、at_most、approximately、greater_than、less_than 的数值容差；严格比较保持严格。目标负号不能改变比较方向。区间必须保留两端，不造中点；无法清晰解释的 operator×range 组合给具名不兼容诊断。
5. 负/零增长目标不采用会误导方向的 attainment_ratio；既有 difference_percentage_points、比较状态、原文和显式原因承担解释。不能用 null 抹掉可比较的观测值或偷判 meets_target。
6. 原生 annual/quarterly/YoY 只消费现有参数与实际路径。季度不乘4，ARR/run-rate 不冒充年度收入，CC/gross-net 没有证据时仍 unmodeled_data_gap。
7. 先冻结既有正向 `/1` 对象/输出。对确有历史 signed `/1` 输出的变更，先做源/旧结果对照并在本线说明有限兼容方案；如需新 opt-in 比较合同，可只在本 typed 模块/构建器内添加有限 `/2`，旧默认保持。不要静默改大 schema、历史快照或放松 output 验证。白名单外需要协作的接口由 ROOT 接收。

## 4．A/B/C 三大节点

### A：冻结责任与真实 RED

- 确认真实 HEAD/Git status；只解释本线变化，不恢复主目录 WIP。
- 在自己的 PWF 写最小接口表、带符号比较真值表、各数值范围/单位角色和独立手算期望。
- 新测试先 RED：负同比单值/跨零区间；level_multiple<1 的目标比较；CNY/RMB 同币；HKD 万/亿/百万；错误 FX、金额负值、错误 unit family；operator×range 和 unknown 基期。
- 使用现有原生 fixtures 构建合成输入，不改旧 expected；若失败是新构造器不存在，单独列 API RED，不冒充经济行为 RED。
- 记录哪些假设未复现，合理旧拒绝不强行改。

### B：共同责任层实现与一次集中回归

- 按单一金额描述和 typed 比较合同实现，构建/验证/比较共用规范化语义，不复制税率、币种、规模、日期或公司特例。
- 新测试含独立手算，覆盖同币反向转换、负增长/零增长、严格边界、上下界顺序、base缺失/为0、scope/quarter/schema原有拒绝。
- 兼容保护：DU5 129组旧字典/旧record重推导、现有正向管理目标和 quarterly/YoY 路径输出不变；不刷新旧 golden。
- 一次集中命令（实际工作树内）：

```powershell
python -B -m pytest -q -p no:cacheprovider tests/test_du6_target_measurement_boundaries.py tests/test_management_targets.py tests/test_management_target_semantics.py tests/test_target_measurement_comparison.py tests/test_independent_targets.py tests/test_input_quantity_conversion.py tests/test_du5_money_unit_registry.py tests/test_du5_root_unit_boundaries.py tests/test_input_semantics_e2e.py --basetemp <OWNED_TEMP>/pytest
```

- Ruff仅改动文件，禁写全仓格式化；只在具体风险需要时增加测试，不把41市场/供应商全矩阵加进每次commit。

### C：公开入口及交接

- 使用至少三份合成模型：HKD/CNY同币缩放的正金额目标、负同比/跨零区间目标、没有支持转换的run-rate/CC目标。不得针对公司名称编码。
- 完整经过 builder → run_forecast → validate_published_forecast →公开 CLI validate-only/正式JSON和Markdown；保留原文、raw目标、scenario数值、差异和状态。最后一份应保持具名gap，不以全绿为由填假数字。
- 当前实际入口为 `python -B scripts/revenue_forecast.py INPUT --validate-only`，正式输出用 `--output`/`--markdown`；先看 --help，不创造不存在的 --mode 参数。进程内工程计算可用 `run_forecast(..., mode='draft')`，C节点正式发布只能写隔离registry。
- 记录每个负控预期拒绝和真实退出码，成功造出报告不等于预测经济质量。
- 正常commit自己的分支，交给ROOT验收并STOP，不自行安装/并线/推送主线。

## 5．测试、空间与原件保护

- 所有 runtime import 和任何 formal 调用前，在父进程/全部子进程明确设置 `REVENUE_PUBLICATION_REGISTRY=<OWNED_TEMP>/registry.jsonl`；不能只给CLI子进程设。pytest的既有测试可能formal，因此运行测试的外层环境也必须设置。
- `PYTHONDONTWRITEBYTECODE=1`；pytest basetemp、JSON/Markdown、registry、其他输出均在本线独立临时目录。自有输出路径不得指向生产公司目录或作者旧receipts。
- 运行前记本线夹具SHA、原默认registry存在性/SHA、sentinel；运行后核对不变。ROOT主目录alert WIP完全不碰。
- 若临时目录原先不存在，结束必须删除；已有sentinel/既有目录恢复原样。Windows只对已确认属于本次的临时文件解除只读并删除，不能递归清理父目录。失败也执行清理并保留小型失败收据。
- 0供应商/LLM/外部网络；不读取密钥。持久证据优先小JSON、stdout/stderr、少量合成fixture，不保存完整环境/原文副本或虚拟环境，不做完整备份恢复演练。

## 6．交接合同（沿DU5，DU6 id）

`handoff.json` 使用 `schema_version="du6-handoff/1"`、`card_id="DU6-RF-TARGET-MEASURES"`，至少包括：base_commit、branch、implementation_commits、changed_paths、逐文件必要性/最终SHA、entrypoints、interfaces_reused/接口变化、red_receipts、tests（真实argv/exit/pass/fail/skip/时间）、fixtures（synthetic/SHA/手算来源）、旧行为对照、supplier_calls、production_writes、cleanup_receipt、known_limits、not_run、root_integration_steps。

单测/组件/合成E2E通过不能写“全部公司预测通过”。失败、未知、没跑和兼容分歧必须如实保留。作者不要在交接中猜自己尚未创建的最终commit SHA；ROOT可读分支精确值。无需新增人工签收JSON、private/public或授权文件。
