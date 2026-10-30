# M5-B 新模板quote-primary选择独审

结论：**INDEPENDENT_PASS_NEW_RAW_TEMPLATE_POLICY_ONLY，范围内0 OPEN**。作者两文件SHA到位后才执行；未跑未封WIP，也未修改任何产品/作者测试/母计划。

最终 **38P / 0F / 0skip / 4.38秒**（15独立中性case＋作者23项独立重跑，含3种实际持久fixture的冻结恢复模式）。ruff作者两路径通过，源码/测试raw和LF SHA在独审前后稳定；AST核对只有prepare_official_narrative_request函数改变，其外整个模块与HEAD一致。作者65P另报，不与本次相加。

验证新模板条件完全有限：显式selector0.9、projection字段缺省、sources/items成员均不存在时，才注入现存/5。P1/P2/P4保留配置model/provider/pricing及额度；显式/4、/5、/6、/7尊重；null/invalid继续原validator拒绝，不替caller修意图。旧完整raw DTO即使没projection仍保持None、canonical DTO/request SHA/input hash不变；schema1/2直接解析继续有效/4。实际冻结fixture恢复检查原run/jobs/budget/request不变、无新增attempt，不是只比较一个字符串。generator imports只消费一次、输入字典不改。

**这不是全局默认切换。** 实现位于CWP官方来源的新raw模板composition层，确实不是仅改benchmark；但现CLI读取保存JSON直接from_dict、generation unset和benchmark显式缺省/4都不变。完整DTO、没有显式shared selector的模板、绕过builder的消费者都不会获得新/5。schema2 builder能力没有扩展；不能把已有projected解析恢复或其他调用者自动签成已迁移。已有完整request要换recipe仍应显式新请求/新run，不能重写旧generation。CodeGraph无静态resolved callers不足以证明没有局部import调用，已读实际CLI与已知benchmark入口核对责任边界。

独立探针初轮12F/3P是我自己的synthetic Ref用了非canonical source_id，而CWP DTO要求SHA派生ID。已只纠正独立夹具为合法canonical ID，不改产品边界；日志保留且不冒称生产RED。

当前基线为8b939b9c，ROOT已报告精确CI41064827392成功；旧41056460382是历史失败，不再误当当前主线。该CI不代签尚未提交的本M5变更。原件/config/费用未动、0模型/下载/原件解析；本独审两个临时basetemp均验证在工作区内后清除，见cleanup.json。

真实quote内容、跨市场holdout、RF实际采用及整个公司循环仍由ROOT继续，不由本policy工程签认。当前两文件SHA见seal.json，写后再次一致。
