# D5 ROOT FF 路由子节点收据

状态：**PASS（仅 FF V2/V1 边界子节点；不代表全局 D5 验收）**

## 验收范围

- schema 2.0 请求在公开 CLI 不传 `--source-ref-v2` 时仍自动走 V2，返回 pathless `source_candidate`。
- 同进程直接验证 V2 路由时，将 `validate_handle`（V1 `canonical_path` 文件校验器）设为触发即失败；V2 成功且返回 pathless `source_ref`。
- schema 1.1 显式走 V1 时仍返回 legacy `canonical_path`；路径被测试限定在隔离临时 wiki 公司根内。
- 原有 schema 1.1 + `--source-ref-v2` pathless 测试保留。

## 结果与版本

- ROOT runner：3 passed、0 skipped、0 failed；32.911 秒；`scratch_restored=true`、`source_stable_during_run=true`。
- ROOT runner 选择/覆盖防护单测：`tests/unit/test_source_system_runner_scope.py` 9 passed；证明 D4 固定套件保留、D5 套件不可由 `--tests` 替换、两个强制模式不能混用及 JUnit/consumer 统计不误报。
- 必需案例：`test_schema_2_0_defaults_to_v2_and_never_uses_legacy_handle_validation`、`test_schema_1_1_keeps_legacy_path_handle_in_its_explicit_route`。
- 测试前 CWP HEAD：`bbd103528e117e246b0878d35286495da01e13db`；该次 ROOT 测试包含的工作树差异 SHA-256：`a5d24c0517cb095d5a53957a6a097733517042a2cf06353478228ff8e374729d`。
- 参与版本：RF `90c562ac6e305c4c5f6fba5a439851b20e0490a9`；FF `bf7e1dab4aebcfe671554a4fda59705eb7fe1765`；ET `003c1c065109d0b02c7bd4de09ad3e8461a99c0e`。
- provider mode：离线合成 fixture；临时 catalog 和真实 FF CLI 子进程；不下载、不调用收费服务、不读取密钥。
- 默认受限沙箱首次在测试启动前无法读取 RF 邻仓 Git 元数据；同一命令在用户已授权宿主执行环境重跑成功。该失败不进入 pytest，也不是产品/runner 路由失败。
- 测试输入：测试代码生成的合成 PDF；没有使用或修改生产原件。ROOT runner scratch 自动移除，PowerShell finally 移除独立报告目录；随后只读枚举确认没有 `cw-d5-ff-route-*` 临时目录残留。
- pytest 有一条非阻塞的 `asyncio_mode` 未知配置警告；本子节点无失败或跳过。

## 与全局 D5 的关系

此收据仅关闭 ROOT FF V2/V1 路由边界子节点。CWP pathless normalized-document port、StockWiki 三入口消费、真实只读文档样本的 CWP→StockWiki 组合、测试环境恢复总验和最终独立总审仍未完成；全局解耦保持 **OPEN**，其它主线保持暂停。
