# W08-RF-COMBOS：RF 原生模型剩余五组组合覆盖

## 可以现在独立启动

- 工作目录：`C:/Users/郑曾波/Projects/_harness_worktrees/w08/rf-combinations`（已准备，不是原主仓）
- 所属项目：`revenue-forecast`；固定基线：`8dc2671040f4330d3b54d1bea1d17246130f9c2a`
- 分支：`codex/w08-rf-combinations`；PWF：`.planning/w08-rf-combinations/`
- 先读本卡、同目录HANDOFF_CONTRACT.md与INPUTS.json；不取消稀疏checkout，不拉入旧大体积.planning/assurance/output。
- 本包预算：外网provider/LLM调用0；不要读取真实凭证或恢复暂停母目标。无需等待另外两个W08包。

## 唯一可写集

- `tools/model_generalization_matrix/**`
- `tools/tests/test_w08_model_combinations.py`
- `docs/handoffs/w08-rf-combinations/**`
- `.planning/w08-rf-combinations/**`

未列入写集均只读，包括旧断言/初始input/主线/安装及其他包。ROOT专属母PWF、W04 core、G2真实付费、主线/安装/CI。

## 已确认的缺口，不重复原 W07

W07工具已ROOT修复并发布8dc26710；原16向量及36工具测试通过，但整卡PARTIAL。必须读取input/remaining-coverage.md；它是详细设计依据，不是新许可。保持原16 CaseSpec和原36断言，扩独立COMBINATION_CASES；全清单/报告的required manifest来自同一权威清单，不只检查数量。

| 组合组 | 至少需要的实际原生路径 | 有意义的错/未知向量 |
|---|---|---|
| C01 货币单位 | 原生convert_input_quantity；CNY亿元、HKD百万元、USD millions同币种缩放及量×价 | 100/1000倍错误、自动换币、缺币种；不猜汇率或造单位名 |
| C02 并购/跨FY | 实际draft年度收入及dated contribution ancestry；非12-31年结、控制窗口 | 错年度、非控制期间、缺Q零补、全年+H1双计；不是仅测月份helper |
| C03 联合量价 | 原生unit_sales/联合情景，冻结同一shock的量价路径 | 只变一项、重复shock、偷偷重排scenario；不强迫Low≤Base≤High |
| C04 目标/净额 | 原生累计目标比较、gross/net、cannibalization/防双计 | 累计/期末当年度、混毛净额、新业务重复加到已含收入 |
| C05 actual/WAPE | 实际draft与既有历史误差接口，scope精确到segment/year/scenario | future assumption当actual、缺actual补0、无样本WAPE=0、校准跨scope |

每组至少一个合法向量和反例/未知向量，至少10个有不同机制的补充案例；必要的分支再加，不用十个同义数值凑数。独立期望在运行前固定，来自手算量纲/净额恒等式/期间，不从actual反推。一个场景需同时检验实际入参及真实结果，不能参数改了却运行旧input。

## 实施细则

1. 读tools/model_generalization_matrix的native/cases/oracle/runner/report/run，以及原tests/test_lifecycle_forecasts.py、test_research_evidence_roles.py、research数量/历史误差接口。已有测试helper可能修改参数和claim，逐例deepcopy；只读scripts与旧测试。
2. A先固定每个新case的native_entry、真实调用参数、expected推导、结果JSON pointer、哪些情况确实不支持。先写“错误实际结果必须被检出”的行为测试取得RED。
3. B扩现有工具，不另建引擎、不复制forecast计算代码；mode=draft。拒绝必须为真实合同拒绝，未知不算PASS；NOT_SUPPORTED列未关闭组及实际异常。保留原native异常分类、request/result SHA、readonly/cleanup及完整清单。
4. C实际原生全清单一次E2E，现有公开run.py --e2e实际合法/拒绝/support三个CLI。全清单至少原16+补10，不删原case。CLI与引擎差异单列，不mock本节点。
5. 如发现core缺陷，输出最小原生复现和先红测试建议，由ROOT修scripts；本包继续可做部分，不越界或改期望求绿。

## 测试包与交付

B一次集中：python -B -m pytest -q tools/tests/test_w07_model_generalization.py tools/tests/test_w08_model_combinations.py。
C公开入口：python -B tools/model_generalization_matrix/run.py --owned-root ABS_NEW --out-root ABS_NEW --e2e；先--help确认已有参数，不创造不存在的开关。至少一次absent恢复和一次existing empty dir/sentinel失败恢复。没有平台实测就记NOT_RUN。

输出保持model-generalization-matrix/1兼容或明确有依据的additive字段；source_truth_verified=false、economic_reasonableness=not_evaluated。每组交case/native入口/指针/推导/status映射；缺组或未知不能升级整卡COMPLETE。原生payload一份ZIP与小摘要，禁止PWF、handoff再各复制完整JSON。零API/LLM。

## 交工

按本地HANDOFF_CONTRACT.md正常commit并STOP；交给ROOT卡号、实际branch/HEAD和handoff绝对路径。允许如实PARTIAL，不以只测wrapper冒签原生E2E。
