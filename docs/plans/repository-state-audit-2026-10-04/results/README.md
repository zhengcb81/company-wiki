# 审计结果收集区

每个 harness 只能新增/写入它 lane 卡指定的单个文件。总指挥负责读取、核对和归并；harness 不改本 README、master plan、其他结果或 lane 卡。

`company-wiki` 是特例：由于结果若写在 CWP 内会污染被审计的当前工作树，CWP harness 必须按统一模板在回复中返回完整报告，不在任何 CWP 路径写文件。
