# Findings

W07 FF已验收并发布FF64b4d29/ETd0ac42c6；Audit2c494913已安装；RF8dc26710工具已发布但五组组合覆盖PARTIAL。CWP本地122bbe3b，W04本地核心7a0b702a仍有18既有边界FAIL，远端5c07f47c。禁止重派原W07包。

候选三个不同repo/独立工区：RF仅扩现有组合工具和新测试；Audit仅补真实执行/四审证据的报告型核对，不增加许可；CWP仅新G2离线联调工具/测试，ROOT专属W04 src保持排他。需固定代码与fixture输入，不消费浮动WIP。

调查错误：Git默认GBK解码含中文的清单失败；一次复杂python -c PowerShell引用失败；后续改显式UTF-8独立inventory脚本。PowerShell不展开rg路径通配符，改读取具体已知路径/rg -g。Audit CodeGraph未初始化；本次仅读已知文档与Git路径，既有初始化授权不强行执行重索引。

准备检查首次断言将Git对untracked .planning的折叠字符串当作唯一格式；已有tracked规划根可显示具体新plan子路径。改检查每一项必须为 .planning 内 untracked，源码不能有变更；不放宽产品测试。

2026-10-12三个实际工区、base/branch/card/readonly输入检查通过；总准备空间26357008B，没有全湖/旧规划复制。三包不同repo且目录互不嵌套；CWP只新tool/test，ROOT源写集排他。INTERFACES.json明确实际公开入口、输出与ROOT消费者；全部READY_NOT_STARTED，0收费。
