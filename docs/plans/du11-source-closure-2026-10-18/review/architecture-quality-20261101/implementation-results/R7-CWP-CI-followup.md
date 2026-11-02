# R7 CWP CI 七项合同迁移

状态：**5 测试文件冻结，交 ROOT 独立增量审查/正常发布**。生产源码零修改；已发布 core 的 25/25 源码 SHA 与 `R7-core-implementation.json` 一致。原 CI `41428479689` 的 8F 证据保留；本线只负责其中七项，不代替另线的 W08 报告修复，不宣称完整 CI 已绿。

## 真实 RED 与共同根因

正常宿主精确执行七个原 node：**7F / 3.05s**，无平台异常。对应的五个测试文件仍按退休门槛、旧默认分配或旧重复验真位置断言；本次没有恢复这些阻断，也没有删掉仍有意义的负控。

| 原失败 | 新合同与保留的反控 |
|---|---|
| 默认 draft 必须 ≤56 KiB 且部分卡 deferred | 参数化为默认 None 与显式 56 KiB。默认完整保留 13 张卡、77,912 字节及最后一条重要材料；显式额度仍整体分配、保高优先级末尾材料及所有 task，超额不截原话。 |
| 399 行 execution 必须因 >32 KiB 被拒 | 合法大收据完整 wrap/parse/extract，399 行顺序和 source/model incomplete 状态保留。原坏类型、plan/task 绑定、重复身份、未知字段等负控完整保留。 |
| rank 三例假定默认 56 KiB 会筛掉 96 张卡中的一部分 | 默认 96 张完整送达，原文不改。真正“未传入的任务”与“剩余源内容未处理”改用当前源 owner 标出的 unresolved 第 96 个 scope；仅 95 张可送达，伪排未传入任务仍 RANK_INVALID，全部传入项排完仍 RANK_INCOMPLETE，96 行和原 unresolved scope 不丢。 |
| 70,006 字符合法 claim_id 必须 RESULT_SIZE 失败 | 改为真实 handler 大合法结果正控，全部 claim/标识及 native usage 保留，最终响应 hash 正确、可完整序列化回读。13 类真实 JSON/语言/来源/引用/闭包/路径失败及 usage 负控全部保留。 |
| 构造 VerifiedContent 后改 data，要求 upper guard 再整 SHA | worker 对已经验证的返回值只作身份配对，generation policy fingerprint 不是许可。新增 5 类错误 source/document/SHA/size/实际 data 长度仍拒；实际同长字节腐坏由 reader owner 的真实读取测试验证，不靠 consumer 重新 hash。 |

资料准入与全文完整度没有混淆：无隐式 byte cap 表示已选材料不被任意尺寸丢弃，不代表全文读完。96 张默认样本仍保留原 `selection.status=partial`、20 个 omitted candidates，request 明示 `selected_source_tasks_only`；真实 unresolved scope 的 source/model coverage 继续 false。没有把“全部已准入任务发出”升级成全文或语义完整。

## 验证与一次夹具纠正

- 一次受影响集合：五个完整修改文件 + 已有 verified-source operation 邻域，共 **112P / 1F / 11.42s**。原语言、JSON、数值、闭包、任务绑定、source identity 及单 SHA 负控都在这个集合内执行。
- 唯一新正控 F 是测试将 provider 的 `e1` alias / draft 状态直接等同 decoder 规范结果；正常路径会解析为真实 span 并保留 needs_review。修正为与正常小 baseline 的规范化结果对照，只改变长 claim_id，保持原 decoder 规则，不修改产品。
- 随后仅重验此一项 + 两个真实 source-reader 合同 node（参数化为 4 例）：**5P / 5.74s**。这些真实读取分别证明原件字节返回、稀疏辅助元数据不挡合法读取，且同长原件替换为 OTHER 后拒绝 `no_verified_location`。没有重复 113、325 或整个 Unit。
- 五文件 Ruff 通过。关闭非必需插件后出现既有 `asyncio_mode` unknown warning，非本轮产品缺陷。

新大小正控不检查任意生产默认值：56 KiB 只在显式预算 fixture 中传入；32 KiB 和 64 KiB 只作为“合法结果已超出退休阈值”的样本证明，不成为新的 permit。

## 清理与后续

真实读取测试使用显式独占 basetemp，现有 hook 报告 removed=false。测试进程退出后只读核对该日志绑定的唯一绝对目录、预期父目录及无 reparse，再清理其 12 文件 / 1,511,480 字节，确认恢复 absent；清理收据已入 JSON。post-model 既有 autouse fixture 保原始合成文件、sentinel 与生产配置 SHA/size/mtime，并自动移除自己的 TemporaryDirectory。本轮无真实原件、配置、密钥、供应商或收费调用。

同名 JSON 记录全部 5 文件 SHA、25 源冻结身份、原 8F 注释、7F 完整 trace、112P1F 和 5P 收据及 argv。ROOT 负责独立增量审查、提交、推送；只有远端完整 CI 的新实际结果才能关闭该发布节点。本线 STOP，不改 Git、主 PWF、全局安装或其它仓库。
