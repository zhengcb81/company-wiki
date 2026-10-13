## 当前发布状态 — 2026-10-13

旧 DU 三包接收与 ROOT 共同修复已并 master、推送 `9e9907cd7c013ecf0a6787dd0f591ba242eb223a`，[精确 CI](https://github.com/zhengcb81/company-wiki/actions/runs/38462668903) success；[接收结果](reception/acceptance.md) / [下一步](reception/task_plan.md)。首次 push 抓到共享 Windows 同目标 rename 争用，已 TDD 根治并实际1000写入零失败，未跳过测试。新 DU2 三卡仍独立施工，生产模型摘要与真实业务漏读/G2/G4/G5保持开放。下方“发布中”是历史。

## 当前执行入口 — 2026-10-13 旧三包接收

[reception/task_plan](reception/task_plan.md) 优先于下方历史阶段表。旧 DU 三包/ROOT 最新成果及两条排他接收修复已整合；491 项集中与 11 项四原件回放通过，最终 oracle seam 5 PASS，独审无剩余并线阻断。正常并线/推送收尾。生产模型摘要与实际业务漏读不当完成；新 DU2 三卡仍正在施工。
ROOT 后续按 review/root_implementation 接策略/布局/业务价值预算→真实配置摘要与回开→母计划 G2/G4/G5。仅大节点测试审查，不添加小节点许可。

# 文档理解架构升级：调查与实施计划

## 最新优先事项（2026-10-13 深化复审）

本轮复审与增量施工由 [review/task_plan](review/task_plan.md) 跟踪。三条旧卡及 ROOT 整合分支已有交接，尚未主线启用；旧阶段表保留为分发时状态。ROOT下一步是核对最新分支接收并按 [root_implementation](review/root_implementation.md) 修评价目标/证据绑定、完整依赖闭包、配置实际消费，再做正式接线与B/C；新三卡可独立准备文档策略/业务策略/布局辅助。不要依据旧oracle分数调高切片数量或另建HTML前端。

PLAN_ID: document-understanding-2026-10-13
PWF_PLAN_ROOT: C:/Users/郑曾波/Projects/company-wiki/docs/plans
Owner: ROOT
状态：用户已确认共享引擎＋多份阅读策略配置；三条分包已分发、独立施工中；生产解析链未切换。

2026-10-13：用户已发出三包，当前由各自harness施工。ROOT已完成W08 RF/Audit验收并线/必要安装，详母计划W08接收入口；现在准备主线真实G2及三DU包集成，三包代码与各自PWF不由ROOT代写。

## 目标与边界

根据真实 A/H/US 文档及现有代码，实施已确认的共享引擎与文档类型/章节阅读策略。原件不改，不增加逐材料授权、不复制全量 PDF/MD，不新增研究结论 writer。复用 SourceRef/SourceExport、AUTO Store、现有资源预算与配置供应商。W08 RF/Audit 接收已完成；母计划真实 G2/G4/G5 保持开放，不能用模块交付或本轮调查替代。

## 阶段

1. [complete] 读当前路由/规范化/选择/摘要边界与历史设计；20份原件原生扫描/重点抽读、4页视觉核对、3份真实selector回放。
2. [complete] 已写design、INTERFACES、implementation，明确共用结构/策略/语义证据、资源与A/B/C测试。
3. [complete] 三卡、冻结接口/交接格式和独立worktree已准备并分发；共同基线7f6f7cbd5c438ecfd06f6ffb1241442f26ff43b8，创建时已验证干净。
4. [in_progress] 三包各自实施；ROOT准备现有units适配及G2真实输入/配置/预算。生产接线、真实摘要和公司G2/G4/G5验收仍待完成。

## Next Step

三包按原卡和DU/1接口继续独立施工。ROOT不写它们的独占模块和各自PWF，准备共享生产适配及真实G2；收到交付后集中接收、并线、跨层离线验证，再合并母计划真实G2/G4/G5。新增文档类型先扩展策略，不建立另一套引擎或技能。

## Errors Encountered

- 首次 CodeGraph 用宽泛自然语言命中旧 ClaimRouter，后续改用明确符号；未据此推断新解析链。
- 历史 W04 source_rows JSON 已归档不在原路径；改读已发布压缩回放定位六份原件，无重新生成历史证据。
- Python 首次输出中文编码失配；后续统一 `-X utf8` / PYTHONIOENCODING=utf-8，原文件不受影响。
- PyMuPDF原生save向沙箱Temp写PNG失败；改写工作区自有临时目录、tobytes写入后目视核查；四PNG已删除恢复。
- HKEX年报编制指南打开失败，正文未核验；设计引用本地真实港股年报和官网摘要，不将搜索摘要当全文已读。
- 母PWF首次prepend被Windows换行转换造成全文件diff；已按HEAD原字节保留正文、仅追加LF前缀恢复，diff仅14行新增。
- 新worktree --no-checkout后稀疏规则未填入空索引；在三个刚创建的指定分支执行read-tree -mu HEAD完成检出，三者status均0，无原件目录复制。
