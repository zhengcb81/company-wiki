# 策略升级后的legacy快照补审

独审人：`/root/w08_reporting_rule_review`。结论：**PASS，仅针对本次四个legacy策略投影快照更新**。没有修改先前最终报告或其SHA绑定，也不重新签发全部材料/摘要/RF完成。

原漂移测试明确规定policy upgrade可更新快照，并持续要求几何元数据不进入legacy wire。更新理由已由前一轮真实源标题/口径问题、五family策略变更和61项独立组件验收支撑，因此本次不是任意按当前结果刷新全部gold。

独立验证采用`912f6fbd`里的旧fixture和其父提交里的旧catalog作反事实。原生产registry加载旧catalog时，15个legacy投影精确还原旧fixture全部hash；加载当前已审catalog时，15个投影精确匹配新fixture。只有`hk_periodic`、`sec_20f`、`prospectus`、`earnings_call`四个变化；另11个key和值都未变。旧/新catalog实际变化的family恰为已审五个：HK中期、20-F、电话会、A股IPO、港股IPO；两个市场IPO共享现有prospectus legacy绑定，故形成四个wire变化。`policy-baseline-upgrade.json`的四组before/after与独立计算一致。

漂移保护的反控直接调用原测试：在内存中给未授权的cn_annual阅读问题增加语义变化，原断言仍抛AssertionError；只改变该family的几何意图元数据，原断言继续通过。这证明没有删断言、通配放行、全体失效忽略或几何字段泄漏。

当前原产品源码、原几何测试本体及原case01相对`912f6fbd`的`git diff --exit-code`为0；先前独审绑定的16份产品/规格/测试/源case文件SHA也全部未变。新baseline只替换四个已审预期投影hash。原source gold字节没有为了适应代码而改写。

实际集中执行 **112 passed / 0 failed / 0 errors / 0 skipped，2.57秒，exit0**：68个几何策略测试、17个作者永久策略测试、24个既有registry测试、3个独立baseline反事实。JUnit为`baseline-followup.xml`。运行在非沙箱，使用本目录独占`.tmp-baseline`，仅关闭夹具路径自动向外迁移，未跳测试；完成后自有临时目录及本目录pycache精确清理。没有网络、模型、下载、生产修改或新许可门。

正常push的原8215P/1F/24skip失败记录仍应保留为失败，不能被本补审112P覆盖成原push成功。ROOT仍须正常提交/推送并观察精确CI；本报告只确认此快照更新与既有审过的策略升级严格对应，且漂移保护仍有效。
