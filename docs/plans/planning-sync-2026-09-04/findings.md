# 三仓规划一致性 — 发现

> 2026-09-06后继说明：下面GP008/sections/daily等描述是9/4～9/5发现快照，不是最新状态；已由[9/6原痛点审计与同步](../painpoint-outcome-audit-2026-09-05/README.md)覆盖。旧manifest/receipt/inventory字节不改，历史范围完成不等于产品目标完成。

## 范围与初始状态

- 三个用户指定目录都存在，均为Git仓库；此前App项目列表并未列出filing-fetch，已由磁盘确认。
- company-wiki存在既有代码/临时文件改动、38个旧worker计划文件删除和新v5未跟踪目录；不恢复或覆盖。
- filing-fetch初始授权git status为空。
- revenue-forecast有未跟踪audit_review、assurance运行证据及众多.tmp/.review夹具；不能视作本次产物。
- 部分.tmp-zr408-unit目录即使授权读取仍拒绝访问；是否含planning文件需单独盘点，不能记已读。
- worker v5当前是基线导入完成而非正式v5计划冻结/实施通过；导入快照必须保留原字节。

## 审计原则

“最新”指当前可证实状态和权威入口，不把历史审查报告改写为当前结果。
有hash绑定/审查签署的文件作为历史证据保留；通过当前状态侧说明解决旧计划被误当活动计划的问题。

## 2026-09-04 已确认的不一致（文档修订前）

- company-wiki 与 filing-fetch 的 TERMINAL_NOTICE.json 均将根三件套封存为 closed_superseded_incomplete；不得直接更新成新的活动队列。统一旧范围账本在 revenue-forecast/assurance/unified_completion/state.json，新 GP 续作不能被旧117 accepted掩盖。
- company-wiki 四个旧子计划共13份Markdown已全文读取：catalog-space-remediation（含granularity-proposal）、core-section-extraction、portfolio-reuse-automatic、portfolio-reuse-fix。它们已有8/9历史覆盖，但findings中无统一历史警告，仍有“规范栈无章节”“只认company_raw”“Strategy A应自动提升”等已失效结论。应统一指向当前状态索引，保留带日期原证据。
- granularity-proposal 的“旧locator不重写”和“DELETE旧span后重解析”不能同时作为无条件执行保证；仅提案不代表迁移或兼容验证完成。
- CodeGraph确认当前存在 extract_sections_catalog 与只读 SectionQueryService；因此8/6“无章节能力”属于实施前记录。本次不运行业务测试。
- worker v5 的README/task_plan/findings/progress四份已全文读取，当前状态正确：V5-0/V5-R完成，V5-1/V5-2待办；历史progress多处“当前”按日期解释，不改import/baseline。
- 本轮只读 worker_control 仍 desired_state=paused；HKCU Run 查询无该值（后续显式核对读取成功）。未触发恢复。
- filing独立审计报告：E2E设计夸大为全链路、synthetic seeds及hook描述过时；FC-903 reviewer绑定的implementer hash与当前字节不符，不能重签旧收据来消错。
- revenue独立审计发现：GP-008 daily注册参数 --run-daily 与当前子命令 run-daily不匹配；GP-006 CI仅临时roots且非阻断；GP-010已执行但summary6/7。这些须同步活动计划，不能仅改日期。
# 2026-09-05 revenue 最终范围与并发漂移

- 独立范围复核确定 canonical planning-with-files 为93份、25,163行，全文93/93；新建根状态入口后为94份。46份冻结输入SHA重算46/46匹配。`assurance/fc` 16份及unified receipts 194份属于执行证据而非计划正文；13个不可访问tmp目录保持UNKNOWN。
- revenue HEAD在审计期间从`6b4e3cf`推进到`2cbd585`，旧patch已作废并重新编制。当前HEAD虽修复电源条件、StartWhenAvailable与22:00触发，但注册器仍生成`--run-daily`，parser仍只接受`run-daily`；安全探针在argparse阶段失败，GP-008仍是代码阻塞。
- 9/4 broker分节能力已落地并真实执行，七份目标研报由sections=0推进为5/7；不能沿用旧0/7，也不能把能力代码或registry 197/197提升为生产7/7闭环。
- 新patch SHA-256为`80acde09d9ee07a40deba7cdaac4abcf4ec5031501458cb9cd79734e067d4d0d`；编制时六个目标文件CAS分别为task `c47e5e47...`、findings `4795e004...`、progress `78aa9279...`、deployment guide `48d76850...`、GP010 `11a0c6d8...`、N1/R9 `8d287d55...`。应用前必须再次相等并取得独立review PASS。
