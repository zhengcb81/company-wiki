# CWP SQLite 定向 CI 修复

GitHub run 45735946650，job 139629114658，失败项是 `test_job_and_event_scopes_are_intersected_in_sql_before_ordering`。源基线 `7aa5b605366a22d5dd03fa0106de6e145ed42b07`。

查询已经由 AutomationStore 的只读 SQLite 连接执行。原测试把 trace callback 装在旧的可写连接 helper 上，正确结果返回后仍因未观察到任何 SQL 而抛出 `StopIteration`。同文件的 EXISTS 检查在空 trace 上也会假绿。修复通过 SQLite 公开的连接与 trace API 观测真实 SQL，断言过滤、排序、EXISTS 的实际执行及连接的只读模式。空 scope 零连接、零查询。补丁只更新一份测试文件。

| 验证 | 结果 | 证据 |
| --- | --- | --- |
| Ubuntu Python 3.12.3 原单项 | 1 fail，`StopIteration` | `linux-red.xml` |
| Ubuntu Python 3.12.3 范围查询与原 Store 对照 | 33 pass，0 fail，0 skip | `linux-green-focused.xml` |
| Windows Python 3.14.2 同上加 runtime lifecycle | 45 pass，0 fail，0 skip，临时目录已清理 | `windows-green.xml` |
| Ruff 单文件检查 | 通过 | `ruff check --no-cache tests/unit/test_automation_job_scope_queries.py` |
| 发布工区补丁干跑 | 工作树与 index 均通过 | `git apply [--cached] --check --whitespace=error-all` |

Ubuntu 本机扩展 lifecycle 试跑含三项因缺少 CI 已声明的 `lxml` 而失败，该试跑记录在 `linux-green.xml`。带该依赖的 Windows 对照全部通过。Ubuntu 定向测试与依赖缺口分开记录。

从当前目录复现 Ubuntu 定向检查，使用已有 `baseline.tar` 和 `repro_ci.py`：

```sh
/usr/bin/python3 repro_ci.py --name linux-red tests/unit/test_automation_job_scope_queries.py::test_job_and_event_scopes_are_intersected_in_sql_before_ordering
/usr/bin/python3 repro_ci.py --name linux-green-focused --overlay tests/unit/test_automation_job_scope_queries.py tests/unit/test_automation_store.py
```

补丁 `cwp-ci-scoped-read.patch` SHA-256 `0175c24b229b58a2eb5874adaa40fddaad5ea604acb9a94dde5dc8a987af95d2`。清单记录单一测试文件上下游 hash。发布候选 `4154161da0e3f5902812606c1b8bf0740dc82955` 的 Git blob SHA-256 已核对为 `408cc0124cc32ca3d57c188b2fbba9e63c00a60a5ffc7f836f9464e7f57af894`，与清单一致。
