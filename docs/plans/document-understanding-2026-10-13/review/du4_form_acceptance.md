# DU4-FORM ROOT接收与共同根因修复

2026-10-15，ROOT。作者head 2cde9de9，实现28d90c9c/04dbeb33，工作区只读检查干净，变更24文件全部在包/包测试/独立PWF内。作者72测试ROOT显式作者src+独立临时目录复跑72PASS/2.85s，0供应商、生产配置不变、Temp删除。此结果只证明组件，不是生产router端到端验收。

独立审查与ROOT均复现：单位ID形状校验在扣费前遍历完整列表；raw carrier JSON去重递归读取未计费的value_refs和无关attributes；reserve用list membership二次复杂度。ROOT预算1仍访问20001ID，预算2仍遍历20000refs；独审在200units/200chars真实route cap内同样复现，200turn有19900次reserve字符串比较。属于有界运算责任共因，不能靠延长超时。

独审另发现同owner非连续引用FORM 10-notaform-Q可删中间字拼为FORM 10-Q且complete。修复应保留原文字节/字符连续性，不把“同owner”当成可以跨任意缺口拼接；连续inline引用仍应保持，非连续给逐项诊断，不拒绝其他载体。未知kind list/dict应结构ValueError，不能TypeError。

ROOT将源分支正常合入本工作树后，先加集中RED，再按单一载体遍历与有限语义身份去重改造：工作发生前扣已有WorkBudget；units只遍历一次并同时校验parent/shape；value_refs只在已计费解析后进入去重，不序列化raw或ignored属性值；native attributes仅取固定键、未知键只有限诊断；reserve用有序list+set；冲突/输出仅消费已确定结果。实际work单位的每次迭代含义变化要在测试和收据如实记录，不强凑旧计数，预算实例不重置/不加新阈值。

集中根因反例+原72+路由/adapter现有契约、Ruff/mypy通过，再独立审查修复，正常提交推送。组件完成接收后，ROOT还需一次原生walk生产接线、VRSK/真实电话会/8-K holdout；不可提前称全部DU4或共享引擎完成。TABLE/STATE仍施工，作者树均不写。


## 集中整改和独立复核结果

9个反例初版全部RED；计数夹具发现builder会复制list，直接装回实际input并清零后仍9RED，两个版本均留证。统一修改后81PASS/1.76s；原72+现有profiles/router/adapter/父子scope集中327PASS/14.30s（包含81）。Ruff/mypy两源PASS。独立强制ROOT/src的11组纯探针确认预算尾部访问归零、ignored raw无序列化、reserve比较19900→0、gap不产生事实而连续inline保持、hidden重复不伪装resolved，最终PASS_COMPONENT。根因档和初始REQUEST_CHANGES均保留在[紧凑归档](../common-root-quality-evidence/du4-form-component-receipts.zip)。

测试目录额外做namespace隔离：新增__init__.py、builders/conftest改相对导入，避免将来兄弟包同时collection时共享全局helpers；不改业务断言。327运行早于该import-only变更，最终正常prepush负责复核此版本，不能误称327已跑最终文件。已预冻结的v3请求gzip继续保存在既有不可变归档/owned scratch，未把尚未使用的future fixture混入FORM提交。

原工作预算每unit/carrier/unit-ref/value-ref的计费含义和已有精确计数不变（形状与parent检查合并一次）；没有新预算/门禁/身份检查。未知属性的值和任意扩展不遍历，去重只消费已确定entry；失败/hidden重复保持不可用。原FORM fixture SHA、span原文/locator不改。作者tree原样，ROOT当前merge包含作者完整history，正常提交后再核精确CI。生产E2E/真实原件回放仍NOT_RUN，不提前宣布完成。
