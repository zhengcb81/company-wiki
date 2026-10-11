## ROOT 完成 — 正常主线并入、远端与 CI 已确认 — 2026-10-11

A/B/C/D均完成。正常ROOT merge commit c7fb1b81，master merge ae0ca0d3，已发布8862372f；精确远端SHA相同，现有push3257PASS/224.81秒，GitHub CI38140484490同SHA success。冻结publication.json记录全部范围与实际验收；旧pending勾选/失败记录仅作历史，不再作为待办执行。

原件/config未改；无provider/LLM费用。后续W06测试工具或W04候选修复不重开本卡、不重复整套OCR或3257全集；新的受影响变更按当前现有测试映射检查。

## ROOT 最终资源与真实回放通过 — 2026-10-11

OCR source/resource 大节点已通过：预分配7真实RED→54集中PASS/3.78秒、15旧输出/坐标/原错误完全一致；非作者34纯几何/预算探针PASS/0.383秒。真实初次处理+新进程locator回开总83.006秒，阶段37.706/44.104秒，原85/90上限不变；22旧行EXACT、两定义置信度.98912/.99044及locators同旧PASS，5原件/配置SHA与4产品SHA前后相同，scratch恢复absent，0调用/费用。原85秒native FAIL、旧独审FAIL、预分配7RED全部保留。

Windows native边界最终22项此前通过，当前未再改其源码；184项仅属去掉重复监听之前的组合基线，不能说已按最后源码重跑。最终独审PASS_WITH_SCOPE；POSIX仅静态审查、没有峰值RSS实测，不签研究质量。报告 independent-preallocation/report.md 与 preallocation-real-e2e/ 位于共用W05接收证据。

为避免关键回归未接CI而漏检，ROOT在既有FAST_CONTRACT_CASES登记6个小节点（实际11参数用例），先6登记断言RED，再既有fast入口148PASS/24.45秒；没有新gate，也没有把真实模型/整套normalization纳入每push。正常源码发布时既有完整受影响节点仍会执行。

## Next Step

A/B/C完成；待正常暂存ROOT的两份登记变更、commit/merge/push与精确CI。用户新交付W06-CWP-PORTABILITY当前只读验收发现owned目录清理缺口，FF matrix也发现oracle/隔离缺口；它们单独修复，不改已冻结OCR，不把测试工具的错误称为CWP生产缺陷。母W04/G2/G4/G5尚未完成。

# ROOT 接收 W05-CWP-OCR

PLAN_ID=w05-cwp-ocr-reception；PWF_PLAN_ROOT=C:/Users/郑曾波/Projects/company-wiki/.planning；owner=ROOT。

## 目标与边界
验收交付 6fe9a82a（feat 4e3d28a9），在最新主线 f10a8a67 上验证并合并。原件、生产配置保持原样；本次无云 OCR、LLM、下载模型、项目费用。保留 worker 原始失败证据，不修改 W04 工作树，不给下游经济质量 PASS。

## 大节点
- [x] A：核验交付 manifest/Git范围，隔离整合最新主线；独立原交付审查完成（FAIL留证）。
- [x] B：最终组合184PASS/66.32s、ruffPASS，恢复六反例及独立有效50ms startup截止PASS；工程质量范围通过。
- [ ] C：真实 SourceVersionReader→slide7→OCR恢复→正常组合→locator回开；硬截止、原始SHA及测试目录还原。
- [ ] D：正常 hooks 提交/并线/推送，更新共用 PWF，核验远端 CI。

## Next Step
真实E2E phase1首次原图推理触85s硬截止，整体FAIL；原日志/result/receipt以original-fail冻结，scratch恢复absent，5原件/配置SHA不变。下一步分段定位spawn/import/engine init/inference性能根因，遵守原模型配置、85/90s预算，不凭增加时间或再跑变绿并线。

## 验收关注点
两条定义必须正确恢复；22 条旧行 text/box/confidence 不变；乱码仅诊断；最多4区域/2次每区域/8次每图；像素和时间请求累计；原生不协作计算有真正父进程硬截止；旧构造兼容、fingerprint缓存区分、真实回开全等。合成探针局限不得隐瞒。测试只在大节点做，不扩展人工许可。

## 证据
docs/plans/cross-market-rf-e2e-2026-10-08/phase6/w05_parallel_common_roots_2026-10-11/evidence/root-cwp-ocr-acceptance/

## Errors
沙箱读取外部 linked worktree 的 git status 提示 not a work tree；后续使用真实工程环境核查，不据此修改 Git 配置。
