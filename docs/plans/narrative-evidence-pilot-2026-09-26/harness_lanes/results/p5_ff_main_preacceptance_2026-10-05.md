# P5-FF MAIN预验收与下一节点施工细则

状态：收到交付、尚未验收/并线。FF独立树干净`ab9ce33`，base
`d4d2fac4c690bfb8b1368d2ca140fd75150fd288`，功能commit
`7c6cf48c5aa890fe34cb8304830246d4c20f16fa`；b5c1c82/5a5006e/ab9ce33
是PWF/交接收尾。源码位置与原卡见[p5_ff_runtime_simplification](../p5_ff_runtime_simplification.md)。
不要从原owner fcap未提交树施工，不读FMP key，不改Dayu/RF/ET或CWP配置。

## 已确认及尚待验证的事实

交付确实删除旧Worker暂停编排，两个runner共享新进程层；旧wire未升级。
handoff报告18新责任case、194迁移case及快速发布门GREEN；全仓463过、10
baseline-red、14skip。未把这份报告当作MAIN完整验收。

MAIN零网络/零项目写入的三个实际受控child，`stdout_cap_bytes=10`：

| 输出字节 | 实际结果 | 耗时s | 正确结果 |
|---|---|---:|---|
| 9 | ok/读9B | 0.399 | ok |
| 10 | OutputLimitExceeded | 0.051 | ok：等于上限不算超限 |
| 11 | OutputLimitExceeded | 0.057 | 拒绝 |

源码`_reader_loop`在remaining=0时没有再判EOF，导致实证等号错误。
以下是**读码风险，尚未实测**：

- `_pump_stdin`同步写完后才开始`_await_streams`期限，写入阻塞未覆盖；
- 双流EOF后`_finalize`无timeout的`proc.wait()`可能无限等；
- 单流overflow/error没有及时唤醒等待，仍等双EOF或完整deadline；
- POSIX leader已退出后`getpgid(pid)`可ESRCH，已有进程组/孙持pipe仍未终止；
- Windows Popen后才assign job存在早生子进程竞态，不能把注释“before
  grandchildren exist”当保证。正常hand-off案例通过不等于覆盖该边界。

## MAIN顺序、接口与测试包

1. **固定交付并读现有计划。** 使用已交付且干净的独立FF树或从该HEAD建
   同仓新整合worktree；`.planning/p5-ff-runtime-cleanup/`为外线历史只读。
   MAIN验收记录放CWP本结果目录，不改外线计划和原owner文件。FF源仓仅最终
   快进/合入目标主线；有未知WIP先保持隔离，不reset。
2. **TDD先证明公开进程行为。** 用同一短独立根和实际本地child，覆盖输出
   cap-1/cap/cap+1（stdout及stderr）、持续单流overflow另一流不EOF、关闭
   stdout/stderr但继续运行、stdin不读使写入阻塞、父退出孙持pipe。Windows
   快速派生必须用可控同步信号，不靠多次sleep碰概率；POSIX相同孙进程案例
   在真实POSIX runner验证，未跑须明确标记。每个异常由外部watchdog终止测试
   自建树，收集PID/elapsed和读取线程回收；watchdog根不能杀他人进程。合成
   child、PID文件、pipe和raw/DB副本全部finally删除，根恢复原样。
3. **一个进程生命周期修复。** `ff_process_transport`只负责bytes/deadline/
   exit/cleanup，两runner复用；单一绝对deadline从spawn前起算，覆盖stdin、
   两流和进程退出。等于cap允许，超过最多读一个探测byte就具名拒绝。异常
   及时停止自建进程树，try/finally关闭job/pipe并join本调用线程；清理宽限
   有界且单列，不能重新给每阶段完整timeout。不复制第二transport，或悄悄
   放大32MiB/64KiB/ET3秒兼容限制。无新人工签收/额外权限文件。
4. **修10项旧fixture与真实跨仓E2E。** 先复现报告中的fc803与isolated-wiki
   两组，按当前CWP下载请求补`acquisition_limits`，不放宽生产门。旧Worker
   停启不再是FF工作；保留来源锁/明确请求/错误分类等实际责任。复用既有
   FF→ET→CWP companion测试和离线fake provider，另复制固定SHA中微2025
   年报到独立目录，通过公开FF CLI复用/有界fake下载→CWP SourceRef verified
   read，重复不触provider、Worker调用/暂停文件均0；不下载外网或模型调用。
5. **一个大节点收口。** 合并新边界/生命周期、两个runner职责、具体红灯修复
   与三仓离线链责任包。hand-off已绿的provider/身份/SHA/期间/as-of/golden
   不为了“保险”重跑全仓长历史包。Ruff/既有快速门与实际行为都绿后commit，
   合入FF目标main/推远端、查精确CI；CWP总PWF更新实际SHA/结果。若仍有技术
   失败，只修对应风险，不用删除正确断言或“baseline-red”排除当前责任。

不新增公开wire字段、备用provider、自动无限重试/后台Worker或投资研究状态。
单次受控Download费用0、network0、translation false；测试真实原文副本必须
核`d64c410832f22f5127277bad6dc357c664aede523561af99150c494857fd3aa5`。
这份结果是普通交接/施工记录，不是运行时授权合同。下一步执行第2项RED。
