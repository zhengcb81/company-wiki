# DU2-FACETS：业务关注点、经营机制和必要上下文

本包回答“业务里什么最有用、证据必须带哪些限定”，产出各类文档共用的数据策略。
**不做投资模型、不代替 revenue-forecast、不抽全套财务报表、不调用 LLM 生产答案**；不产生
目标价/评级/估值/研究结论（遵守 AGENTS.md 职责边界）。

- 规格契约：`du2-facet-spec/1`、`du2-facet-index/1`、`du2-reading-case/1`
  （见 `../../INTERFACES.md` §3/§4）。
- 数据运行时归属 ROOT：ROOT 消费 `required_context` 与 `summary_focus`，统一实现闭包、选择、
  校验；本包**不实现**独立自然语言推理器、**不实现**第二 summary generator、不写新检查器。
- 状态：`integration_status=not_integrated` 全部记录；语义反例一律
  `execution_status=NOT_RUN_ROOT_INTEGRATION`——本包只交语义输入与期望，不代表引擎已正确理解。

## 目录

| 路径 | 内容 |
|---|---|
| `records/facet_*.json`（8） | 八个共用面：主业/行业/新业务/海外/客户订单/产能募投/经营指标/风险否认 |
| `records/semantic_stage_progression.json` | A级语义规格①：第二曲线阶段阶梯（含关键错误反例、合法空值规则） |
| `records/semantic_capacity_project.json` | A级语义规格②：产能项目（分期/口径/资金/测算语态） |
| `records/mechanism_*.json`（4） | 可组合经营模式：软件订阅/消费、零售店网、制造认证/利用率、生物医药/CDMO |
| `cases/*.json`（14） | 6 个真实原文锚定 case（CN/HK/US）+ 8 个合成正反配对/合法退出 case |
| `c_verification/real_excerpt_checks.json` | C节点人工对照原文记录（单列）：20 条引文逐字核对 + SHA/mtime 复核 |
| `tests/` | 结构不变量测试（311 项），不含语义判定 |
| `index.json` | du2-facet-index/1：记录清单与覆盖行 |
| `coverage_matrix.md` | 面/机制/市场覆盖、缺口与合法退出矩阵 |
| `acquisition_requests.json` | 缺样清单（11 项），交资料获取层按既有授权补齐 |
| `tools/verify_real_quotes.py` | C节点核对工具（只读、确定性、0模型） |

## 每条记录回答五件事

1. **保存对象**——`positive_evidence[].description`（保存什么、连同什么一起保存）；
2. **证据形态**——`positive_evidence[].unit_kinds`（DU/1 语义包类型）+ `signals`（仅提示词，
   不是 regex/DSL，不作事实蕴含依据）；
3. **必须随带条件**——`required_context`（条件式：`always_for_assertion` / `quantity_emitted` /
   `project_emitted` / `explicit_condition_present`；只有输出数量才要求 unit/分母，定性进度
   **不强制补数字**；stage/subject/role/否定/条件决定原意时不可丢）；
4. **常见误解**——`confusions`（原文含义 → 错误断言 → 为什么错 → 需要的槽位）；
5. **未披露/未读/未答行为**——`absence_rules`（四态必须分开：未披露≠未答≠否定≠未读）。

强事实、推测、指导目标、计划、假设风险通过 `modality` 槽位分开保存；管理层展望不升级成确定
收入；缺字段标 unknown/null，不按模板造数。

## 正反配对与合法退出

正反 case 保持**同一原文**，只改变主体/时间/单位/范围/语态/条件，或删否定/换项目，每个
mutation 带 `expected_failure` 与 `reason`。三类语义级关键错误（缺否定、错项目、未来当实际）
均有配对反例，交 ROOT 执行。低信息/无业务/无回答各有合法退出例；纯财务数字“不要求选，但选了
不可错”（correctness_if_emitted），防止基准反向逼引擎膨胀。

## 测试（结构不变量，非语义）

```
python -B -X utf8 -m pytest docs/plans/document-understanding-2026-10-13/review/deliverables/facets/tests -q
```

测试只查：schema/枚举、条件式槽位绑定、支持组引用完整（组内 AND、组间 OR）、mutation 维度
覆盖、`candidate_claim`/`expected_missing_slots` 显式字段一致、引文预算（每 source ≤8KiB）、
可移植（无绝对路径）、0 原件复制、持久数据 ≤512KiB、机制组合不互相覆盖（轴不交叠、无公司/
产品专名、不重定义对方语义）、C记录与真实引文一一对应。测试用 pytest tmp_path 自带临时空间，
不触碰仓库其他文件。

## C节点（真实原文核对）

`tools/verify_real_quotes.py` 对 6 个真实 case 的每条引文做原件核对：SHA-256 复算、按页/全文
空白归一化逐字比对、读取前后 mtime 不变（原件只读、0 复制、scratch 目录 finally 清理）。
结果：20/20 命中（CN 募集说明书/可转债/投资者关系记录、港股双语年报、美股 HTML 业绩发布与
TXT 电话会）。本机路径只存未提交的 `.planning/du2-facets/bindings.local.json`。

## 已知边界（诚实声明）

- 语义正确性（引擎是否真的保留分期/否定/口径）**未测**：属 ROOT B/C 节点，本包不冒充。
- 生物医药/CDMO 机制只有通用规则与合成样本（`spec_status=proposed`），缺真实原文；
  其余缺口见 `coverage_matrix.md` 与 `acquisition_requests.json`。
- 机制记录只写通用机制，不含任何公司固定产品名单；真实公司事实仅存在于 case 的原文锚定中。
- 本包持久数据全部为 JSON/MD/小工具，0 原件复制、0 模型调用、0 付费。
