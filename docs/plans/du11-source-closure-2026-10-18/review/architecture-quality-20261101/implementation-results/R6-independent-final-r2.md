# R6-r2 最终定点独审 — 语义返修与异常传播PASS

**结论：本次R6-r2定点范围 PASS；原 R6-A-01 的并列补语共因在本轮范围闭合，未发现新增实质P1/P2。** ROOT可据此冻结候选、推进精确CI。此结论不签完整候选CI、真实H1、摘要/持久恢复/RF采用，也不重新签W23。

工区 `C:/Users/郑曾波/Projects/company-wiki/tmp/architecture-r2`，基线 `718fced8d0cc5b15fc9eb144982b627086eaf348`。审查者 `/root/rectification_review_a` 未参与本次返修。绑定作者 **6源＋1新语义测试的7个SHA**，再绑定ROOT **4个异常源文件＋1新测试**，合计12文件；全部与首读freeze一致，执行后未变。同名JSON保存源码身份、独立复现程序、JUnit及作者历史8份receipt的实际SHA核对。

旧 `R6-independent-final.md/json` 的NEEDS_ROOT_FIX和旧2RED原样保留；本报告是新源码的新结论，不覆盖历史。

## 独立22例：22P / 0F，16.84s

正常获准host Python，短自有tmp，无真实文档、LLM/OCR或网络调用。没有重跑322/746、上一轮CI诊断17或W23。

- **原具体业务＋抽象目标**：重开病房/创造价值双序、诊疗/价值、and/or/but及嵌套help→treat均保留support/relevant；原3句不再被最后value吞掉，未制造typed fact。
- **中文governor**：努力/争取、而且/或者及双序保留具体业务；静态检查确认lexer只提供瞬态切词边界，不改字典/POS或原文；作者保存的名词化反控未在本次另做全组重跑。
- **归属边界**：direct product relative（供软件、处理客户订单）保留；`for customers whose products process orders`不得给纯goal捐typed proof。独立另加“beneficiary relative后，but we reopen neonatal wards”的新矩阵边界，也保留具体原话。
- **量目标**：direct `serve 1200 customers`仍unresolved+relevant、reason为source_goal_quantity_unresolved，没有quantity/metric-change/current-state事实；one vision及PP里的300 customers保持负例。
- **原普通typed路径**：把POS入口替换为会失败的探针，普通软件处理订单仍support且原typed fact成立，证明未把所有typed句都拖进POS。
- **能力缺失与局部继续**：实际公开selector在goal的EN资源缺失时partial、processing_complete=False，健康独立typed scope仍输出，诊断理由保留。未mock私有validation。
- **准备复用**：direct quantity名词角色callback只观察一次，传入customers，不重复数字转换或借它生成数量；同prepared scope复用。
- **真实recipe**：新增 `statement_grammar/predicate_arguments.py`在PDF、非PDF两条实际AST闭包中，hash等于真实规范化字节；内存扰动该模块的读取字节，两条recipe均改变，无物理源码改动。
- **ROOT四种异常**：caller/select/summary/verify四个contextlib scope均保留原异常实例、code、outcome、原cause、traceback与cleanup，未出现FrozenInstanceError。

22例的具体文本、断言、逐例结果在JSON。2条第三方jieba/pkg_resources弃用warning不影响结果，不将其伪称为源码缺陷。作者322P/15.65s作为其receipt保留，独审没有把22P累加成新的全域测试数。

## 语义根修判断

旧实现把整个tagged后串最后一个VB之后的名词当成全句补语；新纯 `PredicateArgumentScope` 前向观察各谓语的直接NP、量词、修饰语及attachment。EN按POS CC、CN按c处理协调关系，没有按and单词、reopen/treat或公司/行业列举补丁。直接产品relative可消费自己的补语，受益者PP及其relative不参与发行人目标的direct补语判定。消费者使用scope而非全文名词投票。

原whole-clause typed witness在goal处先完成attachment绑定，再供fact/passsage复用；不会仅因受益者relative包含typed功能就让整个抽象goal走原快通道。普通非goal typed句仍不要求POS。删除原整句 `_VAGUE_OBJECTIVE` 否决，有限的goal/vision/程度/修辞形态归回既有abstract argument owner，未知技术NP修饰语保留。

direct量词仅供“这个名词是原文direct经营角色”的观察，完整数值/单位/期间/是否实现仍归原metric owner。本轮检查了原话unresolved保留与错误数量证明被拒的边界；不把source readability提升成已实现经营事实。

成本仍为既有 **16M/112、4096字符/1024tokens、POS32n+1、SourcePassage36n**。目标的新增一次POS/补语观察有实际工作成本；prepared语法与callback缓存共享，未增加全局额度或另一个身份/许可系统。新模块是有界语法观察器，不能据此宣称覆盖所有依存语义；真实H1召回/耗时仍OPEN。本次16.84s也不是性能无退化证明。

## ROOT异常传播修复判断

对4文件的diff只有Exception类装饰器 **`@dataclass(frozen=True)`→`@dataclass`**。没有把配置、limits、source值或HandlerMetrics改成可变，没有改变预算/模型调用、catch分类、重试或失败结果逻辑。caller原 `__post_init__` 的finish/status/content-byte/provider-code等字段校验保留。

Python异常对象必须允许contextlib写回 `__traceback__` 等协议字段；对Exception冻结导致错误恢复期间抛FrozenInstanceError、遮蔽原存储异常。修复直接落在这4种异常载体，不放宽原子写或付费门限。独立4例真实contextmanager传播验证了原code/cause/trace可见，而非只检查一个装饰器字符串。

## 清理与后续界限

所有新测试材料只在 `C:/Users/郑曾波/Projects/company-wiki/tmp/a7`，basetemp长43、无重定位，最后恢复初始不存在；JUnit与复现代码以文本留JSON，没有资料/源码副本遗留。作者12个冻结文件SHA前后不变，旧历史receipt也未改。未改Git、源码/测试、主PWF、生产配置/DB或模型资源。

**PASS并STOP。** ROOT下一责任是冻结真实版本、运行候选精确CI并收口PWF；本独审不提前签完整CI、真实公司链或项目目标完成。
