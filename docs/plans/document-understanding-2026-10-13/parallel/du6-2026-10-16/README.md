# DU6：三条独立施工线

状态：DISPATCHED。2026-10-16 用户确认三张施工包已发出。三个独占工作树及启动种子此前已核对 READY；ROOT现在冻结三卡源码白名单，等各自交付后接收，不进入作者工区施工。DU5 已接收，不再派发旧卡。

|卡|独占工作目录|计划入口|与主线的接口|
|---|---|---|---|
|DU6-RF-TARGET-MEASURES|`C:/Users/郑曾波/Projects/revenue-forecast-du6-targets`|`docs/plans/du6-targets-2026-10-16/task_plan.md`|现 RF typed management target、同币单位责任和原生 forecast 输出|
|DU6-AUDIT-IMPORT|`C:/Users/郑曾波/Projects/revenue-forecast-audit-du6-import`|`docs/plans/du6-import-2026-10-16/task_plan.md`|已公开 bundle/2、/3 → 现 DU5 map/packet，不依赖内部 v4|
|DU6-FF-PORTABLE-EVIDENCE|`C:/Users/郑曾波/Projects/filing-fetch-du6-portable`|`docs/plans/du6-portable-2026-10-16/task_plan.md`|原 matrix report/相对 artifacts → 同一 oracle 的显式路径重放|

施工卡：[RF](du6_rf_target_measures.md)、[AUDIT](du6_audit_summary_import.md)、[FF](du6_ff_portable_evidence.md)。统一开工、隔离和交接见 [INTERFACES.md](INTERFACES.md)。每个工作目录内会有施工卡、接口文档及自己的三份 PWF，交给对应 harness 即可；不需读取整段聊天。

ROOT 独占 CWP src、来源准备和 WorkBudget、FORM→STATE→TABLE、v4 正式摘要/费用恢复、总 PWF 和最终真实供应商调用。三线不写 CWP；三线分别在不同仓库，不互改源码、数据库、安装副本、原件或共享输出。RF 主目录的三个 alert WIP 保留，不复制到独立树。

FF 的 CWP/ET 联调依赖使用固定已提交的只读 checkout；CWP 固定 `f08aa101ab49ca983d3a40356abfb05347f586b3`，ET 固定 `d0ac42c60dcca992db78860b8469cfed3dd527e5`。ROOT 的后续未提交接线不进入该卡测试。实际只读目录及种子提交以 `launch.json` 为准。工作树共享 Git 对象；不复制原文湖、AUTO、凭证或生产运行目录。

三卡可同时运行，任一卡完成即可交 ROOT 接收。只有 A/B/C 三个大节点；不增加人工许可。全部卡默认 0 API/0 模型；真实摘要质量和全公司 RF 循环仍由 ROOT 主线验收，组件绿不能关闭母计划。

## 启动留证

[launch.json](launch.json) 记录实际种子 SHA、基线、导入路径、各 PWF SHA 和只读依赖。三个作者工区逻辑大小共约8.62MB，只读 CWP/ET 依赖约20.27MB，共约28.89MB；共用 Git 对象，0原件副本、0API。只核对启动环境，尚未执行三卡业务测试或声称实现完成。卡稿中的 PREPARING 为起草时状态，当前以本表及各工区 task_plan 为准。
