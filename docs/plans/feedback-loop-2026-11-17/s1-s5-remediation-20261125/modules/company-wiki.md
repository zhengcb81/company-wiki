# company-wiki 整改交接

2026-11-25 Windows 候选。基线 `c918a402e3cf5a58ed11c27413f92fd1f50ec256`。35 个产品和测试 Python 文件的原独审指纹为 `489f5593cf02c51bd8e5f141aa4407b87d641ec57e1dc6a272f993ea8392301f`。指纹输入是按 PowerShell `Sort-Object -Unique` 排序的仓库相对路径和当前工作树字节 SHA256，每行 `路径 空格 小写SHA256`，LF 拼接，无末换行。候选路径位于 `src/company_wiki` 和 `tests/unit` 的本轮改动，排除既有在途 `source_catalog/read_budget.py`。发布检查随后补了 `_uses_descriptor` 对 `typing.TextIO` 的参数注解，用项目原有全 `src` 类型检查验证。

## 根因与整改

- **先分配运行身份，再建立进程和调用业务。** AUTO supervisor 启动前记原运行号、槽位和独立尝试。读取实际退出后记录原终态。子进程保留加载工厂、开始轮询及同一作业尝试的阶段，业务进度仍由 AUTO SQLite 台账管理。父进程观察到强停时，按原尝试生成诊断。子进程异常由捕获范围内的结构化日志保留，外部只看到进程实际退出。装配点复用已有失败投递。 [Supervisor](../../../../../src/company_wiki/automation/supervisor.py) · [Worker 进程](../../../../../src/company_wiki/automation/worker_process.py)
- **只让已脱敏文本接触诊断介质。** 提取共享的分片文本流，完整行脱敏后才追加。测试覆盖分割头、完整头之后的折行以及同一异常写到不同渠道。叙述传输原来丢弃 Python 与本地文件描述符输出，现在在进程内通过管道排空并脱敏，业务 stdout 和 stderr 继续按原机器格式输出。诊断介质失效可退到 owner 状态根。SourceRead 提供可选身份与降级状态字段，默认线协议保留。 [诊断流](../../../../../src/company_wiki/diagnostic_stream.py) · [叙述传输](../../../../../src/company_wiki/automation/narrative_transport_cli.py)
- **留存生命周期并保留公开业务回执。** `runtime-trace` 模块可依原运行号及尝试号冷读有界本仓时间线；每条事件含 UTC、包版本、产生日志的实现文件 SHA 及安全输入引用。已验证来源的定位、验真、传输以及下载、摘要和维护入口都使用原运行上下文。F4 复用失败观察协议，成功记录留在 owner 轮转日志。坏批请求保存实际解析异常，坏库维护保存实际 SQLite 分类。 [生命周期](../../../../../src/company_wiki/runtime_trace.py) · [诊断投影](../../../../../src/company_wiki/runtime_feedback.py)
- **把真正只读和业务存储操作交回所属层。** AUTO 计划和查阅用只读连接，缺库不创建，旧兼容库不触发迁移。AUTO 写端共用受限时长的连接。目录注册和断言通过具名查阅和事务操作访问存储，任务编排拿不到业务层 SQL 连接，在同一事务内完成投影、原件恢复和审计。 [AUTO 连接](../../../../../src/company_wiki/automation/migrations.py) · [目录断言记录](../../../../../src/company_wiki/source_catalog/assertion_records.py)

## 本机独立复跑

从仓库根在 PowerShell 执行。测试插件自动加载关闭，Windows Python 使用 `C:/Miniconda/python.exe`，每次命令使用独立短临时目录。用已生成的合成夹具和外部端口替身，无供应商调用或费用。

```powershell
$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD='1'
$env:PYTHONDONTWRITEBYTECODE='1'
C:/Miniconda/python.exe -B -m pytest -q -p no:cacheprovider --basetemp .planning/r25c-check tests/unit/test_cwp_runtime_lifecycle.py tests/unit/test_source_metadata_storage_boundary.py
```

- 12 个生命周期回归和 2 个存储边界回归最终通过。最初 6 个公开或原生反例先红，分别包括原凭据进入继承流、缺强停身份、只读建库、坏库维护原因丢失、成功无法冷读、批解析丢真实异常。其后折行凭据、已有 Store 只读触发重建、原生叙述诊断消失和断言 SQL 穿透均实测先失败。
- 200 项 AUTO、日志、存储及边界组合通过，涉及 `test_automation_migrations.py`、`test_automation_store.py`、`test_automation_supervisor.py`、`test_automation_controller.py`、`test_owner_runtime_feedback.py`、`test_layer_public_boundaries.py` 和上面两份用例。73 项公开原文流、文档浏览、历史定位和 N4 实际子进程用例通过。
- 目录行为覆盖 217 项，包含并发恢复期间保持不可见、重投幂等、交易失败回滚和原件不变。该批的一项公共 API 静态检查因新增模块尚未声明 `__all__` 而失败，添加字面量公开入口后，200 项组合中的同一检查通过。
- 额外 151 项早期组合中，150 项通过。一项坏叙述请求的重复子进程启动在并行资源争用时触发原测试 20 秒约束。相同真实入口的异常断言回到进程内，以免再次承担冷启动，正式子进程协议仍由同组已有测试覆盖。Ruff 和 Git whitespace 检查通过。

## 后续独审口径

按本候选重新运行上面的两文件，并从默认机器收据核对二进制原文。检查故障、脱敏、阶段关联和只读数据库行为；过往已经丢失的日志无法补造。当前新证据覆盖 worker 工厂边界和受 supervisor 观察的真实终止。宿主在 Python 子进程首次进入目标代码前的极早启动异常、两个进程同时突然掉电以及 Windows SYSTEM 排程实际触发尚未逐条验收。跨仓冷查由总控验证。历史回填和内部辅助工具仍按真实采用情况核对。模型协议内部旧共享私有调用及其已付缓存身份另需复验，当前成果未改变该模型运行边界。
