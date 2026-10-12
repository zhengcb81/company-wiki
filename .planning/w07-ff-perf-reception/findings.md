# Findings

## ROOT verified common causes and fixes

Exclusive per-attempt compact caches replace unsafe reuse of existing pc; independent attempts cannot alter/delete each other's cache. Final proof merging retains full worker groups and cannot overwrite failed or incompatible byte proofs. Metric failures cannot bypass cleanup, and repeated communicate failures reap the child. Seed summaries must match schema/cardinality/order/tag/request, not silent zip truncation. Original handlers/oracle/limits remain unchanged. One old cache test is strengthened to require exclusive ownership while preserving sentinel/restore assertions.

ROOT first full run28PASS/13PARTIAL at130.5777s revealed our own overconstraint: two independent catalogs may have different logical alias counts while retaining the same byte hash and one physical original. Removed only alias-count equality and added a behavioral counterexample RED→GREEN. Final225PASS4.92s; fresh original41PASS99.9624s, zero oracle findings,26 unique proofs (g1=15/g2=12), all restore facts true; compact longest pyc214chars. Summed child timings overlap and are not batch wall time. Scratch peak unmeasured, not invented.

Frozen author inputs/14 handlers and production/WIP metadata unchanged. ET additional53PASS21.88s. Both attempts and raw request/response/fixture/usage evidence retained in one490060-byte ZIP. Independent replay of unchanged oracle returns41 cases/zero findings. First sandbox-temp extraction failed with WinError5; normal allowed temp replay succeeded after correcting ROOT replay's artifacts subdirectory. These helper errors do not alter runtime acceptance or oracle.

Author claims18 focused+195 original tests; final41PASS/90.29s,26 final verified proofs, zero paid calls. Reported common causes: repeated ten ensure startups; Windows mirrored pycache paths over260 silently skip caching; final proof starvation; transport exceptions leaving children; gitless dependencies misreported as parentHEAD. Adds two isolated worker groups and same-clock10s final-proof reserve.

ROOT initial code review: OwnedAttempt.cache uses fixed owned_parent/pc and can reuse a pre-existing directory; need behavioral check that caches never modify original sentinel state or interfere between separate attempts. Main FF4167dac, main ETc91f5f5; ETd0ac42c6 and FF2d380a05 still unpublished. Need inspect ET commit ancestry before merge. Fixed input was repaired with three ET test seam files from pinned Git blobs; verify actual source commit bytes rather than requiring a new permit.

## 2026-10-11 W07-FF-PERF ROOT 最终接收

W07-FF-PERF已完成ROOT接收：原41场景全PASS/99.9624s、零oracle findings、26最终原文证明，原30/180秒上限与case/期望不减；225集中绿、ET53绿。FF main/origin/main64b4d29、ET main/origin/main d0ac42c6已正常发布，FF精确CI38170433893状态成功；ET没有配置workflow。两运行文件×两物理FF技能副本同步、各5实际安装后边界绿；三仓配置体检绿，非选文件元数据和原WIP保持。Audit已接收安装；RF工具已发布8dc26710/精确CI成功，整卡仍缺五组组合覆盖。W04已本地并线7a0b702a但正常push18FAIL，远端仍5c07f47c；ROOT后续W04共因→G2→G4→G5。目标工具当前paused，本次仅完成用户授权的接收，0付费调用。

共因修复：Windows长路径重复编译/重复准备与proof饥饿由作者统一解决；ROOT补独占attempt缓存、proof失败不可覆盖/完整worker证明、子进程reap、异常清理和seed完整序列。ROOT自己的逻辑别名数过约束有反例修复；首轮28/13记录保持，最终原41重跑全绿。两轮原始证据仅490060-byte ZIP，隔离重放oracle零发现、自动恢复。长矩阵手动大节点；轻量测试走同一正常push/CI，未新增人工门禁。

证据入口：company-wiki/.planning/w07-ff-perf-reception/publication.json、acceptance.json、offline-evidence.zip、replay_evidence.py。工程绿不认证真实供应商可达、来源真值或研究质量。预算母账保持413778tokens/334463µUSD+2764FXhold，累计$20/200万tokens。
