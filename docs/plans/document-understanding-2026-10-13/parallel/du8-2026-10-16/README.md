# DU8：三条独立施工线

状态：READY，可立即同时开工；3工区/启动提交/干净状态/实际imports已核对。业务A/B/C由作者实施，未冒称通过。三线分别写RF、FF、AUDIT仓库，无路径重叠；ROOT独占CWP/ET生产接线。不是重派已完成DU6/DU7。

|卡|工作目录|施工卡|
|---|---|---|
|DU8-RF-COMPARISON|`C:/Users/郑曾波/Projects/revenue-forecast-du8-comparison`|[单一比较责任](du8_rf_comparison_owner.md)|
|DU8-FF-MATRIX-COMPLETION|`C:/Users/郑曾波/Projects/filing-fetch-du8-matrix`|[固定时限完整覆盖](du8_ff_matrix_completion.md)|
|DU8-AUDIT-MEASURE-EVIDENCE|`C:/Users/郑曾波/Projects/revenue-forecast-audit-du8-measures`|[数值与实读证据](du8_audit_measure_evidence.md)|

统一接口/测试/清理/交接见[INTERFACES.md](INTERFACES.md)，实际base/seed、干净状态、固定只读依赖见launch.json。每个工区自带施工卡、接口、task_plan/findings/progress，harness独立启动只需该工区上下文。只A/B/C大节点集中验收，不加逐小节点人工审查，不付费。

ROOT并线顺序：各卡独立交付即接收；先看独立反例与旧行为，再相关集中套件和实际CLI，必要跨仓大节点由ROOT统一运行。卡间无强先后；ROOT当前CWP/ET升级不被卡住，作者也不追ROOT未提交代码。
