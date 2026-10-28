# 已发布 SOURCE 组件 CI 根修冻结

状态：FROZEN_READY_FOR_INDEPENDENT_RECHECK。13 文件完整 raw/LF SHA、四原测试绑定及命令见 `handoff-ci.json`。基线 ec7c8d84 / CI40725371023。源码已停止写入。

保留 ROOT 的原26case **13F/13P** 原样收据（source-use-ci-red/results.log/xml），以及本轮18中性case **12F/6P**（ci-neutral-red）。修复后原26＋新18定向44P/7.83sec；必要影响包 **416P/13.29sec，416 unique**，44全部包含于416，不相加。所有四个原失败测试文件均与HEAD无差异，未删改其断言或夹具。

实际关闭的共同根因：

1. `_EN_DESCRIPTION` 将 product-for/available-in/offered-in 名词修饰当成完整谓语。共享角色证明现在要求有限 comes-in 或实际 copula；裸 reduced relative 不能再落入普通 function verb 绕过。OCR10原失败不再把独立右NP入库，原12隔离控制及整个43case OCR文件通过；合法闭合OCR保持。
2. 中文已收购经营对象被 source-purpose 认作 operating，但动态理由投影后没有共享完整关系可保。现有同句 actor→predicate→operating object proof 接通收购/收購；裸词、金融资产、跨句对象不获得完整业务关系。没有新进展阶段或公司特判。
3. 有效 forecast 独句识别正常，闭合加入 disclaimer 后却被后句 reporting_definition 抢占整个scope。source-purpose 现在在实际 forecast clause 使用既有 issuer-bound revenue_guidance proof；单独 disclaimer 仍非经营断言，不撤销同句会计规则。原主体/年份/限定前提闭合和全部来源指引控制通过。
4. 数值存在被错误耦合于至少两真实值的 ambiguity 阈值。现有结构 sweep 分别缓存“至少一真实 numeric cell”“多值歧义”“完整row覆盖”；正向经营量纲沿现有 table-purpose owner 准入可读性。1实值＋缺失标记的经营行恢复为 unresolved 独立候选，不新增多值质量flag，不进入正式生成support。未知/财务/Other行不因可读性获得support。

必要416范围包括完整 `test_source_support_use.py`（含原真实51scope与缓存/结构控制）、完整原OCR文件、完整 untyped_numeric_prose_controls＋untyped_numeric_quality、完整 guidance_source_controls＋guidance_condition_scope、完整 du11_source_quality/test_business_admission。私有两观察布尔以false默认追加，不改变wire/质量标记；直接generation use仍延期未绑定数值。

仅4源码＋owned test相对v6c变化：table_shapes、assertion_roles、narrative_source_purpose、narrative_support_use 和 test_source_support_use；另8清单文件不变。Ruff4src＋test、mypy4src、scoped diff-check通过；`.c3su`清、config clean。没有消费者、工具、旧测试、PWF/Git/paragraph改动，没有原件/PDF/SDK/模型/下载/新holdout访问。

ROOT继续独审、一次真实native五gold/全views和正常发布。允许新增有正向经营量纲的单值未决候选，不以维持旧38support/0unknown数字作为验收。未宣称新正式供应商摘要通过。
