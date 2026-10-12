# ROOT W06-FF-MATRIX 当前发现

2026-10-11最新：固定CaseSpec工具195PASS、独审28/28；冻结CWP来源修复191PASS、独审13+1，原41真实离线公共入口回放40PASS/1FAIL，164.62秒，scratch恢复、3生产配置SHA和真实密钥stat不变。最后call_past_cutoff：ET实际过滤2027-06-01晚于2026-12-31的电话会，却只返回not_found/candidate_count=0；FF转为provider_unavailable，截止日具体原因丢失。没有误接收未来资料，但诊断不满足原合同；须修共用结果边界，不修改原expectation。证据root-matrix-replay/，独立根因调查cutoff-diagnosis/。

真实联调41case为19PASS/21FAIL/1PARTIAL。九份三市场2024财报由真实CWP公共ensure入库，同期复用正确；缺2025/2026时供应商未启动，多数ET场景受primary失败前置影响，不能判为ET内部错误。

已独立确认CWP共因：resolver排除旧期后，local_reconcile把同实体同类型来源重新纳入；canonical已验入库事实没有steady correction assertion，缺patch被无条件当目标缺口，阻断新下载。需在所属来源层统一可信事实和相关性，保留目标字节/身份/期间/as-of及预算；不增加人工签收或许可。

工具最终独审另发现3反例：删22失败案例并同步自报集合、删cutoff expected、把CN请求改HK并重算请求SHA，均可假PASS。ROOT要求单一CaseSpec权威、完整请求和覆盖核对，不能只加3字段特判或仅数41条。旧报告、ZIP、freeze及输入SHA保持。

完整证据：intake/初始错误；fix/冻结34测试与真实矩阵；independent-final/权威缺口；root-cause-review/生产根因；新修复 fix/case-authority/ 与 producer-scope-fix/分别归属不同目录。

## 2026-10-11 当前大节点

工具及CWP来源已正常发布/精确CI成功。cutoff修复实际原因正确，但原41新attempt因180秒批次截止不能认证，原2/31/8及无fresh proofs保留。另独审发现三例malformed stdout丢实测usage同根，集中修复和必要复验后，错开重型测试按原41限额新attempt。

## 2026-10-11 W07-FF-PERF ROOT 最终接收

W07-FF-PERF已完成ROOT接收：原41场景全PASS/99.9624s、零oracle findings、26最终原文证明，原30/180秒上限与case/期望不减；225集中绿、ET53绿。FF main/origin/main64b4d29、ET main/origin/main d0ac42c6已正常发布，FF精确CI38170433893状态成功；ET没有配置workflow。两运行文件×两物理FF技能副本同步、各5实际安装后边界绿；三仓配置体检绿，非选文件元数据和原WIP保持。Audit已接收安装；RF工具已发布8dc26710/精确CI成功，整卡仍缺五组组合覆盖。W04已本地并线7a0b702a但正常push18FAIL，远端仍5c07f47c；ROOT后续W04共因→G2→G4→G5。目标工具当前paused，本次仅完成用户授权的接收，0付费调用。

共因修复：Windows长路径重复编译/重复准备与proof饥饿由作者统一解决；ROOT补独占attempt缓存、proof失败不可覆盖/完整worker证明、子进程reap、异常清理和seed完整序列。ROOT自己的逻辑别名数过约束有反例修复；首轮28/13记录保持，最终原41重跑全绿。两轮原始证据仅490060-byte ZIP，隔离重放oracle零发现、自动恢复。长矩阵手动大节点；轻量测试走同一正常push/CI，未新增人工门禁。

证据入口：company-wiki/.planning/w07-ff-perf-reception/publication.json、acceptance.json、offline-evidence.zip、replay_evidence.py。工程绿不认证真实供应商可达、来源真值或研究质量。预算母账保持413778tokens/334463µUSD+2764FXhold，累计$20/200万tokens。
