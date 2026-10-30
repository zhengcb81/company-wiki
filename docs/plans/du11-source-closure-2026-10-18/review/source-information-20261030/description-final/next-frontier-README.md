# M6 后的单一 frontier（只读交接）

**下一操作是恢复既有 C3 冻结来源 holdout 的资格检查点，先读 manifest 及其 source-review/qualification 收据；现在不启动模型或重抽样。** ROOT 已确认 M6 `09be`、CI `41079560122`、部署及新进程验证全部闭合；读取时 CURRENT_STATUS 仍含旧 M6 文案，不能据此重跑 M6。

最新 CURRENT_STATUS.json 的明确顺序是“fresh source holdout and company loop”。它尚未绑定一条当前版本可直接执行的 holdout 请求。因此本次能确认的是下面的第一读取操作及缺口，不能凭历史卡片补造一次执行命令。

## 第一读取与固定输入

先读 `docs/plans/du11-source-closure-2026-10-18/review/pdf-c3-20261026/holdout/manifest.json`，再读同目录 `independent-source-review.json` 和 `.planning/c3-20261026/holdout-exact-registration-v2.json`。绝对路径及当前字节 SHA 均在 README.json。该 manifest 于 2026-10-26 冻结，PWF 仍记录 `holdout_candidate_output_produced:false`、20 检查点/101 support units、source-review `PASS_WITH_GAPS`。

冻结样本保持不变：华利 CN 中文 IR，SHA `d4cec6d3…`；Berkshire 2008 英文股东信，SHA `46920242…`。后者不是 SEC 10-K。exact registration 只证明原字节可读，明确不证明 issuer/period/asof 资格。两份资料的官方字节来源收据仍缺失、publication 未知；Berkshire 原 HK metadata 有误，须交既有 source-facts owner 在隔离 catalog 正确处理，不能用签署日补出版日。资格缺口不阻止这次只读检查，但不能跳过后宣称正式 source 合格。

检查点：核 manifest/gold pin 不变且不向 executor 泄露 gold 答案；核 exact SourceRef 和当前 source-owner 状态；核这两个 SHA 是否有后续 candidate 暴露；冻结当前 producer/安装/config 指纹，之后再确定兼容的现有 source-only replay 入口。不能假定 W18 的 manifest loader 接受 C3 schema。选材可见性、context、输出和独立语义结论分别记录；不以匹配率代签语义。

## 为什么不是重新跑 W18 或直接下一家公司

CURRENT_STATUS 的 W18 接收已明确 `candidate_started:true`、`new_blind_holdout:false`。它的工具/oracle 已接收，适合回归，不能改称新盲测；旧作者 COMPLETE 不代表新版本内容通过。万润 IR、8 开发 gold、中微 H1 实际采用及微软/名创开发档案同样不计未见 holdout。C3 两源也只是一段来源侧 holdout，不覆盖 HK 或 US SEC 财报，更不等于完成三市场公司循环。

来源 holdout 处置之后，完整公司任务恢复既有药明康德 W12 新 attempt，再药明合联 → Snowflake。固定 run 为 `C:/Users/郑曾波/Projects/revenue-forecast-audit/runs/r1-20261021-cn-wuxi-apptec`；W12 在其 `remediation/r1-final3-review-20261022/work_packages/W12.md`。旧 `r1-remediation-01` 封存，不覆盖、不重新 init/reset。技能入口是 `C:/Users/郑曾波/.agents/skills/revenue-forecast-audit/SKILL.md` 的第6步原公司再验收，同时保留完整八步义务：真实 RF、四路独立审查、第7步质量巡检、第8步检测演进及新 attempt 实际采用。旧 scope 的 100k/2M 等历史限制须与当前政策明确对齐，不能当现行母预算。

W21 canonical C2/长路径和 US RPO 仍 OPEN；已读取的权威状态未说明它们是本次 metadata 检查的全局前置。不能从旧 THREE_WORKTREES 或历史待实施段落重跑已经发布的工程，也不能在没有目标证据时把所有 OPEN 串成许可门。

## 预算与未确定项

本次下一操作为 **0 POST、0 下载、0 新解析、0 费用**。现行 config 为累计 10M tokens/$20（含 unknown），公司软目标 150k/$1，document work 16M。最后母账观察 1,827,558 tokens/$0.732814；这是历史观察，任何真正收费前由 native owner 重算，不是本次确认的实时余额。

仍待 ROOT 绑定的具体项是：当前 fresh holdout 是否继续这份冻结 C3（而非另有未读新交接）；source-facts 资格缺口的当前状态；兼容 replay 的实际 argv/当前 producer SHA。**信息不足时先读上述 manifest 和绑定收据，而非启动 paid 或更换样本。** 本报告没有执行候选、API、下载、解析或修改母计划/产品。
