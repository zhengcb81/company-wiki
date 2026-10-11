# W05-RF-FLOW：任意真实日期的并表收入贡献

**可立即开工。** 工作目录已创建：`C:/Users/郑曾波/Projects/_harness_worktrees/w05/rf-flow`；分支 `codex/w05-rf-flow`；起点 `1b616622763ece6549676f2a74f596e6c65244af`，含已发布WP06/财务日期null修复。读SKILL.md、CHANGELOG、本文及 `docs/handoffs/w05-rf-flow/input/`；RF此基线没有AGENTS.md，有文件才读，不因缺该文件阻塞。本线PWF `.planning/w05-rf-flow/`。只在此树施工，不碰canonical assurance/output未提交内容。

## 实证与完成标准

schema3.9实际验证器只允许3/6/12完整月。G4原生probe接受01-01..06-30，却拒 `2026-05-31..2026-06-30`。收购后5月底起控制/6月并表贡献不能伪称H1/全年，净资产存量不能当收入。ROOT研究可以先用真实集团H1＋下半年条件假设继续；本卡完善通用表达，不等待CWP新OCR。

交付输入→validate→公式DAG→forecast→report→输出/snapshot读者全链支持。不能仅放宽 `{3,6,12}`，还须守住收入确认、实体范围、日期、金额和单位。

## ROOT固定的数据接口

新增 additive **schema3.10 / skill与engine4.3.0**；默认schema仍3.7。数据版本不是许可flag，不要求人签。复用 `time_basis="period_flow"`、`period_start`、`period_end`，不再造一套短期参数：

- 3.10允许真实、包含首尾日的任意有限区间，start≤end（同日流量可表达），合法ISO，仍在FY/当前fiscal_year_end窗口内。跨FY金额须按真实来源/显式估计拆分，不能裁日期而保留整个金额。
- 3.9保持start<end、3/6/12完整月；3.7/3.8及旧schema拒新字段。旧pure helper默认3.9含义，新调用明确传schema，不暗改历史。
- 金额只属于所写window，不隐式x2/x12/按天年化。控制期、贡献期、发表日不同，来源日期必须有原source_id/locator；缺日期保持unknown，不用available_by猜。复用既有evidence/definition/rationale，不加身份合同或审批receipt。
- point_in_time继续是存量，不借period伪装收入；估计/情景必须用既有analyst_assumption/scenario_stress，不能reported_fact。
- annual consumer集中复用period_flow/annual_consumption规则。局部贡献可做全年构成，但不能直接冒完整FY基础/总额。收购前不在集团范围与缺数据不同，缺口不能默认补0。全年需显式完整构成/口径解释。
- H1和Q2等重叠观察可共存，但同口径年度求和组件不得双算；同实体/口径/窗口矛盾沿用事实冲突校验。重hash不能使伪造结果通过。
- engine升级后明确保留4.2.1合法历史发射矩阵（当前registry引用ENGINE_VERSION，升级不应丢历史）。版本/CHANGELOG/registry/runtime/report统一；旧输入/输出不修改。

## 排他可写集合

- scripts/contracts/{period_flow,annual_consumption,document,constants}.py、scripts/schema_compatibility.py；generate_input_template.py仅新schema的模板/版本接线，旧模板语义不变。
- scripts/forecast/、scripts/report/ 中确需期间接线的文件；revenue_core.py/revenue_report.py/revenue_forecast.py的公开接缝/版本。逐文件解释必要性，不做无关重构。
- scripts/research/{target_measurement,timing_bridge}.py 只在真实反例证明需要的日期接线；drivers.py只做3.9/3.10的role-aware schema族接线，不改业务评分/研究算法。communication_scope.py、source_clock.py、FF/CWP适配器只读，ROOT owns。
- 新 tests/test_w05_dated_contribution*.py；旧test_m3_period_flow_*/test_m3_schema_compatibility/test_schema_compatibility只新增新版本覆盖，不删旧断言。
- SKILL.md、CHANGELOG.md、references/{input-schema,output-schema,input-construction}.md、新references/dated-contribution.md。
- 本线PWF与docs/handoffs/w05-rf-flow/。

不改gate/CI/assurance/配置/安装；ROOT集中接快测和安装。交付快测文件/耗时/接口清单，不自行并main、force或跳hooks。

## 三个实施节点与测试

### A：TDD与RED

记录现helper及native入口拒真实短窗口；构造现有合法fixture上的新3.10文档反例，先真实RED，再实施。保留旧3.9短期拒绝、3/6/12合法、单位旧断言。路径/导入失败不算业务RED。设计稿有可手算贡献公式、主体范围、来源日期支持；不创造“真实公司”数字。

### B：实现及集中单元/集成

至少覆盖：

1. 05-31..06-30、10天、同日、闰年、不同财年；非法/倒序/跨FY/未知开始日；3.9兼容。
2. 真实窗口贡献进入FY低中高DAG，明确集团范围变化；缺控制期证据不冒reported fact；无隐式年化。
3. 期末股票/净资产/客户存量不能冒收入；RMB亿/USD million/billion单位与币种、转换复算。
4. 重叠组件双计、漏全年基础、无解释gap、错误年度/跨主体误合并反例；合法显式sum/recognition仍通。
5. 相对于冻结bound-input的输出篡改日期/币种/范围，即使重hash仍拒；报告实际显示日期、金额、来源，不虚称全年。自洽改写整个input及其证据引用不是单凭hash能验真的事实，不能承诺本层可代替来源实读。
6. 3.7/3.8/3.9正式/输出/snapshot兼容，4.2.1历史保留；3.10属于新engine，旧engine不能冒发。
7. 新3.10继承3.9的role-aware triangulation：history/financing/peer不能因schema严格等于3.9的分支未更新而冒充mechanism；真机制来源与3.9同口径，旧3.7/3.8不被静默改义。

集中运行旧关键套件并追加新测试：

```powershell
python -B -m pytest -q tests/test_m3_period_flow_contract.py tests/test_m3_period_flow_consumers.py tests/test_m3_period_flow_annual_consumers.py tests/test_m3_schema_compatibility.py tests/test_schema_compatibility.py
```

版本字符串预期需要更新时单列原因，不放宽数学/语义断言。受影响快速测试足够，不每小步全集几十分钟。

### C：隔离CLI端到端与交接

先用真正 `scripts/revenue_forecast.py --help`确认命令（库文件空stdout不是CLI证明）。在全新scratch冻结构造输入，跑native prepare/validate/forecast/report及published output reader；改一个实质window验证拒伪造结果。至少收购贡献和非12-31财年短流量两种通用情形，提供可复算金额/公式；来源真实日期按随卡实证保留，fixture金额明确synthetic，不冒真实reported revenue。

本卡不需下载或LLM。87来源键/12sealed审查/旧real runs不改；真实公司经济端到端仍由ROOT在G4/G5做，局部CLI不宣称买方质量PASS。初末scratch清单恢复，保留小型输入/输出/关键日志；按input/handoff_contract.md普通commit并交付JSON/MD/manifest、TDD、接口与安装列表。只三个大节点，不新增签收链。
