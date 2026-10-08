# MAIN R6格式主线接线

状态：MAIN共用接线及集中258责任测试、37实际资料链集成已通过；图片识读缺口和最终真实研究保持待做。

## 责任与接口

1. SourceVersionReader验证当前SourceRef原文；不新增公司/期间/旧policy许可。生成任务使用冻结source_metadata作为处理输入，当前诊断不重签旧账。
2. 纯normalize_document负责HTML/PPTX结构、稳定locator、财务表启发式与具名opaque缺口；只在内存工作。
3. NarrativeSelectHandler统一路由PDF/HTML/PPTX，调用现有selector；金融表数值排除，表内具体业务描述保留，原语言填入selected spans；图片页不能记为成功跳过。
4. 现有NarrativeVerifyHandler/Transport按MIME与parser版本走同一回放层；HTML/PPTX全部选中locator仅重解析一次，按locator+字节绑定+结构匹配，不能每span全文parse。禁止新数据库、全文MD或图片落地。
5. parser/selector执行版本在新格式run中明确冻结；老PDF/TXT版本与旧run保持兼容，新解析器不冒充旧parser。
6. batch语言判定从格式正文提取；全图PPTX返回具名无法识读/语言未知缺口，不猜语言、不启动无配置的视觉或收费模型。视觉/OCR能力另按既有配置和预算调查。

## TDD与集中验收

先实际select→原语言summary依赖→verify测试HTML/XHTML/有文本PPTX、业务表保留/财务数值排除、坏包/全图不自动skip、locator或parser冒用拒绝、多span只parse1次。随后64格式责任集、相关select/verify/transport/batch语言/版本集成一次集中验收；只读真实SEC10-K和真实22页图片deck补验，原件SHA不变、临时资料清理。不是每次修改跑全部公司或增加人工签收。最后两组完整真实研究按总计划大节点验收。

## 当前并线状态

FF已推main a1f3e4f；RF main b1763fc0并线，静态7项修复17fce29c发布中；CWP格式包已merge master。主目录RF assurance/output和FF密钥保留；Dayu零写。


## MAIN接线节点完成

- 三包已并各自主线；FF main a1f3e4f18bf644c6af668fddc009cacdf1aace20已推送且CI37847921596成功；RF main17fce29cbed65e839484b1df4c0c9ecf58aa51e7已推送且CI37848277872成功。CWP格式接线dbffc282已提交/推送，CI37849838844成功。
- 新格式路由、原语言、财务cell筛选、parser版本与batch生成identity、select/verify/公共transport共享回放均完成。一次解析回放所有选中locator，无全文MD/图片持久化。PDF/TXT普通batch的生成hash不因新解析器版本漂移；格式batch显式冻结document_normalization版本。
- 258项集中责任测试PASS/34.48秒；37项实际catalog→AUTO→3任务→projector→public read集成PASS/47.16秒，包含真实微软8,158,067B SEC HTML（SHA99d693f6...0bbe）；只有模型是本地ReplayNarrativeModel，无外部付费调用，不能据此签模型摘要经济语义正确。
- FF→CWP离线诊断25/25PASS，报告r6_ff_main_cause_e2e.json；脚本覆盖的一份工程报告已恢复原提交字节，其临时根确认不存在。FF→ET→CWP旧冻结契约仍PASS，新真实电话会账户entitlement限制保留。
- 实际补充发现capture争议未清空对应document列，已用共用字段alias投影修复，unknown种类按unknown处理；Worker不再比较当前kind与历史生成kind作为准入。原version/hash/byte-size/MIME绑定和locator仍保留。
- 全量CI unit现有范围2120PASS/4旧争议门FAIL，唯一4项已在上述258集中中全部通过；当前不逐修改重跑全部unit，发布后监控同一CI。4unit旧许可合同21RED→99PASS已在前提交关闭。
- 本轮清理6个owned根，释放141,697,363B，全部恢复不存在，原件/生产配置/外包工作树删除0。ruff现有CIscope和新格式测试绿，mypy五接线模块绿。

## 仍待MAIN完成

1. CWP失败边界发布有证明的provider原因、started/usage字段；FF/RF消费，unknown不可猜为0。
2. RF安装闭包定点同步、真实NarrativeRef→claim→参数消费；重做第一组三公司真实研究和独立审查。
3. 真实图片deck22页仍opaque，尚无配置可用OCR/vision正文识读；不要把named incomplete算成功skip。继续按已配置模型能力和预算调查，不硬编码供应商。
4. 现有AUTO/内容寻址对象实现跨run默认复用及显式refresh；保留原事件与费用账，不加第二数据库或人工许可。
5. 换A/H/US三家固定新样本真实执行、逐家独立审查与后续根因循环。


## 发布后回放检查

CWP dbffc282已推master，CI37849838844成功；真实HTML full检查从BLOCKED改善为PASS。有文本PPTX资料链已通过；真实22页全图仍无正文。新增CLI闭集语言原因和format探针具名BLOCKED分类，52责任测试通过，坏字节/任意异常不豁免，新的冻结回放待提交后执行。主线查收、安装和其他仓问题统一见[r6_handoff_intake.md](r6_handoff_intake.md)。


最终发布d41edbba CI37852832070成功；完整回放真实HTML PASS、有文本PPTX责任链绿、真实22页全图PPTX有字节/结构证明的PARSER_INCOMPLETE→BLOCKED，无模型/产物。此格式接线节点已完成，OCR/vision能力仍归后续；接口总记录r6_handoff_intake.md。
