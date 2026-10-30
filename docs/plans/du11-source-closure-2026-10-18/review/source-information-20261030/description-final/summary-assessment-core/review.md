# M3 纯 assessment 模块独立终审

**结论：PASS（仅纯模块限定范围），M3 整体仍 OPEN。** 终审基线为 M2 已提交的 `6c12970609024b3cc09eeb238e4d66cd8296d186`，审查未接线的 `narrative_summary_assessment.py` 与对应测试。没有启用生产默认、修改产品、付费、下载或解析 PDF。

## 最终证据

- 独立限定测试：**21 passed in 4.61s**，其中本模块永久测试 10 例、已有 source admission 测试 11 例。测试执行前后两个文件 SHA 一致，完整记录见 `final-tests.json`。
- 12 个固定跨语言中性对照全部通过：英文共同主体不再向无关实际陈述传递未来/报道风险；中文“已将”“计划完成率”不误报；窄否定/问询事实不继承无关限定；当前命题的程度与报道归属不会被另一分句的 material/reports 遮住。
- 真实 v3 仍准确暴露 **6/8 任务发出、t3/t7 缺失**；t2 归属风险与 t4/t6/t8 混合语态风险均可见。
- 合法同证据双任务绑定：只请求 t1 时准确计入 t1；两项均请求但规范 claim 无法区分语义 task 时，返回 `ambiguous_claim_scope`、不任选末项、不算 emitted。
- 有限诊断：合法同 task 两条 clause、33 个 support spans，生成 **132 项诊断、保留 64 项明细、limited=true**；两个风险 claim ID 都保留，即便后一个 claim 的明细完全落在限幅之外。
- 语义和子事实覆盖始终 `not_evaluated`。无已知诊断不构成语义通过；task emitted 不构成该 task 所有子事实均保留。

## 本轮发现与修复

| 问题 | 最终状态 |
|---|---|
| plan marker 被硬码为 20，无法代表各冻结协议 | API 显式要求 `plan_max_claims`，捕获 marker20 与新明确 marker40 分别绑定通过 |
| 英文共有 “the company” 将无关分句当作同命题 | 功能词与普通主体不再作为有效锚，固定中性对照通过 |
| 裸“将”及“计划”误报实际处置/完成率 | 收窄有限未来语法，实际句不再误报 |
| 别处 material/reports 能掩盖当前命题限定丢失 | claim 同样按局部分句配对，不跨分句借用程度/归属 |
| 同 support/context/role 的多个 admitted task 被 dict 单值覆盖 | 先过滤真实 requested 集，再处理唯一或歧义候选，不信 claim-ID 前缀 |
| 收窄未来语法一度漏掉真实 t8“建成后将为…提供保障” | 完成条件+将为/提供/支持的有限结构恢复真实 t8 诊断 |
| recipe 仅绑定自身代码、诊断明细没有上限 | 现绑定七个直接 owner 依赖；64 项明细上限、总量、limited 与全部风险 claim IDs 分开记录 |

以上只诊断可定位的已知 source constraints，不声称通用 NLI。任意陌生改写即便保持合法 scope，也仍可能需要独立语义审查；程序没有“未触发有限规则即真实性成立”的分支。

## plan marker 更正

初始 `initial-probe.json` 将手工编译的 **decoder40 视图**字段命名成 `actual_request_plan40`，该命名不准确。本次真实捕获 HTTP material 的 `max_claims` 是 **20**，`output_plan.max_claims` 则是 **40**，旧 builder/decoder 的 marker 并不一致。

因此不能把初始比较描述为“真实 v3 请求 marker40 被错误绑定20”。真正的问题是硬码20无法表达所有实际冻结协议。最终 `probe.py` 从捕获 HTTP JSON 读取 marker20验证，再单独检查显式40的视图；不会重命名或改写历史捕获，使它冒充新协议。

## 绑定、预算与架构判断

模块消费已经选定的 spans/source tasks，使用完整 support/context/role 匹配最终 canonical claims。requested 必须是唯一、真正 admitted 的 task；source unavailable/duplicate、budget deferred、missing requested 分开，不能抹掉 admitted 预算缺口后称完整覆盖。

输入仍依赖上游 canonical DTO 的数量、文本和字节约束；此纯 observer 不是第二套模型预算或任务调度器。诊断明细有界，总量与限幅显式，风险 claim 标记不依赖是否还能存明细。它不读原件、不重写缺失事实、不产生新任务、不触发重试、不创建人工许可或第二个状态库。

recipe 覆盖 normalization、task plan、admission、scoped view、canonical role owner、encoding 与 assessment 自身；只保存路径无关的代码指纹，不含原文、密钥或配置凭据。

## 稳定快照与复现

| 文件 | SHA-256 |
|---|---|
| `src/company_wiki/automation/narrative_summary_assessment.py` | `559f42adb11e4f271f2fc2d22738ee6d598ee510527fc6e38ad760f6ce891a58` |
| `tests/unit/test_narrative_summary_assessment.py` | `096ec432f68b9977a0b2796b953e1c5aebd50ceaa8464ee6687c29e5338698ed` |

从仓库根目录运行：`python .planning/summary-quality-20261030/summary-assessment-independent/probe.py`。它只读取捕获 JSON 和本地 fixture，只更新本独审目录 `probe-result.json`。初始问题结果、scope 碰撞结果和中间测试仍留档；中间有一次 recipe 修改跨越测试窗口，已明确保留为 `intermediate-tests-changing-recipe.json`，未拿来做最终稳定验收。

## 不属于本次通过的范围

**生产新协议、wrapper、bundle 2.1/3.1、generation/publication/cache 接线、RF 消费接口及真实收费实验均未由本次验收。** 尚未证明新模型回复更完整、更忠实，也没有执行 source locator replay。

纯 observer 正确标出旧 v3 的风险和遗漏，只是让局限可见，并未修复那六条旧摘要。主线后续接线改变依赖后，应按新的实际 recipe 与产物再验收；本 seal 不签 M3 整体完成。
