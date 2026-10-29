# W20-FF-REPLAY ROOT独立验收（2026-10-29）

**结论：需要返工（2项P2，1项P3），暂不并线。** 当前未发现此次新增产品FF适配器缺陷（产品scripts零改动）；问题是关键恢复场景未被证明以及测试故障触发器隔离遗漏，不把历史PASS改成FAIL，也不要求重跑全41。

实际HEAD：`e81953dd8d122381265b7ba46c35117c3395cf1b`；base：`5396bd688e5b775e746fe3290852f0532d4548f8`；作者受测/独审e07b424之后无实现源码变化；13个实现/测试文件SHA逐一匹配。作者工区clean。

## FF-R1 [P2] durable后丢回执分支尚未被验证，未durable重下载却可计同一case PASS

位置：`tools/offline_contract_matrix/w20_case_specs.py:327`

证据：4份保留真实report（3bb0a6bc/465ac1a/b9d326/d163ba8）的kill_after_import均PASS、recovery_branch=not_durable_at_kill、恢复GET=1/downloaded。ROOT用当前断言复核465ac1a得到[]，即该未durable分支被明文允许。没有一份证明durable成功后中断且首次恢复0额外GET。

根因：用规范sidecar出现代替source已完成持久登记；并将两个不同故障阶段合成一个可任选成功条件，之后把case PASS扩大为R3已通过。

返工要求：保留原历史报告及其真实PASS含义，纠正覆盖声明；在既有测试边界实现独立确定性durable后丢回执/返回中断用例，证明杀树前本请求source可通过公开CWP接口实读、杀树后首次恢复0GET且Ref/SHA相同，再次复用也0GET。未durable路径继续单列，不能代签durable路径。无需保证并发exactly-once，不提高预算，不重跑41全批；如真正需要CWP接缝，仅交ROOT最小需求，禁止跨仓改源码。

复验：先加入会拒绝not_durable替代durable验收的断言回归，再仅运行新的durable代表case和原before_durable相关case，保存实际进程/HTTP计数/公开实读证明及清理。

## FF-R2 [P2] 中断触发器会被前序期次的任意sidecar提前触发

位置：`tools/offline_contract_matrix/w20_fault_cases.py:298`

证据：case_call_kill_after_import使用lambda: bool(_transcript_sidecars(ctx))，没有before delta/本请求过滤。ROOT纯handler探针只预放unrelated-period.source.json、没有本case新sidecar时，kill_when立即True。此探针是控制流单元反例，未假称真实E2E。

根因：一个组内case共享fixture wiki，但trigger观察全公司文件，缺少本请求/期次的隔离；同文件before_durable和et_fault已使用before delta，此处遗漏。

返工要求：以本case实际请求Ref/身份期次/新durable记录匹配触发，不以任意旧sidecar存在触发；复用已有owner公开接口，勿在FF复制存储逻辑。

复验：预先存在另一期次/另一case sidecar时不得触发；只有本请求达预期持久阶段才触发。有界跑同组顺序A→本case及本case单独，确认都观察正确阶段，不要求整批全绿。

## FF-R3 [P3] 最终交接两项机器字段未随实际资料更新

位置：`delivery/w20-ff-replay/handoff.json:188`

证据：files[]中run-receipts.json期望a863cc936fd9c632ded2baaf30612a08a930665ef90cab1a709f2ba40367bb2d与当前实际SHA不符（其他22条一致，13个实现/测试SHA均一致）；tests[2]直接pytest命令申报1462 passed/13failed同时exit_code=0。13个基线失败已诚实披露，但pytest本身不应填0。

根因：文档后置修正后未再生成交接摘要；把基线问题归因通过混同测试进程退出码。

返工要求：刷新这一个收据SHA；按真实命令进程退出码更正tests[2]，若未知填null并解释，保留13failed及基线归因。明确全仓并非绿，不需重跑已知404秒全仓。最终更新本次返工独审/修复证据，不增人工审批。

复验：重核实际changed文件SHA、读取原失败收据与实际运行记录；不重复全仓。

## 独立实际执行与边界

- 当前新增两测试文件＋既有authority：**183 passed，6.78秒**，exit0。缓存禁写，临时测试根仅ROOT owned目录；测试后已删除，作者status仍clean。
- 四份保留真实report均只覆盖未durable分支；精确路径/SHA见同名JSON。当前断言复核未durable PASS得到零error。纯handler反例证明任意旧sidecar可触发，未启动真实跨仓进程，不称新E2E。
- 原始run-receipts/handoff/独审初审和复审保留，不伪造最终独审。已有复审列3个P3且作者后续文档修正，这里不为纯文书增加审批门。
- 未改任何作者/其他仓源码、Git索引、原件/生产配置，无供应商POST/下载/费用；不恢复主线循环。没有重跑完整41或404秒全仓。
- ROOT初始provenance脚本曾命名inspect.py导致标准库遮蔽；已改名provenance_scan.py，修正后纯反例正常执行，此错误与产品无关。

## 建议返工规模

原harness在同一分支修复FF-R1/R2，加最小回归和一份确定性durable真链证据，按FF-R3更新交接字段；独立agent只复审本次变化与关键场景。无需重新做本卡A调查、无需每个小节点ROOT签收、无需全41/全仓复跑。完成后交原同一路径handoff.md/json给ROOT复验。

独立可移交复现：[evidence/ff/README.md](evidence/ff/README.md)（小fixture＋通用只读probe＋核验摘要，无SDK/原件/整attempt树）。
