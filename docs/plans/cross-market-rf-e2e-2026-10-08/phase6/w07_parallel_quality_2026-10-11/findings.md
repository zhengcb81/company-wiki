# 调查结果

- 三包均有实际独立 worktree；分支、commit 和 FF 代码依赖见 prepared-roots.json。
- RF 已有单模型、期间、校准测试；新包只补原生 draft 引擎的组合反例和可复用报告，不修改 core。
- Audit 已有 W06 数字度量审查；新包只补 A02/A05/A06/A08/A10/A13/A17/A18 的可观察风险诊断，不重复算术、来源身份验证或预测。
- FF 旧 41 为 40PASS/1FAIL、164.62 秒；修 cutoff 后两次结果分别 2PASS/31PARTIAL/8NOT_RUN、182.86 秒和 1PASS/27PARTIAL/13NOT_RUN、184.54 秒。底层 cutoff/usage 的最终集中复验 7PASS；当前阻碍是批次准备/进程/最终证明共同超时，不是 31 个产品缺陷。
- FF 以 2d380a05 为基线，ET d0ac42c6/CWP d75f0d42 的 code-only 快照已准备；这些来源修复尚未因此发布到主线。
- 详细只读候选复核在 candidate-review.md。当前范围不需要真实金融数据或 LLM；不能据此认证经济结论。

- Audit交付34b5c8ee/e3206880；ROOT独立TDD及agent试读发现引用存在不等于可解、全局合集丢scope、period-only actual假覆盖。通用native索引和scope/日期/数值修复后正常接收e7c92577、资料2c494913在Audit main；作者提交保持，旧断言保持，仅修默认synthetic builder悬空依赖。90PASS+4子案例，13真CLI，两安装入口及28×2 SHA绿。0网络/付费，不新增许可或预测阻断。

## W07-RF-MODEL ROOT 接收结果

工程工具接收、整卡部分覆盖：作者d282c9d/72d0ced保留，ROOT22RED/1PASS暴露误报共因；系统修复异常分类、per-case真实request/result、未知/空比较、完整清单、CLI/readonly/清理状态和原目录恢复。原assertions不变，最终36PASS/4.19s，原16向量11PASS/5REJECT_OK、三实际CLI0/2/0，1.394767s。正常main/origin/main8dc26710，推送前390PASS＋36subtests/32.07s，精确CI38168556914成功；150WIP文件SHA保持，不安装工程工具。

仍缺CNY/HKD、并购控制/跨FY、联合量价、累计/净额/防双计、future actual/WAPE五组覆盖，不能称整卡COMPLETE，详[后续](ROOT-rf-remaining-coverage.md)。ROOT留证只存单份压缩native JSON与摘要，当前约330KB。0provider/LLM/费用；来源真值/买方经济判断仍未认证。CWP母PWF提交可在本地保存，远端发布仍待W04旧18失败修复，不以RF CI代替CWP发布。

## 2026-10-11 W07-FF-PERF ROOT 最终接收

W07-FF-PERF已完成ROOT接收：原41场景全PASS/99.9624s、零oracle findings、26最终原文证明，原30/180秒上限与case/期望不减；225集中绿、ET53绿。FF main/origin/main64b4d29、ET main/origin/main d0ac42c6已正常发布，FF精确CI38170433893状态成功；ET没有配置workflow。两运行文件×两物理FF技能副本同步、各5实际安装后边界绿；三仓配置体检绿，非选文件元数据和原WIP保持。Audit已接收安装；RF工具已发布8dc26710/精确CI成功，整卡仍缺五组组合覆盖。W04已本地并线7a0b702a但正常push18FAIL，远端仍5c07f47c；ROOT后续W04共因→G2→G4→G5。目标工具当前paused，本次仅完成用户授权的接收，0付费调用。

共因修复：Windows长路径重复编译/重复准备与proof饥饿由作者统一解决；ROOT补独占attempt缓存、proof失败不可覆盖/完整worker证明、子进程reap、异常清理和seed完整序列。ROOT自己的逻辑别名数过约束有反例修复；首轮28/13记录保持，最终原41重跑全绿。两轮原始证据仅490060-byte ZIP，隔离重放oracle零发现、自动恢复。长矩阵手动大节点；轻量测试走同一正常push/CI，未新增人工门禁。

证据入口：company-wiki/.planning/w07-ff-perf-reception/publication.json、acceptance.json、offline-evidence.zip、replay_evidence.py。工程绿不认证真实供应商可达、来源真值或研究质量。预算母账保持413778tokens/334463µUSD+2764FXhold，累计$20/200万tokens。
