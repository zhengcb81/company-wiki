# S5 验证与发布台账

审计给出的源码位置、快照版本及优先级见[原报告](../module-boundaries-2026-11-11/review/s1-s4-post-rollout-12-module-audit-20261125.md)。本页在每个关键节点记录复现、责任仓、通过的版本、测试及实际投产路径。

| 模块 | 核对项 | 当前证据 |
|---|---|---|
| CWP / F4 | 异常类别投影；启动前 stderr；轮转竞争；CLI 诊断；仓内边界扫描 | `c68ad80b` 已推送，组合 105 通过、6 个既有环境跳过，折行及轮转 6 通过，绑定 15 路径的独审 10 通过。远端又覆盖一条旧的故障注入，因轮转类移到公共日志模块，该测试仍从退役导入位置取类。故障注入更新到实际 stdlib 轮转方法，故障保留与脱敏断言沿用。S5-08/09 继续。 |
| StockQA | Bearer、stderr 尾段、显式环境、日常用例及 F4 版本 | `master@0ffb3c7a` 已推送。已复现未缩进折行、窗口边界及旧收件目录的失效；父版日常 422 通过，最终无 stderr 及定向 38 通过。[同版 Ubuntu CI](https://github.com/zhengcb81/StockQAbyLLM/actions/runs/45694928466) 失败，正在按实际统一编排复现。实际采用等待对应版本验收。 |
| RF | 测试被远端实际收集、FF 子进程诊断、原作业资料根、跨层探针 | `main@1577be3c` 已推送，[同版 CI](https://github.com/zhengcb81/revenue-forecast/actions/runs/45696604761) 通过。首次 CI 暴露现行用例误靠历史归档、Linux 去读 Windows 任务与仅 Windows 的内存字段。修复后，用真实精简检出和 Ubuntu/Python 3.12 收集并执行 911 通过、2 跳过、46 子测试。专用运行检出已快进，两个路由与原作业冷读正核对。 |
| MC | CLI 配置优先级、运行时校验、ffmpeg 非零、HTTP 响应释放、日志 | `master@fa1f840d` 已推送，现场工作区已快进，原在途文件摘要一致。底层候选 386 通过，最终新增的 stderr 及独立 CLI/传输复验 7 通过。[同版 CI](https://github.com/zhengcb81/MeetingConverter/actions/runs/45692989173) 通过。 |
| FF | 非内建异常、T3 stderr / 原收据、旁路、矩阵跨仓调用及安装 | 独立候选 `1d3e0caf`。六项 RED，95 项定向通过，新真实子进程用 CRLF 原件核公开 CWP CLI 和 SHA。额外三个矩阵场景的 WSL 依赖缺失，未执行；保留原批次待验证状态。 |
| ET | worker 启动故障、用量出口、manifest、旁路、中断语义及帧 | 正式基线 `2fc8f92e`。已定位启动前 stderr 丢失与 manifest 假成功。原报告将捕获 `BaseException` 描述为吞中断，现有函数实际会再次抛出，须验证清理与退出语义。 |
| SID | CWP adapter 入口、旧文件句柄、stderr 兜底和脱敏轮转 | 待责任仓复现 |
| Audit | journal 降级后的原失败读回、日志、全局副本 | 待责任仓复现 |
| StockWiki | 跨库确认可重入、复本误报、日志与错误码 | 精确基线 `dd5b0338`。用原公共操作在 receipt DB 提交后注入 SQLite 错误，旧版已能用同一子收据、同一身份版本收尾，未复现卡死。相同原记录两份导致补投确实误拒。区分原诊断正文与投递状态，补投走当前目录，历史原字节保留。 |
| IQS | 截断/非法 HTTP、同阶段不同题、StockWiki 调用、F4 检出 | 待责任仓复现 |
| Dashboard | 相关号与落盘状态、预览错误/取消、旁路、公开路由 | 待责任仓复现 |
| IR | 成功响应损坏重试、末次等待、旁路和安装 | 待责任仓复现 |
