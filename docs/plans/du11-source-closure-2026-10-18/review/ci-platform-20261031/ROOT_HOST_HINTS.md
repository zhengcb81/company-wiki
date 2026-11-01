# ROOT host-hint simplification

2026-10-31：原pre-commit全树启发式误报41项已发布的合成路径/能力夹具，阻止无关平台修复提交。它不分析实际I/O，也不能捕获断言层的平台错误；把字符串拆开能绕过，维护人工baseline会加重复杂度。

按用户长期明确要求精简多余门禁，使用该工具已有--report并置stages=[manual]；日常commit不再扫描整树或要求给测试路径签许可。检测器实现/既有严格CLI与42项规则测试不变；原“全仓无任何新hint”的合同替换为小型fake repo行为合同：严格模式报告失败、诊断模式仍显示同条hint但返回0。43P/1.23秒，hook配置验证/ruff通过。真正pytest、LinuxCI、Ruff/mypy和源字节校验仍阻断失败，不关闭它们。

这是ROOT新增策略调整，不冒称原8文件独审覆盖这两处增量。原失败pre-commit与21.95秒旧全树合同日志保留；无baseline补录、字符串重写躲检查、--no-verify或平台审批绕过。
