# G5 三包 MAIN 正式验收（2026-10-07）

> **后续当前状态：**G2-08 FF安装修复及真实闭包同步已完成，见[G2-08正式验收](g2_ff_installation_acceptance_2026-10-07.md)。本页下方剩余项为G5验收当时的历史时点；当前施工入口为task_plan。

## 当前结论

**complete：三包已正式验收、合入实际执行分支并推送。** 配套的G2-12单请求获取、FF和当前兼容pin也已发布。目标仍active；G2剩余安装收口、R2、R3、R5仍需实施，不将三包完成当作全部项目完成。

| 包 | 实现commit | 已发布执行分支 / HEAD | 结果 |
|---|---|---|---|
| G5-CWP-CHECKS | b3e7f74 | CWP master / 057f1cd | 六旧工程/批处理壳薄退休；真正来源质量反例迁移保留；MAIN更新caller分类 |
| G5-SID-RUNTIME | 7a4bf0d | SID v2-clean-rewrite / 47e1059 | CWP provider不依赖browser；身份查询、公告、下载共享真实预算；adapter1.3.0合同保持 |
| G5-RF-INSTALL | a2116ca6 | RF main / 436fed68 | 指定文件/零写plan/只写差异/准确partial与恢复；实际8文件定点安装完成 |
| MAIN配套FF | 5001dcb | FF main / 5001dcb | 一次ensure及资源scope；新增4个便宜CI反例；旧expiry仅诊断 |

详细完整SHA、保护清单和证明范围见[结构化验收](harness_lanes/results/g5_main_acceptance_2026-10-07.json)。SID远端仓库名仍为StockInfoDownloader，但本项目仅维护简易版的`v2-clean-rewrite`执行分支，不维护旧main。

## 一次集中节点的测试

| 责任包 | 实际结果 | 耗时 |
|---|---|---|
| CWP全Unit + G5真实退休CLI E2E + gold质量/突变 + caller合同 | 2048通过，0失败/跳过 | 157.635秒 |
| SID API/预算/身份/G4-G5及实际离线CLI + 当前已提交CWP消费 | 163通过 | 44.369秒 |
| RF新定点安装及三tmp目录E2E/失败恢复 | 17通过 | 19.267秒 |
| RF既有installer/包装及兼容manifest | 40通过（16安装/包装、24兼容） | 11.106秒 |
| FF与当前CI对应的21文件责任包 | 391通过、4跳过，78子测试通过 | 74.362秒 |

FF JUnit计数473包含子测试，不等同473个pytest用例；跳过不记为通过。SID测试在clean `_g5/sid`完成，其HEAD与已并入/推送的执行分支47e1059相同；原仓11个owner未提交改动未混入测试。

正常静态commit检查和pre-push也通过：RF107短测、CWP短合同smoke、FF静态/配置/声明/BOM。没有新增每commit完整pytest；文档收据发布复用此次已绿源码节点，不重复长包。

三个有workflow的仓库均核对精确源码HEAD：

