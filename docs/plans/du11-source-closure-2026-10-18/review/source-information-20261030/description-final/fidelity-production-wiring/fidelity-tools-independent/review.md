# M4验收工具独立审查

范围仅phase_c_runner/phase_c_observer及两个相关测试文件，当前四文件绑定见seal.json。结论 **PASS_SCOPED_TEST_TOOL_ENGINEERING，0 OPEN**。

发现并修复一项P1：原消费者验收比较摘要正文和来源上下文，却没有检查新增summary_assessment，RF丢弃或篡改质量观察仍可能被称为完整上下文通过。现在只要正式bundle存在该字段，RF结果必须保留且逐值一致；新永久正例、删除反例、伪semantic verified反例覆盖。此处只验证传递，不复制来源/语义算法。

其余核查：/6显式选入而默认/4保持；/7 observer从同一协议owner取marker40并要求全量实际material，合法strict subset也拒绝。未知财年但已有精确SourceRef走正式RF注册原件入口，不造年份、不改为latest、不重新下载；FF记录NOT_REQUESTED而没有伪造成功exit/receipt。已知期次的旧FF链保留。注册读失败立即失败，不擅自发现替代原件，子进程保持禁止联网。

实际短测 **30 passed / 2 deselected，5.09秒**，ruff四路径通过。两项既有localhost HTTP测留ROOT宿主运行，未删断言、未改超时。新增永久负对照包括合法subset、新观察丢失/篡改和注册来源失败不走fallback。

本节点未调用模型、未下载、未运行作者脚本/整批HTTP。**不签真实摘要、真实缓存恢复、安装副本、RF参数/公式实际采用或全仓CI**；这些由ROOT继续实测。


## ROOT实际run准备后的补查（本段为最新）

ROOT指出CLI允许/6但内部reading_projection_for仍只接收旧版本，已经从共享FIDELITY_SCOPED扩展明确/6，新增永久测试直接调用真实resolver而非仅测argparse。旧selector0.8仍返回None，默认/4保持。

进一步检查成功观察器，发现它会将真正assessment当旧extractive report读取plan_sha256，并且/6缺失report时未拒绝。现按显式协议区分：/6必须有正式assessment；缺失或旧extractive不能冒充。输出单列summary_assessment_observation，source_card_execution为空，不伪造来源卡片报告或语义验收；semantic/subfact仍not_evaluated，带实际report SHA和原生receipt来源。

留存TDD：resolver ValueError、缺assessment未拒绝；首轮有一项测试误取DTO不存在execution_report属性，已纠正夹具为正式bundle所持assessment，再单跑复现真正plan_sha256 KeyError。测试夹具错误没有冒充生产问题。见followup-red.log及followup-red2.log。

最新固定短测 **34 passed / 2既有HTTP deselected / 4.96秒**，四路径ruff PASS，0 OPEN；此前30项不与此相加。最新seal.json已重绑四路径。仍不签付费模型、完整run_pair、真实缓存、RF实际参数采用或全仓CI。


## 真实v1消费者DTO失败后的补查（最新）

ROOT实际/6摘要、恢复和缓存已执行，消费者却因download_events mismatch失败。**该v1 overall/receipt的FAIL原样保留，本补查不改为PASS、不重跑付费模型。** 根因是本工具注册candidate把下载次数误写为事件列表[]，RF契约要求exact int0；之前mock只认可步骤顺序而未验证这个DTO字段，独审漏掉了跨仓边界形状。

已改为整数0，并在所有注册消费mock边界锁定type is int及value0，不能再宽松接受任意shape。先复现4RED/2P，修后固定短域 **34P / 2既有HTTP deselected / 4.13秒**；四路径ruff PASS。不是通过修改RF生产验证器放宽契约。

另用实际runner生成的candidate与保存的真实M1来源manifest/ref调用RF现有company_wiki_source_v2._validate_candidate（无原件打开）：整数0通过，[]、False、字符串0、浮点0.0、None和整数1均拒绝，7次纯边界验证。见actual_rf_candidate_probe.py、actual-rf-candidate.json及日志。它不是RF真实reader/模型采用验收，真实原件和正式摘要的0paid consumer replay由ROOT继续。

最新四文件seal已刷新；0 OPEN限于本工具工程范围。先前34P/4.96秒和30P/5.09秒不与本次相加。
