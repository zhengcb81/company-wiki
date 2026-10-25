# PDF-C2：来源路由、慢路径与按需结构增强

状态：IN_PROGRESS。基线6c83cb43；沿用已有PDF-C2实施细则，不重做C1，不写W19/作者工区、Dayu/IQS或RF运行WIP。

## 本轮顺序与验收

1. **先定位，避免整批重跑：** 半年报旧900秒与ROOT120秒不同，不能判回归。分别记录原件读取、native观察/选择、production compile阶段耗时；一次受界真实剖析，保存紧凑热点/最后阶段，不重复全量。DOCX用同字节、真实MIME/不同业务kind的中性输入复现语言检测路由。
2. **TDD根修：** 载体由字节/MIME/规范化层负责，业务kind不能把ZIP当UTF-8；同一文档读取结果可复用，保留语言/来源验真，不用公司名特例。耗时问题按热点修共享算法，保持预算和内容断言，不靠提高timeout/cap。
3. **C2单层接线：** 通用缺口分诊、严格native成员对齐，原生一次读取、现有continuity到实际summary task；限页/资源的按需增强在PdfReading职责内，外部SDK/参数不泄露给AUTO/FF/RF。
4. **集中验收与独审：** 中性反例与调用者定向包、单源真实失败复现/修后检查，原件与生产配置不变、测试目录恢复。独立agent审完整增量和真实收据，修本范围问题后正常提交推送，核精确CI。

## 不变边界

复用现有WorkBudget、deadline、generation/cache与原始span/locator；不另建任务/权限库，不复制PDF→全文MD，不强制读取历史三表。W18已暴露，回放只作为回归；正式摘要语义、缓存恢复和RF采用仍由C3验收。C2完整细则见../pdf-parser-reuse-pilot-20261025/implementation.md。

## 当前证据

W18候选4源中HK PDF/US HTML可编译，CN H1超时，DOCX语言提取失败。薄回放先跑默认0.8 native observation再跑0.9/v4 compile，120秒是两段总上限；必须分段归因，不能当生产单次耗时。当前独立审查先只读核DOCX共因及单层设计；ROOT负责代码与定点实验。

## 根因定位（源码修改前）

- DOCX：独审实读47,403B原件（65305c…），normalize 0.035秒/250正文unit，唯一缺口docx_header_footer_not_parsed。旧默认语言函数把任何structure.errors当全文失败；显式Normalization已有正确行为。中性中英文DOCX含header两项真RED，统一owner后语言＋DOCX包30P（0.92秒）。不是kind/目录路由故障，不修错误假设。
- H1：当前PdfReading 0.9，16M同账户，read3.639s/6830unit/671955work，select16.935s/112spans/15260630work，partial。含cProfile采样开销，不与未剖析运行计算加速比。旧0.8单源剖析95秒停，最后92.32秒在reading_select，853次栈样本落_minimal_matching_unit_windows，重复前缀regex/枚举为热点。原W18先隐式0.8诊断再0.9compile，120秒上限不能代表生产一次读取；优先修版本/观察入口，而不盲改退役算法或提高cap。
- 旧profile父runner在TimeoutExpired拼接str/bytes时报TypeError，live栈收据仍保存；记录失败，不重复95秒运行。后续runner统一处理stdout类型。

根修实施补充：DU-BENCH观察增加显式selector版本，当前PDF走同PdfReading与配置WorkBudget/context；W18传当前请求版本，旧冻结producer接口没有此能力时明确保留历史版本，记录实际路径而非默认常量充当执行证明。phase耗时和异常保留，不引入新状态/评分框架。新旧oracle不混算收益。

## 根修实施/集中工程节点

DOCX不再有两套默认/显式解析错误策略；build_batch_events增加可选Normalization参数，configured_preview将已创建的配置owner下传，避免OCR/期限配置丢失；语言判定成功不抹去原partial。观察器显式接selector，.9 PDF调用唯一PdfReading+同预算/阅读意图；W18记录actual/旧API回退和阶段耗时。合法native_range先由owner原成员重放验证再观察，解决旧单locator映射漏记，未认证span不补造证据。

TDD：语言2真RED→30P；观察3真RED（前一轮2个沙箱tmp ERROR不计真RED，短自有根纠正后3FAIL）；配置owner端口1真RED→32P/4.59s。全W18＋du11_production153P/51.96s；range/replay58P/8.20s、首48P/2.15s有重叠，不相加。Ruff绿。旧95秒legacy剖析只跑一次，日志父进程str/bytes故障留证，未反复整批。

当前等待本节点独审，随后正常提交冻结、只对H1和DOCX各做一次120秒同cap真实回归。这是C2前置来源根修，不宣称Docling按需增强/实际任务完整闭包已交付；C2主体与C3仍OPEN。

根修独立终审PASS_ROOTFIX_ENGINEERING_ONLY，0 OPEN：68P/9.19秒，额外默认版本/owner材料拒绝/零预算/TypeError不重试四反例通过，7份源码测试LF SHA绑定。首次独审stdout GBK解码失败（原测试退出0），显式UTF8后保留有效收据，不记作产品失败。全src mypy376与Ruff绿。正常提交后再执行两源真实回归；C2增强仍OPEN。
