# 独立施工线交接模板

仅在自己卡指定PWF目录写 HANDOFF.md 与 handoff.json；不要把报告写进共享根计划或冻结专家包。

## 1 实际状态

lane_id / owner / 接管时间；原内置agent已停止的事实；自己的PWF路径。

每repo：绝对worktree、branch、base完整SHA、head完整SHA、remote branch、exactCI（无workflow明确not_available）。git status逐解释，不reset/commit其他owner文件。

状态分列：package工程范围、共享MAIN接线、真实公司/研究。后两项未跑就是not_run/pending，不能用单元GREEN写全目标complete。

## 2 需求与根因

冻结card/root ID及实际反例；改的是哪一责任层，为什么对另一公司/布局也成立；哪些旧工程接受有效且未重做。明确任何设计偏差，不改旧报告来回填。

## 3 源码与接口

每changed file对应repo与授权写集、作用、runtime是否需要安装、工作树byteSHA、git blobSHA。新DTO request/response JSON、版本/兼容/unknown语义、import/module/入口；MAIN需做的最小patch与测试命令及预期。

## 4 测试证据

每次实际argv、cwd、UTC、exit、collected/PASS/FAIL/SKIP、原日志路径/SHA；RED失败具体产品原因与GREEN变化。单元/集成/公共E2E分别说明，纯helper、loopback协议、真实provider不得混同。

写实际新增provider/model calls/token/cost；工程包默认0，不从预算cap推算。旧unknown保持原未知。

## 5 隔离与恢复

绝对owned TEMP、初始文件清单/size/SHA，cleanup目标在此root内的证明，恢复后差异；保护raw/config/他owner WIP的前后SHA。未恢复项必须具体解释，不能声称测试目录已还原。

## 6 提交/推送/安装

normal commit/push exit与raw日志，remote exactSHA与CI；安装仅供MAIN的changed runtime闭包，不执行全仓覆盖或拷贝真实材料。是否已经并主线准确填，施工harness默认false。

## 7 剩余与MAIN接线

工程未完成、外部客观未知、共享consumer待接线、真实研究待验分别列；不把未测当PASS、不新增许可。列一次MAIN大节点必须重跑的确切测试包。
