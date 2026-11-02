# R7 tooling CI 旧 oracle 跟进

状态：**TARGETED_PASS，待 ROOT 提交/远端复验**。基线 `bd911a2bd1125fe46d7c5a0f605fe3b0104f17be`；只修改 `tests/unit/test_w08_narrative_g2_replay.py`，不回退已发布产品源码。

## 根因与迁移

旧 `test_report_may_not_exceed_eight_mib` 在写报告前只断言 `MAX_REPORT_BYTES == 8MiB`，随后写的还是小报告。它没有验证真正的超限行为或内容完整性；R7 按用户新规则移除常量后，该内部实现断言直接 AttributeError。

本次把原概念测试迁为 `test_report_larger_than_eight_mib_is_written_completely`：实际构造并写入 **>8MiB UTF8 合法报告**，逐对象比较完整反序列化结果，既有必需 case/来源/引用字段及新增 trace、False/None 全部不丢。

没有删除/跳过测试，也没有重新造常量或大小门槛。补充两种真实编码失败（非 finite、不可 JSON 对象）仍拒绝并保持旧报告字节；真实目录冲突使写入抛 OSError，不返回“已保存”，原目录 sentinel 保留；相邻独立 attempt 不覆盖控制保留。

## 实际验证

- 单独原样复现旧失败：**1F/0.34s**，准确重现 AttributeError。
- 仅相关完整性、两项编码、真实 I/O、attempt 边界：**5P/0.64s**。
- 一文件 Ruff 通过。`tools/narrative_g2_replay/report.py` 前后 SHA 相同，本次没有发现须改产品的 writer 故障。
- 不跑 211/全 Unit，不读真实原件/密钥，不调用模型或收费，不碰 RF/invest、CI/hooks、主 PWF、Git。

版本 SHA、JUnit 与控制台在同名 JSON。其它七条核心 CI 失败仍由原作者处理，本报告不冒签整个远端 CI。

自有 `tmp/r7t-7aa56b` 初始 absent，收据保存后已按精确绝对路径/无 reparse 核验清理9文件、8,455,202逻辑字节，恢复 absent；完成 STOP。