- CWP057f1cd：[CI37692354260成功](https://github.com/zhengcb81/company-wiki/actions/runs/37692354260)，[收据](harness_lanes/results/g5_cwp_exact_ci_2026-10-07.json)。
- FF5001dcb：[CI37692509218成功](https://github.com/zhengcb81/filing-fetch/actions/runs/37692509218)，[收据](harness_lanes/results/g5_ff_exact_ci_2026-10-07.json)。
- RF436fed68：[CI37692576850成功](https://github.com/zhengcb81/revenue-forecast/actions/runs/37692576850)，[收据](harness_lanes/results/g5_rf_exact_ci_2026-10-07.json)。
- SID无workflow，不声称远端CI；已正常推送`origin/v2-clean-rewrite`。

RF当前兼容组合为FF5001dcb、CWP057f1cd、RF实现0d8b5ded。manifest提交436fed68不把自身SHA写入自身文件，避免自指循环；旧冻结baseline/registry不改。

## 实际接口、安装与原件保护

1. CWP六壳仅stdlib退休/exit78，零模型、Store、生产目录和签收；有价值gold来源/未来公开/定位反例仍在。MAIN将legacy caller文档中的`test_framework`分类同步为已退休。
2. SID保留source候选/receipt/wire和identity责任；不要求上层新加org_id，也不通过预seed全公司cache假装解决。实际identity/API调用使用同一字节与截止时间预算；Dayu/IQS零写。
3. RF `--file`只选择指定文件；`--plan`零写；实际失败如实报告written/not_written/conflicts，恢复幂等。当前8文件已应用到`.agents/.codex`两个物理目录；`.claude`是`.agents`别名，因此3逻辑入口共16次物理文件写入，历史“24条”估算不再当实际数量。
4. 实际RF安装经只读plan后执行；未选文件size/mtime清单不变，config/output无删除；两个物理目标各help/version成功，重复同步0写。证据：[真实安装](harness_lanes/results/g5_rf_real_install_acceptance_2026-10-07.json)、[只读plan](harness_lanes/results/g5_rf_install_plan_2026-10-07.json)、[应用结果](harness_lanes/results/g5_rf_install_apply_2026-10-07.json)。不声称整套安装全MATCH。
5. G2真实FF→ET→CWP链：CN v1/v2第一次下载、第二次零fetch；US真实HTML复用及实际ET worker原语言JSON入库、第二次provider0；四次真实binary reader核SHA。HTTP与identity是明确离线夹具，不冒充live供应商权益。未知电话会公开日期仍未知，preview不冒充as-of预测资格。[实际链证据](harness_lanes/results/g2_chain_e2e_accepted_2026-10-07.json)。
6. 18个owner/生产保护文件最终SHA与节点前完全相同。RF pre-commit stash恢复曾把weekly_manifest的CRLF转成LF；JSON和未提交patch内容不变。只有重建CRLF字节SHA精确等于预先保护SHA后才恢复换行，未用HEAD覆盖owner内容。原件删除0、模型/翻译0、Dayu/IQS写0。

## 尚未完成与下一步

**MAIN下一步：G2-08 FF installer系统修复和实际三文件定点同步。** 旧`tools/sync_installs_b3.py`会删除manifest外用户文件，不能用于当前安装。先以TDD框住用户配置/输出/额外文件保留、选择/差异/幂等、失败清理和准确结果，再升级正式工具；随后仅同步已发布的SKILL.md、fetch_filing.py、filing_contracts.py并验证实际入口。此项与已通过的RF installer分属不同项目。

继续核G2A/B和当前指导的一致性，然后R2真实生产metadata/ET登记→R3正式final及RF/StockWiki消费/恢复/空间→R5最终收口。R4已有证据决定不做对象化迁移，不重复已绿模型或测试，也不恢复人工签收。生产final当前仍0；预算与模型配置不因本次三包验收变化。

## 交接错误与修正

- 最后保护校验失败来源仅RF日志换行，按上述精确SHA方法恢复，18文件复核通过。
- 首次RF CI查询误录完整SHA，已从实际Git读取436fed68完整值，按精确HEAD核CI；不以空结果或别的commit冒充绿色。
- 报告路径首次误在results下找Markdown；实际报告位于总计划目录。
- PWF批量更新首次未识别前置空行，断言在写入前拒绝；调整匹配后更新。首次Markdown替换patch重复目标被拒绝，未改文件，改用已知目标的单次写入。

PWF当前状态/Next Step/四张G5卡页首同步；原施工历史保留且不再重派。

## 测试临时资料恢复

G5本次owned测试根、JUnit重复文件和MAIN临时脚本均已清理并恢复absent，结构化测试/CI/真实安装证据保留；交接工作树和五个历史未分类根保留。首次清理在RF负例创建的junction处按保护规则停止，确认链接与目标均位于本次owned测试根后仅移除链接，再清理根；未跟随链接删除其他目录。首次已删除CWP根的大小未及时保存，不虚构该部分空间数字，其余实测删除5024834字节。[清理收据](harness_lanes/results/g5_temp_cleanup_2026-10-07.json)。
