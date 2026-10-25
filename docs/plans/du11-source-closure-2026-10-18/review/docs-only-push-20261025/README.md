# 纯计划推送重复测试根修

## 事实与范围

`09a758c8`是PWF/调查更新；现有changed_unit_tests已返回空列表、no behavior changes，pre_push_gate却无条件合并FAST_CONTRACT_CASES，154项耗时160.83秒。不是测试失败，也未测量耗时波动的其他原因。

最终修改tools/pre_push_gate.py、tools/changed_unit_tests.py与两份对应测试；独审发现旧分类器漏判后，已将明确文档/归档与未知资源分开。hook、CI、原件和外包工区未改。空选择由完整push range分类取得，不能仅凭reason文字跳过。空目标在pytest分发前显式返回，避免空参数触发全仓测试。

## 实施与大节点验收

1. TDD：可信空选择不分发/不宣称tests passed；真实隔离Git仓先基线push，再纯计划push；随后未推代码失败+最后文档commit仍阻断。
2. 实现空列表分支；修旧测试中“纯文档必须跑smoke”的过期政策假设，把原契约覆盖断言改用真实runtime/未知范围输入，不移除失败传播、未知/config/dynamic、显式CI/full的断言。
3. 集中运行门禁相关定向测试、Ruff；真实Git仓和资料放独占tmp，成功失败均清理。独立agent检查最终代码、范围判断、测试完整度；问题全部修复后发布。
4. PWF更新且正常提交推送。下一长期节点仍A01/A05层级来源，不将此效率修复当作内容或RF验收。

当前：实现和ROOT验收完成，独立产品探针PASS，等待最终报告后发布；无新增API费用。

## 独审扩大根因（尚未发布）

第一轮3项RED后初版105项通过（178.82秒），隔离环境清理成功。独审发现旧classifier对根config.yaml、未知.ps1/JSON同样返回空，因此单改gate会放大旧漏分类，不能发布。先新增配置/未知资源/混合计划与产品目录Markdown的集成反例，再由classifier唯一owner明确哪些是文档，其他未知资源保守fallback。原docs/receipt.json测试改为docs/plans/run/receipt.json：通用JSON不能仅因在docs目录就当非运行物。保留初版通过结果，不能拿它代签修复后的版本。

## 最终验证边界

- scope-red为14 FAIL/11 PASS（4.70秒）；修复后四相关文件主跑129 PASS/1 FAIL（160.84秒），唯一失败是Git自带sh在hook启动前NtCreateDirectoryObject失败，没有到达缺runner断言。保持断言不改，只将该原例主机单跑：1 PASS（3.36秒），收据environment-rerun。不能写成一次130全绿。
- 新真实Git联调通过：纯计划probe.py推送不启动pytest；前一未推代码失败、最后一commit仅文档时，仍拒绝推送。显式fast/full、unknown/config/dynamic、失败/启动错误传播及完整ref范围保持检查。
- 所有新建独占临时Git仓、bare remote、pytest目录均按收据恢复不存在；Ruff/diff-check通过。既有pre-push mode工作未改动/暂存。下一长期节点仍A01/A05。
