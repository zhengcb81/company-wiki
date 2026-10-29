# W20-AUDIT-CHECKPOINTS ROOT独立验收（2026-10-29）

结论：**需原 harness 改进，暂不并线/安装。2项P2共同根因，7条独立中性断言真实5 RED、2兼容控制通过。** 不是新增审批；是该包自己输出的机械观察仍有错误。主线公司循环继续暂停。

## 已核实交付与有效进展

作者工区 `C:/Users/郑曾波/Projects/revenue-forecast-audit-w20-checkpoints`，实际HEAD `7ac295ffe9582533eb004ad10a8afc97f1bebc24`。基线 `33200f8c`，受测/独审实现 `470e1f9f5e196f5e3975744036aa690507be55ba`，之后仅交接/独审/PWF文档，源码不变。交接清单17文件SHA全部匹配；工区clean、无remote。观察器SHA `613766a9e3e134e8137e85ca5e511e3c1d1e4f4e2db2f5f0c7f8cf7c88677acd`。

改动遵守卡片边界、复用原packet/coverage/four-role/expert，没有新生产分类器/权限/预算库。初审与复审均保存，作者之前确定性修复有效。ROOT只读复跑自身26项通过（0.388秒wall）；公开CLI synthetic 11步通过（3.451秒wall），coverage records_complete/0 gaps。独审已有真实脱敏材料试读，但生产claim未声明锚点字段，多数锚点not_declared，交接已如实写明。该followup不强塞入本卡，也不当已完成生产数字验真。

## R1（P2）先丢失类型/符号/期间，再按词面签正向锚点

责任文件 `skills/revenue-forecast-audit/scripts/summary_checkpoint_observations.py`。

- **比例/金额**：`_number_candidates` L227–248 / `_value_anchor` L259–289 自行乘scale后比数，金额`0.1元`与`比例10%`报`scale_equivalent`。已有numeric_audit.verify_row明确拒绝ratio→amount；仅引用其SCALES并不等于复用其兼容约束。
- **符号**：`_NUMBER` L128无正负号；原文`亏损-5元`、claim value=`5`报`literal_match`。这不是完整数字字面相同。
- **期间**：`_period_anchor` L303–316把完整`2024H1`和降级`2024`用any相或；原文只有`2024H2`仍报整个period `literal_match`。
- **币种**：`currency_families` L200–201把任意含`元`且未识别三币种的文本推为CNY；`5日元`被认作人民币，与claim人民币unit报`literal_match`且无币种风险。

这些不是要求工具做语义判断：`literal_match/scale_equivalent`作为机械标签本身必须准确。报告虽然不发总体PASS，也不能靠该免责声明保留错误的正向观察。

**统一修法：** 字面观察和typed换算分清；可比较的显式数据调用既有numeric owner，比例/金额/币种不兼容或unknown就保留unknown，不新建换算表/权限/生产分类器。保留数字符号；全年/半年度/季度完整锚点和仅共享年token分级，后者可partial但不full literal；取消bare元推CNY，对不支持币种显式unknown，不要求建立无穷币种词典。真实正向12.5亿→1,250,000,000人民币及同期间控制保留。

## R2（P2）明确unread的保留文本仍贡献正向观察

同文件 `_value_anchor` L266–269、`_period_anchor` L306–309、`_subject_anchor` L328起和`_unit_anchor` L342起只以nonempty text认作readable。来源声明 `reading_state=unread`，但保留`2024H1收入1亿元人民币`时，四个锚点全是literal_match。原测试只给unread空串，没测真实缺观察条件本身。

**统一修法：** 在共享入口一次计算显式material availability，两个入口（standalone observe_map、existing packet）一致使用；明确unread的claim-support锚点应not_observed，仍可呈现保留的metadata/context与原missing诊断。不要引入额外来源重授权或把所有文档再打开一次。补unread保留文字、空文字、read正向对照。

## 返工复验（一个大节点即可）

1. 将[7条独立反例](evidence/audit/test_independent_expectations.py)合入作者独占测试包。当前真实5失败/2通过，[RED日志](evidence/audit/independent-red.txt)和[收据](evidence/audit/red-receipt.json)保留；内容全为synthetic，不是公司研究/新资料/新模型结果。
2. 修上述两个共同责任点，避免逐case公司/页码/整句特判。保留已有26项、DU5兼容断言、R1–R6独审边界。
3. 在独立TMP内跑W20短测、必要numeric/period受影响回归及一次CLI chain，不要求又跑121秒全仓；原链路records_complete不等于机械观察全对。
4. 调真正独立agent复审两个根因、全部新反例及最终源码绑定，修复后交新handoff。保持初审/旧RED不覆盖、不改旧金标、不全局安装/擅并主线。

可直接复现：`C:/Miniconda/python.exe -B -X utf8 C:/Users/郑曾波/Projects/company-wiki/docs/plans/du11-source-closure-2026-10-18/review/w20-reception-20261029/evidence/audit/test_independent_expectations.py`（脚本只读导入作者工区，需正确引用该工区；不得拿结果签其他版本）。返回exit1为当前真实RED。

## 清理与证据

所有新TMP/CLI产物只位于总控自有 `.planning/w20-reception-20261029/audit/temporary`，原不存在、测试后恢复不存在；删除45个自有文件、清理前235365B，未采样peak（unknown）。仅保留小脚本/日志/JSON；无生产原件/SDK副本、LLM/下载/密钥读取，作者worktree未改。详见[完整机器报告](audit-review.json)、[测试](evidence/audit/tests.json)、[清理](evidence/audit/cleanup.json)、[SHA核对](evidence/audit/sha-verification.json)。
