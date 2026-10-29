# FF返工R2 ROOT最小独立复现

使用已有宿主Python，不必准备CWP/ET源码视图：

```
python -B -X utf8 replay_probe.py --ff-root <filing-fetch-w20-replay目录>
```

第一部分读取retained-case.json精确旧真实case并交新版断言：其run0已正常收到downloaded，run1才立即杀新重试，assertion_errors仍[]，仅证明已有原文情况下重试中断，并非同次新增采集落库后丢其返回。不能把这个组件断言当完整oracle或新E2E。

第二部分在当前cwp_public_readback函数所调用的CLI边界放置纯mock，用Events形成两个并发caller：A的query将读取B的sys.stdin。没有实际CWP模块/数据/进程/API参与；这是线程隔离缺陷的控制流复现。脚本恢复sys.stdin/stdout和sys.modules。当前实际输出见counterexamples.json。

189项离线短测（4.87秒）详见ff-review.json；没有全41/404秒全仓复跑。作者工区只读且clean。小fixture只包含报告case，原完整report路径/SHA保留于fixture，没有SDK、PDF或整attempt树。
