# R1 首家独立executor交接

实际scope：`C:/Users/郑曾波/Projects/revenue-forecast-audit/runs/r1-20261021-cn-wuxi-apptec/scope.json`。run目录同级；初始attempt。N1审查结论/提交由ROOT另行派工时给出；本文不代替它。

## 任务

按运行时安装的revenue-forecast-audit执行卡和完整revenue-forecast技能，真实完成药明康德收入预测全流程。你不是编程修复agent；不改产品代码，遇到阻塞用真实诊断和不依赖它的研究继续，封存complete/partial/failed，交四路审查。不要无限绕同一失败转圈、改库字段或手组RevenueSourceRecord。需要ROOT修复时报告真实请求/exit/原生诊断。

当前CWP/FF/RF/audit版本与安装内容已冻结于versions.json，代码不在本阶段变化。先读scope、对应AGENTS、安装技能全文和相关原生CLI --help。配置由现有Config加载，provider选mimo，不能自填model/endpoint/生成参数；原语言不翻译。不要读gold/oracle文件、其他审查报告或期望事实答案。通用checkpoints是要求，不是已通过事实。

## 权限和独占目录

用户已明确恢复实施、沿既有采集/外发/预算授权，不逐公司询问。你写本run roles/executor、execution及scope隔离wiki；repo生产原件/配置及Dayu只读。跨仓沙箱访问失败时用require_escalated并说明本run具体读写动作，不改Git权限/配置。密钥只使用既有配置环境变量，不输出值。审计工程runs被Git忽略，ROOT会把可复查摘要加入计划，不提交原件/大响应。

不要修改scope/run元信息、ROOT计划、旧NVDA或其他owner文件。初始隔离清单和生产配置指纹已保存在preparation_receipt.json；本次新增下载保留到四审/必要复验完毕，ROOT统一清理恢复。

## 真实接线

1. 首个实际RF source_preparation请求用隔离preparation_receipt里的native argv，通过capture留存请求输入并实际消费。公司身份由该owner一次确认，execution/identity.json保留真实资格。不可把候选603259/目录名/文件名当已核身份/期间。
2. 使用完整result-envelope，包含filing与ET companion独立结果。源查询先reuse_only，缺原件才同任务fetch_if_missing，acquisition_limits不得超过scope。更改请求另存新文件，旧失败保留。当前年报之外必须真实发现截至as-of前新中/季报、材料性IR/业绩/处置融资信息；文档矩阵有IPO/新股/可转债/电话会/演示等全部类型的相关性和实际查询/不可用原因，不能机械N/A。
3. RF→FF→CWP同一个隔离catalog，使用verified SourceRef/公开read。已存在文件不重复下载，不直接枚举公司原始目录研究冒充虚拟化。不复制全湖、不写生产manifest/sidecar。
4. 用正常narrative_batch_configured生产入口正式摘要重点业务内容；request的model:{}由Config替换，profile=P1，selector_version遵当前生产；pricing用母metadata该provider的price_proxy，不猜。不得注入phase_c_observer或其他gold驱动拦截器。RF source_preparation的narrative_request_file实际读取公开bundle，来源摘录和数字仍回原件核对。摘要失败也保留真实状态并继续能做的研究，不拿原文阅读冒充正式摘要。
5. 由scope native_operation_index登记每个将调用的AUTO DB/run/attempt及request引用，先登记再POST。跨本公司所有文档/batch/run/replay累计最多100k tokens/$1，且必须与母账余量取小。调用前先复核已登记native账并用现有phase_c_runner.append_native归母账，mother_totals重计。POST后无论成功失败都归账。未知收费保留全hold，不盲重发；有付费响应用原生resume不换run_id。该索引只含操作引用，绝不是第二收费账。
6. 所有业务工具调用留真实argv/tool ID、输入、UTC、exit/response、bytes/cost/unknown和产物定位。用execution_request build+audit_run capture的真实request/consumed SHA，RF validate/compute/render/snapshot同样冻结并消费输入；多位置输入用freeze-arg-index。capture日志有界，不能整PDF转stdout。

## 研究和交付

按当前RF方法建立九维覆盖、管理层沟通/目标、独立经营参考、至少两期历史、可比业务合并边界、识别实际收入曲线/确认政策、三情景三年经营桥、因果树、敏感性和共同冲击、置信度/边界。条件化预测有真实数值，但未来假设明确标记，不能编造已观察区间/来源/共识；当前信息缺口不意味着把所有未来单元留空。研究报告不含估值/评级。

每个报告事实/数字追到source+locator和原文上下文；原始币种/scale/FY/季度/累计/CC/并购处置口径不丢；billion/亿转换明确。每项claim/parameter进入native DAG的对应关系可查。当前RF原生校验失败不通过修改库/降低规则掩盖；一次collect-all诊断后，只对具体新研究输入缺陷修正，不循环拍脑袋填字段。

execution产物按artifact-contract：manifest、step_ledger、document_matrix、source_ledger、facts/parameters/calculations（原生等价索引即可）、forecast/input+engineJSON+MD+snapshot+support diagnostics、TRUST_BOUNDARY。注册/输出registry仅owned目录。

普通缓存/恢复要求属于本轮大节点，可先完成基线摘要并保留native refs/paid响应供ROOT做一次受控恢复；不要为每文档额外收费恢复，也不打开默认OFF实验性two-attempt修复开关。

执行结束或真实阻塞时：先封存manifest与actual outcome，再交ROOT。交接说明真正完成/未完成步骤、失败根因线索、真实费用及unknown、隔离文件保留状态、下一可执行动作。不要给自己质量PASS，不读四审初稿，不替其他角色写报告。
