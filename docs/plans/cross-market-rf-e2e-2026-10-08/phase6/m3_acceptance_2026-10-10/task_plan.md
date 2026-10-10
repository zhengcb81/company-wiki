# M3 三卡集中验收与根修

本目录归MAIN，原交付分支及handoff不改，冻结157项共因包不改。

## Goal

验收三卡实质工程交付，修共因后正常并线、提交推送、精确CI与定点安装。原件、生产配置、Dayu与ownerWIP保留。不以工程绿签公司研究通过。

## 大节点

1. 分支/交接/原diff实查 — complete。
2. 三责任TDD和MAIN共同接口根修 — complete，10类问题见root_fix_register.json；原生失败日志保留。
3. 独立公共责任验收 — complete；JSON152、USAGE CWP169/FF44/RF101+public7，FLOW109/46subtests；公共跨进程101PASS，另137 CWP快合同/FF646+78subtests6明确skip、类型绿；计数有交集不相加。最后RF稳定快门日志记录实际结果。
4. 正常commit/main merge/push/exact CI与定点runtime install — complete；三个精确CI均success，18fresh installed子进程通过。不得使用分包FLOW早前no-verify/红CI作为发布依据。
5. 原PWF归总正常发布 — complete；04f45c86精确CI38084232316 success。测试记录自动隔离补充正常提交/推送进行中。
6. 原九卡后续AUTO JSON/W04/W03/W05/W08/W09与真实复验 — 本验收节点外的MAIN后续，pending。

## Next Step

本节点正常发布、定点安装、155保护SHA与邻仓WIP检查已完成；归档最后验收PWF后继续AUTO JSON公共路由/投影与generation绑定。无需新逐材料许可、人工签收或canary链；既有资源上限继续生效。当前goal仍active，真实三家四审/新三家泛化/池loop和后续八家尚未完成。

正常主线并线/推送全部完成：CWP f94b9ef0、FFe1e3ad86、RF6883bf00，精确CI38083232923/38083419792/38083371392均success，ls-remote与local相等。FF4+RF14工程文件按Gitblob SHA定点同步两个物理技能根共36文件，554其他文件未变，.claude junction一致。155保护SHA全部未变；fresh installed child独立18probe已通过并归总本节点，不声称真实公司研究通过。


## 测试记录自动隔离补充（2026-10-10T20:39:25.463148+00:00）

三仓源工程发布结论不变；原PWF收尾提交04f45c86的精确CI38084232316也success。随后修复独立测试脚本复跑会覆盖旧收据的问题：默认自动生成唯一attempt目录，写入独占创建，不再要求人工备份。11项输出分配正负控与一次fresh18 installed复跑通过；MAIN重新实核40份封存记录和新36份日志SHA，590安装文件无测试修改，两处owned TEMP均恢复，新增provider/model/费用0。原sealed receipt继续绑定原执行脚本，不重写旧报告SHA。

补充证据：[自动隔离与恢复](installed_probe/attempts/20261010T203521373000Z-5517ba96006c41b9be5a9581419e1525/output_directory_checks.json)、[本轮18项真实安装复跑](installed_probe/attempts/20261010T203521373000Z-5517ba96006c41b9be5a9581419e1525/verification.json)。10类产品共因和1类测试证据保留共因分开记录；没有增设材料审批、签收链或扩大产品源码范围。当前补充正常commit/push待执行，之后只核对新精确HEAD的远端结果。
