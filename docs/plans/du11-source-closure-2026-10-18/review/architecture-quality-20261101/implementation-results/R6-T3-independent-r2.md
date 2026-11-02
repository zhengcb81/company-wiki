# T3 增量独审 R2

结论：**PASS_T3_ENGINEERING_INCREMENTAL**。上次 P2 `T3-A-01` 在当前工程范围闭合；本轮未发现新产品 P1/P2。ROOT 仍须结合精确候选完整 CI 绿正常整合。本报告不签真实 H1、摘要/cache/RF 或整个 PWF 完成。

审查人 `/root/rectification_review_a`，2026-11-02；实测提交 **`fa8ef38ee0e6e0cd659ad602df5844cc9571ebb9`**，工区 `C:/Users/郑曾波/Projects/company-wiki/tmp/w23-r6`。本次 4 个增量文件与其余原 T3 冻结文件组成 **21 项 raw SHA**，开始/结束全匹配、Git LF blob 全匹配。返修报告 SHA `36961e6294a76bb6b354c174d7ebe9a5ba12ce5aac0c2160f8da67dd39b1f3fa`。逐项身份与复现见同名 JSON。

## 实际验证

正常宿主 Python 3.13.9 / pytest 9.1.1，候选 config/rootdir/confcutdir 显式绑定；**11 passed，1.79 秒**。只复原 R1 的最小失败函数，未跑其余旧 6 项或 82/84/整仓，没有原件、下载、OCR/LLM 或收费调用。

- **R1 原函数未改**，从历史报告精确恢复执行：b23、b24、b25、b26 现均 partial/context_blocked、不作 material anchor；真正新标题后的 healthy_body 仍不 blocked、仍为 anchor。
- 73 个成员到新 note 的边界验证 exact suffix 全部被阻断、诊断每批至多 24 IDs，新 note 保自己的 intro，后续健康标题范围可用。
- 页间缺口与实际 column/layout-order 冲突都保留首个失败目标及后续原始成员的未决状态，不因几何重排将它们漏到健康标题后。
- 工作预算不足时继续使用原 WorkBudgetExceeded，不能在未付尾部扫描/输出成本时发布伪完成范围。没有提高 24 或其他全局限额。
- 独立构造短本地 token、中文 opaque block token 的字符范围证明均有效；不等 token、空 token、范围重叠和异源四个负控均拒绝，原输入不变。来源 SHA 验真仍归 parser/source，局部连续性不另造长度许可。

## 共同 owner 修复判断

`source_scopes` 现在一次有序、计费的状态机处理局部范围：cap/缺 proof 只停止正向成员扩张，unproven 状态延续至真实 marker、heading、source/role/turn 或结构边界。按原始序列保守保留未证后缀；`layout_next` 仅用于拒绝冲突，仍需已有原生 member 或 physical proof 才有正向边，不将 ordinal 作为业务或范围证明。不按 note 排序或重扫全仓。

分批 exact IDs 继续经既有 semantic partial/material context_blocked 消费链传播，未改消费者补偿规则。旧四项 CI 失败的局部 block identity 64 长度门也已撤掉：同 token、同 source、顺序、role/turn、真实非重叠范围约束保留，恢复旧接口而不越层重验原件 SHA。

作者四份原日志按 Windows CRLF 重建后 SHA 全匹配：原四 CI RED、新五项 3F/2P、新五绿、最后九绿均保留，不把分段结果合成一次大组通过。JSON 的 LF 显示文本不等于原日志 raw bytes，核对时已明确处理换行序列化，未认作产品失败。

## 历史、清理与范围

R1 `R6-T3-independent-r1.md/json` 保持 `8782050b` 的 NEEDS_ROOT_FIX 历史，本轮单独签当前返修。原 6 份 tests-first 当前仍在 w23 tracked 文件中并匹配 manifest；本轮不依赖 ROOT 已清理的旧 r2 临时副本。

唯一 owned 目录 `C:/Users/郑曾波/Projects/company-wiki/tmp/u2` 初态 absent；核准确绝对路径及无 reparse 后只清理该目录，最终恢复 absent。复现函数、脚本、JUnit、实际 target 观测与 SHA 完整留在报告。未写产品/旧测试/Git/主 PWF/配置，未建索引。

**STOP**，交 ROOT 精确 CI 与正常并线。仍不签真实资料/模型、缓存恢复、RF 采用或总目标。
