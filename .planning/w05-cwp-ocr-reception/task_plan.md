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
