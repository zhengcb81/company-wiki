# DU8 RF 对比外包最终接收 — 2026-10-17

**已验收、合入main并推送，精确远端CI成功。** 作者最终8845bc18，完整历史合流6bd53b78；ROOT共因修复b41dceef；工程/交接发布c984a8fa。[独立审查](du8_rf_root_review.md)PASS/0未解决，12源/测试raw及Git blob绑定明确。作者旧handoff末提交/计数已过时，ROOT以实际最终源及新收据接收，不要求作者补小签收。

## 实际工程效果

比较计算归属唯一target_comparison owner，legacy/typed兼容路径显式保留；生产与报告使用同owner。报告绑定独立输入并从两个参数中剥离被审比较行，保留防回声能力。原季度、币种/金额单位、约束后收入、未建模/超期空比较和旧wire保持；不更改原gold或发布数字。

ROOT独审实证0/1能冒充False/True；legacy bool()及typed dict==具有同一Python等价陷阱。report共享边界以owner bool/None singleton验真，两条路径均修；合法未知null仍not_comparable。新57 TDD回归覆盖7模型/4伪值/两验证入口及合法null；修复前语义RED28FAIL/29PASS。首次48FAIL中的20只是消息regex过窄，错误及纠正都留证。原始ROOT集中559PASS/2FAIL为表达式AST限制正常重构，删除3个重复/无效AST测试及专用helper142行，独审实际确认所有手算/CLI/篡改/owner行为/gold保留，不靠改数值洗绿。

## 最终证据

- 最终28相关套件558PASS/7SKIP＋163subtests，26.09秒；与作者实际27目录504PASS/7SKIP范围重叠不可相加。
- 独立7正常模型、35篡改拒绝、38行为、4owner消费/echo检查通过。
- 正常pre-push416PASS＋36subtests，36.90秒；[精确CI39016431219](https://github.com/zhengcb81/revenue-forecast/actions/runs/39016431219) SUCCESS。
- .agents/.claude/.codex三份技能各定点4文件同步，共12；写前核对旧主线，原子替换，配置/output未覆盖。全新进程确认模块确来自安装目录；6正常模型运行＋6数字冒充拒绝通过。

[全部ROOT收据](du8-rf-receipts)；原作者UTF16收据留原仓历史，ROOT新收据UTF8。原始运行argv/目录如实保留，归档探针不是可在归档目录直接运行的生产入口，固定测试套件可在干净检出隔离复现。

## 清理与范围

0真实HTTP/供应商/下载/原件复制、0生产配置写入，作者工区只读；自有临时目录清理且sentinel字节/mtime不变。RF main三条原告警WIP SHA及147个output文件元数据未变。ROOT新建重复接收工区发布后核清洁移除，不移除作者树。该包只证明合成模型工程流程，不宣称真实公司/买方质量或CWP来源深页摘要验收完成。

下一步返回CWP母计划的native导航→唯一matcher→POLICY→PLANNER→同一WorkBudget→source单parse生产接线，之后真实PDF深页/正式摘要/缓存恢复/holdout。外包仅ET仍待最终交付；旧定时任务不存在，未重建。
