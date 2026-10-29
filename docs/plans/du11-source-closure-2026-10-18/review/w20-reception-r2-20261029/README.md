# W20返工重交复验：唯一当前接收入口（2026-10-29）

> 已完成：本包最终修复/独审/并线结束，本文件为历史返工记录，勿重新实施；见[最新完成入口](../w20-reception-r3-20261029/README.md)。

**三包返工都已收到，原反例多数关闭，但五项实质遗漏仍需定点补完；均暂不并线/安装。** 有效进展保留，不重做整个包，不恢复暂停的主线公司循环。本页取代[上一轮接收](../w20-reception-20261029/README.md)的当前状态；旧报告/RED按版本留存。

| 原包 | 已关闭 | 剩余范围 | 交原harness的当前返工入口 |
|---|---|---|---|
| AUDIT | 原R2 unread及原7个反例 | 原R1：显式unit=元被正文比例覆盖；币种向另一笔金额借 | [RETURN_AUDIT.md](RETURN_AUDIT.md) |
| RF | 异源误报、多路径、解压大小；/3多父兼容 | 同源不同片段收据仍可串用；坏DEFLATE未命名捕获 | [RETURN_RF.md](RETURN_RF.md) |
| FF | 旧sidecar误触发、机器交接记录 | 用弱场景代替同次入库丢回复；并发读回probe串全局I/O | [RETURN_FF.md](RETURN_FF.md) |

这仍是原来同三包的剩余返工单，不是新派三个项目。原工区/分支独立不变，可以各自续改，不等别包，不需小节点ROOT签收。所有包都有源码绑定、干净工区、作者复审记录；这些有效事实保留，但不能代替行为正确性。RF/FF远端已核与交接HEAD相同；AUDIT无remote，不新建公开仓库。

## 本轮独立证据

- [AUDIT](audit-review.md)：原7P、作者35P、numeric7P、11步合成CLI；新参数化6子例仍RED，原R2确认关闭。20文件SHA匹配。
- [RF](rf-review.md)：37P/10.95秒；真实wire/consume/forecast证明同capture不同材料仍可误报，19B坏压缩流真实CLI错误未归一。/3多父与缺hash宽松正例保留。
- [FF](ff-review.md)：189P/4.87秒；核实际旧真链三run形状不是同次新增采集lost-reply；Events控制流probe证明A读B公司请求。没有冒称新跨仓E2E。19文件SHA匹配。
- [版本/交接核对](root-provenance.json)、[结构化状态](SUMMARY.json)。源码清单匹配；RF一份progress文档SHA滞后不作为产品拒绝理由。

所有新测试仅ROOT自有临时树，结束恢复初态；只存紧凑合成反例/日志/收据，无原件/SDK大副本。ROOT未改作者源/索引/主线、未付费或下载、未碰RF原三份assurance WIP及CWP原hook mode。原CWP代码CI仍为已确认success，不用来签当前包质量。

## 下一轮如何避免只修眼前例子

按关系不变量设计参数化正反例：一个数值的typed信息必须属于它；一次consume回执对应其创建claim的已声明材料；一次故障的持久化和丢回复必须是同一个新增采集请求；线程内probe不能共享进程全局I/O/错误。只修共同owner，显式矛盾给诊断、缺观察保持unknown，不加人工门禁/hash必填/无限词典，不提高额度。

各原harness完成剩余修复与有界短测后，真正独立agent复核不变量/兼容和最终实现，保留旧报告，更新同handoff/commit/SHA，正常提交推送原分支，再交ROOT。无需全仓/全41反复跑。主线循环继续暂停，真实摘要/缓存/RF公司采用与总体目标未完成。
