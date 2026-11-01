# R6 — W23 Xiaomi OCR R1 ROOT 接收独审

审查对象：`C:/Users/郑曾波/Projects/company-wiki-w23-xiaomi-ocr-r1`，分支 `codex/w23-ocr-r1-20261031`，HEAD **`d2f6e6f015cb69b826b499ef56e1ab3d6053fced`**。审查者为 ROOT 的独立接收 agent `/root/rectification_review_a`，未参与本包实现及其原作者终审。

**结论：可接收 PARTIAL 实验资料；当前工具工程不通过，不能签 READY/生产 OCR 通过。** R0/N0 的有限样本结果、X1 两次失败及硬件限制可作为真实试验资料保留。真实 X1 路径的预算/缓存/恢复仍有可复现缺陷；交付中声称的最后两轮独审未出现在提交的独审报告内。ROOT 已安排工具根修，本报告不替未来修复版签字，也不补造历史审查。

本报告与同名 JSON 一起读取；JSON 绑定源码、报告、gold、manifest、原件 SHA，保存四个独立 RED、完整轻测复现脚本及清理收据。

## 接收范围与已经成立的证据

- Git：宿主只读 Git 核实本地 HEAD 与 `origin/codex/w23-ocr-r1-20261031` 跟踪 ref 都是 `d2f6e6f0`；已跟踪工区/索引无差分，唯一未跟踪目录为 `.w23_cache/`。本轮未联网查询实际远端，不能把跟踪 ref 等同于实时远端证明。
- 身份：交付清单内 **13 个工具源码 raw/LF SHA 全符**，manifest/gold/control 三个冻结 SHA 全符；6 份原件实读 SHA 与 manifest 全符，原件共用页没有重复计成新文档。最终声称 tested `3934e9fa` 后只有 handoff/progress 三份文档变更。必需平台修复确实以 `6705c3ea` cherry-pick 进入分支；其中 ROOT 的 CI/平台文件不应误判为作者越界重写生产 OCR。
- 样本：最终 **8 页/6 文档**，CN 3、HK 3、US 2，eval 6/holdout 2；gold 合计 15,600 字符、189 facts、117 conditions、316 raw numbers，其中 25 个数字条目被声明排除，数值检查分母 291。R0/N0 均 8/8；两次 X1 的最终聚合分母也是 8，后来新增 QA 页明确为 not_run；X2 8/8 not_run，无隐去失败页。
- 冻结：原 7 页 gold 在 `970532af`、2026-11-01 13:49:14Z 已提交，首个账本条目为 14:01:51Z；两页 holdout 的完整 page 对象与该提交逐字一致。Wuxi 更正保留版本/分母说明，不应冒签原错误 gold 没改过。新增 QA gold 当前 mtime 早于该页 capture，但其首个 Git 提交 `bf672e6c` 在运行之后；只能接受其自述的预先冻结时序，不能补造一个不存在的预运行 immutable commit。QA 是 eval，不把它提升为新增盲 holdout。
- R0/N0 定量资料：最终 JSON 的 R0 macro strict CER **0.10002816**，N0 **0.10954591**；R0 facts 164/189、conditions 107/117、numbers 288/291。它们是有限 born-digital 页图试验，R0 拼接 backend 返回行，不是生产几何读序的完整端到端结果；surface/numeric-anchor 指标不证明主体/条件/表格关系正确。
- X1：attempt 1 加载 MemoryError；attempt 2 在修正平台工具链后，第一页面 generate 分配失败，随后第二页原生崩溃 `0xC0000005`，receipt wall 106.5s。记录 cap **1,719,988,224B**、job peak **1,882,599,424B**，超出 **162,611,200B**。B4 标 partial、总体 PARTIAL、Xiaomi quality claim null 是诚实边界；本轮不能判断小米准确率或部署可行性，也不能证明所谓“6.5GB 空闲内存”就必然足够。
- 控制：空白输出 0 字符；公式是 **1/4 formulas** 符号保真，另有 **6/10 symbols**，不是“1/4 symbols”。无扫描件/双栏、CN/US 表格缺项及 X2 未跑均需继续保留披露。N0 只读 text layer，并未在执行中把 gold.full_text 作为结果；但仓内记录无法独立认证转录 agent 的真实身份，也不能用 native text 与 gold 近似相同反证或证明其独立性。

## W23-R6-01 / P2 — 真实 X1F 没接上已宣称的预算、缓存与恢复闭环

定位：`tools/ocr_comparison/campaign.py:68`、`:238`、`:250`、`:344`。真实 X1F 分支直接 `run_x1_batch(...)`，在它返回后才写缓存/账本；与 fake、R0 分支不同，它从未 `cache.get`。零余额判断也在调用 runner 之后。`load_ledger` 没有 finite 检查。已有两进程 TDD 使用 `X1F-fake`，没有约束真实 dispatch，因此假路径通过不能覆盖这些缺陷。

ROOT 授权后，将 **campaign.py/cache.py 两份字节原样复制**到自有临时目录，以真实 `arm='X1F'` 调度及显式 stub runner/identity 做四个小反例，不进入 `X1F-fake`，不导入模型/torch，不读任何权重或密钥，不下载：

| 检查 | 应有行为 | 实际结果 | 结论 |
|---|---|---|---|
| 相同页/参数/目录，两个独立新进程恢复 | 第二次命中缓存，backend 共 1 次、无重复扣费 | backend 共 **2 次**，spent **1→2**，无 cache_hit | RED |
| batch 已开始后 runner 异常，再新进程恢复 | 已有持久 in-flight 预留/保守费用，不能洗掉未知耗时 | 异常后 **spent=0、entries=[]**；重启照常执行 | RED |
| 余额 0 的真实 X1F | 不进 runner，返回全分母 not_run | 仍调用 runner，以 total/deadline=0 触发与真实 `validate_card_limits` 一致的 ValueError，未返回 not_run | RED |
| `budget_seconds=NaN` 损坏账本 | LedgerCorrupt | 被接受；remaining 为 nan，request_budget 却为 **180** | RED |

