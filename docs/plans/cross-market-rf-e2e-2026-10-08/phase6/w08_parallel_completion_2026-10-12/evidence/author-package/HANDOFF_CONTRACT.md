# W08 共用交接接口（工程记录，不是许可门）

仅A设计/TDD、B集中回归、C一次实际E2E三个大节点。平时可跑必要小测试，不增加逐文件人工审查。正常commit后STOP交ROOT；不push main、不合并其他线、不安装技能、不改CI/hooks/生产配置。正常hook失败记录原因，不用--no-verify，不删旧断言。ROOT最后收集三个交付并串行接线、修core、并主线、安装和精确CI。

## 文件

自己docs/handoffs/<plan_id>/handoff.md与handoff.json；JSON schema=w08-lane-handoff/1。包含lane_id、plan_id、repo/workdir/base_head/branch/implementation_commits/handoff_commit、scope_status=COMPLETE|PARTIAL、changed_files(path/sha256)、readonly_input_manifest_sha256、A/B/C记录（UTC/真实命令/exit/elapsed/结果/证据ref）、case_coverage(expected IDs/实际运行IDs/missing/unknown)、actual_code_binding、cleanup(before/after/remaining)、resource_usage（未测用null）、provider_calls/llm_calls/cost（本包都0）、known_baseline_failures、新缺陷最小复现、remaining、ROOTintegration建议。

实施SHA可取提交代码时的HEAD，handoff_commit若自引用不可填则交工消息补精确SHA，不猜自身hash。记录完整changed_files含计划/测试/工具，但不用复制整仓hash。初始input不可改，准备的START_HERE/施工卡/INPUTS是独立上下文；自己PWF写进度即可。旧本仓AGENTS职责边界适用。

每个产品/工具问题按issue→机制→最小反例→所属责任层→修复建议→测试记录映射；未执行/未知/外部限制不能PASS。只检查本层职责，不叠新身份、hash必填、授权JSON、人工签收、canary、第二budget/state库。

## 测试恢复

首次记录absent或已有文件/空目录/sentinel；只清理该次新建且确定归属的scratch。保留初始文件与报告；不global kill，不删除其他agent数据；失败/timeout也恢复，无法恢复交准确残留路径。保留少量关键失败与一个最终压缩证据，实际payload不重复复制。Code-only快照不是全湖备份；累计所有报告建议≤8MiB，峰值未测填null。

## 独立运行

不能读另一W08工区或等待另一包交付；所有必需输入已在本工区/固定input可得。ROOT主线升级不会进入本包代码，固定base保持。需要其他层新增API时给ROOT建议；本包不得偷偷改邻仓。只有ROOT批准的新版本输入才另建新的证据attempt，不倒改初始manifest。
