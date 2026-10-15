# DU5-RF-UNITS：单一金额单位描述与真实参数一致性

状态 READY。工作目录 `C:/Users/郑曾波/Projects/revenue-forecast-du5-units`；分支 `codex/du5-rf-units-20261015`；源码基线 `090a63109a62507a23adcaa774cf65021e7c4614`。PWF `docs/plans/du5-units-2026-10-15/`。不要在 revenue-forecast 原主目录施工，其 assurance alerts/output 是既有 WIP，不属于本卡。

## 实际问题及待证假说

当前 `scripts/research/input_quantities.py` 用 `_UNIT_ALIASES/_UNIT_FAMILY/_UNIT_SCALE` 三份平行表，并在 `_SHOCK_SEMANTICS` 再枚举货币拼写，USD/RMB有有限支持，HKD无支持。W08 的 HKD未知负例是当时能力边界，不能当作 HKD 已完成。A/H/US 正式收入预测需要明确币种与尺度，这项能独立补齐。

实际 consumer 为 `scripts/analysis/sensitivity.py`。静态只看到转换记录自洽和 engine_value与shock相等核对；是否允许“自洽USD记录却配HKD参数”进入计算，**目前只是待证假说**，A节点必须通过真实calculate_sensitivities/输入校验路径写反例确认。若现有入口已拒绝，保留该正控，不虚报缺陷。

本包只处理显式声明单位和同币缩放，不解析财报、不查询外汇、不猜币种，不改来源角色/身份流程。

## 独占可写范围

- `scripts/research/input_quantities.py`：单位唯一责任层。
- `scripts/analysis/sensitivity.py`：仅调用共同helper核对记录与实际参数单位，不复制转换表。
- `tests/test_du5_money_unit_registry.py`、`tests/fixtures/du5_money_units/**`。
- `tests/test_input_quantity_conversion.py`：必要的新旧单位兼容用例。
- `tools/model_generalization_matrix/combinations.py` 的 `C01-HKD-C`、`tools/tests/test_w08_model_combinations.py` 的 `test_unwritten_unit_is_unknown_not_a_guessed_rate`：仅更新 HKD已知后仍跨币不兼容的拒绝原因，保留 case ID、原金额和失败预期，另加真正未知拼写控制。
- `references/money-unit-conversion.md`。
- `docs/plans/du5-units-2026-10-15/**`。

build_sensitivity_test 也在 input_quantities.py，使用同一责任层实现可选engine_unit即可，不扩另一套builder。除此之外其他文件只读；禁止碰 CWP reader/source/evidence hash、schema大改、forecast主引擎、发布/registry、audit/FF/StockWiki、安装副本/总PWF。

## 设计与接口约束

1. 用有限 Currency×Scale 描述推导规范名/别名/维度/尺度与 shock兼容性，清理平行手写清单。沿现函数命名/返回结构，不建立plugin/provider/新配置框架。有限支持 USD、RMB（CNY同币别名）、HKD，必要尺度元/千/万/百万/亿/十亿；未知币种/拼写仍明确拒绝。
2. 保留 `rf-input-quantity/1` 和现调用默认行为、旧已保存规范 unit 名与记录重算语义；CNY可以规范到既有RMB，但不重写历史产物。新增词汇不自动等于需要换schema；若发现确需shape或语义破坏，停止该越界部分并交ROOT具体方案，不创建半兼容格式。
3. `convert_input_quantity`/`validate_input_quantity_record`/敏感性构造/consumer共用同一描述。若支持 `engine_unit` 可选参数，缺省沿旧行为，显式传入时真转换到目标参数币种/尺度，不能只改标签。
4. 实际参数绑定已有顶层 currency/scale，由既有 contracts 验证。本层据实际parameter单位检查currency family、scale、dimension和shock semantics；同币可换尺度，USD/HKD/RMB互转禁止。不要比较数值相等就接受不相容记录；也不能为合规再查询身份库。
5. 人民币万元/亿元、HKD million/billion 与 USD 不混；无币种的“万元”必须有明确调用上下文，否则 unknown/错误，不能默认RMB。比例pp/percent/bp/ratio和count保留，百分点不当百分比增长率；绝对money shock与relative shock分开。
6. 有限数和实际浮点容差沿现标准，NaN/Inf/溢出/篡改记录拒绝；不为本卡把全引擎改Decimal。不得根据公司、市场代码、示例数值特判。

7. monetary-per-unit 等复合维度不能当成纯金额，已有参数单位无法安全解释时给明确诊断；不能靠剥去分母让错误记录通过。

## A：TDD与兼容冻结

先读 input_quantities、真实sensitivity consumer及现单位/W08组合测试。记录具体函数签名与调用方。冻结既有USD/RMB/share/count记录样例与旧调用结果，再先写新反例：

- HKD billion→million、million→thousand；RMB/CNY亿→百万/万，反向缩放、0/负数/小数。
- USD↔HKD、HKD↔RMB、money↔count、share↔money明确拒绝；未知拼写/多币表达不猜。
- 自洽record却与真实parameter币种/尺度/维度不符；engine_value或source_value/unit/factor篡改；真实 public sensitivity路径至少各一例，不只helper测试。
- pp/bp/percent/ratio旧病例完全保持；absolute/relative语义不混；有限数边界。
- 旧记录、旧默认builder调用输出保持；新增显式engine_unit确实进入最终revenue delta而非闲置元数据。

W08 `C01-HKD-C` 的实际输入是 hkd_million→usd_million：新增HKD后仍必须拒绝，原因从unknown input_unit改为跨币不兼容，保留原case/金额/失败。另加真正未知拼写反例及HKD同币正控；不能替换掉原跨币场景、删除整组或放宽所有未知unit。

## B：共同责任实现和集中回归

集中跑本包、`tests/test_input_quantity_conversion.py`、`tests/test_sensitivity_dependency_dag.py`和上述W08组合测试，再跑相关W05/W07/W08原生模型集；实际命令先按仓内组织确认。按现 RF unittest/pytest组织，不引入新runner或每commit慢E2E。静态检查按仓现工具，所有错误/未测照实保留。

## C：真实公开入口离线E2E

用仓内现公开 `scripts/revenue_forecast.py INPUT --validate-only` 及 `run_forecast` 正式路径：显式HKD来源数量→input_quantity→目标参数HKD尺度→敏感性计算→报告/产物，检查中间单位、最终delta和证据记录均一致。加入同数字不同币种拒绝、重新加载记录重算、旧USD/RMB样例不回归三组；独立手算7.25亿元=725百万元、5十亿元=5000百万元及反向缩放，不只比较实现自己的结果。

E2E资料是隔离 synthetic，不冒充真实预测/外汇验证；读取现有真实表头摘录可作辅助，但不能跨仓改CWP。0API/0模型；不发布正式snapshot、不写生产registry。临时目录/sentinel/config恢复测试前状态；新输出原先不存在则删除。

交付最小单位表说明、公开用法、真实consumer证据、RED/GREEN/兼容结果、接口变更和精确文件清单、PWF handoff。作者正常commit后STOP；ROOT接收后再将本能力放入原三/新三预测E2E，不将本单元卡通过当作预测经济质量通过。
