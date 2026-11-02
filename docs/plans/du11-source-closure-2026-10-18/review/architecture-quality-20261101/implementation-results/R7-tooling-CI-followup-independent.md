# R7 tooling CI 旧 oracle 独立增量审查

结论：**PASS**，仅覆盖本次一文件测试合同迁移，不代替完整 CI。未发现需返修的问题。

作者报告 SHA `7a13b9615937b332c13ea2c642d26717edb993d650749825ce7e65acd4e45078` 已核对；测试文件 SHA `446c23dc5e7126e1f9485291c523385b31cb7f0ae18b477f44a01ff9a8003834`、writer 源码 SHA `048c386c2965cf8a43dc76a3f5c2aaa9844e4b7bfc6cfaa6e72be910ebbd4911` 在独审前后均匹配。没有写任何产品代码或既有测试。

从真实 `bd911a2b` Git 基线逐函数比较 AST：**38 个共同函数完全不变**。旧 `test_report_may_not_exceed_eight_mib` 由实际大结果完整保存正控替代，新增编码错误和真实目录冲突反控，没有删掉原来源/必需文种/引用回放/第二轮复用/未清理不得 PASS 等检查，没有新增 skip。Git 旧 blob 与作者旧工作区 SHA 的差异已证明只有 LF/CRLF 转换。

独立新增 **3P / 0.28s**：

- 使用真正多字节中文/emoji，生成超过 8 MiB 的 FAILED/PARTIAL 报告；完整原始对象、必需 unit/span/locator/SHA、False、None 和 trace 均保留，输入无修改，未把失败状态改成 PASS。再次创建 attempt 不会覆盖原报告。
- 嵌套 Infinity 编码错误拒绝，之前报告字节不变。
- 循环 JSON 对象编码错误拒绝，之前报告字节不变。

作者新增的非 JSON 对象、NaN、目录写冲突测试及现有 attempt 反控还在，绑定作者 5P 原收据；独审未重复其完整文件、211 或全 Unit。writer 使用 `allow_nan=False` 且先完整编码后打开文件，因此编码失败不会覆盖旧报告；真实 OSError 不被捕获成保存成功。本次不声称一般中途磁盘 I/O 失败具备原子替换保证。

测试全为合成资料，零原件、模型、API、密钥、配置、RF/invest、全局安装或 Git 写入。自建 `tmp/r7tool-independent` 初始 absent，源码归档到 JSON 后删除恢复 absent；pytest 实际宿主 basetemp 的 hook 也确认 removed=true。同名 JSON 记录精确源码/收据哈希与清理。

可由 ROOT 正常提交、推送并以实际远端 CI 收口；本线 STOP。
