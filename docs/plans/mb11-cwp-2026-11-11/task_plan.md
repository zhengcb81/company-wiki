# MB-CWP 计划

工区：`C:/Users/郑曾波/Projects/mb11-cwp`；分支 `codex/mb11-cwp`；基线 `08dfe8bf1ae97dff34b28976d532b3482d3ba358`；目标主线 `master`（原仓 `C:/Users/郑曾波/Projects/company-wiki`）。

卡来源：`docs/plans/module-boundaries-2026-11-11/harness_lanes/MB-CWP.md`。
总控：`docs/plans/module-boundaries-2026-11-11/{reconciliation,interfaces,acceptance,runtime_verification,handoff_contract}.md`。

## 阶段

| 阶段 | 内容 | 状态 |
|---|---|---|
| A0 | 接收历史未并线成果（T-READ / T-CANON / T-B33 / T-B34 / T-N4 / T-CONFIG） | 进行中 |
| A | 活动入口/模块归属/依赖方向清单 | 未开始 |
| B | 四项已确认缺口 CWP-01..04 的 RED→GREEN | 未开始 |
| C | 七责任逐项结果 + 安装验收 + 独审 + 交接 | 未开始 |

## A0 接收清单（来自卡 A0 表）

| 子项 | 历史提交 | 处理方式 | 状态 |
|---|---|---|---|
| T-READ | `3199adab`（X-C04 compat CLI） | 与现行 `stream_version` / parser sink / 读取预算比对；给消费者迁移证据或撤销 | 未开始 |
| T-CANON | `62602102a` | canonical browser / CN issuer / calendar 反例按路径移植 | 未开始 |
| T-B33 | `dc837a21f` | readiness / legacy source link / recovery 反例重放 | 未开始 |
| T-B34 | `29b562dac` | diagnostic / IPO cover 对照现行 local_reconcile | 未开始 |
| T-N4 | `2b5bec914` | CN quarterly / IR 独有反例映射现行语义 | 未开始 |
| T-CONFIG/W04 | 旧 M3 四文件 + W04 scoped-negation | `Config.load(validation_scope='llm')` 已是主线事实；只迁反例 | 未开始 |

约束：A0 可读旧工区/refs，不覆盖本卡工区同名整文件；不新增第二身份库/下载预算；旧 256MiB 帽、固定 8 条诊断帽、旧 eligibility 策略不复活。

## B 阶段缺口

| ID | 缺口 | 归属 | RED 测试 |
|---|---|---|---|
| CWP-01 | `automation/narrative_transport.py` 默认从 reader 反查 catalog/config 拿 OCR | 注入已有 normalization | `test_transport_replays_ocr_with_protocol_only_source` |
| CWP-02 | `source_catalog/narrative_selection.py` `_select_pdf` 无参读全局预算配置 | 注入 WorkBudget 工厂 | `test_raw_selector_uses_injected_work_budget_without_config_io` |
| CWP-03 | `automation/narrative_source_guard.py` 中立类型经 source_reader 导入具体 catalog runtime | 直连 source_contract | `test_source_guard_imports_without_catalog_runtime` |
| CWP-04 | packaging_contract 只检查 TOML | 真实 wheel 安装验收 | `test_installed_public_entrypoints.py` |

## 规则

- 保留现有公开协议；各模块只写自己代码和状态。
- RED 必须来自真实越界/错误行为；fixture/缺依赖/沙箱权限失败不冒作产品 RED。
- 只在模块最终交付前调用独立审查 agent。
- 测试用新临时目录，恢复初始状态；不动生产原件/配置/既有 WIP。
- 提交并推送自己的交付分支；不自行合并主线。

## 工作量记录

见 progress.md。
