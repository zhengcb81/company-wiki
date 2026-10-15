# DU4-TABLE / STATE ROOT集中接收细则

2026-10-15。用户已通知两包完成，保持固定du4-interfaces/1；本文件归ROOT共享PWF，不改作者独立记录。组件测试不代表生产共享引擎已调用组件。

## 实际接收状态

| 包 | 作者head | ROOT复跑原测试 | 范围 |
|---|---|---|---|
| TABLE | fa1681c0514df4b1896857ff56baa60be5729fc7 | 36PASS /0.89s | 31文件，均新组件/本包测试/独立PWF |
| STATE | 284eea600764e0dfe98270c364c9c6cd2c095478 | 90PASS /3.25s | 22文件，均新组件/本包测试/独立PWF |

两个作者工作树正常host只读status干净；沙箱Git曾报worktree/cwd PermissionDenied，正常host读取成功，不能据此诊断作者Git配置或历史损坏。测试只读作者src，输出和Temp由ROOT所有，结束删除Temp，配置/sentinel保持，0供应商。owned收据在`.planning/shared-reading-production/du4-table-state-acceptance/`；最终以紧凑归档发布，不提交整个scratch。

实际Git字节核验：TABLE gzip及两个源夹具当前符合声明SHA；STATE cn-ir-observation.json工作区SHA为f70cc6f4…ba086a，符合原manifest，但作者旧Git blob为d71de3f1…c0ae2（换行转换）。ROOT合入后从已验证工作区只读取准确字节，并按现有`.gitattributes`定点暂存；不修改原manifest、不改gold，不对历史全树renormalize。

## 同一个接收大节点的实施顺序

1. 独立只读审查两个包的真实引用、数值列/期间/单位、否定/主体/阶段、偏移及运算边界。ROOT同时复跑原作者测试和Git边界，已完成上表；不另设小节点人工批准。
2. 对每个实际复现的阻断先写集中RED，再共同责任修复。重点验证STATE预算前全units/context复制、归一化扫描；TABLE未计费header/provenance/range扩张及每列/每值重复扫描。不能只看到work_used小于上限就称真实工作已受限，也不能通过提高cap/超时掩盖。预算仍由既有WorkBudget实例负责，组件不得重置。
3. TABLE语义负控：外parent/外page的表头与行单位不能绑定当前值；日期范围起止和重复/冲突标签不能首个匹配即定为end；合并格无逐值定位仍unknown。STATE负控：连接词/前缀消隐后actor/object原文偏移准确；发行人与股东、联系与合同、希望与出货不互换。待探针确认后记录事实，不先把源码疑点写为已复现缺陷。
4. 两作者分支合入ROOT保留commit历史；仅ROOT改接收副本。测试helpers改包内导入、删除无fixture的重复bootstrap，复用仓库tests/conftest.py；避免兄弟包同名helpers/import及测试目录结构影响真实验证。原作者记录不改。
5. 两组件+FORM+当前路由/adapter/原文scope集中回归与独审复核、静态检查，随后一次正常提交/推送/精确CI。保留首个RED和未测范围；不运行每个小步的全库测试。
6. ROOT继续单一共享引擎生产接线：同一次native观察、同一WorkBudget、原cap预留与依赖闭包、唯一router/经营谓词/表格解释、正式v4摘要/旧缓存恢复及真实holdout。未完成前默认0.8，组件接收不宣布全文召回或真实摘要质量达标。

## 仍属生产主线的责任

TABLE作者真实HK包只为保留的部分原生观察，包含明确的测试适配派生；34bound/7ambiguous不是全财报召回率。STATE真实m41与合成holdout分开，当前二元回答无观察指代不猜；语义模型/第二真实公司/RF消费者验收仍由ROOT承担。当前新v4尚未实现，原六错引/业务遗漏FAIL继续保留。

## 独审已复现的接收阻断（2026-10-15）

显式作者src纯内存探针已确认：TABLE可以借外parent的日期/单位仍bound；明确Six months from January 1, 2024 to June 30, 2024把start/end均填January 1。STATE对未签署/计划签署/尚未建立联系/计划商业化/has not signed出现positive actual/current，前导空白/连接词还会令actor原文ref错位。预算0仍遍历STATE1001units、转换5000字符、复制10000context；TABLE零费用遍历10000header_rows、work2遍历10000provenance，work4耗尽后仍扩张5001列范围。

