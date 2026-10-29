# W20-FF返工第二轮ROOT复验（2026-10-29）

**结论：仍需小范围返工，2项P2。** 实际HEAD `a693e10da2fc14c96fa9e96e0c6406a6a3fbb1ec`，最终实现`3747e4a`之后只有文档变化，作者工区clean。19条交接SHA全部匹配；当前离线短测189通过/4.87秒。不重跑41全批或404秒全仓。

上一轮两项已有实质进展：公共接口现在能查到并实读本请求Ref/SHA；原任意sidecar触发已替换为本请求receipt tag；原13个基线失败exit_code已更正null，收据SHA一致。原件/产品FF scripts仍零改动。尚未完成的是下述真正丢回复场景，及新探针引入的线程隔离问题。

## FF-R2-1 [P2] 关键场景仍替换为成功返回后的另一条重试被立即杀死

`tools/offline_contract_matrix/w20_fault_cases.py:519`

证据：当前run0=_execute无kill完整收到downloaded/exit0；公开实读在run0成功返回之后；run1=_execute(kill_when=lambda:True)刚创建新进程即无条件终止，不观察该重试进入CLI/query或即将返回阶段。两份真实durable PASS（solo2ebbf3d7/prior2a273f32）均[(exit0,killedFalse,GET1,downloaded),(exit1,killedTrue,GET0,no envelope),(exit0,killedFalse,GET0,unknown_publication)]。新版assertion_errors均接受此形状。

根因：把“系统里存在durable资料”与“导致这份资料durable的同一次未确认采集在返回边界中断”视为同一故障；所以测试实际只证明已有资料时杀一个新重试不会妨碍后续复用。

返工：保留此已有资料重试中断用例作为有效但较弱的覆盖，不能签原卡R2/R3关键场景完成。增加一次真正同次采集持久成功但客户端尚未收到该次成功结果的边界丢响应反证；在测试/harness拥有的transport/FF公开CLI输出边界缓冲/截断/丢弃首次成功返回，先经公开query+reader实读验证本请求Ref/SHA，再模拟客户端未确认/中断，重启后首个同请求0额外GET且同Ref/SHA。允许真实FF进程已经处理完而响应在transport边界丢失；不要求产品CWP增加failpoint，不要求必须在服务器同一微秒杀中，也不要求exactly-once。

复验：先加会拒绝“run0已交客户端成功＋新空请求kill”替代场景的单元，再只跑这一种新的同次lost-reply真实链；before/mid/preexisting-reuse分别标清。若现有边界确实不能观测，交付最小seam需求并标该项PARTIAL，由ROOT处理，不伪完成。

## FF-R2-2 [P2] 线程组中的公共readback探针会串用全局stdin/stdout

`tools/offline_contract_matrix/w20_fault_cases.py:181`

证据：现有cli_main.py:492用ThreadPoolExecutor(workers最多2)同时跑case组；新cwp_public_readback设置全局sys.stdin及contextlib.redirect_stdout。ROOT Events纯边界mock确定性复现：A应该读取Company A，实际读到Company B（probe_errors=[]）。finally恢复不能防并发期间错读。全局_CWP_PROBE_LAST_ERROR同样共享。

根因：用单线程CLI的process全局I/O作为线程内函数API；新的readback探针没有遵守原case组隔离。

返工：保留公开接口边界，优先调用显式参数公共函数或将这段CLI调用放入既有有界隔离进程；如用局部锁，需完整覆盖stdin/stdout替换/恢复和探针结果，避免与其他组process全局重定向冲突。不要新增用户许可/生产状态库。readback返回值应区分明确not_found与probe失败/unknown，不能把异常None直接用is not None转换成“公开确认未durable=False”；这在mid-import相位断言会把探针失败当负证据。

复验：在2workers等效并发下，A/B不同公司或资料根请求均进入各自公共查询，不串stdin/stdout、不串错误；加入query异常/rc非0不被当明确notdurable的断言测试。仅短测＋相关case，不跑全41。

## 验证、清理与边界

- 当前189项离线单元/authority真实通过，4.87秒；新增六项虽绿，但只约束作者设计的新形状，尚不能补足原lost-reply场景。
- 两份真实durable PASS的实际三run形状/原report SHA与新版断言在[evidence/ff](evidence/ff/README.md)保存。公共reader确有同请求Ref/SHA验证的实现；这里不否认这段真实进展，而是区分“成功后复用中断”和“未确认的新增采集回复丢失”。
- 纯Events探针确定性展示线程A读到B公司payload，未启动真实CWP/HTTP，不冒充E2E。既有两组线程并发是实际支持路径，单次finally恢复不足以隔离。
- 只读作者工区、未修改索引或代码，未merge/commit/同步技能。0新供应商POST/下载，无完整41或全仓重跑。ROOT pytest临时树已删除；作者.w20-deps与_w20-runs/owned实际均不存在。
- 文档非阻塞修正：cleanup收据return_r1的false字段与实际已删除盘面矛盾；handoff旧9项计数及旧独审入口需随本次返工更新，不需新增审批或重跑测试。

## 最小后续

继续同卡原分支，仅修测试边界丢首个新增采集返回、探针线程隔离/unknown语义，定点验证后让独立agent复审这两项并更新handoff。若既有接口不能观测同次边界，给ROOT明确PARTIAL＋最小接缝需求；不通过重命名阶段或多起一个立刻杀掉的空进程来代签。
