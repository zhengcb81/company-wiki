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
