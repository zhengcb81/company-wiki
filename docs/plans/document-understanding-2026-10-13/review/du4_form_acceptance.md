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


ROOT已正常merge commit8406461c，推送前进一步去除测试专用重复bootstrap：仓库tests/conftest.py本来已把当前src插入首位，新包的conftest没有任何fixture，只重复改sys.path并存一个fixture目录常量。将常量迁入本包builders并删除这份新conftest，保持全局已有隔离fixture/网络拦截不变；避免新局部bootstrap不必要地触发全库prepush，也消除测试工作树进口分叉。不是修改CI选择器、跳测试或弱化断言。作者原工作树conftest保留不变，ROOT整合通过统一测试入口。最终集中组件和正常push重新验证。

收尾静态检查曾发现新夹具常量放在第三方import前触发Ruff E402；已移动到所有import之后，最终Ruff通过。提交准备脚本随后因manifest未生成而停止，未产生误提交；已修正顺序。81项运行在常量搬移后的功能版本，最后仅调整该常量的模块声明位置。


## Git字节边界：发布前发现并根治，不改gold

ROOT在正常推送期间独立核验Git实际blob，发现作者两观察fixture在Windows工作区为CRLF且SHA符合manifest，Git却已规范为LF（189/59处换行），Linux CI必将失败。已停止唯一owned push runner PID22016，所属Windows Job退出清理；ls-remote确认远端仍a89467b0，未发布这个已知问题，未跳hook。取消收据明确NOT_CAPTURED，不伪造未完成的test结果。

根因属于版本传输层：工作区测试没有覆盖clean filter→index→另一平台checkout。新增独立tmp Git repo测试先2RED/1PASS，统一PWF fixtures字节证据规则后84PASS；最终加有/无规则、true/input/false和Linux式checkout共6控制，加原组件共87PASS/4.58s。不改任何manifest/gold/原件；只定点renormalize这三份fixture，actual index blob已符合原SHA。

.gitattributes按目录角色统一`/docs/plans/**/fixtures/** -text -diff -eol`，复用现有evidence原始字节职责，不新增逐公司/文件白名单。单纯-text保存CRLF后diff --check把原始CR视为空白错误（已实际观察）；故raw fixture按二进制证据diff对待，SHA/JSON语义/真实Git往返测试继续检查，源码和测试的diff/lint规则不变。未对其他历史fixture批量renormalize。后续TABLE/STATE接收同样必须先核实际blob对manifest，若作者Git已转换要从其已验SHA原始观察恢复，不能改gold迎合坏blob。

独审已独立确认两组工作区/坏blob SHA，并认可通用fixtures角色规则设计；没有冒充重新执行ROOT新Git矩阵，具体证据分开记录。ROOT最终Git矩阵最后删除了一次冗余的同平台checkout，只留新目录的Linux式实际checkout；最终正常prepush会执行该文件最终版本。
