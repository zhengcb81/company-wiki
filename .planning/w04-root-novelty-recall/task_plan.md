# ROOT W04：完整事实覆盖与保守软冗余排序

状态：下一实施包，位于现FF/CWP跨期修复之后、G2摘要之前。实施树为保留的 `C:/Users/郑曾波/.codex/worktrees/m3-acceptance-20261010/company-wiki`，该树已有330集中测试通过的未提交selector0.8实现，不能清空或重做。ROOT负责并线发布；来源scope作者、FF工具作者不写本包文件。

## 已证实问题及验收事实

1. 当前文字shingle丢独立数字，300/500会得到相同tokens；min集合50%重叠的软重复排序排在新阶段/score之前，压制新数量与阶段。330测试中的手造tokens没有覆盖实际tokenizer→完整group→budget链。
2. 原精确年报三组未选仍是FAIL。另处“薄膜设备总量突破300”不能替代“LPCVD设备累计出货突破三百反应台”。原文“部分新型设备重复订单”不能扩写成LPCVD专属重复订单。
3. PRISMO47交付进行生产验证与56验证通过、4反应腔、6/8英寸切换包含不同业务事实，不能为腾预算把后一组当重复。

不改96年报cap、现有IPO160cap、whole-group真实span成本、原文字节、默认legacy和六份0.7.1完整package hash。纯soft排序，不删除原候选；不加LLM、事实库、配置许可、人工签收。

## 三个大节点

- [ ] A：先写真实tokenizer/公开finalizer行为RED：中文/英文数字、小数/range/百分比与主体不同；计划/进行验证/验证通过/否定/订单阶段不同；短subset/长组新事实；相同完整内容只有排版变化的重复正控。复用已有stage predicate，不为公司/页码特判。
- [ ] B：共用有界完整group signature，按native coordinates而非locator字符串或逐span独立提取。保留数值和主体/谓词状态的保护信号；高对称重叠且无新保护信号才软降级。截断或无法绑定主体时不冒重复。0.8独有，旧调用默认legacy。一次集中330既有+新增必要测试、类型/lint；真正新事实不被旧词汇重叠压制。
- [ ] C：新唯一stem真实六原件一次解析/回放；冻结SHA/config、0.7.1完整有序package、原文相等、cap、完整组、omitted partition。年报LPCVD主体数量、钨验证与重复量产订单、供应交期条件分别提供同SHA同完整组原文见证；保留PRISMO56新增事实。非作者一次大节点复核→正常commit/并线/push/CI→G2。

原精确locators断言永久保留为另栏。可接受另一处等价原文时，必须绑定同source/group的native顺序、实际locators/原文SHA及主体→数量/限定→阶段归属；跨组substring、其它型号数量、薄膜总量替代LPCVD量、计划替代完成均须拒绝。固定检查点不允许在见到新结果后偷偷降级。仍漏钨或LPCVD便记FAIL_CRITICAL_RECALL，根据真实budget诊断修共用策略后再验，不能抬cap换绿。

## 恢复与发布

测试只用独立自有tmp；真实回放不下载、不复制原件、无模型费用，保留小压缩证据。保留旧FAIL及已有WIP；把本树已与主线相同的CI选择修复按Git三方比对处理，不覆盖最新远端。共享12份PWF由ROOT引用当前状态，作者只维护本包。新分包前必须重新定义排他写集。

Next Step：完成FF CaseSpec/生产scope的原41联调接收，随后在原ROOT selector树固定上述行为RED并实施。
