# M2：原生匿名发言轮次与跨载体阅读

状态：实施中，尚未验收。承接remaining_root_causes的M2，不代替M1源侧校准、annual14剩余问题或正式摘要/RF循环。

## 当前实施与真实检查（2026-10-24补记）

- M1已由独立源专家接受，51事实/139锚点/102P，报告在m1-independent。四份新gold是开发回归集，旧版不改，不称新holdout。
- DOCX1.2、TXT0.4复用同一原生标签观察和原事件流；旧1.0/1.1及TXT0.3.1回放保持。anonymous标签只证明轮次，不证明公司身份；正文结束、空标题/表格、新实名speaker都终止继承。不同source与同actor空白变体不能凑成电话会。
- 定性经营意图使用同一source语义owner的marker→action→宾语中心词语法。更新产品与更新“产品培训手册”不同；动作不能被连接token吞掉。新增扫描预扣原WorkBudget，未提高限额。
- 原生相邻同turn中的明确计划限定，作为语义内在约束进入既有local dependency/component/envelope，保留原始跨度；未知角色不升issuer。限定须进入citation_support_views和实际source card，只有context链接不足。跨speaker/其他公司的计划/员工计划不能混入。
- 实际select→DTO JSON往返→model-input/5→extractive source card测试覆盖两载体、中文、未知身份；新版本还需经过实际batch options→worker normalization构造与原文replay，不以默认normalize单测代替。
- 独审首次发现的边界、词法、worker pin及限定漏传问题均在原责任层修复；失败XML保留。530相关P/11skip、374文件mypy零错、Ruff通过是中间版本证据，最终须绑定最终源码。
- 真实Gbits阶段观察19→23，新增经营计划段5/6/16/89原文精确对应，ASR歧义不改，原件SHA不变；oldgold仍FAIL。晚于该观察的修复须新目录重新回放，不能覆盖旧观察或把它当最终摘要验收。

## 已证实的根因

吉比特原件是DOCX，首段为财报交流会标题，后续有“说话人1 00:00”等原生转写标签，回答延续到多个无标签段落。当前DOCX仅识别问/答前缀；speaker时间戳与延续没有进入原生观察。collector本来只消费native carrier，不能在collector再全文搜索。真实0.9有116段、97段因无经营信号拒绝；只有19段入选，不能将缺陷全部归咎路由。晚段计划/不确定性还要由共用语义/局部依赖修复。

## 层与接口

1. 共享纯文本标签观察：只读取开头有界label+有效时间戳，保留原文与label/时间戳；匿名speaker角色unknown。仅有数字编号不推公司、分析师、CEO或管理层身份，不把ASR纠正为强断言。
2. DOCX/TXT载体各在自己的原生读取过程中消费同一观察，记录来源内稳定turn ID及连续段落；表格、真实标题、新speaker是边界。DOCX locator/原文不变。现模型及业务语义不在这里实现。
3. observation adapter仅投影已观察speaker/turn；native bridge向既有collector发carrier，collector不解析新全文。中文财报交流会类型须有实际多speaker轮次佐证；只有标题、相同speaker重复或普通文章提及不得冒充电话会。
4. 结构/选材按既有有界接口保留后续回答及条件，不能全turn无限合并、不能从邻近提问借数字、不能抬96/48K/16M或8/4/2048。未知机构角色保持unknown，仍可读取其中有来源的业务描述。

## 版本与测试

DOCX新版本与TXT新版本显式区分已保存解析语义，旧版本保持可回放；不能以旧缓存证明新版本完成。先写跨载体、匿名unknown、连续段/边界、标题与文章负例、source locator/replay反例，再实施。旧版本字节/指纹及既有真实TXT不得回退。大节点相关测试和独立审查后发布；匿名轮次接通不代表经营选材质量已验收。

M1作者独占m1-source-checkpoints；ROOT不写该目录。独审由未参与实现者执行。W13–W15/Dayu/IQS范围不改；原件/旧gold/模型费用账不动。路径查询失败已纠正为先CodeGraph定位再读文件，不将猜错路径当产品缺陷。
