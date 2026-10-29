# W20-FF 第二轮定点补完（2026-10-29）

本文件替代上轮RETURN_FF作为当前返工入口；同一原卡、原工区、原分支续改，保留已有真实进展。暂不并线，主线公司循环仍暂停。

- 工区：`C:/Users/郑曾波/Projects/filing-fetch-w20-replay`
- 分支：`codex/w20-ff-replay-20261028`
- HEAD：`a693e10da2fc14c96fa9e96e0c6406a6a3fbb1ec`，最终代码`3747e4a`。
- 原PWF：`docs/plans/w20-ff-replay-2026-10-28/`，PLAN_ID不变。
- 必读：[ROOT报告](ff-review.md)、[机器报告](ff-review.json)、[可重放反例](evidence/ff/README.md)、原卡construction_card.md。

## 已关闭，保留成果

旧任意sidecar live trigger改成本请求receipt，19个交接SHA全匹配；13项基线失败的exit_code已按真实未知改null，原R3关闭；公共query+reader实读同请求Ref/SHA确有实现。189定向测试/4.87秒全绿，不改写历史PASS，不重跑41或404秒全仓。

## FF-R2-1/P2：原关键故障不能用较弱场景代签

当前durable新case：run0完整download并已向客户端成功返回；run1新建后kill_when恒True，甚至未观察是否进入FF工作；run2复用。两份真实PASS和新版oracle都证明的是“已有原文后杀新重试”，不是“本次新增采集已durable但其成功回复丢失”。保留此有效对照，纠正关键场景完成声明，不需删全部已有case。

在harness拥有的transport/公开CLI输出边界，截留或丢弃**同一次真实新增采集**成功返回；此时通过公开query+reader实读本请求Ref/SHA，模拟客户端尚未收到成功/传输断流，然后同一公司期次恢复第一次0额外GET/同Ref/SHA。允许服务端已经处理完、响应在传输层丢失；不要求微秒级杀点、不新增CWP产品failpoint，不承诺exactly-once。

测试要有不变量：单次acquisition身份贯穿下载、durable、被截返回；此前未向该客户端交付成功。能拒绝“已返回成功的run0＋另一个空进程kill”代签。先做此断言RED，再只跑新lost-reply代表真链，before/mid/reuse中断各自范围明确。若现有边界确实不可观测，给ROOT明确PARTIAL和最小seam需求，不能靠重命名phase报完成。冻结CWP/ET源码视图与既有限额沿原卡，不跨仓改产品。

## FF-R2-2/P2：公共读回探针隔离与unknown

新cwp_public_readback在既有ThreadPoolExecutor组内改process全局sys.stdin/redirect_stdout和last_error；确定性Events反例已证明线程A读到B公司请求，finally只恢复最终状态，不保证执行期间隔离。

优先用显式参数的既有公共函数或受界隔离子进程；如局部锁方案，必须完整覆盖全局I/O替换、使用和恢复，且不能与其他case全局重定向并发冲突。结果/错误归本调用，不共享全局last_error。没有新用户许可/状态库。

把明确not_found、found、probe_error/unknown区分；异常返回None不能当“公开确认未durable”的负证据。两个不同公司/资料根并发、查询异常/非0返回和stdin/stdout恢复都有有限测试。只需短测和相关代表case，不全41。

## 收尾

原allowlist/隔离不变，先有效RED再修共同harness owner。真实链只用本地fixture边界，0收费/真实下载；自有TMP恢复初态。随收尾修旧9/新10计数及cleanup false字段歧义，文书不增审批/不重跑测试。

调用真正独立agent按原卡及上述执行阶段不变量检查质量，发现本范围问题全部修复，保留旧审查/旧RED，新review另存。更新同delivery/handoff.md/json最终源码commit/SHA、实际命令/阶段证据/清理/局限，正常commit/push原分支；不自行合主线或全局安装。完成交ROOT，无中间小节点签收。
