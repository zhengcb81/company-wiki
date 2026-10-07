# 完成核查发现的批次准备时间预算：窄幅收口

基线ed2dc51/运行aa52cbd。RF6e6b817a三owner、CWP用户配置SHA3609e707只读保护。总目标继续，先TDD验证实际缺口；本单不新增权限、人工签收、状态库、供应商请求或全九重测。

## 问题与公开行为

当前run_batch配置/互斥阶段未计入deadline，_run_owned开始后即使预算在来源身份/语言推断/原文SHA准备中已用完，也会继续下一来源并准备AUTO任务，直到Worker loop才看到到期。既有N4要求请求总时间覆盖准备，不能仅靠worker loop证明。

要求一次请求从run_batch入口使用同一monotonic绝对截止点，准备动作前后检查剩余额度；已到期不再读取后续来源或物化新任务，不发HTTP，返回具名静态错误，实际既有usage仍由现账本读取。存储SHA/身份/语言验证不省略，正常批次与既有恢复语义保持。单次已开始的有界本地I/O无法在Python同步调用中强制打断，停止/SQLite关闭仍有收尾开销；不能把本改动声称为OS级严格实时硬截止。

## 写集与顺序

1. 新一般性Unit反例：metadata耗尽不得打开推断语言原文；第一份语言读取耗尽不得处理下一份；第一份验证耗尽不得开启AUTO；配置准备耗尽不得重新起计时；正常限内保持来源与请求identity。用可控monotonic推进，不靠长sleep或贴实现断言。
2. 仅修改automation/narrative_batch.py及CLI：deadline从run_batch入口传给准备/现worker loop；build_batch_events可选截止参数供生产接线，既有纯调用兼容。CLI对该种超时给静态具名失败并保留实际ledger；不把其他异常路径/源正文暴露出来，不新增公共请求字段。
3. 集中责任包：batch/配置/预算/终态恢复相关短Unit；一个正式本地CLI E2E故障注入验证后续来源零读、HTTP0、未生成AUTO任务、所有原件/旁路任务/生产保护、owner锁释放和目录恢复。再复用现正常配置CLI以证明同一入口仍可完成/恢复，旧预算错误不归零。无需再次全九、真实供应商或已绿kill/ACK包。
4. 当前CI范围Ruff/mypy、正常commit/push、精确代码CI、小收据及总PWF更新；完成后继续final_scope_audit剩余各项，不因补一个deadline就宣布目标complete。

## 状态

本地集中节点已完成：57责任Unit/12.58秒、五个真实CLI/35.78秒（新超时两类及原配置三类），Ruff全CI范围+新Integration、47源mypy绿。真实到期后无第二原文读取/新AUTO任务/模型HTTP，既有付费费用原样保持，同一锁正常恢复成功。10个自身测试/缓存路径恢复absent，清除29351660B临时材料，原件零删；生产17表count/digest与S5收据完全一致、9raw SHA/size/mtime与S7发布相同、DB222408704B/无free页且检查前后SHA不变，RF owner/config保持。正式[节点收据](harness_lanes/results/final_batch_deadline_acceptance_2026-10-07.json)、[当前事实](harness_lanes/results/final_current_source_facts_2026-10-07.json)。正常提交/精确CI尚待发布，不冒称整体完成。

功能TDD已实测：五类配置/目录/元数据/语言/原文验证预算耗尽反例在旧实现5 failed / 0.90秒，全部错误地进入AUTO初始化。窄幅修复后五项0.65秒通过；初次57项责任包56绿/1失败是验证阶段耗尽前已收集两份元数据的测试期望错误，已改为允许到期前元数据但严格禁止到期后第二原文读取。配置到期还明确断言不得打开Catalog。Ruff初查新CLI测试有unused json import，改为直接json.loads。下一运行新真实CLI两类及既有配置入口，再集中静态/发布；无九文档或付费重测。
