# W05-AUDIT-LOOP 最终独立复验

**结论：PASS_WITH_SCOPE。** 原 6 个纯反例及 2 个临时目录反例全部通过；本轮范围内没有未修的 P1/P2。

候选：`C:/Users/郑曾波/Projects/_harness_worktrees/w05/audit-loop-root`

核心 `pool_progress.py` SHA：
`821221f58fb38fd601a22cad6626f402eab8dcac0bfe6395b591ef48bad7792f`

## 原反例复验

| 检查 | 真实结果 |
|---|---|
| 缺报告引用 | 不计 clean，streak=0，证据列表不含 null |
| 旧 run / 迟到版本 | 旧 run 不入槽；reviewer-2 可以绑定 initial；迟到有效报告保留 run_started 旧版本，建议同公司重跑 |
| 未知费用 | outcome=unknown 及 known/null 均继续对账、resend=false；3 个合成完整轮次仍 streak=0 |
| 历史主要问题及复测 | 3 clean 不吞旧未修 major；无 evidence_ref 不关闭复测 |
| 最后一家公司 | 提示 advance_round 收尾；只耗尽 2 家池不冒称通过 |
| 活锁 / ABA | 31 秒旧 mtime 不抢活锁；旧持有者重复 release 不释放新持有者；实际释放后 1.507ms 获锁 |
| plan 输出覆盖状态 | 拒绝占用路径，状态 SHA 前后相同 |

原始结果保存在 [final-pure-probes.log](final-pure-probes.log)、[final-tmp-observer-error.log](final-tmp-observer-error.log) 和 [final-plan-probe.log](final-plan-probe.log)。

## 源码与文档

读取新增 19 项回归和 3 份技能文档，核对 run/执行 attempt 边界、review 输出 attempt、run_started 冻结版本、全部 null 费用对账、旧责任保留、内核锁、CAS/幂等及 init/plan/migrate 原子 create-only。没有重新跑集中全集、真实杀 holder 或 E2E。

冻结清单只有 E2E 合成 fixture SHA 被 ROOT 更新，核心及合同均保持冻结。已实读 ROOT 最终 E2E 两份收据：48 步、86.696 秒、PASS、scratch 恢复 absent、零外部调用。该收据明确是合成恢复协议测试，不是公司研究通过。

## 真实局限

进度工具仅记录并建议下一步；非空引用不证明报告真实、四个角色实际独立或预测数字正确。协调员仍须实读证据。这里不证明真实公司研究质量、所有市场路径或外部收费 exactly-once。

独审观察脚本曾误用不存在的 `STATE_SCHEMA` 常量，退出 1；产品此前已拒绝覆盖。这份小失败日志保留，owned scratch 已核 absent；只修观察比较并补跑 plan 别名成功，未修改产品。

旧 FAIL 的 8 份文件及 manifest、旧交付树 9 个输入均按 SHA 保留。所有新文件使用 `final-*`；源码、共享 PWF、安装目录零写入，网络/LLM/费用为零。本轮 STOP。
