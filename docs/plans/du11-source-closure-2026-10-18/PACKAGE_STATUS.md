# 外包当前状态总表 — 2026-11-06

本表只汇总已审计的近期卡，**不是项目总完成率、所有历史卡总数或所有仓全部分支盘点**。机器表为[PACKAGE_STATUS.json](PACKAGE_STATUS.json)，主线只看[CURRENT_STATUS](CURRENT_STATUS.md)。工程接收、真实产品验收和整家公司研究是三种不同结果。

当前主线闸位：D4 按原范围 CLOSED，D5 全局解耦 ACCEPTED。CWP pathless 规范化文档 port、StockWiki 三入口、FF V2/V1 路由和真实本地样本的固定跨仓测试 18/18 通过，0 skip；最终独审 PASS。收据见 [ROOT D5 closeout](review/decoupling-recheck-20261104/root-d5-final/README.md)。主线下一步恢复 T4/SEM-QUAL-01；新版摘要、缓存恢复、RF 实际采用和公司循环仍 OPEN，详见 CURRENT_STATUS。

| 任务卡 | 已核状态（卡内范围） | 依据 |
|---|---|---|
| W09-RF-RESEARCH | MERGED_PUSHED_INSTALLED | [证据](review/r1-w09-reception-20261023/publication/publication-final.json) |
| W11-CWP-SOURCES | MERGED_PUSHED | [证据](review/r1-w11-reception-20261023/publication-final.json) |
| W13-CWP-GATES | ROOT_ADAPTATION_MERGED_PUSHED_CI_SUCCESS | [证据](review/pwf-reconciliation-20261031/package-observations.json) |
| W14-RF-CLEAN-CHAIN | MERGED_PUSHED | [证据](review/package-reception-w13-w15-20261024/receipt.json) |
| W15-AUDIT-PORTABLE | MERGED_LOCAL_NO_REMOTE | [证据](review/package-reception-w13-w15-20261024/receipt.json) |
| W16-RF-BASIS | MERGED_PUSHED_INSTALLED | [证据](review/package-reception-w16-w17-20261025/README.md) |
| W17-AUDIT-COVERAGE | MERGED_LOCAL_INSTALLED_NO_REMOTE | [证据](review/package-reception-w16-w17-20261025/README.md) |
| W18-CWP-HOLDOUT | TOOL_ORACLE_MERGED_PUSHED_PRODUCT_FINDINGS_OPEN | [证据](review/package-reception-w18-20261025/acceptance.json) |
| W19-SINA-STATEMENTS | CWP_FF_MERGED_PUSHED_INSTALLED | [证据](review/w19-reception-20261026/published-binding.json) |
| W20-AUDIT-CHECKPOINTS | MERGED_LOCAL_INSTALLED_NO_REMOTE | [证据](review/w20-reception-r3-20261029/SUMMARY.json) |
| W20-RF-ADOPTION | OBSERVER_TOOL_MERGED_PUSHED; ROOT_HUALI_ADOPTION_PASS | [证据](review/w20-reception-r3-20261029/SUMMARY.json) |
| W20-FF-REPLAY | MERGED_PUSHED | [证据](review/w20-reception-r3-20261029/SUMMARY.json) |
| W21-PDF-RUNTIME | ENGINEERING_MERGED_PUSHED_CANONICAL_C2_OPEN | [证据](review/w21-root-reception-20261030/PUBLICATION.json) |
| W22-CWP-ATOMIC-IO | ENGINEERING_MERGED_PUSHED | [证据](review/w22-w23-reception-20261031/summary.json) |
| W22-PDF-DEPLOY | ENGINEERING_MERGED_PUSHED_REAL_DOCUMENT_C2_OPEN | [证据](review/w22-w23-reception-20261031/summary.json) |
| W23-XIAOMI-OCR | TOOLING_MERGED_PUSHED_EMPIRICAL_REWORK_REQUIRED | [证据](review/w22-w23-reception-20261031/summary.json) |
| IR-REPORT-GENERATION | MERGED_PUSHED | [证据](review/older-packages-merge-20261031/receipt.json) |
| QA-RAG-SAFE-REBUILD | MERGED_PUSHED | [证据](review/older-packages-merge-20261031/receipt.json) |
| MC-OUTPUT-INTEGRITY | MERGED_PUSHED | [证据](review/older-packages-merge-20261031/receipt.json) |
| W23-OCR-R1 | LAST_KNOWN_READY_EXECUTION_UNKNOWN | [证据](harness_lanes/20261031/R1-setup.json) |

| D4-01 | MERGED_LOCAL_NO_REMOTE | StockWiki `23d84586`; no remote | [D4 closeout](review/d4-closeout-20261104/README.md) |
| D4-02 | MAIN_PUSHED | tested code `96713029`; current PWF commit `90c562ac` pushed to origin/main | [D4 closeout](review/d4-closeout-20261104/README.md) |
| D4-03 | MERGED_PUSHED | CWP master; included in `e7469d68` | [D4 closeout](review/d4-closeout-20261104/README.md) |
| D4-04 | MERGED_PUSHED | CWP master; included in `e7469d68` | [D4 closeout](review/d4-closeout-20261104/README.md) |
| D4-05 | MAIN_PUSHED | FF `bf7e1dab` | [D4 closeout](review/d4-closeout-20261104/README.md) |
| D4-06 | ROOT_INTEGRATED_ACCEPTED | CWP `e7469d68`; AUDIT code `2449df4a` + PWF `3589b69`, local only/no remote | [D4 closeout](review/d4-closeout-20261104/README.md) |
| D5-CWP-STOCKWIKI | ACCEPTED_LOCAL_MERGED | CWP `a28692a6`; StockWiki `6d1e40bc` (local master; no remote); ROOT run-6 `18 passed / 0 skipped`; independent final review PASS | [ROOT D5 closeout](review/decoupling-recheck-20261104/root-d5-final/README.md) |


W15等Audit仓无remote是已记录的发布边界，不是等作者未交付。W18交的是冻结/评分工具，不代签内容通过；W20-RF交的是采用观察工具；其后ROOT华利M8当前v6新版artifact有界实际采用及45独立检查已通过[新证据](review/mainline-closeout-20261031/p1-current/README.md)（先前v5原签收保留），不能由旧卡或此局部通过代签整家公司研究；W21/W22环境/部署/IO工程不代签canonicalC2。IR/QA/MC三包已并各自主线，属于非阻塞旁线。

小米OCR工具已接收，但原实证仅PARTIAL，R1仍最后已知READY、当前是否开工未知。原作者确做过模型推理，旧“0”只可能是ROOT该节点新增量，不应写成全项目从未推理。现有生产OCR继续可用，不等R1。

早期DU/DU2/P1–P4及DU3–DU9按各自历史接收范围结转到本主线；原卡/接收收据不改写。不因旧README、setup或handoff里READY/pending再发同一任务。剩余产品和公司责任以task_plan的P0–P3闭合，不继续按卡号增加串行尾巴。
