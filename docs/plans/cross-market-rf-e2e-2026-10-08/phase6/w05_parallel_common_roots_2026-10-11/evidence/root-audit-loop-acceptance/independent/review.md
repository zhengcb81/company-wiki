# W05-AUDIT-LOOP 独立大节点审查

**结论：FAIL，需由 ROOT 在独立集成树修复后再验收。** 交付源码保持冻结：pool_progress.py SHA `03f0d33b9233aac894d415e26406e4ccec22caa2b955adcb678856ca5836ce51`。

## 实际范围

只读交付树、施工卡、契约、核心源码和测试。6 个纯 reducer 场景、2 个独立 scratch 场景；没有重复 201 单元测试、交付 E2E 或 manifest 校验。它们由 ROOT 负责。0 网络、LLM、provider、费用；不改 producer、旧报告、共享 PWF、安装或 W06。

## 5 个根因，6 项失败反例

| 问题 | 实际结果 | 最小修复方向 |
|---|---|---|
| P1 结论缺出处或未绑定来源 | 4 个 PASS 无 report_ref 仍计 clean；另有 run-old 的旧版结论被当前版本盖章，用来计 run-new clean | 在完成 handoff 入口绑定适用 run/review attempt、真实版本和已有报告出处；缺少或未实读只诊断、不能计 clean |
| P1 对账尝试当成已解决 | outcome=unknown 后不在 pending_reconciles，cost=null 却建议 dispatch_executor | 分开对账尝试和未知费用解除；未解决持续 reconcile、resend=false，沿用原账 |
| P1 活写者锁被接管及旧 owner 误释放 | 活 PID 的锁 mtime 置31秒前，默认30秒使 B 获取；A.release 又删除 B 锁，C随后获取 | 使用短时内核锁或等价的有效所有权互斥，进程退出释放；不按年龄抢活锁 |
| P1 plan 覆盖 state | plan(state, obs, state) 返回 exit0，把进度 schema 改成 plan，后续无法读取 | 独立输出 create-only，拒绝输入输出别名；只有 apply 持锁替换活动 state |
| P1 旧复测无证据被勾销 | retest_done 未给 evidence_ref，填造 unspecified 并从待复测转为抽样达标 | 缺真实复测来源保留未完成状态；消费已有复测 handoff，不加人签 |

这些是数据一致性、证据因果关系和恢复协议的问题。修复不需要新增授权、身份审查或小节点签收。

## 一个 P2 进度建议局限

最后一家公司执行、四审和 expert 完成后，工具建议 no_action，仍只记 closed=2/streak=2。手工 advance 才关闭第三家并达到抽样条件。严格按建议运行的 harness 缺末尾关闭动作。ROOT 应统一末尾关闭建议和 action 契约；该现象本身没有冒称所有公司正确。

## 已确认的正向行为与诚实边界

- 只有两家 clean 时池耗尽会建议 no_action，未虚报达标。
- unknown 初次记账确实 cost=null、resend=false；旧复测在错误勾销前确实阻止达标。
- 工具只提出动作，不启动 agent/provider，也不建第二费用账或人工许可。
- 四角色标签不能单独证明四个原生 agent 独立；真实执行、审查质量和来源实读由现有 native harness/P7 记录证明。
- 锁反例是单进程多个 StateLock 对象，把文件 mtime 人工置旧来触发实际接管路径；没有声称真实等待31秒、杀进程或并发提交已经发生。
- 本审查是离线合成契约检查，不是实际公司收入预测验收。脚本 exit0 表示成功保留 FAIL 结果，不表示反例通过。

## 隔离、失败记录和收尾

第一次 sandbox TEMP 写 sentinel 遭 PermissionError，尚未进入锁/plan检查；原始错误保留，已知空 scratch 在 native 核验时已不存在。随后使用本报告目录内新 owned scratch 执行两个反例。sentinel SHA `4073b18801d9a2e0a120eb2f5c214379874acf6f18a7ac6071f289d29b0957e5` 初末一致，所有测试文件及 scratch 已精确移除。9 份输入 SHA 前后相同。

完整命令和原始输出见本目录 pure_probes.ps1/log、tmp_probes.ps1/log、failed_tmp.log、failed_tmp_cleanup.log；精确输入 SHA、具体状态和定位见 review.json、manifest.json。ROOT 后续隔离修复，本审查 STOP。
