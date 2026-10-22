# R1 当前进度与封存设计的区别

本目录只承载当前 R1 的计划、索引及小体积证据，不复制整棵运行湖。

- **整体唯一入口**：[CURRENT_STATUS](../CURRENT_STATUS.md)。用户最新“继续”已恢复实施；先收口当前发布/CI，再按W03→W07/W06→新公司推进。
- **实施进度**：[implementation-progress.json](implementation-progress.json)，含 W01/W02/W04/W05 的实际工程状态；[stage-progress.json](stage-progress.json)保留 initial 运行历史并记录当前暂停阶段。
- **本轮收尾与当前实施细则**：[HANDOFF-2026-10-22](../HANDOFF-2026-10-22.md)。提交、推送、安装和最终组合测试以它引用的收尾收据为准。
- **冻结的设计输入**：`remediation/` 和 `diagnosis/` 是独立专家交付的原字节镜像，文件 SHA 不改。它们的“待接收”“未施工”“Next Step”只表示专家交付时刻，不是当前施工状态；其完整根因映射、接口、测试方案仍供后续实施使用。
- **冻结的首轮失败观察**：`initial-audit/`、`initial-execution-seal.json`、原 manifest 不回写。工程修复通过不把原 FAIL 改为 PASS，也不把药明康德继续当未使用的 holdout。
- **真实运行树**：`C:/Users/郑曾波/Projects/revenue-forecast-audit/runs/r1-20261021-cn-wuxi-apptec`。639 工件、36,665,980 bytes 的 initial partial 封存保留；Git 内不是整棵完整运行树，fresh clone 尚不能重演全部 live。

恢复顺序：新 W01 producer 与已安装 FF/RF 组合检查 → W03 公共 narrative 时间资格和 0.9/v5 接线 → 一次配置内真实摘要同时验证 W07 普通付费恢复、cache、RF 实际消费 → W06 原公司新研究 attempt 与四路独审 → 药明合联、Snowflake 泛化。每次收费前重读现有母账，未知费用预留不释放。
