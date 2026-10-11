## ROOT 完成 — 正常主线并入、远端与 CI 已确认 — 2026-10-11

A/B/C/D均完成。正常ROOT merge commit c7fb1b81，master merge ae0ca0d3，已发布8862372f；精确远端SHA相同，现有push3257PASS/224.81秒，GitHub CI38140484490同SHA success。冻结publication.json记录全部范围与实际验收；旧pending勾选/失败记录仅作历史，不再作为待办执行。

原件/config未改；无provider/LLM费用。后续W06测试工具或W04候选修复不重开本卡、不重复整套OCR或3257全集；新的受影响变更按当前现有测试映射检查。

## ROOT 最终资源与真实回放通过 — 2026-10-11

OCR source/resource 大节点已通过：预分配7真实RED→54集中PASS/3.78秒、15旧输出/坐标/原错误完全一致；非作者34纯几何/预算探针PASS/0.383秒。真实初次处理+新进程locator回开总83.006秒，阶段37.706/44.104秒，原85/90上限不变；22旧行EXACT、两定义置信度.98912/.99044及locators同旧PASS，5原件/配置SHA与4产品SHA前后相同，scratch恢复absent，0调用/费用。原85秒native FAIL、旧独审FAIL、预分配7RED全部保留。

Windows native边界最终22项此前通过，当前未再改其源码；184项仅属去掉重复监听之前的组合基线，不能说已按最后源码重跑。最终独审PASS_WITH_SCOPE；POSIX仅静态审查、没有峰值RSS实测，不签研究质量。报告 independent-preallocation/report.md 与 preallocation-real-e2e/ 位于共用W05接收证据。

为避免关键回归未接CI而漏检，ROOT在既有FAST_CONTRACT_CASES登记6个小节点（实际11参数用例），先6登记断言RED，再既有fast入口148PASS/24.45秒；没有新gate，也没有把真实模型/整套normalization纳入每push。正常源码发布时既有完整受影响节点仍会执行。

## Next Step

A/B/C完成；待正常暂存ROOT的两份登记变更、commit/merge/push与精确CI。用户新交付W06-CWP-PORTABILITY当前只读验收发现owned目录清理缺口，FF matrix也发现oracle/隔离缺口；它们单独修复，不改已冻结OCR，不把测试工具的错误称为CWP生产缺陷。母W04/G2/G4/G5尚未完成。

# 进度

最终工程节点184PASS/66.32s、ruffPASS，独立最终六反例和有效50ms startup产品截止PASS。真实PPTX phase1首次原图推理85.047s触deadline FAIL；original-fail三文件封存，原件/配置五SHA相同、scratch恢复absent、增量费用0。并线暂停于性能诊断，不能增加时间或凭重试签通过。

2026-10-11 接收中。已读卡、交接JSON/MD、设计和worker findings；已派独立审查 agent，ROOT负责测试/真实E2E/并线。无产品修改，无付费调用。

当前 A，未通过验收，未合并。

A：32项交付 SHA/字节核验 PASS；外部 worker 工作树真实环境 clean。latest master f10a8a67 与6fe9a82a在独立 cwp-ocr-root 合并无冲突、尚未提交。首次 merge 在 worktree add 仍在写 index 时运行导致 index.lock；已等待创建完成后正常 merge，未删除锁或绕过。

B：原交付整合后的129项 normalization 包正在重跑。独立审查已指出需用真实 adapter 契约验证：ROI预算须在调用前计入原图累计；ROI低分内容已移入诊断，不能只检查通过阈值的剩余行就称整行恢复。

原完整包129PASS/81.76s已留证；独立审查FAIL，原6探针5FAIL/1PASS与报告SHA封存。ROOT分两个排他写集实施修复，恢复正式新增反例9FAIL/2PASS已RED。硬截止修复正在以真实不合作child而非测试timer验证。A已核验；B仍进行，禁止宣布接收完成。

恢复线最终38PASS/3.38s，原9FAIL及源边界相交追加1FAIL保留。实际ROI推理前预扣预算、filtered正文相交判断、split全框及非方形旋转已修；bounded-source-roi/2入配置指纹。独立原6探针6PASS（此后补相交判断的最终SHA还待最终集中复核）。

硬截止用 subprocess 而非multiprocessing，兼容AUTO daemon worker；复用现有WindowsJob/Unix进程组，配置型代理每请求持一份原生engine，无审批链。硬线34PASS（10新代理+24旧NNorm契约）初绿；父死/子孙进程等大节点检查仍待freeze。

新交付队列：用户报告W05-RF-FLOW、W06-AUDIT-MEASURES完成；已各派独立只读盘点/审查，与OCR写集无交叉。它们尚未ROOT接收或并入主线，ROOT先收尾当前OCR。
