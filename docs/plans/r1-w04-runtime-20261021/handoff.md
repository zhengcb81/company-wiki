# W04 ROOT 接收入口

状态：**本地实现及129项测试通过，等待ROOT集中独立审查、整合；未发布主线。**

- 产品提交：`588d46352fdd17834d569b0099613c3d8006009e`、`375c29f915fd9206be1ee01fef2bf2eea4d99a58`。
- 分支：`codex/r1-summary-runtime`，工作目录 `C:/Users/郑曾波/.codex/worktrees/du11-extractive-runtime/company-wiki`，base `0622f242`。
- 精确范围：4个automation源码、1个旧测试改造、1个新测试；[机器交接](handoff.json)绑定实际文件字节SHA、命令/退出码、UTC观测与15项新行为+114原有控制。
- 正常提交的ruff、mypy-contract、host-assumption hooks均通过，无绕过。组合最终 **129 PASS/61.42s**；原RED和测试编写失误均保留在[evidence](evidence/)。

## 交付内容

1. 删除新实验paid coverage repair的env开关、自动retry、第二scoped请求与merge/fallback。raw与official JSON旧env=1都不触第二笔收费；原阅读覆盖与needs_review不伪造完整。
2. 历史partial DTO和snapshot保留；只读结果不再要求新模型/新generation，合法partial具名保留、无新POST/无假final。
3. 统一native输出结算只认实际verify消费的成功summary与精确工件。历史首笔immutable0不改，成功merged final归已证明的第二model operation；普通paid恢复沿唯一原reservation，不新增费用/slot。
4. 新测试真实跑Catalog、source locators、AUTO、metered caller、verify、outbox、受控激活缺口、重开、精确读与compaction。有限provider是测试端口，**0真实网络、下载、LLM费用**。

## 如实保留的范围

- 原真实R2 AUTO路径缺失，未重放历史dirty源码/原DB；原导出不改。当前同类native状态可恢复，不等于旧DB已恢复。
- 未完成多paid pin仍具名unavailable、不新付费；没有可证明final slot的旧fallback返回`output_accounting_unresolved / LEGACY_FINAL_OUTPUT_OWNER_UNRESOLVED`，artifact_ref保留可读、旧零收据/费用不改。这不记恢复成功。
- W07的真实配置0.9/v5 paid中断恢复、缓存和RF上下文消费未做。本包没有更改selector默认、生产配置、原件、安装或其他仓库。
- 测试临时目录已恢复为初始不存在，见[cleanup.json](cleanup.json)。两份自动cleanup的removed=false原日志未改，进程退出后仅清本包新建owned TEMP；不清开始已有`.planning/du11-*`。

**下一步：** ROOT按`product_head=375c29f9`做集中独审，修复确认问题后正常整合W04；W03在其后接线，W07负责一次真实付费大节点。无需重复许可或小节点签收。
