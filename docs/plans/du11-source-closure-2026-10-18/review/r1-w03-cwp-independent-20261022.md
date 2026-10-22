# W03-A CWP producer 非作者独审

结论：**PASS_ENGINEERING_PRODUCER_ONLY**。审查者 `/root/r1_w02_source_boundary` 未编写CWP产品；绑定 `aff8be80c68b9f39c76dad2011354031132c9cef`。实际runtime和作者测试与该Git blob逐字节相等，运行前后不变，raw/CRLF与LF映射见JSON。没有未修产品发现。

## 独立结果

**12 PASS /0 FAIL /0 SKIP，8.63s**。8个真实source/owner/artifact API夹具控制，4个common资格反例；共享原件/owner-provenance构造器仅用于准备，场景和验证断言独立。

- PDF/native JSON: one actual original verification then one real owner lookup bound to same ref; no source_fact writes and DB unchanged; null publication retained
- Actual current_verified_open metadata from source owner, with artifact/ref/DB unchanged
- Old Git parent vs new known-publication source: exact body and full canonical receipt bytes; actual source reader clock frozen; read_at retained, not normalized
- Refresh stored owner proof changes receipt only; read does not mutate artifact reference or generation DB
- Proof cannot replace requested source identity
- Wrong SHA/later proof/known future pub/invalid pub refused through common qualification
- Current unknown/no-proof remains readable and creates no observation
- Projected two-parent result never calls root raw-proof lookup, rejects extra key, and rejects same-size B raw tamper despite real A proof

作者22新例、166相关PASS/1显式SEC HTML原文未提供SKIP是作者证据，不计入本12例。ROOT另做真实公开CLI→RF组合；本报告不冒充该流程或真实公司研究。

## 验收脚本与环境纠正

首轮沙箱拒绝临时immutable object硬链接，8个夹具未准备好、4纯控制通过；正常权限同测试恢复实际原生硬链接。随后11PASS/1失败仅因旧/新read_at来自source reader而审查者错冻transport；改冻实际owner时钟，仍比较包含read_at的完整字节，不删字段或改产品。封存时再纠正CRLF物理/Git blob与LF规范化的比较映射；实际源码始终与aff完全相等。原错误日志/XML保留，细节见JSON。初读预想test_r1_路径不存在，实际是test_narrative_availability.py；CodeGraph未初始化，均未向作者工区写入。

## 清理与边界

独占TEMP `C:\Users\郑曾波\Projects\company-wiki\.planning\w3crv` 初始/最终不存在，清0文件/0 bytes。原件生产数据0删除，作者工区/旧.planning不清理；0 API/下载/费用/安装/预算或默认切换。

**下一步：ROOT实际公开producer→FF/RF组合，先consumer后producer并线/选择安装。** W03-B、W07、模型摘要/paid缓存恢复及研究质量仍开放，工程PASS不等于整个PWF完成。
