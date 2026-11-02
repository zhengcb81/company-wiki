> R7更新（2026-11-02）：本页为R6历史过程记录。旧观察器保留300KB/16KB的设计已被用户明确取消，当前完整表示方案及最终独审见[R7-ROOT-observer](R7-ROOT-observer.md)与[R7-ROOT-independent-r2](R7-ROOT-independent-r2.md)。恢复实施只读主CURRENT_STATUS/HANDOFF，不照旧限额施工。

# 来源验收观察器：持久、有限、可复现

当前source runtime为fa8ef38e，T3工程已独审/精确完整CI41385431656通过并本地主线；未签真实C。H1 v3单次真实调用因旧末端300KB guard丢收据，见C-source-v3-observer-failure，未知结果不补造。

原一次性runner/checks迁至tools/source_case_runner.py、source_case_checks.py，复用pure source_case_receipt；历史路径只薄shim/manifest数据。canonical入口`python -m tools.source_case_runner --manifest CASES --case ID --output RECEIPT`，无公司/市场/物理资料目录路由硬编码。CI和precommit只将三tool纳入原Ruff范围，无新阶段/逐小节点测试。

保持300KB/90s/16M/112。原12/9 oracle及当前引用原始unit excerpt、源/DB/runtime前后证明保留；重复span正文改长度/SHA，大debug明确omission/digest，不拿摘要冒原字段。必需项仍超cap/不可JSON时显式OBSERVATION_INCOMPLETE、source_status及完整性checkpoints，不把源失败改成功。源与观察器代码均绑定。

独立小checkpoint覆盖RUN_START、SOURCE_READY、原件打开前和RESULT_READY；编码失败仍有最终未完成收据和可恢复checkpoint。父超时保留子进程已提交结果，不覆盖它；读源前没有新材料许可。

独审R1发现exists→write→replace首次提交竞态（1F7P），ROOT另固化first/owned两变形2F0.79s。首次改为同目录atomic no-clobber link；既有owned checkpoint在pending fsync后再核当前hash才replace，first run claim保证遵守工具协议的不同进程不会共同拥有同一路径。原子replace失败仍保旧checkpoint；不创建全局锁库/权限/人工JSON。R1历史不改。

另外冻结target的结构context直接从既有producer tree/per-target maps投影，不依赖target被选中；不重新推断主体。缺/循环/重复/过深parent不能变完整，保存exact diagnostics与对应原始intro excerpt，永远标结构观察待语义审查，不自动actor PASS。

实际测试：编码16RED→18P；集成最终29P4.54s（合成/真实子进程缺config负控，无原件）；R2只新失败和结构/旧原子控制11P1.24s，未重29/原件。UUID短tmp均核验恢复absent；2RED静态tmp/osred未留初始清单，cleanup NOT_VERIFIED保留，不猜删。真实半年报只在新观察器增量独审后单例重跑；本节点0收费/下载/原件写入。
