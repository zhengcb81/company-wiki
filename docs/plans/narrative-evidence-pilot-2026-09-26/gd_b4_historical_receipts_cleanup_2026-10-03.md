# B4补批：保留历史Git引用，删除四个旧审查checkout

<!-- CURRENT_PWF_NAV -->
> **历史施工/调查材料：**当前状态与唯一下一步见[总计划](task_plan.md)。下方旧待办、暂停、人工签收和预算只是当时记录，不自动恢复；R3/R5的真实剩余范围以总计划为准。

2026-10-03总指挥冻结；首批23根已完成，本卡只覆盖下表四根，约228,310,996B。无新增人工审查门。space_reaudit已只读核：全为8月历史审查，无代码WIP/活动owner；来源/状态40文件各自均Git tracked，无唯一原件或manifest。普通remove，不force/reset/prune，不碰managed/pinned/其他仓。

| 精确根 | 必须不变的HEAD | 保留办法 |
|---|---|---|
| C:/Users/郑曾波/Projects/.fcap-review/fc-802/company-wiki | ec00a028048da40cb43e8fc058aad9c8a7e1f963 | 新ref codex/history/fc802-rejected-20261003；仅两份REJECTED历史审查文档 |
| C:/Users/郑曾波/Projects/.fcap-review/fc-802-r3/company-wiki | 29abc878dcf04fba46f8919331bdb9d5f1f9a297 | 新ref codex/history/fc802-r3-accepted-20261003；仅两份ACCEPTED历史文档，main已有相同blob |
| C:/Users/郑曾波/Projects/.fcap-review/fc-804/company-wiki | 7d9f40cace24aafed4ef9414a3f5ecbb929c42da | ancestor/main；下方两份untracked文档main HEAD已同blob |
| C:/Users/郑曾波/Projects/.fcap-review/fc-805/company-wiki | 9587cb4650f03ea96327526c1e2f8142843e56f8 | ancestor/main；下方两份untracked文档main HEAD已同blob |

## 仅可先unlink的四份重复小报告

必须同时核候选字节SHA/size、主树同相对文件以及当前main HEAD blob均相等；主线存储不修改。只用精确文件unlink，不递归删目录。HEAD有新变化只hold该根。

| 根内相对path | B | SHA-256 |
|---|---:|---|
| fc-804: assurance/fc/FC-804/12_reviewer_receipt.json | 9530 | a7d35b6559217a377987d66a0f76ea57185a7b275f0de1928b5aa875a20ee106 |
| fc-804: assurance/fc/FC-804/REVIEWER_REPORT.md | 5854 | d49d0191f6f8be8df150618a0214d3fb72b1deb0ce9d6e5e029fc9bb0e8d0eac |
| fc-805: assurance/fc/FC-805/12_reviewer_receipt.json | 11126 | b2f4c8ece047c04c6bf9d4d3c49f252c2ac68506704d9bf838076eed53ee484a |
| fc-805: assurance/fc/FC-805/REVIEWER_REPORT.md | 3543 | 84e7bb600a901ae9188bbe6eb552b38c524d86a33c254e5d295f5de2cf6da085 |

## 执行与交接

1. 总指挥普通commit/push本卡后执行；逐根重核绝对根/registered/HEAD/reparse/状态。fc802/802-r3先创建并核两个精确历史branch ref，已有同ref只能同SHA，不覆盖；root会在收尾推送历史ref。
2. fc802唯一ignored catalog为221184B空schema，SHA9854f20ba2ebb0b0a3f80657869d87cde5bf2577a31a834c0a25691b83f30fc3，所有业务表0行、只有schema_version。即时复核仍空；其余只允许pytest/ruff缓存/pyc，unknown只hold该项。
3. fc804/805的四份上述重复小报告核main HEAD已持久保留后逐文件unlink，再检查checkout clean。接着对四根普通git worktree remove，不force。不新增重复报告副本。
4. 写独占worktree_historical_cleanup_2026-10-03.json/.md，记保留refs、候选/主线blob hash、实际逻辑字节、逐根路径/Git登记缺席、事实稳定和失败/持有项。只移除已核具体根，不恢复两个近乎空的.git-only根、不处理三个managed附件。
5. agent执行Git写入期间总指挥不同时commit；完成结果交总指挥更新PWF/推送。已有节点检查足够，不跑全仓或恢复原件。
