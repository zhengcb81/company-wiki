# 独立审查接口

用户明确要求每家完整流程及所有细节审查。审查不得只看执行报告/green validator，不改变成功定义。读取 common_execution_contract.md 与 RF 实際 SKILL/所需参考、公司 execution 全部命令和 events、output manifest；另外从实际 producer/catalog 和官方原文独立验证。

## 审查所有事项（每项结论有路径、hash、命令或具体原文定位）

### A. 执行完整性

- 三个独立执行身份、真实进程/时间、start→finish pairing、退出码、失败尝试、输出 bytes/hash、流程顺序，report 与实际日志一致。
- 每一个 RF 步骤 0/1/1A/1B/2/3/4/5/6/6A/7/8/9/10/11 有执行证据或具体不适用理由。未来实绩未知不能强做回测。
- installed/runtime/CLI 版本实核；skill-required 正式 validate、engine、report render、snapshot 真执行，禁止伪造 manual prose 替代结果。

### B. 资料获取与存储

- RF→FF→CWP→对应 CN SID/HK-US Dayu 调用真实发生；reuse/download outcome 与实际原件 before/after 对应，所有调用 caps 传递，下载后复用0新下载。
- FF main filing / companion transcript 各自状态，ET是否实际调用、配置生效、provider能力、原语言TXT、失败不掩盖。对网页补充明确另一路，不冒称检验了FF/ET。
- SourceRef/Export 不泄露本地存储路径；consumer用CWP验证打开不是读固定root；多根原件可复用、公开日/期间身份真实。用户授权下载正确保存公司目录、SHA/来源manifest完整。
- CWP 初级解析/选择/质量/原文回放每项分辨已跑、复用、未跑；不存在的processed内容不冒称。临时全文/中间物没有写穿生产、永久缓存没有无界增长。
- 不因本地标题可信就信正文。文本/PDF实际company/period/page、格式、尺寸，来源网页的真实内容与本地原件对应；发布日期不能猜。

### C. 全量事实与参数审查

- 枚举 input 所有 source/claim/parameter/history/segment_base/target/growth_driver_evidence。逐个打开原件完整上下文（包括表头、脚注），记录review locator/quotation/hash；不能仅复用执行者摘录。
- 复核所有值/小数/人民币亿与million/USDscale/百分比及百分点、报表期间与as-of、合并/分部范围、外部/内部收入、重分类、毛/净额、实际/指导/问答/假设区别。
- 两年或更多历史基数、分部之和/调整、准则recognized vs订单/订阅ARR/run-rate/backlog；latest communications 与materialtargets不能遗漏。九维有实际搜索研究而非复制九句空泛irrelevant。
- 管理目标全部明确口径/语言/measurement/treatment；来源冲突真实保留。抽取完整性按源文重新检索，不只审查input里已有claim。
- 模型经济合理性独立判断：不足数据不是随意填写精细量价；透明fallback不伪装operatingmodel；每条range/assumption有基础、反证、outsidebenchmark、因果链/leadingindicator/falsifier。

### D. 计算、产物与恢复

- 独立复算历史base、每segment每year/每scenario、recognition、constraint/adjustment、companybridge、growth/CAGR、driverallocation/increment、scenarioordering、sensitivities以及confidence解释。
- 重跑 strong input-required validator，与 input/runtimebinding、publication/workflow receipts、registry/snapshothash核对；在自己的独立TEMP copy重跑calc并剔除时间/签名字段比较确定性数值，不覆盖原执行产物。
- JSON/Markdown为同一正式输出，不有报告额外新数字/研究结论；scope没有价位/评级/仓位。
- 原件beforeSHA保持，config/WIP未越界；工作恢复/ownedcleanup透明，provider费用未偷加，外部LLM符合配置且每call记账。

## 输出

审查只写 `reviews/{company}/review.md` 与 `review.json`，命令也用 run_logged.py落在 reviews/{company}/commands；不改执行者产物、runtime、安装、生产manifest或共享PWF。

JSON字段：`schema_version, reviewer_agent_id, company, reviewed_at, reviewed_runtime, executed_agent_id, verdict(PASS|FAIL|PARTIAL|BLOCKED), checks[{id,topic,status(PASS|FAIL|NOT_APPLICABLE|BLOCKED),evidence,details}], facts[{claim_or_parameter_id,source_locator,independent_value,unit,period,status,evidence}], independent_calculations, missing_steps, findings[{id,severity,category,description,paths,reproduction,requested_fix}], artifact_integrity, limits, command_index`。

无法验证的项目记 BLOCKED/FAIL，不给它 PASS。审查报告可附“数据可靠性”、“工作流完成性”、“模型经济合理性”分别结论，防止一条green掩盖另两条。发现问题立即通知MAIN，执行agent修复后由独立review再检查改变的dependencyclosure；无需无变化全文重复读。
