# 未来收入指引与明确局部前提：冻结RED及契约说明

**当前20项：7 FAIL / 13 PASS，Ruff通过。** 真实公共selector/引用/模型输入端口，无假pipeline；10个源码/测试文件前后字节稳定。源样本为设备服务、物流服务、订阅服务、新材料，覆盖简体、繁体和英文，全部内存合成。

## 共用根因

1. 未来收入range/growth缺少明确阅读语义。简体/繁体作为弱description保留，英文subscription收入指引被finance-only过滤。收入指引应保留原预计、未来期间、区间、币种和单位，不是已发生的经营收入成果。
2. 真实前提虽可被单独选中，却没有进入其指引的source citation/task闭包。3个中文/繁体后置前提及明确“以下…展望假设…”的前置前提均实测脱落。英文closure例目前先卡在指引召回，修复后仍须验证前提绑定，不把它伪报为已观察的第二个EN问题。

## 真实契约与最小接线

`OperatingFact`只有eligible/topics/reasons/score/financial_exempt/purpose，没有stage/modality。stage/modality在`du4-operating-relations/1`，本4个收入指引都返回complete但relations为空。公共EvidenceSpan/reading_context/模型输入只有原文、来源/定位、现有reason/topic/quality和support/context；forecast枚举仅在模型**输出**schema。

因此测试没有创造`fact.modality`、`span.forecast`等字段。现可证的future-not-actual是原预计/年份/range进入实际模型材料，且不被附加已有current/milestone错误标签；不能宣称机器已验证一个不存在的forecast-input字段。若ROOT需要显式机器可判语义，最小方案是在现有source purpose/selection reason通道定义一个明文约定并传到已有task binding，而不是新建持久schema或让测试先编字段。

收入范围、同比增长与未来scope应由同一source policy观察器负责；真正前提由共享source-support依赖owner按明确above/this/following guidance引用、真实parent/section/frame和主体判断，使用已有required graph。不要把“收入指引”塞进设备/产品词典，也不要用邻近conditional词猜关系。已在同一原文的前提保持原样。

13条通过包括跨parent/section、无明确挂接的天气风险、未来内部流程、供应商自己的指引、中文内联原文、预算及源不变控制。tight预算测试是保护闭包的控制，基线部分路径因弱description未被选中而通过；不把这种通过冒称已实现条件绑定。

## 交接与边界

冻结正式文件为`tests/unit/document_understanding_selection/test_reading_guidance_condition_scope.py`，精确SHA见`diagnosis.json`/`red.json`。所有原文、source ID/locator、native carrier成员与96/48000/16000000、8/4/2048保持。执行命令及实际/请求临时目录清理收据见`red.json`。0原件、0格式parser、0网络、0收费。

ROOT实施后复跑同一20项及现有测量、限定和typed表格控制。当前只交TDD诊断，不代签实现或全年度摘要。
