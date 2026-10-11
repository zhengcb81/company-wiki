## ROOT 最终资源与真实回放通过 — 2026-10-11

OCR source/resource 大节点已通过：预分配7真实RED→54集中PASS/3.78秒、15旧输出/坐标/原错误完全一致；非作者34纯几何/预算探针PASS/0.383秒。真实初次处理+新进程locator回开总83.006秒，阶段37.706/44.104秒，原85/90上限不变；22旧行EXACT、两定义置信度.98912/.99044及locators同旧PASS，5原件/配置SHA与4产品SHA前后相同，scratch恢复absent，0调用/费用。原85秒native FAIL、旧独审FAIL、预分配7RED全部保留。

Windows native边界最终22项此前通过，当前未再改其源码；184项仅属去掉重复监听之前的组合基线，不能说已按最后源码重跑。最终独审PASS_WITH_SCOPE；POSIX仅静态审查、没有峰值RSS实测，不签研究质量。报告 independent-preallocation/report.md 与 preallocation-real-e2e/ 位于共用W05接收证据。

为避免关键回归未接CI而漏检，ROOT在既有FAST_CONTRACT_CASES登记6个小节点（实际11参数用例），先6登记断言RED，再既有fast入口148PASS/24.45秒；没有新gate，也没有把真实模型/整套normalization纳入每push。正常源码发布时既有完整受影响节点仍会执行。

## Next Step

A/B/C完成；待正常暂存ROOT的两份登记变更、commit/merge/push与精确CI。用户新交付W06-CWP-PORTABILITY当前只读验收发现owned目录清理缺口，FF matrix也发现oracle/隔离缺口；它们单独修复，不改已冻结OCR，不把测试工具的错误称为CWP生产缺陷。母W04/G2/G4/G5尚未完成。

# 发现

性能分段诊断当前事实：child握手3.67s、权重SHA约0.07s，import rapidocr卡住，尚未进入ONNX session/推理；child约2s CPU/54MB，不能归因为识别慢或机器负载。正在核堆栈及native EOF监听线程与Windows CRT stdin互锁；此为待证伪假设，不先按猜测改预算或配置。

2026-10-11 ROOT最终工程184PASS/66.32s、ruffPASS，六未改反例及有效50ms startup截止独审PASS。真实PPTX首次原图推理85.047s触产品deadline，完整回放未通过；原日志/result/receipt以original-fail冻结，原件/配置SHA全等、测试根恢复absent、增量费用0。下一步先查隔离进程的配置与native初始化/推理耗时共因，不提升时间、不绕硬截止。

2026-10-11：主线 f10a8a67 clean。交付 HEAD 6fe9a82a、产品feat4e3d28a9、base159b993e。31文件，其中产品3、测试3，其他设计/计划/交接留证；Git状态待真实环境复核。

交付声称59 focused /129 normalization PASS；真实微软slide7两定义恢复，22行精确保留，两个阶段36.4s/33.5s。ROOT尚未认可。新指纹承担缓存失效，parser version仍2.0.0以兼容回开。后台detected未知=null。合成中英文低分探针未触发丢弃分支，局限明确保留。

需核验：每阶段90s不等于总流程90s；生产恢复是否被真实父进程硬限；跨图像素预算与回开一致性；timeout test2→20的冷启动解释；六处mypy旧问题是否与当前主线一致。

## 独立反例（原始FAIL保留）
原交付129PASS（ROOT81.76s）不能覆盖缺陷。独立6探针5FAIL/1PASS：ROI剩余1像素仍调用290×54推理；真实filtered契约的margin和stack忽略diagnostic dropped而误称完整恢复；跨stack chunk框按center伪映射；90/270非方形逆变换用错宽高。另一个只读审查确认：NNorm模型预检/语言采样发生在AUTO supervisor之前，原生加载/推理同步，仅返回后查deadline；旧20s测试验证的是测试自建父进程，而非产品限时。

ROOT决定隔离系统修复：恢复线统一原图+ROI预扣预算、filtered完整性、完整bbox映射和revision；hard-boundary线让配置型OCR一份可回收child持engine，预检/原图/ROI共享deadline，NNorm及公开normalize/replay接入；不新增许可、任务库、网络或费用。所有原始失败证据不改。
