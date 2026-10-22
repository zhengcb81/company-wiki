# W01 来源准备独立审查 — PASS（绑定最终内容）

> 收尾字节补充：原 155 PASS 仍绑定当时的原始 SHA；随后 `source_reader.py` 仅 CRLF→LF、`cli.py` 仅 identify 分支局部变量改名。当前字节的等价证明和 7 项窄 CLI 验证见[2026-10-22 补充审查](r1-w01-source-review-postprocess-20261022.md)，不冒称 155 项已在全部新字节上重跑。

**结论：PASS_ENGINEERING_CONTENT_BOUND。** 独立审查发现的 7 类问题均已由 ROOT 根修并复验。最终集中 **155 PASS / 45.66 秒**，包括 14 个审查者独立反例；9 份产品源码与两份反例测试前后 SHA 完全一致。该结论只覆盖 W01 来源准备工程，不代表 W03 新版正式摘要、W07 真实付费恢复或 RF 新 attempt 的研究质量已完成。

审查人 `r1_w05_rf_targets` 是 W01 非作者，只读产品；源码由 ROOT 修改。0 网络、下载、模型、安装和生产原件写入。最终源码 SHA、测试 SHA、完整命令及测试结果见同名 JSON 和 [最终收据](r1-w01-source-review-20261021/review2-after.json)。

## 独立发现与根修结果

| 问题 | 根因与修复 | 最终验证 |
|---|---|---|
| P1 IR 提及财报被当成财报原件 | 封面 owner 从任意位置关键字改为有界实际标题结构；真实 IR 标题可持久为 source-facts / investor_relations | 纯周期解析器拒 IR；实际 writer 可证明 IR 后合法不相关，不强制所有 IR 阻断 |
| P1 名称命中掩盖证券代码冲突 | 正文明确代码冲突优先，不能由名称子串覆盖 | 真实 PDF 正/负封面反例 |
| P2 同期间同发布日期猜最新版本 | 不按 provider/source ID 猜不同原文的 chronology | 同日不同版本保留 ambiguous |
| P2 混合已证/未知期间回退发布排序 | 只有旧全无期间证明路径保留既有发布日期兼容；混合未知不冒认最新 | 混合反例保留 ambiguous；available_by 不充当发布时间 |
| P1 错旧标签使真实 CN 原件消失 | 已有 CN 正文 owner 可以修复误标 HK/OTHER 的 sidecar；明确不相关原文仍排除 | 原件 SHA 不变、0 下载；之后已有证明禁止再加载身份库或解析 PDF |
| P1 generic unknown 被当空湖 | discovery 不吞来源证明错误；未知项每次重试仍可见，不能在目标 kind SQL 中丢失 | 连续 3 次重试始终具名阻断；已证 IR 则正常不相关 |
| P1 first-found 冒充 latest | 修复 prepare 已有命中与 discovery 首次命中两处早退；最新请求先做有限盘点，已持久完整 scope/date 只读元数据，最终所选仍真实读字节 | 空库旧/新、已有旧库新增、同期间修订、max4/21份历史有限推进、已有旧稿+新 unknown 共 5 个真实反例 |

## 最终检查范围

- `test_w01_counterexamples.py` 9 例、`test_latest_discovery.py` 5 例：独立测试最终副本在本报告同名目录 `checks/`，与实际执行副本 SHA 一致。允许 ROOT 复制到永久测试目录，仅改 helper 导入路径，不改断言。
- 既有 source availability、单一 source scope qualification、完整 30 例 single-intent/latest CLI/ensure、6 例 qualification E2E、local reconcile、qualification 单元，共 155 例全部通过。
- current_verified_open 保持真实 UTC、精确 ref/SHA/size/mime 绑定；不回填过去 as-of，known future publication 优先，publication 仍可为 null。查询不会创建观察或初始化冷库；显式 prepare 可做有限初始化。
- 文件名只排序，不作期间事实。增量登记保留进度，不靠扩大 16/256/4096 上限或新 cursor 库；已证元数据与最终原件验证仍归所属 owner。
- 未发现新增人签、private/public、授权 JSON、canary、第二预算/任务库或消费者物理根逻辑。
- CLI 顺带修复的 identity/optional_identity 变量和旧显式 entity 请求兼容，由完整 30 例已有合同覆盖；未新增必须 company-query 身份 DTO 的门。

## 失败证据与归因

首轮 6 例有 4 RED，作者修后通过；writer/generic 及 latest 的后续 RED 也保留，没有删除旧断言。原 120 例集中在沙箱环境下 119 PASS、1 个既有 artifact fixture 的初始 projection 为 retry_scheduled，未进入日期断言；相同 node 在 elevated 环境下 1 PASS / 1.78 秒。第一次窄复跑缺测试 helper 路径，是命令环境错误，已如实保留。最终在 elevated 环境一次跑完整 155 例全绿；没有修改测试让它通过，也不将环境现象伪称已查实某一 hardlink 调用。

## 清理与范围限制

自有 `.planning/r1w1v` 初始不存在；测试结束按绝对路径校验后删除 1,837 个合成临时文件、81,627,461 字节，恢复初始不存在。原始业务文档无下载、复制或删除。只保留约束清晰的小测试、日志/XML与 SHA 收据，不保留测试 PDF/数据库副本。详见 [清理收据](r1-w01-source-review-20261021/cleanup-receipt.json)。

没有本节点未解决的工程审查发现。ROOT 仍负责永久回归接入、正常提交/推送与精确 CI；共享引擎正式摘要、实际付费中断恢复、安装后的 FF/RF 消费及新 holdout 研究属于之后的节点，不能由本工程 PASS 代替。按最新收尾暂停指示，本审查不扩展新的实现任务。