这些是有限合成反例，不是生产事故统计。按上面同一接收节点先ROOT可执行RED，再统一来源ref作用域/日期事实组合、状态谓词及qualifier绑定/原坐标映射、预算前运算与索引复杂度修复；不按公司/词组各打补丁。两包当前为REQUEST_CHANGES_COMPONENT，不能称已验收或生产接线完成。独立原始probe保留在owned independent-review目录，最后同一节点集中复核归档。


## ROOT最终组件验收

## ROOT当前状态 — 2026-10-15 DU4三包组件集中接收

FORM已发布master cbfe3e7f，正常推送5784PASS/24SKIP321.47s、精确CI38804974095 SUCCESS；文档收尾de6b4660已正常推送148PASS/26.54s，docs-only无workflow。TABLE/STATE用户均已交付，作者head fa1681c0/284eea60，36/90原测试ROOT复跑通过。两分支已合入ROOT待提交工作区，保留作者完整历史；独审发现的7类共因经集中RED/共同责任修复，最终三包+Git字节 **251PASS/6.42s**，独立纯探针复核通过，Ruff/mypy8源PASS。仍待正常提交/推送和精确CI，不能先称两包已发布。

修复包括真实ref作用域与表头可用性、明确起止与同标签冲突、单位维度保留、稀疏原生列/一次label缓存；STATE限定词/条件/假设、主句与供应商从属描述的主体隔离、控制动词对象及原文偏移，原relative反例中取得类助动词也不再被当成对象。所有变量长工作先扣原WorkBudget，无第二预算或重复身份流程。23初始RED、后续4/3/6及aux1RED与旧失败均保留；foreign row仅剔除并partial为原绑定定义允许行为，不为此新增整表阻断。STATE真实fixture恢复原manifest准确字节，不改gold；作者目录不写。

细则见[两包接收](du4_table_state_acceptance.md)，证据见[紧凑验收](../common-root-quality-evidence/du4-table-state-acceptance.json)。**组件通过不等于生产接线或语义完成**：默认0.8、新0.9仍v3，新v4未实现；六错引/重要遗漏、真实holdout、HKIPO性能及母G2/G4/G5/公司循环继续开放。原件/配置/sentinel保持、测试Temp删除，0供应商，累计599590tokens/385113µUSD预算代理（旧unknown7；限2M/$20）不变。

**Next Step：** 正常发布两包组件；三包均到齐后先统一source-owned生产接线（FORM native/carrier→原cap/router、STATE唯一经营谓词、TABLE原生槽/解释依赖），再完成v4正式边界/源任务覆盖/费用恢复和真实摘要验收。先修来源作用域可避免新协议绑定旧错误来源，不重复付费探路。只在原A/B/C和母G大节点集中验收，未完成不切默认。


收尾工具曾把混编码prepush日志严格当UTF8读取而失败，随后依赖manifest不存在的commit准备也停止；原日志未改，改为仅在计数观察时替换坏编码，raw完整归档，之后正常完成FORM文档发布。没有错误提交或跳hooks。


提交前diff --check发现作者RED日志保留pytest实际尾随空格，以及参考Markdown的硬换行双空格。原始RED不修剪，按既有fixtures/evidence的原始字节角色统一将PWF results声明为-text/-diff/-eol；不批量重写旧结果、不动源码检查。参考Markdown仅把两处等价硬换行改为反斜线。首次提交准备在check处停止，尚未commit，错误和修法如实保留。

提交准备重试又遇到已从index移除的新conftest路径不再匹配；修复ROOT准备脚本只暂存仍存在或index仍跟踪的清单项，保持同一允许范围与精确最终文件集合断言。这是准备工具幂等问题，无源码/测试失败，也未产生commit。


## 组件正式发布

两包已正常合并并推送master `a4cb40c9`：**5948PASS/24SKIP，515.93秒**，精确CI **38810541475 SUCCESS**，作者完整history保留。[发布收据](../common-root-quality-evidence/du4-table-state-publication.json)。

后续生产接线/真实质量仍开放；以task_plan当前状态及du4_production_integration.md为准，组件发布不是默认切换。
