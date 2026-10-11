# 发现

2026-10-11 ROOT最终工程184PASS/66.32s、ruffPASS，六未改反例及有效50ms startup截止独审PASS。真实PPTX首次原图推理85.047s触产品deadline，完整回放未通过；原日志/result/receipt以original-fail冻结，原件/配置SHA全等、测试根恢复absent、增量费用0。下一步先查隔离进程的配置与native初始化/推理耗时共因，不提升时间、不绕硬截止。

2026-10-11：主线 f10a8a67 clean。交付 HEAD 6fe9a82a、产品feat4e3d28a9、base159b993e。31文件，其中产品3、测试3，其他设计/计划/交接留证；Git状态待真实环境复核。

交付声称59 focused /129 normalization PASS；真实微软slide7两定义恢复，22行精确保留，两个阶段36.4s/33.5s。ROOT尚未认可。新指纹承担缓存失效，parser version仍2.0.0以兼容回开。后台detected未知=null。合成中英文低分探针未触发丢弃分支，局限明确保留。

需核验：每阶段90s不等于总流程90s；生产恢复是否被真实父进程硬限；跨图像素预算与回开一致性；timeout test2→20的冷启动解释；六处mypy旧问题是否与当前主线一致。

## 独立反例（原始FAIL保留）
原交付129PASS（ROOT81.76s）不能覆盖缺陷。独立6探针5FAIL/1PASS：ROI剩余1像素仍调用290×54推理；真实filtered契约的margin和stack忽略diagnostic dropped而误称完整恢复；跨stack chunk框按center伪映射；90/270非方形逆变换用错宽高。另一个只读审查确认：NNorm模型预检/语言采样发生在AUTO supervisor之前，原生加载/推理同步，仅返回后查deadline；旧20s测试验证的是测试自建父进程，而非产品限时。

ROOT决定隔离系统修复：恢复线统一原图+ROI预扣预算、filtered完整性、完整bbox映射和revision；hard-boundary线让配置型OCR一份可回收child持engine，预检/原图/ROI共享deadline，NNorm及公开normalize/replay接入；不新增许可、任务库、网络或费用。所有原始失败证据不改。