重现脚本全文在 JSON 的 `light_probe_reproducer_source`；它用标准库、两份复制源码、独立子进程和 dummy 路径，不需要真实模型。脚本第二次完整运行耗时约 4 秒。第一轮审查者自己的 stub 子进程缺显式 `-X utf8`，导致读取错误栈时编码失败；只修改自有探针后重置自有临时文件再跑，不把这个审查工具错误计作产品问题。

账本 **40 项 sum=spent=1431.40547/1800** 的算术成立，但不是全部实际推理成本的证明：首轮 R0 七个成功零秒条目仍未补计，时间戳首末跨 170.989549s，之后又有重测；另有 1080s 的未开始页超额记费。披露这两类历史错误是正确的，不能据此把 B2/B3 严格闭合改成 done，也不能自动拿两类错误相抵。已知 106.5s 的一次失败和最终 cap/peak 等原始记录不得重写。

ROOT 根修建议：在这个实验工具层统一真正执行路径，缓存命中先于推理；一次持久 reserve/finalize 负责实际 in-flight 和恢复；非有限数明确拒绝；额度检查先返回全分母 not_run。用上述四例约束真实 X1 dispatch，保留 fake 的低成本测试；无需另建生产任务库、人工许可或模型 CI。当前资料足够定位根因，不需要重跑重模型来证明这些工程修复。

## W23-R6-02 / P2 — 最终独审绑定没有随交付保存

`delivery/w23-ocr-r1/review_independent.md:139` 起最后一轮仍是 **round 3 / fc4228c1 / final tested da9ca2c8 / 7 页**；末结论 **NEEDS_FIXES**。文件只保存三轮。

但 handoff.json:27 声称 **76292e3f independent delta review READY_FOR_ROOT**，progress.md:28 声称五轮全部闭合，最终 8 页；所指新增独审正文/结果/版本绑定未在提交的 report/receipt 中找到。原报告确实描述未参与实现的独审方法，并曾发现真实问题；不否认前三轮的价值，但不能替它推导“最后一版已独审通过”。

ROOT 可以对最终新版重新独审，明确作为**新的接收结论**，修正 handoff/PWF 对缺失记录的声明；不能在旧报告补写一个未留存的历史 PASS。作者的 59P 来自原独审报告，本次没有重跑这些测试，也没有替最终源码作59P认证。

## 可直接小修，不需重跑模型的事项

1. **清理声明**：`.w23_cache/r1_pages/r1_wanhua_qa2021_p003.png` 仍在，579,214B，SHA `097eaf47d1da132c80a64dfdd42ca81c72d3b559969ca552b6bc7fb1d00478fc`，与 manifest 声明的生成图一致。“所有 PNG 已删”失实。它是实验保留页图，不是本次 ROOT 轻测生成；本审查保持原样，不盲删。ROOT 可确认用途后把清理声明改为真实保留，或在获准清理工区时删除这一明确生成资产，不能动原件/模型缓存。
2. **PWF 旧态**：task_plan.md:5 仍 READY_TO_DISPATCH/未正式试验，:15 Next Step 仍“开始 A”；阶段 B 仍 7 页/1406.5。应转为“PARTIAL 证据接收，真实工具根修/ROOT复核”，不用增加 A 的人工签收。
3. **同源报告旧字段**：handoff.json 的 B6/C1/status_reason 仍 7 页，limitations 仍“no IR-Q&A”，但已有 QA；campaign.runs 未列 QA 扩展两份 capture。progress 最后一行 N0 0.1178 已过期，应为最终 0.10954591。修正单一 builder 后生成，避免改报表却留下会再次产旧态的 builder 常量。
4. **数量口径**：handoff.md 的“1/4 symbols”改为“1/4 formulas (6/10 symbols)”；历史段落与当前终态分开，不能把历史 7 页结果覆盖/伪改成后来 8 页。
5. **准确表述 OPEN**：资源 cap 违反/记录矛盾继续 open，X1 没有合格质量输出。更大机器只能列下一次试验条件，不能宣称已经解决限制或已经可替换 RapidOCR。

这些文档/清理小修不会单独否定已取得的 PARTIAL CPU 对照资料；真正阻断工程签收的是前两项 P2，及若未来再做真实 X1，尚未解决的 cap/peak 问题。

## 隔离、清理与终止

作者 `.w23_cache/` 前后均 **20 文件 / 695,733B**，所有路径/大小/SHA 一致；包括上述 QA PNG，没有新增模型副本。13 源码、交付/计划/冻结报告绑定 SHA 前后不变。宿主只读 Git 仅用于检查；未改作者工区/索引，不 checkout，不执行作者脚本或模型，没有接触生产 config/src/DB，也没有触碰当前其他 R6 agent 文件。

ROOT 自有 `C:/Users/郑曾波/Projects/company-wiki/tmp/r6-w23-intake` 初始不存在，完成后按已解析且落在指定 tmp 根内的绝对路径清理，最终再次核实不存在。仅保留这两份紧凑审查报告，复现脚本以文本嵌入 JSON，没有留下源码副本或测试材料。

**STOP。** 工具根修冻结后另做最终版独审；本报告不签生产 OCR，也不签主线真实摘要、持久缓存恢复、RF 经济采用或公司完整循环。
