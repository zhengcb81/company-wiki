# W11 独立复审（2026-10-09）

结论：本次工程责任范围通过。原 `independent_review.md` 及其 FAIL receipt 保留；此次复审不证明任何一家公司的 M3。

## 审查版本与范围

- `revenue-forecast-audit/skills/revenue-forecast-audit/scripts/audit_run.py` SHA-256：`2c30b29fe64c78deef194ace0650ad73d3402e22510995baa2cf184c5ae54c57`。
- 复读实际 argv 绑定、历史/消费副本、聚合容量、运行后完整性检查，以及共用原子写入错误处理；未编辑源码、技能安装副本、旧执行记录或主 PWF。
- 独立重跑 `test_precall_input_history.py`：15 tests PASS，2.199s。
- 独立补控 10 项，确切 argv、观察字段、源码 SHA 和测试日志见 `re_review_receipt.json`。

## 原缺陷闭环

1. 原 R1：输入与输出采用同一路径时，旧实现错误地改写两处 argv，子进程可覆盖历史材料。现在重复路径必须指定 `--freeze-arg-index`；未指定时记录有限失败且不启动 child。独立实际子进程验证输入 index=4 指向消费副本，输出 index=6 保留原路径；历史副本与消费副本原字节一致，输出写入未破坏历史。
2. 原 R2：trust statement 写入失败后清理异常覆盖主异常。现在 trust writer 和通用 JSON writer 使用同一原子写入处理；两者注入 replace 主失败及 unlink 次失败均保留 PRIMARY_REPLACE_FAILURE，报告 cleanup_failures=1，旧目标未替换。

## 相邻责任检查

- index 0、-1、非输入 index 3 和越界 99 均为有限失败，未启动 child。
- 在逻辑输入 cap 等于 19 bytes 时，两份初始副本共 38 bytes，等于 2× cap；聚合、缺文件、未绑定输入和原字节不重编码由 focused suite 验证。
- 消费副本被子进程改写后保留原历史；真实 child exit=9 原样保留。改写后超时仍保持 exit=124、timed_out=true 及 TimeoutExpired 主原因；完整性诊断不会覆盖主失败。
- 终端不重复正文；JSON 不把 unknown/null/unattested 伪装成完备质量签收。没有新增许可文件、签名、身份门或配置扫描。

## 限制与后续

- 本次是预调用记录器工程验收：外部 provider/付费调用 0，整家公司 M3 未验证。父线程已有 4 次实际安装 RF native 调用记录，本报告没有重复消耗或覆盖该历史。
- artifact contract 早期段落的“argv 指向 frozen path”建议与后续已明确的 `frozen_path`（历史）/`consumed_path`（实际输入）术语统一，属于文案清晰度问题，不影响本次通过。
- 子进程后代及消费副本被恶意扩写不构成此次初始副本容量保证；当前实现诚实报告运行后完整性变化。
- 独占 TEMP 基线恢复、临时根不存在；审查前后源文件 SHA 一致。原始资料和生产配置未触碰。
