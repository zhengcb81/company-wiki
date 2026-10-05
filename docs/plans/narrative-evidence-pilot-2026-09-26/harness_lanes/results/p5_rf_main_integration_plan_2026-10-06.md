# P5-RF MAIN 整合节点 — 2026-10-06

## 已核事实和单一目标

交付树 `cwp-lanes-20261005/rf-source-v2` 干净，代码31fe65e6、报告a74b9ceb，均基于已发布8a153f33但尚未push。9项TDD及98责任回归、2项公开CLI已由外线实跑，MAIN复用收据，不重跑全仓/生产数据包。当前FF main758e8f4、CWP master f65e8c9（生成器代码b148123），均已发布/精确CI绿。

本节点让RF的默认真实来源链在上述已发布producer下可用、并入主线，再解除CWP生产旧derived处置的消费者前置。保留收入预测计算、UC/hash-pending、原文SHA/身份/期间/as-of及既有wire；不引入审批文件、私有根或多开关。

## 实际缺口

1. compatibility/current.json仍钉不支持v2的FF89c8bdb；新CLI E2E无env即skip。不能把skip当默认路由验证，MAIN重绑已发布FF/CWP并使新契约测试正常运行。
2. message-contract测试仍调用已退出的CWP evaluate_review。对齐当前原件/引用SHA合同或退役只测旧人工审查的部分；不恢复已删控制，不为GREEN改投资计算。
3. RF quality.yml仍全套pytest+第二次coverage+mutation+安装同步+生产相关门并行/重复运行。按照用户已反复授权的CI简化，收敛单Python短CI及同一pre-push精选集合；相关来源/公式行为和真实离线默认链保留，长演练仅大节点手动运行。退出陈旧workflow签名/两job名称断言，改测真实配置与责任包；不新加小节点门禁。
4. 当前main被旧rf-impl占用，242项staged WIP；不能reset或把它们夹带并线。owner fcap5319ee26仅两份weekly日志，SHA分别b617b0b0…和0d55cb8c…，保持字节。干净rf-mainline-integration-20261004可复用。生产来源不能因本地主树仍旧代码而继续读derived，发布后须让正式调用目录使用已验收代码；必要时只改旧main树的branch归属并保留index/文件，再同步正式checkout，owner两日志精确保留。

## 顺序、接口和写集

1. MAIN在干净rf-mainline-integration-20261004创建codex/p5-rf-main-integration，复核remote main未变后ff-only到a74b9ceb。外包树/原owner/RF-impl WIP均不施工。
2. 先实跑新9项及2项公开CLI（显式指向已发布FF/CWP），保存短测试根并finally恢复。追踪当前Git tracked生产caller和字符串CLI调用，旧历史runner明确退出当前入口；默认来源不能退回正文/猜目录。必要的历史造数器仅test fixture，不重复建设reader/registry。
3. TDD先框住新依赖绑定、CI和pre-push使用同一有界责任集合、正常E2E不靠env skip，以及已退出人工review API不再成为测试依赖。再最小修复current pins、fixture namespace/版本配置、文档与快门。已有合法字节/来源错误必须失败；null usage不伪造0。
4. 集中跑来源默认、metadata/hash/合同、公式核心与新真实三仓链。真实AMEC原PDF只读复制到独立短根，经RF公开CLI形成raw SourceRecord、重复reuse；旧artifact删除不影响结果，篡改原文失败后恢复、所有根/进程恢复。0模型/外部下载；fixture身份/公开日明确不伪称生产资格。不复跑已签收的长压力/生产数据包。
5. 正常commit/push HEAD:main，精确CI全绿；用Git历史和状态清单同步本地main/正式checkout，保留RF-impl全部WIP与owner日志SHA，不force-push、不跨仓写producer。安装副本若需更新按已授权部署责任单列实际结果，不能用CI虚构本机已升级。
6. 更新CWP总PWF、RF MAIN收据和本卡验收（base/delivery/code/published SHA、精确CI、实际责任命令/计数、真实CLI/原件SHA、根恢复、owner/WIP保护、遗留项）。只有实际默认消费者退出、公开读取/新引用可回放后，再执行已经验收的CWP retire-derived/prune/VACUUM存储大节点。

此计划不要求额外人工签收。CodeGraph原RF索引属于旧fcap，交付worktree未初始化；按已打开的候选源文件和当前tracked AST核调用者，不能把旧索引当交付代码证据。
