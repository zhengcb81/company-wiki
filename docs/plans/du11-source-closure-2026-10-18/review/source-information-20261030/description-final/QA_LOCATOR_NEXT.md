# 当前交接：QA定位工程验收完成，正常发布后真实摘要v3

工程细节和真实零POST定位收据见[qa-locators/README.md](qa-locators/README.md)。稳定7文件独审通过；实际原件15/15定位、8/8输入业务gold，原件/config未变。先前严格相等quality方案在原诊断合同失败，现改来源标记不能删除、允许保守增补，160项定向验证通过；原guard/原测试不减断言。

正常发布后使用 summary-preflight/RUN_NEXT.md 的原命令，只把 --output 改为 `.planning/source-description-20261030/real-summary-v3`。meta-v4/gold-v3不变，配置MiMo/0.9.0/v4/registered_readonly/activation-recovery/FF-RF consumers不变。单次50k tokens/$0.05；母账不重置、不启W21 SDK。记录实际生产源码身份。成功后必须实际claim独审和恢复/跨run零重复POST；consumer通过不等于整个RF实际模型采用。

以下故障调查和施工细则为历史依据：

# 当前下一步：QA cell片段的真正稳定定位

来源准备工程已在master提交推送 `f88221d2578eac078bb7b30d9a8c00b08f2ee6d2`，正常pre-push158P/26.35秒，11个Git源码LF与独审封存一致。295P/mypy/独审不等于真实摘要已通过。

真实 `real-summary-v2` 已能自动准备002643 IR；随后7.618秒的实际worker在select拒绝 `selected material is not reliable parsed source evidence`。0POST/0tokens/0费用，原件/config/sentinel未变、临时湖已恢复。母账不变。`ACTIVATION_RECOVERY_NOT_AVAILABLE` 是前置select失败的下游结果，不能据此重复发模型或改恢复额度。

已定位根因：`narrative_evidence._emit_pdf_qa_fragment` 无条件给每个QA cell子片段 `locator_unstable`，坐标只有cell没有子串range。保存的真实selection15片段中14个如此；metadata虽然记录cell SHA/fragment range，来源定位尚未把其作为独立定位表达。正式admission正确拒绝此不稳定标记；不能仅删除guard/quality flag，也不能把之前输入8/8当生产select已通过。

实施顺序：

1. 先纯cell TDD：不同问题/多个相同答案的同cell片段有不同的char范围，exact cell slice与fragment SHA一致，换行trim保持；篡改range/父cell/问题/角色/parser不能回放，跨页answer continuation不能因新的char范围误断。原 `locator_unstable`/OCR低信任负对照全保留。
2. 在PDF reading/source层定义版本化稳定cell范围。保持旧0.1.0/0.1.1回放行为，检查new parser与native-range base version/cache依赖，不跨层在benchmark/FF/RF清flag或重造来源。W21 runtime三个文件独占不碰。
3. 先独立设计复核，再实现/小域验证；新native结果真正从同一原件重解析一次并经实际handler admission，而非复用旧不稳定snapshot冒签。先保存snapshot供后续诊断，避免反复解析整批。
4. 大节点独立源码与纯合成/真实定位回放审查，过后正常提交推送并观察精确CI。新真实模型运行输出另起v3，保留v1 NOT_RUN与v2 FAIL，gold只作必要的版本化locator映射，不减业务事实/原文锚点要求。
5. 仍须实际摘要、claim审查、持久响应/恢复/跨run缓存0重复POST、FF原件0下载与RF实际采用；不扩大费用/token/重试/空间额度。W21/holdout/US RPO/完整公司循环仍OPEN。

本轮测试临时目录已清约369,727,202字节，compact验收约59KB；原件/SDK/外包目录未清理。本次调查中的不存在路径read、PowerShell通配符rg错误为调查命令错误，已改为确切文件/目录级glob，不作为产品缺陷。
