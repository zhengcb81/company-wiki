# 施工卡 SR-DASH · 定期文档更新开关

**工作目录** `C:/Users/郑曾波/Projects/investment-dashboard`

**起点参考** `main@007787aa` 或最新无冲突主线。另一个 Dashboard 项目目前有约 30 个受跟踪的计划/交接改动。首步确认与接口、适配器、UI 作用范围无交集，从已合并源代码建自己的短路径隔离工区。

**第一步** 读 [共同接口](../interfaces.md) 第 1、4、5 节、本仓 `AGENTS.md` 及 M8 jobs owner adapter。用冻结的 FF status/config/runs 形状做一个纯本地假 owner。合同已可用来独立施工，实际 owner 联调在 FF 接口完成后进行。

## 写入范围

- 在现有 Frontend Jobs 或其设置入口加一处“定期更新文档”。同仓可编辑 HTTP/OpenAPI、生成类型及由其直接依赖的 FF 调度 adapter/port、UI 和定向测试。沿用现有路由与配置接线，不另建后台或启动菜单。
- 本仓 `handoffs` 的本卡文件。正在使用的统一 Dashboard 总 PWF、其他 owner 卡、现有监听端口和数据根由原负责人维护。发现与在途改动重叠时在本卡交接记准确路径与冲突，保留未冲突的组件和测试进展。

## 实施步骤

1. 用既有 FF owner adapter 模式接第 1 节三个接口。GET 仅 status/runs，PUT 仅 configure。部署侧沿同一 owner runtime 配置传 FF 公开命令和超时，前端不传可执行路径。失联/未安装用现有局部诊断，保留页面其他能力。
2. 页面显示开关、日/周频率、当地时间、名单选择、文种、电话会与阅读档位。名单复用现有 Universe picker，停用时仍可保存和查看历史。动态与定版范围按 owner 声明展示。仅在 FF 报告实际存在能力时展示对应输入。
3. 显示下一次检查与计划时间、最近运行覆盖、已复用/新下载/已阅读/摘要/待续计数，以及具名原因、实际或未知用量。UI 支持历史分页，保留长回执和纪要原出处。缺账号、网络暂不可用、任务未安装与未到期分开显示。
4. 保存失败时表单保留输入且可重试。开关写入成功从 FF 状态重读。FF 配置相同回读稳定。更新设置和打开页面都不会调用 `run`、模型或 Windows Task Scheduler。

## 验收和交接

- TDD 覆盖 A6。用 fake owner 测试全部路由和调用次数，再用隔离浏览器确认开启、关闭、日周选择、真实状态分页和重启重读。保证其他 Jobs、现有阅读和名单接口可用。用 FF public CLI 组合联调校对 schema；入口可先用冻结 fixture 验收。
- 交接前独立 agent 审查作用范围、状态语义、UI 易用性、公开接口与隔离测试，修完并在最终版本复测。使用短路径临时数据目录和独立端口，结束时清理。切换现用 48766 由总控联调后执行。
- 交回本仓 `handoffs/scheduled-refresh-2026-11-21/sr-dashboard.md` 和同名 JSON。包含基线/交付 commit、OpenAPI/客户及部署配置点、fixture 与本机组合测试命令、独审和清理证据、未决的 owner 依赖。使用 [共同回执模板](../handoff_format.md)。
