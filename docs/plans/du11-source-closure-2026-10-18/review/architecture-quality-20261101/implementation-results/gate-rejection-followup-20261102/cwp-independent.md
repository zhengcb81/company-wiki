# CWP27：输出与历史元数据许可整改独立审查

结论：**PASS_ENGINEERING_SCOPE**。13 个源文件、14 个测试/测试支持文件，审查前后 27 个 SHA 完全等于作者冻结 manifest。作者报告 JSON SHA：`16a3a1f370a02778b86aa4923cce52fcd2a617468de5bcb59539b62c283a0b97`。本审查者未写这些源文件、测试、主 PWF 或 Git。

| 项目 | 实际边界及独立结论 |
|---|---|
| CWP-GATE-01 | schema、指令和 decoder 同步去掉 20/40、per-task 2/6、280 字符的第二许可；动态引用仍绑定实际 pinned selection。新 47 条长限定原话完整保留，坏 basis 仅丢弃该条并 needs_review，未知 task 仍拒；task 的两个真实成员闭合均保留。43 条大语言输出在缺资源时仍 unavailable、错引用仍 uncertain，不冒 compatible。 |
| CWP-GATE-02 | 明确用户提供的本地文件/stdin 读完整后进入同一 schema/API；超旧尺寸的坏 JSON/错 schema 诚实拒绝，backend 调用 0。作者已有 277KB batch 与 420KB evidence 正控未被删断或换成假保存。 |
| CWP-GATE-03 | audit/location 改 rowid keyset 分页，128 是 I/O 页而非总量许可；同一个 LocalReadBudget 向 reconcile/restore/CAS/verify/official 传递。独立 133 次真实退役/恢复跨过分页边界，133 个 audit ID 无漏项、原文不变；同一 140 entries 额度第二次观察真实耗尽，不返回部分快照。 |
| CWP-GATE-04 | 长而合法的模型/adapter/prompt 标签可精确 canonical roundtrip，空白/坏 SHA 仍拒。实际假 HTTP 保存后重复采用只有 1 POST、1 reservation、73+19 tokens；改 request 不会重发。长未知历史协议可查看，不获执行支持。 |
| CWP-GATE-05 | content_bytes 是实际测量诊断，不再以 128KiB 后置否决。实际 150000 字符假 HTTP 长度截断错误在 saved replay 中保持 MODEL_OUTPUT_TRUNCATED/已知 usage/仅 1 POST；bool 和负数诊断仍拒。 |

阅读了全部源差分及变动旧测试：狭窄 archive helper 只移除原 maxItems20/maxLength280、替换明确旧指令片段和 advisory marker；原 gzip/base64/付费 fixture 字节与 SHA 未改，source/material/reference/HTTP 字段仍逐项相等。input/schema/instruction/decoder 身份真实变化，未伪造旧版本一致或缺失的 paid input hash。计划里历史目标数只保留为明确 advisory，不是结果许可。

独立执行 12 个 case：初次 9P/3F，失败均为独立探针夹具错误（误认 task 单成员、引用不存在的 enum）；修正后长文本/局部坏引用 1P，metrics 夹具仍缺 3 个必需字段产生 2F；补齐合成零测量后 2P。全部初始/中间失败、探针源码、最终成功证据已保留，**未把夹具问题称为产品缺陷，也未宣称最终单次重跑 12 条或作者 354 条**。过程没有改作者实现来迁就探针。

可进入 ROOT 正常工程发布节点；本报告不签完整 CI、真实 H1、真实摘要、缓存恢复或 RF 实际采用。没有真实原件、供应商、模型、下载或密钥调用。自有 `tmp/cgir-218a` 初始 ABSENT，归档证据后清除 27 个合成文件 / 5,747,771 逻辑字节，最终 ABSENT；真实原文和模型缓存删除 0。完整 27 SHA、各检查理由、实际日志/JUnit、错误与清理在同名 JSON。
