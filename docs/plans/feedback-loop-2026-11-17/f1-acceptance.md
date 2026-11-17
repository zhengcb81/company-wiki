# F1 离线总控及 CWP 首次接线验收

2026-11-17。适用范围为显式交付的旁路、控制 RPC 和 CWP Phase C 工程入口。实际宿主作业编排及正式新摘要 RF 采用在 F3。

| 核验 | 观察 |
|---|---|
| TDD 与独审 | 最初测试 RED 为缺少总控模块。六项基础回归先绿，独审的错责任人和第二修复代次在实现前为红。补上转派、发生绑定、原收据查账、原场景回告后通过。两份观察同 ID、异内容，含跨批的六种处置顺序，均不能静默改变原事实。 |
| 幂等及控制宿主 | 两个真正的控制 CLI 进程竞争同一测试宿主；另一次在宿主登记修复后丢失回复。恢复通过原 key 查得同一作业，一次分诊/修复/复验/回告，并保留原生 observe 绑定。第二发现方可复用修复、分别回告。旧消费版本不能关闭；费用未知只查询原作业。测试宿主使用隔离 SQLite，生产仓不依赖它。 |
| 完成事件 | 已配置旁路和宿主时，真实控制子进程从回执被唤醒。父进程不等待宿主结束。控制输出与原生终态文件隔离，失败不会改变公司运行退出结果。未配置宿主显式记录 `host_unconfigured`。真实 agent/付费凭据未在这次验收中部署。 |
| 原生故障 | 原基线 `d742d350f` 上，同 run 多一次 POST、跨 run 多一次 POST、实际公开 CLI 拒绝错误 pinned SHA 三项全部 RED，耗时 70.49 秒。同三项在修复源码上 GREEN，85.36 秒；每例一次本机环回初始请求，零外部调用。保留了成功、失败和未运行的同级检查。详见[已定位的问题](issues/cwp-native-recovery-observation.md)。 |
| 错绿反例 | 两个 CLI 都返回 0，reader 自报 verified，响应字节却与原 SHA 不符。修复前定向断言显示 `verified`，修复后为 `artifact-bytes-mismatch`。独立对照七项覆盖错引用、错字节、错来源、未验真、正确结果、无结构化退出 2 及具名拒绝。 |
| 本次最终测试 | 在支持既有 Phase C 夹具硬链接的宿主和 pytest 独占短目录，35 项通过，96.04 秒，临时根自动清除。Ruff 通过，技能校验器用 UTF-8 模式通过。Windows 测试夹具的一处 SQLite 事务原未显式关闭，已修复；首次失败遗留的专属临时根已核对路径并清理。 |

## 真实封存回执

输入来自之前真正运行的 H1 `phaseC-090-420049be036e` 的 `overall.json`，SHA-256 为 `b1a3571c346b2592ff4a14b07e3313af120918f88230bc44257a0c655cf9f3bb`。owner 指纹记录代码 `5c6cd5c82cbe3fa5c5f65d63e53e651b5b531c10`，模式 live、selector 0.9.0。通过公开导出命令将三个检查写为 1,155 字节 UTF-8 JSONL；再次导出复用同一文件。公开引用解析回 `a63b4566b0591f963931d2fc61893c5e85af8532a612cc638864c75a911ddba3`，记录原生 locator verified 与当时两个零 POST。原生回执和指纹内容不变，临时根已删除。此次重放不调用模型、供应商或 RF。新选材、正式生成、缓存内容完整性与 RF 采用依[试点条件](company-wiki.md)验证。

## 可重复验证

工程仓根目录运行下列定向组合。测试宿主的 SQLite、环回请求和临时原件均位于 pytest 所有的临时根；Windows 使用原生支持硬链接的本机运行环境。

```text
python -B -X utf8 -m pytest -q -p no:cacheprovider tests/unit/test_feedback_loop.py tests/integration/test_feedback_loop_cli.py tests/integration/test_feedback_phase_c_hook.py tests/integration/test_feedback_native_failures.py tests/test_phase_c_finalization.py
```

日常远端 Unit 会覆盖快速的调度状态测试。真实环回、主动故障和较慢的跨进程测试在大节点运行。
